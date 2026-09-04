#!/usr/bin/env python3
"""Qualify pinned disposable OPA and Keycloak without functional campaigning."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
PROJECT = "ocor-bootstrap"
REQUIRED_SERVICES = ("opa", "keycloak")
DIGEST_IMAGE = re.compile(r"^[^\s@]+@sha256:[0-9a-f]{64}$")


class QualificationError(RuntimeError):
    """A bounded, fail-closed qualification operation failed."""


def command(args: list[str], timeout: float = 10) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(args, text=True, capture_output=True, check=False, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise QualificationError(f"bounded command timeout: {args[0]}") from exc


def validate_lock(lock: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    indexed = {item.get("id"): item for item in lock.get("services", []) if isinstance(item, dict)}
    missing = sorted(set(REQUIRED_SERVICES) - set(indexed))
    if missing:
        errors.append(f"missing security services: {','.join(missing)}")
    for name in REQUIRED_SERVICES:
        item = indexed.get(name)
        if item is not None and not DIGEST_IMAGE.fullmatch(str(item.get("image", ""))):
            errors.append(f"{name} image is not digest-pinned")
    return errors


def lock_index(lock: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in lock["services"] if item.get("id") in REQUIRED_SERVICES}


def inspect_containers() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for name in REQUIRED_SERVICES:
        inspected = command(["docker", "inspect", f"{PROJECT}-{name}-1"])
        if inspected.returncode:
            result[name] = {"error": "container not found", "running": False}
            continue
        value = json.loads(inspected.stdout)[0]
        state = value.get("State", {})
        bindings = value.get("NetworkSettings", {}).get("Ports", {}) or {}
        host_ips = sorted(
            {binding.get("HostIp", "") for group in bindings.values() if group for binding in group}
        )
        result[name] = {
            "health": state.get("Health", {}).get("Status"),
            "host_ips": host_ips,
            "image": value.get("Config", {}).get("Image"),
            "paused": state.get("Paused") is True,
            "running": state.get("Running") is True,
        }
    return result


def get_json(url: str) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            if response.status != 200:
                raise QualificationError(f"HTTP {response.status}")
            value = json.loads(response.read())
            if not isinstance(value, dict):
                raise QualificationError("JSON response is not an object")
            return value
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise QualificationError(f"local API unavailable: {url}") from exc


def collect_api() -> dict[str, Any]:
    return {
        "keycloak": get_json("http://127.0.0.1:8080/realms/master/.well-known/openid-configuration"),
        "opa": {
            "data": get_json("http://127.0.0.1:8181/v1/data"),
            "health": get_json("http://127.0.0.1:8181/health"),
        },
    }


def evaluate(containers: dict[str, dict[str, Any]], api: dict[str, Any], lock: dict[str, Any]) -> list[str]:
    errors = validate_lock(lock)
    indexed = lock_index(lock)
    for name in REQUIRED_SERVICES:
        state = containers.get(name, {})
        if not state.get("running"):
            errors.append(f"{name} is not running")
        if state.get("paused"):
            errors.append(f"{name} is paused")
        if state.get("health") not in (None, "healthy"):
            errors.append(f"{name} health is not healthy")
        if name in indexed and state.get("image") != indexed[name].get("image"):
            errors.append(f"{name} image does not match lock")
        if any(address != "127.0.0.1" for address in state.get("host_ips", [])):
            errors.append(f"{name} host exposure is not loopback-only")
    if api.get("opa", {}).get("health") != {}:
        errors.append("OPA health contract failed")
    if not isinstance(api.get("opa", {}).get("data", {}).get("result"), dict):
        errors.append("OPA data API contract failed")
    issuer = "http://127.0.0.1:8080/realms/master"
    keycloak = api.get("keycloak", {})
    if keycloak.get("issuer") != issuer:
        errors.append("Keycloak issuer is not the local master realm")
    for field in ("authorization_endpoint", "token_endpoint"):
        if not str(keycloak.get(field, "")).startswith(f"{issuer}/protocol/openid-connect/"):
            errors.append(f"Keycloak {field} contract failed")
    return errors


def check(lock: dict[str, Any]) -> dict[str, Any]:
    containers = inspect_containers()
    try:
        api = collect_api()
    except QualificationError as exc:
        return {"errors": [str(exc)], "services": containers, "status": "FAIL"}
    errors = evaluate(containers, api, lock)
    return {
        "errors": errors,
        "services": containers,
        "status": "PASS" if not errors else "FAIL",
    }


def fault_campaign(lock: dict[str, Any], timeout: int) -> dict[str, Any]:
    results = []
    for name in REQUIRED_SERVICES:
        container = f"{PROJECT}-{name}-1"
        paused = command(["docker", "pause", container], timeout=10)
        if paused.returncode:
            raise QualificationError(f"failed to pause {name}")
        try:
            state = inspect_containers()
            detected = any(name in error for error in evaluate(state, {}, lock))
        finally:
            resumed = command(["docker", "unpause", container], timeout=10)
            if resumed.returncode:
                raise QualificationError(f"failed to unpause {name}")
        deadline = time.monotonic() + timeout
        recovered = False
        while time.monotonic() < deadline:
            if check(lock)["status"] == "PASS":
                recovered = True
                break
            time.sleep(1)
        results.append({"detected_fail_closed": detected, "recovered": recovered, "service": name})
        if not detected or not recovered:
            raise QualificationError(f"bounded fault/recovery failed for {name}")
    return {"results": results, "status": "PASS"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="run non-mutating qualification")
    parser.add_argument("--fault-campaign", action="store_true", help="run bounded pause/recovery campaign")
    parser.add_argument("--execute", action="store_true", help="authorize fault injection")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    lock = json.loads((ROOT / "infra/services.lock.json").read_text(encoding="utf-8"))
    try:
        if args.fault_campaign:
            if not args.execute:
                raise QualificationError("fault campaign requires --execute")
            result = fault_campaign(lock, args.timeout)
        else:
            result = check(lock)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "PASS" else 1
    except (OSError, json.JSONDecodeError, QualificationError) as exc:
        print(json.dumps({"error": str(exc), "status": "ERROR"}, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
