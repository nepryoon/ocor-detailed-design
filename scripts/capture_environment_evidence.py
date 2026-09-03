#!/usr/bin/env python3
"""Capture redacted, content-addressable OCOR environment evidence."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

from ocor_bootstrap_lib import root, sha256


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="reports/development/environment-evidence.json")
    args = parser.parse_args()
    repository = root()
    env_file = repository / ".ocor" / "bootstrap.env"
    command = ["docker", "compose"]
    if env_file.exists():
        command.extend(["--env-file", str(env_file)])
    command.extend(["-p", "ocor-bootstrap", "-f", "deploy/bootstrap/compose.yaml", "ps", "--format", "json"])
    inspect = subprocess.run(
        command,
        cwd=repository, text=True, capture_output=True, check=False, timeout=30,
    )
    payload = {
        "artifacts": {
            relative: sha256(repository / relative)
            for relative in (
                "deploy/bootstrap/compose.yaml",
                "infra/fuseki/Dockerfile",
                "infra/services.lock.json",
                "infra/toolchain.lock.json",
                "scripts/bootstrap_development_environment.py",
                "scripts/fault_inject_test_environment.py",
                "scripts/preflight_environment.py",
                "scripts/reset_test_environment.py",
                "scripts/verify_external_services.py",
            )
        },
        "claims": {"E1": 0, "E2": 0, "runtime_conformance": "NOT_ESTABLISHED"},
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repository, text=True).strip(),
        "locks": {
            "services": sha256(repository / "infra/services.lock.json"),
            "toolchain": sha256(repository / "infra/toolchain.lock.json"),
        },
        "schema_version": "1.0",
        "readiness_scope": "container health and host transport only; functional G2 campaigns remain unqualified",
        "service_inventory": inspect.stdout.splitlines(),
        "status": "CAPTURED" if inspect.returncode == 0 else "PARTIAL",
    }
    output = repository / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "output": str(output), "sha256": sha256(output)}, sort_keys=True))
    return 0 if inspect.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
