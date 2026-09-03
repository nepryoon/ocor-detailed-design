#!/usr/bin/env python3
"""Acceptance tests for DEC-211 autonomous tooling and infrastructure bootstrap."""

from __future__ import annotations

import json
import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REQUIRED = (
    "docs/development_methodology/OCOR_AUTONOMOUS_TOOLING_POLICY.md",
    "docs/development_methodology/OCOR_INFRASTRUCTURE_BOOTSTRAP_STRATEGY.md",
    "docs/development_methodology/OCOR_EXTERNAL_DEPENDENCY_POLICY.md",
    "infra/toolchain.lock.json",
    "infra/toolchain.lock.schema.json",
    "infra/services.lock.json",
    "infra/services.lock.schema.json",
    "reports/development/TOOLING_STATE.json",
    "reports/development/INFRASTRUCTURE_STATE.json",
    "scripts/preflight_environment.py",
    "scripts/bootstrap_development_environment.py",
    "scripts/verify_external_services.py",
    "scripts/reset_test_environment.py",
    "scripts/resume_autonomous_delivery.py",
    ".github/workflows/ocor-tooling-bootstrap.yml",
    "ocor-runtime/docs/governance_dossier/ARA_DECISION_RECORD_v1.5.md",
    "ocor-runtime/docs/governance_dossier/registers/OCOR_Decision_Register_v1.5_APPROVED.md",
    "ocor-runtime/docs/governance_dossier/registers/OCOR_Decision_Traceability_Index_v1.5_APPROVED.md",
)


class AutonomousToolingPolicyTests(unittest.TestCase):
    def test_required_artifacts_exist(self) -> None:
        self.assertEqual([], [item for item in REQUIRED if not (ROOT / item).is_file()])

    def test_lock_manifests_are_canonical_and_pinned(self) -> None:
        for name in ("toolchain", "services"):
            path = ROOT / f"infra/{name}.lock.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(json.dumps(data, indent=2, sort_keys=True) + "\n", path.read_text(encoding="utf-8"))
            self.assertEqual("1.0", data["schema_version"])
        services = json.loads((ROOT / "infra/services.lock.json").read_text(encoding="utf-8"))
        required = {"terminusdb", "typedb", "fuseki", "opa", "keycloak", "spire-server", "spire-agent", "openbao", "postgresql", "kafka", "qdrant"}
        indexed = {item["id"]: item for item in services["services"]}
        self.assertTrue(required <= indexed.keys())
        for service in indexed.values():
            image = service["image"]
            self.assertRegex(image, r"^[^\s]+@sha256:[0-9a-f]{64}$")
            self.assertIn("license", service)
            self.assertIn("source", service)

    def test_bootstrap_tasks_and_dependencies_are_governed(self) -> None:
        backlog = json.loads((ROOT / "docs/development_plan/OCOR_IMPLEMENTATION_BACKLOG.json").read_text(encoding="utf-8"))
        tasks = {item["id"]: item for item in backlog["tasks"]}
        expected = {f"OCOR-DEV-{number:04d}" for number in range(70, 85)}
        self.assertTrue(expected <= tasks.keys())
        for spike in ("OCOR-DEV-0016", "OCOR-DEV-0017", "OCOR-DEV-0018", "OCOR-DEV-0021"):
            self.assertIn("OCOR-DEV-0084", tasks[spike]["hard_dependencies"])
        dag = (ROOT / "docs/development_plan/OCOR_DEPENDENCY_DAG.mmd").read_text(encoding="utf-8")
        for task_id in expected:
            self.assertIn(task_id.replace("-", "_"), dag)

    def test_decision_and_evidence_fence(self) -> None:
        record = (ROOT / "ocor-runtime/docs/governance_dossier/ARA_DECISION_RECORD_v1.5.md").read_text(encoding="utf-8")
        self.assertIn("DEC-211", record)
        self.assertIn("E1=0", record)
        self.assertIn("E2=0", record)
        self.assertRegex(record, re.compile(r"runtime.*NO-GO", re.IGNORECASE))
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("DEC-211", agents)
        self.assertIn("modalità di implementazione", agents.lower())

    def test_scripts_have_non_mutating_contract_checks(self) -> None:
        for script in REQUIRED:
            if not script.startswith("scripts/"):
                continue
            result = subprocess.run(
                ["python3", script, "--help"], cwd=ROOT, text=True, capture_output=True, check=False, timeout=10
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        verify = subprocess.run(
            ["python3", "scripts/verify_external_services.py", "--manifest-only"],
            cwd=ROOT, text=True, capture_output=True, check=False, timeout=10,
        )
        self.assertEqual(0, verify.returncode, verify.stdout + verify.stderr)
        payload = json.loads(verify.stdout)
        self.assertEqual("PASS", payload["status"])


if __name__ == "__main__":
    unittest.main()
