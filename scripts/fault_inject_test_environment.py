#!/usr/bin/env python3
"""Apply a bounded reversible fault to an ocor-bootstrap service.

The pre-existing raw mode (a single ``docker`` fault command, dry-run by
default) is unchanged. ``--bounded`` (OCOR-DEV-0083) adds a real bounded
cycle for ``pause``/``unpause``, ``disconnect``/``reconnect`` and the
self-recovering ``restart`` action: it applies the fault, polls for the
expected unhealthy/unreachable condition within a timeout, then -- in a
``finally`` block, so recovery is attempted even if detection never
completed -- applies the matching recovery action and polls for the
service to become healthy/reachable again within a second timeout. Nothing
is ever left mid-fault by a bounded cycle.

Detecting ``disconnect`` required a live-verified correction: a bare TCP
connect to a service's published host port (``socket.create_connection``)
keeps succeeding even while the container is disconnected from the compose
network, because Docker Desktop's own port-forwarding proxy completes the
TCP handshake independently of the container's network reachability. Only
a real HTTP round trip against each service's health endpoint
(``HEALTH_URLS``) actually times out while disconnected and recovers after
reconnect; a bare-port-connect oracle was tried first and silently never
detected the fault, which is why it is HTTP-based here instead.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ocor_bootstrap_lib import root, run

ALLOWED = {"terminusdb", "typedb", "fuseki", "opa", "keycloak", "openbao", "spire-server", "spire-agent"}
RECOVERY_OF = {"pause": "unpause", "disconnect": "reconnect"}
NETWORK = "ocor-bootstrap_ocor-bootstrap"
# HTTP round trips, not bare TCP connects: see the module docstring for why.
# SPIRE server/agent have no published HTTP endpoint (compose.yaml exposes
# no host port for them), so --bounded disconnect is unsupported for them.
HEALTH_URLS = {
    "terminusdb": "http://127.0.0.1:6363/api/ok",
    "typedb": "http://127.0.0.1:8000/health",
    "fuseki": "http://127.0.0.1:3030/$/ping",
    "opa": "http://127.0.0.1:8181/health",
    "keycloak": "http://127.0.0.1:8080/realms/master/.well-known/openid-configuration",
    "openbao": "http://127.0.0.1:8200/v1/sys/health",
}


class BoundedFaultError(RuntimeError):
    """A bounded fault cycle could not complete safely."""


def container_healthy(container: str) -> bool:
    completed = subprocess.run(
        ["docker", "inspect", container, "--format", "{{json .State}}"],
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    if completed.returncode:
        return False
    state = json.loads(completed.stdout)
    health = state.get("Health", {}).get("Status")
    return bool(state.get("Running")) and not state.get("Paused") and health in (None, "healthy")


def http_reachable(url: str, *, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout):
            return True
    except urllib.error.HTTPError:
        return True  # any HTTP response at all proves the round trip completed
    except (OSError, urllib.error.URLError):
        return False


def _poll(predicate: Callable[[], bool], *, timeout: float, interval: float = 0.5) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


def fault_command(service: str, fault: str) -> list[str]:
    container = f"ocor-bootstrap-{service}-1"
    commands = {
        "pause": ["docker", "pause", container],
        "unpause": ["docker", "unpause", container],
        "restart": ["docker", "restart", "--time", "10", container],
        "disconnect": ["docker", "network", "disconnect", NETWORK, container],
        "reconnect": ["docker", "network", "connect", NETWORK, container],
    }
    return commands[fault]


def bounded_cycle(repository: Path, service: str, fault: str, *, timeout: float) -> dict[str, Any]:
    if fault == "restart":
        result = run(fault_command(service, fault), cwd=repository, timeout=30)
        if result.returncode != 0:
            raise BoundedFaultError(f"restart command failed: {result.stderr[-500:]}")
        recovered = _poll(lambda: container_healthy(f"ocor-bootstrap-{service}-1"), timeout=timeout)
        if not recovered:
            raise BoundedFaultError(f"{service} did not become healthy within {timeout:.0f}s after restart")
        return {"service": service, "fault": fault, "detected": True, "recovered": True}

    if fault not in RECOVERY_OF:
        raise BoundedFaultError(f"--bounded only supports pause, disconnect or restart, not {fault!r}")
    if fault == "disconnect" and service not in HEALTH_URLS:
        raise BoundedFaultError(f"{service} has no published health endpoint; disconnect cannot be verified from the host")

    recovery = RECOVERY_OF[fault]
    container = f"ocor-bootstrap-{service}-1"

    def is_up() -> bool:
        if fault == "pause":
            return container_healthy(container)
        return http_reachable(HEALTH_URLS[service])

    detected = False
    try:
        result = run(fault_command(service, fault), cwd=repository, timeout=30)
        if result.returncode != 0:
            raise BoundedFaultError(f"{fault} command failed: {result.stderr[-500:]}")
        detected = _poll(lambda: not is_up(), timeout=timeout)
    finally:
        recovery_result = run(fault_command(service, recovery), cwd=repository, timeout=30)
        recovery_command_ok = recovery_result.returncode == 0

    if not recovery_command_ok:
        raise BoundedFaultError(f"{recovery} command failed: {recovery_result.stderr[-500:]}")
    recovered = _poll(is_up, timeout=timeout)
    if not detected:
        raise BoundedFaultError(f"{service} was never detected as faulted within {timeout:.0f}s of {fault}")
    if not recovered:
        raise BoundedFaultError(f"{service} did not recover within {timeout:.0f}s after {recovery}")
    return {"service": service, "fault": fault, "recovery": recovery, "detected": detected, "recovered": recovered}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("service", choices=sorted(ALLOWED))
    parser.add_argument("fault", choices=("pause", "unpause", "restart", "disconnect", "reconnect"))
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--bounded", action="store_true", help="run a full detect+auto-recover cycle (OCOR-DEV-0083)")
    parser.add_argument("--timeout", type=float, default=30.0, help="seconds to wait for each detection/recovery poll")
    args = parser.parse_args()
    repository = root()

    if args.bounded:
        if not args.execute:
            print(json.dumps({"status": "PASS", "mode": "DRY_RUN", "operation": "bounded", "service": args.service, "fault": args.fault}, indent=2))
            return 0
        try:
            outcome = bounded_cycle(repository, args.service, args.fault, timeout=args.timeout)
            print(json.dumps({"status": "PASS", "cycle": outcome}, indent=2, sort_keys=True))
            return 0
        except BoundedFaultError as exc:
            print(json.dumps({"status": "FAIL", "error": str(exc)}, sort_keys=True))
            return 1

    command = fault_command(args.service, args.fault)
    if not args.execute:
        print(json.dumps({"status": "PASS", "mode": "DRY_RUN", "command": command}, indent=2))
        return 0
    result = run(command, cwd=repository, timeout=30)
    print(json.dumps({"status": "PASS" if result.returncode == 0 else "ERROR", "stderr": result.stderr[-500:]}, indent=2))
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
