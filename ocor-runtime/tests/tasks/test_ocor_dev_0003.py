from __future__ import annotations

import os
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github/workflows/ocor-poc-ci.yml"
MANDATORY = {"contract", "unit", "integration", "backend", "fgm", "evidence"}


def load_workflow() -> dict:
    return yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def test_pull_requests_expose_six_separate_mandatory_statuses():
    workflow = load_workflow()
    assert workflow["on"]["pull_request"]["branches"] == ["main"]
    assert workflow["permissions"] == {"contents": "read"}
    assert MANDATORY < set(workflow["jobs"])
    assert workflow["jobs"]["mandatory-gates"]["needs"] == sorted(MANDATORY)


def test_all_mandatory_jobs_fail_closed_and_have_bounded_execution():
    jobs = load_workflow()["jobs"]
    for job_id in MANDATORY:
        job = jobs[job_id]
        assert int(job["timeout-minutes"]) <= 20
        assert job.get("continue-on-error", "false") == "false"
        commands = "\n".join(step.get("run", "") for step in job["steps"])
        assert "|| true" not in commands
        assert "--maxfail=0" not in commands
        assert any(
            validator in commands
            for validator in (
                "pytest",
                "validate_runtime_evidence.py",
                "test_authoritative_contract_conformance.py",
            )
        )


def test_real_postgres_integration_service_is_digest_pinned_and_not_skipped():
    integration = load_workflow()["jobs"]["integration"]
    image = integration["services"]["postgres"]["image"]
    assert image == (
        "postgres:16@sha256:"
        "33f923b05f64ca54ac4401c01126a6b92afe839a0aa0a52bc5aeb5cc958e5f20"
    )
    commands = "\n".join(step.get("run", "") for step in integration["steps"])
    assert "test_postgres_outbox_live.py" in commands
    assert "OCOR_LIVE_POSTGRES_DSN" in str(integration["env"])


def test_fgm_status_is_explicitly_contract_readiness_not_runtime_evidence():
    fgm = load_workflow()["jobs"]["fgm"]
    assert fgm["name"] == "fgm-contract-readiness-not-runtime-evidence"
    commands = "\n".join(step.get("run", "") for step in fgm["steps"])
    assert "test_authoritative_contract_conformance.py" in commands
    assert "FGM-01" not in commands


def test_aggregator_rejects_one_failed_mandatory_status_and_accepts_all_green():
    gate = load_workflow()["jobs"]["mandatory-gates"]
    assert gate["if"] == "${{ always() }}"
    script = gate["steps"][0]["run"]
    green = {f"{name.upper()}_RESULT": "success" for name in MANDATORY}
    success = subprocess.run(
        ["bash", "-euo", "pipefail", "-c", script],
        env=os.environ | green,
        capture_output=True,
        text=True,
        check=False,
    )
    assert success.returncode == 0, success.stdout + success.stderr

    red = green | {"FGM_RESULT": "failure"}
    failure = subprocess.run(
        ["bash", "-euo", "pipefail", "-c", script],
        env=os.environ | red,
        capture_output=True,
        text=True,
        check=False,
    )
    assert failure.returncode != 0


def test_evidence_status_rejects_non_qualifying_results():
    commands = "\n".join(
        step.get("run", "") for step in load_workflow()["jobs"]["evidence"]["steps"]
    )
    assert "--non-skipped" in commands
    assert "validate_runtime_evidence.py" in commands
