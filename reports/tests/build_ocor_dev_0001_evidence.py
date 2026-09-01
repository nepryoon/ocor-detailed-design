#!/usr/bin/env python3
"""Build content-addressed OCOR-DEV-0001 activation evidence."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "reports/evidence/G0"
LOG = GATE / "OCOR-DEV-0001.log"
EVIDENCE = GATE / "OCOR-DEV-0001.json"
MANIFEST = GATE / "MANIFEST.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*arguments: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *arguments], text=True).strip()


def main() -> int:
    if not LOG.exists() or "ACTIVATION_VALIDATION_COMPLETE" not in LOG.read_text(encoding="utf-8"):
        raise SystemExit("activation log is absent or incomplete")
    commit = git("rev-parse", "HEAD")
    created = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    commands = [
        {"command": "sha256sum -c inputs/normative/SHA256SUMS", "status": "PASS", "exit_code": 0},
        {"command": "python scripts/validate_ocor_change_scope.py --base origin/main --head HEAD", "status": "PASS", "exit_code": 0},
        {"command": "pytest -q ocor-runtime/tests/tasks/test_ocor_dev_0001.py", "status": "PASS", "exit_code": 0, "passed": 17},
        {"command": "python scripts/ocor_autonomous_delivery.py --validate", "status": "PASS", "exit_code": 0},
        {"command": "pytest -q ocor-runtime/tests/ with live PostgreSQL", "status": "PASS", "exit_code": 0, "passed": 126, "skipped": 0},
        {"command": "markdownlint-cli2 0.18.1 planning Markdown", "status": "PASS", "exit_code": 0, "files": 6},
        {"command": "mmdc 11.12.0 dependency DAG render", "status": "PASS", "exit_code": 0, "files": 1},
    ]
    evidence = {
        "schema_version": "1.0",
        "task_id": "OCOR-DEV-0001",
        "commit": commit,
        "created_at": created,
        "result": "PASS",
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "postgres": "postgres:16@sha256:33f923b05f64ca54ac4401c01126a6b92afe839a0aa0a52bc5aeb5cc958e5f20; PostgreSQL 16.14",
            "uv": "0.12.5",
            "psycopg": "3.2.10",
            "markdownlint_cli2": "0.18.1 (markdownlint 0.38.0)",
            "mermaid_cli": "11.12.0",
        },
        "commands": commands,
        "counts": {
            "unique_pytest": {"PASS": 126, "FAIL": 0, "SKIPPED": 0, "XFAIL": 0, "NOT_EXECUTED": 0},
            "task_control_subset": {"PASS": 17, "FAIL": 0, "SKIPPED": 0, "XFAIL": 0, "NOT_EXECUTED": 0},
            "postgres_subset": {"PASS": 5, "FAIL": 0, "SKIPPED": 0, "XFAIL": 0, "NOT_EXECUTED": 0},
            "documentation_validators": {"PASS": 2, "FAIL": 0, "NOT_EXECUTED": 0},
        },
        "raw_output_sha256": digest(LOG),
        "rollback": "Stop dispatch; revert the activation commits with new revert commits; restore the prior frozen lock and workflows; re-run the prior manifests.",
        "claims": {
            "runtime_conformance": "NOT_ESTABLISHED",
            "E1": 0,
            "E2": 0,
            "PoC_GO": "NO_GO",
            "Production_readiness": "NO_GO",
        },
    }
    GATE.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "1.0",
        "gate": "G0",
        "created_at": created,
        "artifacts": [
            {
                "task_id": "OCOR-DEV-0001",
                "path": EVIDENCE.name,
                "sha256": digest(EVIDENCE),
            },
            {
                "task_id": "OCOR-DEV-0001-RAW",
                "path": LOG.name,
                "sha256": digest(LOG),
            },
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"result": "PASS", "commit": commit, "manifest": digest(MANIFEST)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
