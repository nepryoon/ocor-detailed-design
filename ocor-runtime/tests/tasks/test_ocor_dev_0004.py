from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).parents[2] / "tools"
sys.path.insert(0, str(TOOLS))

from evidence_manifest import (
    ManifestError,
    record_task_evidence,
    validate_manifest,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def valid_case() -> dict[str, object]:
    return {
        "requirement_id": "BR-003",
        "case_id": "OCOR-DEV-0004-POSITIVE",
        "command": "pytest -q test_ocor_dev_0004.py",
        "status": "PASS",
        "result": {"passed": 1, "failed": 0, "skipped": 0, "not_executed": 0},
    }


def record(tmp_path: Path, *, cases: list[dict[str, object]] | None = None) -> Path:
    manifest = tmp_path / "MANIFEST.json"
    record_task_evidence(
        manifest_path=manifest,
        gate="G0",
        task_id="OCOR-DEV-0004",
        commit="a" * 40,
        environment={"python": "3.12.14", "uv": "0.12.5"},
        inputs={"uv.lock": "b" * 64},
        cases=cases or [valid_case()],
        raw_output="1 passed in 0.01s\n",
        created_at="2026-09-02T00:00:00Z",
    )
    return manifest


def test_records_content_addressed_evidence_and_requirement_ledger(tmp_path: Path):
    manifest_path = record(tmp_path)
    manifest = json.loads(manifest_path.read_text())
    evidence_path = tmp_path / "OCOR-DEV-0004.json"
    raw_path = tmp_path / "OCOR-DEV-0004.log"

    assert manifest["gate"] == "G0"
    assert manifest["artifacts"] == [
        {
            "path": evidence_path.name,
            "sha256": sha256(evidence_path),
            "task_id": "OCOR-DEV-0004",
        },
        {
            "path": raw_path.name,
            "sha256": sha256(raw_path),
            "task_id": "OCOR-DEV-0004-RAW",
        },
    ]
    assert manifest["requirement_results"][0]["requirement_id"] == "BR-003"
    assert manifest["requirement_results"][0]["status"] == "PASS"
    assert validate_manifest(manifest_path, task_id="OCOR-DEV-0004", non_skipped=True)


def test_multiple_cases_are_preserved_individually_and_sorted(tmp_path: Path):
    negative = valid_case() | {
        "case_id": "OCOR-DEV-0004-NEGATIVE",
        "command": "pytest -q test_ocor_dev_0004.py -k negative",
    }
    manifest = json.loads(record(tmp_path, cases=[valid_case(), negative]).read_text())
    assert [row["case_id"] for row in manifest["requirement_results"]] == [
        "OCOR-DEV-0004-NEGATIVE",
        "OCOR-DEV-0004-POSITIVE",
    ]


@pytest.mark.parametrize("status", ["SKIPPED", "UNAVAILABLE", "NOT_EXECUTED", "XFAIL"])
def test_non_qualifying_case_cannot_be_accepted(tmp_path: Path, status: str):
    case = valid_case() | {"status": status}
    with pytest.raises(ManifestError, match="non-qualifying"):
        record(tmp_path, cases=[case])


def test_missing_command_is_rejected(tmp_path: Path):
    case = valid_case()
    del case["command"]
    with pytest.raises(ManifestError, match="command"):
        record(tmp_path, cases=[case])


def test_missing_raw_output_is_rejected(tmp_path: Path):
    manifest_path = record(tmp_path)
    (tmp_path / "OCOR-DEV-0004.log").unlink()
    with pytest.raises(ManifestError, match="raw evidence"):
        validate_manifest(manifest_path, task_id="OCOR-DEV-0004", non_skipped=True)


def test_tampered_hash_is_rejected(tmp_path: Path):
    manifest_path = record(tmp_path)
    (tmp_path / "OCOR-DEV-0004.log").write_text("tampered\n")
    with pytest.raises(ManifestError, match="digest mismatch"):
        validate_manifest(manifest_path, task_id="OCOR-DEV-0004", non_skipped=True)


def test_task_identifier_cannot_escape_manifest_directory(tmp_path: Path):
    with pytest.raises(ManifestError, match="task_id"):
        record_task_evidence(
            manifest_path=tmp_path / "MANIFEST.json",
            gate="G0",
            task_id="../escape",
            commit="a" * 40,
            environment={"python": "3.12.14"},
            inputs={"uv.lock": "b" * 64},
            cases=[valid_case()],
            raw_output="pass\n",
            created_at="2026-09-02T00:00:00Z",
        )
