#!/usr/bin/env python3
"""Regression tests for scripts/validate_runtime_evidence.py.

Hermetic: builds a temporary manifest + evidence record + raw log and asserts the
validator's fail-closed behaviour on the numeric outcome fields (exit_code and the
failed/skipped/not_executed counters), so that a bare `status: PASS` label is never
accepted on its own.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "scripts" / "validate_runtime_evidence.py"

_TASK = "OCOR-DEV-9999"
_RAW = b"raw log output\n"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _full_command(
    *,
    exit_code: int = 0,
    failed: int = 0,
    skipped: int = 0,
    not_executed: int = 0,
    passed: int = 4,
) -> dict[str, Any]:
    return {
        "command": "pytest -q ocor-runtime/tests/tasks/test_ocor_dev_9999.py",
        "exit_code": exit_code,
        "result": {
            "failed": failed,
            "not_executed": not_executed,
            "passed": passed,
            "skipped": skipped,
        },
        "status": "PASS",
    }


def _write_fixture(base: Path, commands: list[dict[str, Any]]) -> None:
    record = {
        "task_id": _TASK,
        "result": "PASS",
        "commands": commands,
        "raw_output_sha256": _sha256(_RAW),
        "commit": "0" * 40,
        "environment": {"host": "test"},
        "created_at": "2026-10-02T00:00:00Z",
    }
    record_bytes = json.dumps(record, indent=2, sort_keys=True).encode("utf-8")
    (base / f"{_TASK}.json").write_bytes(record_bytes)
    (base / f"{_TASK}.log").write_bytes(_RAW)
    manifest = {
        "artifacts": [
            {"path": f"{_TASK}.json", "sha256": _sha256(record_bytes), "task_id": _TASK},
            {"path": f"{_TASK}.log", "sha256": _sha256(_RAW), "task_id": f"{_TASK}-RAW"},
        ],
        "gate": "G9",
        "schema_version": "1.0",
    }
    (base / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _run_validator(base: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--task",
            _TASK,
            "--non-skipped",
            "--manifest",
            str(base / "MANIFEST.json"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _assert_pass(self: unittest.TestCase, base: Path) -> None:
    result = _run_validator(base)
    self.assertEqual(0, result.returncode, result.stdout + result.stderr)
    self.assertIn("PASS", result.stdout)


def _assert_fail(self: unittest.TestCase, base: Path) -> None:
    result = _run_validator(base)
    self.assertNotEqual(0, result.returncode)
    self.assertIn("FAIL", result.stderr)


class RuntimeEvidenceValidatorTests(unittest.TestCase):
    def test_accepts_full_outcome(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_fixture(base, [_full_command()])
            _assert_pass(self, base)

    def test_accepts_exit_code_only_legacy_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            command = {
                "command": "sha256sum -c inputs/normative/SHA256SUMS",
                "exit_code": 0,
                "status": "PASS",
            }
            _write_fixture(base, [command])
            _assert_pass(self, base)

    def test_accepts_result_dict_only_requalified_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            command = {
                "command": "uv run pytest -q ...",
                "result": {"failed": 0, "not_executed": 0, "passed": 7, "skipped": 0},
                "status": "PASS",
            }
            _write_fixture(base, [command])
            _assert_pass(self, base)

    def test_rejects_nonzero_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_fixture(base, [_full_command(exit_code=1)])
            _assert_fail(self, base)

    def test_rejects_nonzero_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_fixture(base, [_full_command(failed=1)])
            _assert_fail(self, base)

    def test_rejects_nonzero_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_fixture(base, [_full_command(skipped=1)])
            _assert_fail(self, base)

    def test_rejects_nonzero_not_executed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _write_fixture(base, [_full_command(not_executed=1)])
            _assert_fail(self, base)

    def test_rejects_invalid_exit_code_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            command = {
                "command": "pytest -q ...",
                "exit_code": "0",
                "result": {"failed": 0, "not_executed": 0, "passed": 4, "skipped": 0},
                "status": "PASS",
            }
            _write_fixture(base, [command])
            _assert_fail(self, base)

    def test_rejects_flat_nonzero_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            command = {
                "command": "pytest -q ...",
                "exit_code": 0,
                "failed": 1,
                "status": "PASS",
            }
            _write_fixture(base, [command])
            _assert_fail(self, base)

    def test_rejects_bare_status_label(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            command = {"command": "pytest -q ...", "status": "PASS"}
            _write_fixture(base, [command])
            _assert_fail(self, base)

    def test_rejects_empty_result_dict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            command = {"command": "pytest test.py", "result": {}, "status": "PASS"}
            _write_fixture(base, [command])
            _assert_fail(self, base)

    def test_rejects_result_with_only_passed_counter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            command = {
                "command": "pytest -q ...",
                "result": {"passed": 7},
                "status": "PASS",
            }
            _write_fixture(base, [command])
            _assert_fail(self, base)

    def test_rejects_result_xfailed_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            command = {
                "command": "pytest -q ...",
                "exit_code": 0,
                "failed": 0,
                "not_executed": 0,
                "skipped": 0,
                "result": {"xfailed": 1},
                "status": "PASS",
            }
            _write_fixture(base, [command])
            _assert_fail(self, base)

    def test_accepts_result_xfailed_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            command = {
                "command": "pytest -q ...",
                "result": {
                    "failed": 0,
                    "not_executed": 0,
                    "passed": 7,
                    "skipped": 0,
                    "xfailed": 0,
                },
                "status": "PASS",
            }
            _write_fixture(base, [command])
            _assert_pass(self, base)


if __name__ == "__main__":
    unittest.main()
