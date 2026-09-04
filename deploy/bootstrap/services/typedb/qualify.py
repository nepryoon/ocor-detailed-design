#!/usr/bin/env python3
"""Fail-closed qualification for the digest-pinned local TypeDB service."""

from __future__ import annotations

import argparse
import json
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Sequence
from pathlib import Path
from typing import Any


DEFAULT_CONTAINER = "ocor-bootstrap-typedb-1"
DEFAULT_HTTP_URL = "http://127.0.0.1:8000"
DEFAULT_GRPC_HOST = "127.0.0.1"
DEFAULT_GRPC_PORT = 1729
DIGEST_IMAGE = re.compile(r"^typedb/typedb@sha256:[0-9a-f]{64}$")


class QualificationError(RuntimeError):
    """A mandatory TypeDB qualification control failed."""


def validate_lock(lock: dict[str, Any]) -> dict[str, Any]:
    matches = [item for item in lock.get("services", []) if item.get("id") == "typedb"]
    if len(matches) != 1:
        raise QualificationError("service lock must contain exactly one typedb entry")
    entry = matches[0]
    if not DIGEST_IMAGE.fullmatch(str(entry.get("image", ""))):
        raise QualificationError("TypeDB image is not digest-pinned")
    if entry.get("official_source") is not True:
        raise QualificationError("TypeDB artifact is not marked as an official source")
    if entry.get("source") != "https://hub.docker.com/r/typedb/typedb":
        raise QualificationError("TypeDB source is not the approved official registry")
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", str(entry.get("version", ""))):
        raise QualificationError("TypeDB lock has no exact semantic version")
    if entry.get("license") != "MPL-2.0":
        raise QualificationError("TypeDB license metadata mismatch")
    return entry


def validate_inspection(inspection: dict[str, Any], expected_image: str) -> dict[str, Any]:
    configured_image = inspection.get("Config", {}).get("Image")
    if configured_image != expected_image:
        raise QualificationError("running TypeDB image differs from the exact service lock")
    state = inspection.get("State", {})
    if state.get("Running") is not True:
        raise QualificationError("TypeDB container is not running")
    if state.get("Health", {}).get("Status") != "healthy":
        raise QualificationError("TypeDB container is not healthy")
    ports = inspection.get("NetworkSettings", {}).get("Ports", {})
    observed: dict[str, str] = {}
    for container_port in ("1729/tcp", "8000/tcp"):
        bindings = ports.get(container_port)
        if not isinstance(bindings, list) or len(bindings) != 1:
            raise QualificationError(f"TypeDB {container_port} must have exactly one binding")
        binding = bindings[0]
        if binding.get("HostIp") != "127.0.0.1":
            raise QualificationError(f"TypeDB {container_port} is not loopback-only")
        observed[container_port] = str(binding.get("HostPort", ""))
    if observed != {"1729/tcp": "1729", "8000/tcp": "8000"}:
        raise QualificationError("TypeDB published ports differ from the approved profile")
    return {"configured_image": configured_image, "ports": observed, "health": "healthy"}


def validate_http_observations(
    *,
    health_status: int,
    version_status: int,
    version_body: str,
    unauth_status: int,
    unauth_body: str,
    expected_version: str,
) -> dict[str, Any]:
    try:
        version = json.loads(version_body)
        unauth = json.loads(unauth_body)
    except json.JSONDecodeError as exc:
        raise QualificationError(f"TypeDB returned invalid JSON: {exc}") from exc
    if health_status != 204:
        raise QualificationError(f"TypeDB health endpoint returned {health_status}, expected 204")
    if version_status != 200:
        raise QualificationError(f"TypeDB version endpoint returned {version_status}, expected 200")
    if version != {"distribution": "TypeDB CE", "version": expected_version}:
        raise QualificationError("TypeDB distribution or version does not match the lock")
    if unauth_status != 401 or unauth.get("code") != "AUT2":
        raise QualificationError("unauthenticated TypeDB database access did not fail closed")
    return {
        "distribution": version["distribution"],
        "version": version["version"],
        "health_status": health_status,
        "unauthenticated_database_access": "FAIL_CLOSED",
    }


def run(command: Sequence[str], timeout: float = 20.0) -> str:
    try:
        completed = subprocess.run(
            list(command), check=True, capture_output=True, text=True, timeout=timeout
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise QualificationError(f"command failed: {' '.join(command)}: {exc}") from exc
    return completed.stdout


def http_get(url: str, timeout: float = 3.0) -> tuple[int, str]:
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def probe_protocol(http_url: str, grpc_host: str, grpc_port: int) -> dict[str, Any]:
    try:
        with socket.create_connection((grpc_host, grpc_port), timeout=3.0):
            pass
    except OSError as exc:
        raise QualificationError(f"TypeDB gRPC endpoint is unavailable: {exc}") from exc
    health_status, health_body = http_get(f"{http_url}/health")
    version_status, version_body = http_get(f"{http_url}/v1/version")
    unauth_status, unauth_body = http_get(f"{http_url}/v1/databases")
    return {
        "grpc_tcp": "READY",
        "health_status": health_status,
        "health_body": health_body,
        "version_status": version_status,
        "version_body": version_body,
        "unauth_status": unauth_status,
        "unauth_body": unauth_body,
    }


def inspect_container(container: str) -> dict[str, Any]:
    payload = json.loads(run(["docker", "inspect", container]))
    if not isinstance(payload, list) or len(payload) != 1:
        raise QualificationError("docker inspect returned an unexpected container set")
    return payload[0]


def wait_for_protocol(
    http_url: str, grpc_host: str, grpc_port: int, *, timeout: float = 45.0
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last_error = "not attempted"
    while time.monotonic() < deadline:
        try:
            return probe_protocol(http_url, grpc_host, grpc_port)
        except (OSError, QualificationError, urllib.error.URLError) as exc:
            last_error = str(exc)
            time.sleep(0.5)
    raise QualificationError(f"TypeDB did not recover within {timeout:.0f}s: {last_error}")


def wait_for_healthy(container: str, *, timeout: float = 45.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last_status = "unknown"
    while time.monotonic() < deadline:
        inspection = inspect_container(container)
        last_status = str(inspection.get("State", {}).get("Health", {}).get("Status"))
        if inspection.get("State", {}).get("Running") is True and last_status == "healthy":
            return inspection
        time.sleep(0.5)
    raise QualificationError(
        f"TypeDB Docker health did not recover within {timeout:.0f}s: {last_status}"
    )


def fault_and_recover(
    container: str, http_url: str, grpc_host: str, grpc_port: int
) -> dict[str, Any]:
    paused = False
    unavailable_observed = False
    try:
        run(["docker", "pause", container])
        paused = True
        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline:
            try:
                http_get(f"{http_url}/health", timeout=0.5)
            except (OSError, urllib.error.URLError, TimeoutError):
                unavailable_observed = True
                break
            time.sleep(0.25)
        if not unavailable_observed:
            raise QualificationError("paused TypeDB was not detected unavailable")
    finally:
        if paused:
            run(["docker", "unpause", container])
    wait_for_protocol(http_url, grpc_host, grpc_port)
    run(["docker", "restart", "--time", "5", container], timeout=20.0)
    wait_for_protocol(http_url, grpc_host, grpc_port)
    wait_for_healthy(container)
    return {
        "paused_service_detected_unavailable": True,
        "unpause_recovery": "PASS",
        "restart_recovery": "PASS",
    }


def qualify(args: argparse.Namespace) -> dict[str, Any]:
    lock = json.loads(args.lock.read_text(encoding="utf-8"))
    entry = validate_lock(lock)
    inspection = validate_inspection(inspect_container(args.container), entry["image"])
    protocol = probe_protocol(args.http_url, args.grpc_host, args.grpc_port)
    http_contract = validate_http_observations(
        health_status=protocol["health_status"],
        version_status=protocol["version_status"],
        version_body=protocol["version_body"],
        unauth_status=protocol["unauth_status"],
        unauth_body=protocol["unauth_body"],
        expected_version=entry["version"],
    )
    result: dict[str, Any] = {
        "schema_version": "1.0",
        "result": "PASS",
        "service": "typedb",
        "lock": {
            "image": entry["image"],
            "version": entry["version"],
            "source": entry["source"],
            "license": entry["license"],
        },
        "runtime": inspection,
        "protocol": {"grpc_tcp": protocol["grpc_tcp"], **http_contract},
    }
    if args.fault_recovery:
        if not args.execute:
            raise QualificationError("--fault-recovery requires explicit --execute")
        result["fault_recovery"] = fault_and_recover(
            args.container, args.http_url, args.grpc_host, args.grpc_port
        )
        result["runtime_after_recovery"] = validate_inspection(
            inspect_container(args.container), entry["image"]
        )
    return result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=Path("infra/services.lock.json"))
    parser.add_argument("--container", default=DEFAULT_CONTAINER)
    parser.add_argument("--http-url", default=DEFAULT_HTTP_URL)
    parser.add_argument("--grpc-host", default=DEFAULT_GRPC_HOST)
    parser.add_argument("--grpc-port", type=int, default=DEFAULT_GRPC_PORT)
    parser.add_argument("--fault-recovery", action="store_true")
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        print(json.dumps(qualify(parse_args(argv)), indent=2, sort_keys=True))
        return 0
    except (OSError, json.JSONDecodeError, QualificationError) as exc:
        print(json.dumps({"result": "FAIL", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
