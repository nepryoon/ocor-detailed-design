#!/usr/bin/env python3
"""Inspect the OCOR host without changing it and emit structured JSON."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import socket
import sys

from ocor_bootstrap_lib import BootstrapError, load_json, root, run, validate_locks


def executable_path(repository, item):
    if item["provider"] == "repository":
        candidate = repository / "ocor-runtime" / ".venv" / "bin" / item["command"]
        return str(candidate) if candidate.is_file() else None
    return shutil.which(item["command"])


def validate_tool(repository, item):
    if item["provider"] == "container":
        inspected = run(["docker", "image", "inspect", item["container_image"]], cwd=repository, timeout=20)
        if inspected.returncode:
            return None, "container image unavailable"
        metadata = json.loads(inspected.stdout)[0]
        if metadata.get("Id") != f"sha256:{item['integrity']}":
            return None, "container image integrity mismatch"
        environment = dict(entry.split("=", 1) for entry in metadata.get("Config", {}).get("Env", []) if "=" in entry)
        observed = environment.get(item["version_env"], "").removeprefix("jdk-")
        if observed != item["version"]:
            return None, f"container version mismatch: {observed or 'missing'}"
        return item["container_image"], None
    path = executable_path(repository, item)
    if not path:
        return None, "command unavailable"
    if hashlib.sha256(__import__("pathlib").Path(path).read_bytes()).hexdigest() != item["integrity"]:
        return path, "executable integrity mismatch"
    probe = run([path, *item["version_args"]], cwd=repository, timeout=20)
    output = (probe.stdout + probe.stderr).strip()
    if probe.returncode or not re.search(item["version_pattern"], output, flags=re.MULTILINE):
        return path, "version mismatch"
    return path, None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-ready", action="store_true", help="fail if bootstrap prerequisites are absent")
    parser.add_argument("--contract-only", action="store_true", help="validate lock contracts without host-specific probes")
    args = parser.parse_args()
    try:
        repository = root()
        lock = load_json(repository / "infra/toolchain.lock.json")
        commands = {}
        tool_errors = []
        if args.contract_only:
            commands = {item["id"]: "CONTRACT_ONLY" for item in lock["tools"]}
            docker = None
        else:
            for item in lock["tools"]:
                commands[item["id"]], error = validate_tool(repository, item)
                if error:
                    tool_errors.append(f"{item['id']}: {error}")
            docker = run(["docker", "info", "--format", "{{json .ServerVersion}}"], cwd=repository, timeout=20)
        disk = shutil.disk_usage(repository)
        ports = {}
        for port in (6363, 1729, 3030, 8181, 8080, 8200):
            with socket.socket() as probe:
                ports[str(port)] = probe.connect_ex(("127.0.0.1", port)) != 0
        errors = validate_locks(repository)
        errors.extend(tool_errors)
        if docker is not None and docker.returncode:
            errors.append("Docker daemon unavailable")
        payload = {
            "architecture": platform.machine(),
            "commands": commands,
            "disk_available_bytes": disk.free,
            "docker": "CONTRACT_ONLY" if docker is None else ("READY" if docker.returncode == 0 else "UNAVAILABLE"),
            "errors": errors,
            "platform": platform.platform(),
            "ports_available": ports,
            "secret_names_present": sorted(
                name for name in os.environ if name.startswith("OCOR_") and any(token in name for token in ("PASSWORD", "TOKEN", "SECRET"))
            ),
            "status": "PASS" if not errors else "NEEDS_BOOTSTRAP",
        }
        print(__import__("json").dumps(payload, indent=2, sort_keys=True))
        return 1 if errors else 0
    except BootstrapError as exc:
        print(__import__("json").dumps({"status": "ERROR", "error": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
