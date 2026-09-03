#!/usr/bin/env python3
"""Validate service locks or probe the real OCOR development services."""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys

from ocor_bootstrap_lib import BootstrapError, load_json, root, validate_locks


PORTS = {
    "terminusdb": 6363,
    "typedb": 1729,
    "fuseki": 3030,
    "opa": 8181,
    "keycloak": 8080,
    "openbao": 8200,
    "postgresql": 55433,
    "kafka": 19092,
    "qdrant-http": 16333,
    "qdrant-grpc": 16334,
}
CONTAINERS = {
    "fuseki",
    "kafka",
    "keycloak",
    "opa",
    "openbao",
    "postgresql",
    "qdrant",
    "spire-agent",
    "spire-server",
    "terminusdb",
    "typedb",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-only", action="store_true")
    parser.add_argument("--timeout", type=float, default=3.0)
    args = parser.parse_args()
    try:
        repository = root()
        errors = validate_locks(repository)
        services = load_json(repository / "infra/services.lock.json")["services"]
        if errors:
            raise BootstrapError("; ".join(errors))
        if args.manifest_only:
            print(json.dumps({"status": "PASS", "service_count": len(services)}, indent=2, sort_keys=True))
            return 0
        results = {}
        for name, port in PORTS.items():
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=args.timeout):
                    results[name] = "READY"
            except OSError:
                results[name] = "NOT_READY"
        container_results = {}
        for name in sorted(CONTAINERS):
            inspected = subprocess.run(
                ["docker", "inspect", f"ocor-bootstrap-{name}-1", "--format", "{{json .State}}"],
                cwd=repository,
                text=True,
                capture_output=True,
                check=False,
                timeout=10,
            )
            if inspected.returncode:
                container_results[name] = "NOT_FOUND"
                continue
            state = json.loads(inspected.stdout)
            health = state.get("Health", {}).get("Status")
            container_results[name] = (
                "READY" if state.get("Running") and not state.get("Paused") and health in (None, "healthy")
                else "NOT_READY"
            )
        status = "PASS" if set(results.values()) == {"READY"} and set(container_results.values()) == {"READY"} else "FAIL"
        print(json.dumps({"status": status, "services": results, "containers": container_results}, indent=2, sort_keys=True))
        return 0 if status == "PASS" else 1
    except BootstrapError as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
