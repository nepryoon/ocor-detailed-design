#!/usr/bin/env python3
"""Regression tests for scripts/validate_evidence_input_drift.py.

These tests are hermetic: they build a temporary repository fixture and assert the
validator's fail-closed behaviour (PASS on matching inputs, FAIL on drift or missing
files) without depending on the drift state of the real repository.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "scripts" / "validate_evidence_input_drift.py"

_TASK = "OCOR-DEV-9999"
_CONTENT = b"governed evidence input\n"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _build_fixture(base: Path, inputs: dict[str, str], tasks: list[str]) -> None:
    (base / "reports" / "development").mkdir(parents=True)
    (base / "reports" / "evidence" / "G9").mkdir(parents=True)
    state = {"completed_evidence_tasks": tasks}
    (base / "reports" / "development" / "EXECUTION_STATE.json").write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    record = {
        "task_id": _TASK,
        "commit": "0" * 40,
        "created_at": "2026-10-01T00:00:00Z",
        "inputs": {"inputs_tree": "0" * 40, **inputs},
    }
    (base / "reports" / "evidence" / "G9" / f"{_TASK}.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _run_validator(base: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--root", str(base)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class EvidenceInputDriftValidatorTests(unittest.TestCase):
    def test_accepts_matching_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "ocor-runtime" / "src").mkdir(parents=True)
            target = base / "ocor-runtime" / "src" / "kernel.py"
            target.write_bytes(_CONTENT)
            _build_fixture(base, {"ocor-runtime/src/kernel.py": _sha256(_CONTENT)}, [_TASK])
            result = _run_validator(base)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertEqual("PASS", json.loads(result.stdout)["status"])

    def test_rejects_drifted_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            target = base / "module.py"
            target.write_bytes(b"current content")
            _build_fixture(base, {"module.py": _sha256(b"original content")}, [_TASK])
            result = _run_validator(base)
            self.assertNotEqual(0, result.returncode)
            payload = json.loads(result.stdout)
            self.assertEqual("FAIL", payload["status"])
            self.assertIn("module.py", {f["path"] for f in payload["findings"]})

    def test_rejects_missing_input_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _build_fixture(base, {"deleted.py": _sha256(_CONTENT)}, [_TASK])
            result = _run_validator(base)
            self.assertNotEqual(0, result.returncode)
            payload = json.loads(result.stdout)
            findings = payload["findings"]
            self.assertTrue(any(f["path"] == "deleted.py" and f["reason"] == "file missing at HEAD" for f in findings))

    def test_rejects_task_without_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _build_fixture(base, {}, [_TASK, "OCOR-DEV-8888"])
            result = _run_validator(base)
            self.assertNotEqual(0, result.returncode)
            payload = json.loads(result.stdout)
            self.assertTrue(any(f["task_id"] == "OCOR-DEV-8888" for f in payload["findings"]))

    def test_ignores_inputs_tree_digest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            target = base / "module.py"
            target.write_bytes(_CONTENT)
            _build_fixture(base, {"module.py": _sha256(_CONTENT)}, [_TASK])
            # Corrupt only the tree-level digest; per-file hash still matches.
            record_path = base / "reports" / "evidence" / "G9" / f"{_TASK}.json"
            record = json.loads(record_path.read_text(encoding="utf-8"))
            record["inputs"]["inputs_tree"] = "f" * 40
            record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            result = _run_validator(base)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertEqual("PASS", json.loads(result.stdout)["status"])


if __name__ == "__main__":
    unittest.main()
