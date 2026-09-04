#!/usr/bin/env python3
"""Qualify only the digest-pinned disposable OpenBao service."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Sequence
from pathlib import Path
from typing import Any


SERVICE = "openbao"
DEFAULT_CONTAINER = "ocor-bootstrap-openbao-1"
DEFAULT_URL = "http://127.0.0.1:8200"
DIGEST_IMAGE = re.compile(r"^quay\.io/openbao/openbao@sha256:[0-9a-f]{64}$")


class QualificationError(RuntimeError):
    """A mandatory OpenBao provisioning control failed."""


def validate_lock(lock: dict[str, Any]) -> dict[str, Any]:
    entries = [item for item in lock.get("services", []) if item.get("id") == SERVICE]
    if len(entries) != 1:
        raise QualificationError("service lock must contain exactly one openbao entry")
    entry = entries[0]
    if not DIGEST_IMAGE.fullmatch(str(entry.get("image", ""))):
        raise QualificationError("OpenBao image is not digest-pinned")
    if entry.get("official_source") is not True:
        raise QualificationError("OpenBao artifact is not from an official source")
    if entry.get("source") != "https://quay.io/repository/openbao/openbao":
        raise QualificationError("OpenBao source is not the approved official registry")
    if entry.get("license") != "MPL-2.0":
        raise QualificationError("OpenBao license metadata mismatch")
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", str(entry.get("version", ""))):
        raise QualificationError("OpenBao lock has no exact semantic version")
    return entry


def validate_inspection(inspection: dict[str, Any], expected_image: str) -> dict[str, Any]:
    if inspection.get("Config", {}).get("Image") != expected_image:
        raise QualificationError("running OpenBao image differs from the exact lock")
    state = inspection.get("State", {})
    if state.get("Running") is not True:
        raise QualificationError("OpenBao container is not running")
    if state.get("Paused") is True:
        raise QualificationError("OpenBao container is paused")
    if state.get("Health", {}).get("Status") != "healthy":
        raise QualificationError("OpenBao container is not healthy")
    security_options = inspection.get("HostConfig", {}).get("SecurityOpt", []) or []
    if "no-new-privileges:true" not in security_options:
        raise QualificationError("OpenBao no-new-privileges control is absent")
    bindings = inspection.get("NetworkSettings", {}).get("Ports", {}).get("8200/tcp")
    if not isinstance(bindings, list) or len(bindings) != 1:
        raise QualificationError("OpenBao must publish exactly one API binding")
    binding = bindings[0]
    if binding.get("HostIp") != "127.0.0.1":
        raise QualificationError("OpenBao API is not loopback-only")
    if binding.get("HostPort") != "8200":
        raise QualificationError("OpenBao API host port differs from the approved profile")
    return {
        "configured_image": expected_image,
        "health": "healthy",
        "host_binding": "127.0.0.1:8200",
        "no_new_privileges": True,
    }


def validate_health(status: int, body: str, expected_version: str) -> dict[str, Any]:
    try:
        value = json.loads(body)
    except json.JSONDecodeError as exc:
        raise QualificationError("OpenBao health response is invalid JSON") from exc
    if not isinstance(value, dict):
        raise QualificationError("OpenBao health response is not an object")
    if value.get("initialized") is not True:
        raise QualificationError("OpenBao is not initialized")
    if value.get("sealed") is not False:
        raise QualificationError("OpenBao is sealed")
    if status != 200:
        raise QualificationError(f"OpenBao health returned HTTP {status}, expected 200")
    if value.get("standby") is not False:
        raise QualificationError("disposable OpenBao instance unexpectedly reports standby")
    if value.get("version") != expected_version:
        raise QualificationError("OpenBao version differs from the exact lock")
    return {
        "initialized": True,
        "seal_state": "UNSEALED",
        "standby": False,
        "version": expected_version,
    }


def validate_auth(
    *, invalid_status: int, invalid_body: str, authorized_status: int, authorized_body: str
) -> dict[str, str]:
    try:
        invalid = json.loads(invalid_body)
        authorized = json.loads(authorized_body)
    except json.JSONDecodeError as exc:
        raise QualificationError("OpenBao auth response is invalid JSON") from exc
    invalid_errors = invalid.get("errors", []) if isinstance(invalid, dict) else []
    if invalid_status != 403 or "permission denied" not in invalid_errors:
        raise QualificationError("OpenBao invalid token did not fail closed")
    if (
        authorized_status != 200
        or not isinstance(authorized, dict)
        or not isinstance(authorized.get("data"), dict)
    ):
        raise QualificationError("OpenBao authorized system API contract failed")
    return {"authorized_system_api": "PASS", "invalid_token": "FAIL_CLOSED"}


def run(command: Sequence[str], timeout: float = 20.0) -> str:
    try:
        result = subprocess.run(
            list(command), check=True, capture_output=True, text=True, timeout=timeout
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise QualificationError(f"bounded command failed: {command[0]}") from exc
    return result.stdout


def inspect_container(container: str) -> dict[str, Any]:
    try:
        result = json.loads(run(["docker", "inspect", container]))
    except json.JSONDecodeError as exc:
        raise QualificationError("docker inspect returned invalid JSON") from exc
    if not isinstance(result, list) or len(result) != 1:
        raise QualificationError("docker inspect returned an unexpected container set")
    return result[0]


def disposable_token(inspection: dict[str, Any]) -> str:
    prefix = "BAO_DEV_ROOT_TOKEN_ID="
    matches = [
        value.removeprefix(prefix)
        for value in inspection.get("Config", {}).get("Env", [])
        if isinstance(value, str) and value.startswith(prefix)
    ]
    if len(matches) != 1 or len(matches[0]) < 24:
        raise QualificationError("disposable OpenBao token is absent or malformed")
    return matches[0]


def http_get(url: str, *, token: str | None = None, timeout: float = 3.0) -> tuple[int, str]:
    headers = {"X-Vault-Token": token} if token is not None else {}
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def probe(base_url: str, token: str, expected_version: str) -> dict[str, Any]:
    health_status, health_body = http_get(f"{base_url}/v1/sys/health")
    invalid_status, invalid_body = http_get(
        f"{base_url}/v1/sys/mounts", token="ocor-deliberately-invalid-token"
    )
    authorized_status, authorized_body = http_get(f"{base_url}/v1/sys/mounts", token=token)
    return {
        "auth": validate_auth(
            invalid_status=invalid_status,
            invalid_body=invalid_body,
            authorized_status=authorized_status,
            authorized_body=authorized_body,
        ),
        "health": validate_health(health_status, health_body, expected_version),
    }


def wait_ready(
    container: str, base_url: str, token: str, expected_image: str, expected_version: str,
    *, timeout: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last_error = "not attempted"
    while time.monotonic() < deadline:
        try:
            inspection = inspect_container(container)
            runtime = validate_inspection(inspection, expected_image)
            api = probe(base_url, token, expected_version)
            return {"api": api, "runtime": runtime}
        except (OSError, urllib.error.URLError, TimeoutError, QualificationError) as exc:
            last_error = str(exc)
            time.sleep(0.5)
    raise QualificationError(f"OpenBao did not recover within {timeout:.0f}s: {last_error}")


def fault_recovery(
    container: str, base_url: str, token: str, expected_image: str, expected_version: str,
    *, timeout: float,
) -> dict[str, Any]:
    paused = False
    unavailable = False
    try:
        run(["docker", "pause", container])
        paused = True
        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline:
            try:
                http_get(f"{base_url}/v1/sys/health", timeout=0.5)
            except (OSError, urllib.error.URLError, TimeoutError):
                unavailable = True
                break
            time.sleep(0.25)
        if not unavailable:
            raise QualificationError("paused OpenBao was not detected unavailable")
    finally:
        if paused:
            run(["docker", "unpause", container])
    wait_ready(container, base_url, token, expected_image, expected_version, timeout=timeout)
    run(["docker", "restart", "--time", "5", container])
    wait_ready(container, base_url, token, expected_image, expected_version, timeout=timeout)
    return {
        "paused_service_detected_unavailable": True,
        "restart_recovery": "PASS",
        "unpause_recovery": "PASS",
    }


def qualify(args: argparse.Namespace) -> dict[str, Any]:
    lock = json.loads(args.lock.read_text(encoding="utf-8"))
    entry = validate_lock(lock)
    inspection = inspect_container(args.container)
    runtime = validate_inspection(inspection, entry["image"])
    token = disposable_token(inspection)
    api = probe(args.base_url, token, entry["version"])
    result: dict[str, Any] = {
        "api": api,
        "lock": {
            "image": entry["image"],
            "license": entry["license"],
            "source": entry["source"],
            "version": entry["version"],
        },
        "result": "PASS",
        "runtime": runtime,
        "schema_version": "1.0",
        "service": SERVICE,
    }
    if args.fault_recovery:
        if not args.execute:
            raise QualificationError("--fault-recovery requires explicit --execute")
        result["fault_recovery"] = fault_recovery(
            args.container,
            args.base_url,
            token,
            entry["image"],
            entry["version"],
            timeout=args.timeout,
        )
    return result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=Path("infra/services.lock.json"))
    parser.add_argument("--container", default=DEFAULT_CONTAINER)
    parser.add_argument("--base-url", default=DEFAULT_URL)
    parser.add_argument("--fault-recovery", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--timeout", type=float, default=45.0)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        print(json.dumps(qualify(parse_args(argv)), indent=2, sort_keys=True))
        return 0
    except (OSError, json.JSONDecodeError, urllib.error.URLError, QualificationError) as exc:
        print(json.dumps({"error": str(exc), "result": "FAIL"}, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
