#!/usr/bin/env python3
"""Acceptance tests for the governed RCCAD methodology adoption."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REQUIRED = (
    "docs/development_methodology/README.md",
    "docs/development_methodology/OCOR_RCCAD_v1.0.md",
    "docs/development_methodology/OCOR_TEST_STRATEGY.md",
    "docs/development_methodology/OCOR_ARCHITECTURE_FITNESS_FUNCTIONS.md",
    "docs/development_methodology/OCOR_DEFINITION_OF_DONE.md",
    "docs/development_methodology/OCOR_MODEL_OPERATING_PROFILE.md",
    "docs/development_methodology/methodology.json",
    "docs/development_methodology/methodology.schema.json",
    "PLANS.md",
    "reports/development/EXECUTION_STATE.json",
    "reports/development/ITERATION_LOG.md",
    "reports/development/MODEL_HANDOFF.json",
    "reports/development/METHOD_COMPLIANCE.json",
    "reports/tests/rccad_tdd_evidence.json",
    "ocor-runtime/docs/governance_dossier/registers/OCOR_Decision_Register_v1.4_APPROVED.md",
    "ocor-runtime/docs/governance_dossier/registers/OCOR_Decision_Traceability_Index_v1.4_APPROVED.md",
    "scripts/validate_rccad.py",
)


class RccadAdoptionTests(unittest.TestCase):
    def test_required_artifacts_exist(self) -> None:
        missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
        self.assertEqual([], missing)

    def test_manifest_is_valid_and_canonical(self) -> None:
        manifest_path = ROOT / "docs/development_methodology/methodology.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        rendered = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
        self.assertEqual(rendered, manifest_path.read_text(encoding="utf-8"))
        self.assertEqual("OCOR-RCCAD", manifest["methodology_id"])
        self.assertEqual("1.0", manifest["version"])
        self.assertEqual(["G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7"], manifest["lifecycle"])
        self.assertEqual({"E1": 0, "E2": 0}, manifest["evidence_fence"])

    def test_validator_accepts_repository_state(self) -> None:
        result = subprocess.run(
            ["python3", "scripts/validate_rccad.py", "--root", str(ROOT)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PASS_LOCAL_PRECHECK", payload["status"])
        self.assertEqual("CI_REQUIRED", payload["dynamic_assurance"])
        self.assertEqual({f"AFF-{number:03d}": "PASS_STATIC_PRECHECK" for number in range(1, 11)}, payload["fitness_results"])

    def test_validator_fails_closed_on_missing_required_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = subprocess.run(
                [
                    "python3",
                    "scripts/validate_rccad.py",
                    "--root",
                    str(ROOT),
                    "--simulate-missing",
                    "PLANS.md",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertNotEqual(0, result.returncode)
        payload = json.loads(result.stdout)
        self.assertEqual("FAIL", payload["status"])
        self.assertIn("RCCAD-ARTIFACT-MISSING", {item["rule_id"] for item in payload["findings"]})

    def test_validator_rejects_input_changes(self) -> None:
        result = subprocess.run(
            [
                "python3",
                "scripts/validate_rccad.py",
                "--root",
                str(ROOT),
                "--simulate-changed-path",
                "inputs/normative/forbidden.txt",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(0, result.returncode)
        payload = json.loads(result.stdout)
        self.assertIn("RCCAD-IMMUTABLE-INPUT", {item["rule_id"] for item in payload["findings"]})


if __name__ == "__main__":
    unittest.main()
