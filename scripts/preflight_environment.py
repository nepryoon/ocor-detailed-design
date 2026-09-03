#!/usr/bin/env python3
"""Inspect the OCOR host without changing it and emit structured JSON."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import socket
import sys

from ocor_bootstrap_lib import BootstrapError, load_json, root, run, validate_locks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-ready", action="store_true", help="fail if bootstrap prerequisites are absent")
    args = parser.parse_args()
    try:
        repository = root()
        lock = load_json(repository / "infra/toolchain.lock.json")
        commands = {item["id"]: shutil.which({"github-cli": "gh"}.get(item["id"], item["id"])) for item in lock["tools"]}
        docker = run(["docker", "info", "--format", "{{json .ServerVersion}}"], cwd=repository, timeout=20)
        disk = shutil.disk_usage(repository)
        ports = {}
        for port in (6363, 1729, 3030, 8181, 8080, 8200):
            with socket.socket() as probe:
                ports[str(port)] = probe.connect_ex(("127.0.0.1", port)) != 0
        required = ("git", "docker", "uv")
        errors = validate_locks(repository)
        errors.extend(f"missing command: {item}" for item in required if not commands.get(item))
        if docker.returncode:
            errors.append("Docker daemon unavailable")
        payload = {
            "architecture": platform.machine(),
            "commands": commands,
            "disk_available_bytes": disk.free,
            "docker": "READY" if docker.returncode == 0 else "UNAVAILABLE",
            "errors": errors,
            "platform": platform.platform(),
            "ports_available": ports,
            "secret_names_present": sorted(
                name for name in os.environ if name.startswith("OCOR_") and any(token in name for token in ("PASSWORD", "TOKEN", "SECRET"))
            ),
            "status": "PASS" if not errors else "NEEDS_BOOTSTRAP",
        }
        print(__import__("json").dumps(payload, indent=2, sort_keys=True))
        return 1 if errors and args.require_ready else 0
    except BootstrapError as exc:
        print(__import__("json").dumps({"status": "ERROR", "error": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
