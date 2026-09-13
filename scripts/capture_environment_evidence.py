#!/usr/bin/env python3
"""Capture redacted, content-addressable OCOR environment evidence.

Extended by OCOR-DEV-0084 to fold in the real typed health check
(scripts/verify_external_services.py's ``typed_health_checks``) rather than
only the raw ``docker compose ps`` inventory: ``docker compose ps`` proves
containers exist and pass their own Docker healthcheck, but says nothing
about the governed contract each service must satisfy (pinned image,
loopback-only publication, real protocol probe, fail-closed negative
checks). ``environment_status`` reports the typed aggregate; it is
deliberately a separate field from ``status`` (whether the capture process
itself ran cleanly), so a degraded service is visible in the evidence
rather than silently absorbed into a generic "captured OK".
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from ocor_bootstrap_lib import load_json, root, sha256

ARTIFACT_PATHS = (
    "deploy/bootstrap/compose.yaml",
    "deploy/bootstrap/init/initialize_services.py",
    "deploy/bootstrap/init/opa/bootstrap.rego",
    "deploy/bootstrap/fixtures/load_fixtures.py",
    "deploy/bootstrap/fixtures/synthetic_fixtures.json",
    "infra/fuseki/Dockerfile",
    "infra/services.lock.json",
    "infra/toolchain.lock.json",
    "scripts/bootstrap_development_environment.py",
    "scripts/fault_inject_test_environment.py",
    "scripts/preflight_environment.py",
    "scripts/reset_test_environment.py",
    "scripts/verify_external_services.py",
)


def _load_typed_health_checks(repository: Path) -> Any:
    module_path = repository / "scripts/verify_external_services.py"
    spec = importlib.util.spec_from_file_location("verify_external_services_0084", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def capture_environment_status(repository: Path) -> dict[str, Any]:
    module = _load_typed_health_checks(repository)
    services = load_json(repository / "infra/services.lock.json")["services"]
    health = module.typed_health_checks(repository, services, execute=False)
    ready = [item for item in health if item.status is module.ServiceStatus.READY]
    return {
        "status": "PASS" if len(ready) == len(health) else "DEGRADED",
        "services": [item.to_json() for item in health],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="reports/development/environment-evidence.json")
    parser.add_argument(
        "--env-file",
        type=Path,
        help="file with OCOR_LOCAL_* secrets; defaults to .ocor/bootstrap.env if present",
    )
    args = parser.parse_args()
    repository = root()
    env_file = args.env_file if args.env_file is not None else repository / ".ocor" / "bootstrap.env"
    command = ["docker", "compose"]
    if env_file.exists():
        command.extend(["--env-file", str(env_file)])
    command.extend(["-p", "ocor-bootstrap", "-f", "deploy/bootstrap/compose.yaml", "ps", "--format", "json"])
    inspect = subprocess.run(
        command,
        cwd=repository, text=True, capture_output=True, check=False, timeout=30,
    )
    environment_status = capture_environment_status(repository)
    payload = {
        "artifacts": {relative: sha256(repository / relative) for relative in ARTIFACT_PATHS},
        "claims": {"E1": 0, "E2": 0, "runtime_conformance": "NOT_ESTABLISHED"},
        "environment_status": environment_status,
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repository, text=True).strip(),
        "locks": {
            "services": sha256(repository / "infra/services.lock.json"),
            "toolchain": sha256(repository / "infra/toolchain.lock.json"),
        },
        "schema_version": "1.1",
        "readiness_scope": "typed governed-contract health per scripts/verify_external_services.py, plus container health and host transport; functional G2 campaigns remain unqualified",
        "service_inventory": inspect.stdout.splitlines(),
        "status": "CAPTURED" if inspect.returncode == 0 else "PARTIAL",
    }
    output = repository / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "environment_status": environment_status["status"],
                "output": str(output),
                "sha256": sha256(output),
            },
            sort_keys=True,
        )
    )
    return 0 if inspect.returncode == 0 and environment_status["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
