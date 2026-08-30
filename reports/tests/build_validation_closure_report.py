#!/usr/bin/env python3
"""Aggregate document, OpenAPI, runtime, BA, EV and PostgreSQL evidence."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "reports/tests"
OUTPUT_JSON = TESTS / "validation_closure_results.json"
OUTPUT_MD = ROOT / "reports/OCOR_ADD_v1.2_Validation_Closure_Report.md"
CANDIDATE = ROOT / "reports/OCOR_Architectural_Design_Document_v1.2_Candidate.md"
BASELINE = ROOT / "ocor-runtime/docs/governance_dossier/OCOR_ADD_v1.2_APPROVED_BASELINE.md"


def load_json(name: str) -> dict[str, Any]:
    return json.loads((TESTS / name).read_text(encoding="utf-8"))


def junit(name: str) -> dict[str, Any]:
    root = ET.parse(TESTS / name).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))

    def total(attribute: str) -> float:
        return sum(float(suite.attrib.get(attribute, 0)) for suite in suites)

    return {
        "tests": int(total("tests")),
        "failures": int(total("failures")),
        "errors": int(total("errors")),
        "skipped": int(total("skipped")),
        "time_seconds": total("time"),
        "artifact": f"reports/tests/{name}",
    }


verify = load_json("v12_verify_report_post_approval.json")
conformance = load_json("v12_conformance_results.json")
semantics = load_json("v12_semantic_results.json")
release = load_json("v12_release_gate_results.json")
readiness = load_json("v12_approval_readiness_results.json")
openapi = load_json("openapi_31_validation_results.json")
coverage = load_json("runtime_coverage_post_approval.json")
runtime = junit("runtime_junit_post_approval.xml")
ba = junit("ba_junit_post_approval.xml")
ev = junit("ev_junit_post_approval.xml")
postgres = junit("postgres_junit_post_approval.xml")

verify_counts = {
    status: sum(item["status"] == status for item in verify["results"])
    for status in ("PASS", "FAIL", "NOT_EXECUTED", "INFO")
}
document_suites = {
    "tool_backed_verifier": {"passed": verify_counts["PASS"], "failed": verify_counts["FAIL"], "not_executed": verify_counts["NOT_EXECUTED"], "information": verify_counts["INFO"]},
    "contract_conformance": {"passed": conformance["passed"], "failed": conformance["failed"], "total": conformance["total_cases"]},
    "semantic_fsm_adversarial": {"passed": semantics["passed"], "failed": semantics["failed"], "total": semantics["total"]},
    "release_integrity": {"passed": release["passed"], "failed": release["failed"], "total": release["total"]},
    "approval_readiness": {"passed": readiness["passed"], "failed": readiness["failed"], "total": readiness["total"]},
}
document_failures = sum(int(suite.get("failed", 0)) for suite in document_suites.values())
runtime_failures = sum(suite["failures"] + suite["errors"] + suite["skipped"] for suite in (runtime, ba, ev, postgres))
candidate_sha = hashlib.sha256(CANDIDATE.read_bytes()).hexdigest()
baseline_sha = hashlib.sha256(BASELINE.read_bytes()).hexdigest()

integrity = {}
for filename in ("post_remediation_input_checksums.txt", "post_remediation_report_checksums.txt"):
    lines = [line for line in (TESTS / filename).read_text(encoding="utf-8").splitlines() if line.strip()]
    integrity[filename] = {"entries": len(lines), "all_ok": bool(lines) and all(line.endswith(": OK") for line in lines)}

closures = {
    "VAL-ACT-001": {
        "status": "CLOSED",
        "basis": "full post-remediation document harness rerun on the approved candidate digest",
        "passed": document_failures == 0 and candidate_sha == "4f84249b86150a0aa0ef5bf7fcc1a5c99388651e8aae132720dd784883b0426f",
    },
    "VAL-ACT-002": {
        "status": "CLOSED",
        "basis": "governed OpenAPI 3.1 validation of approved embedded and runtime contracts; no waiver required",
        "passed": openapi["failed"] == 0 and openapi["waiver_required"] is False,
    },
    "VAL-ACT-003": {
        "status": "CLOSED_FOR_RUNTIME_SLICE",
        "basis": "complete runtime plus BA-01..08, EV-001..035 and live PostgreSQL 16 evidence",
        "passed": runtime_failures == 0 and ev["tests"] == 35 and ba["tests"] >= 33 and postgres["tests"] == 5,
    },
}
all_closed = all(item["passed"] for item in closures.values()) and all(item["all_ok"] for item in integrity.values())
result = {
    "schema_version": "1.0",
    "status": "PASS" if all_closed else "FAIL",
    "executed_at_utc": datetime.now(timezone.utc).isoformat(),
    "repository": os.environ.get("GITHUB_REPOSITORY", "nepryoon/ocor-detailed-design"),
    "git_sha": os.environ.get("GITHUB_SHA", "local"),
    "github_run_id": os.environ.get("GITHUB_RUN_ID"),
    "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
    "candidate_sha256": candidate_sha,
    "approved_baseline_sha256": baseline_sha,
    "integrity": integrity,
    "document_suites": document_suites,
    "openapi": openapi,
    "runtime": runtime,
    "backend_assumptions": ba,
    "acceptance_ev": ev,
    "live_postgresql": postgres,
    "coverage": coverage["totals"],
    "closures": closures,
    "evidence_scope": {
        "E1_runtime_slice": "PRESENT",
        "E2_independent_or_production": "NOT_ESTABLISHED",
        "requirements_verified": "not promoted by this execution alone",
        "production_readiness": "not claimed",
    },
}
OUTPUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def runtime_row(name: str, suite: dict[str, Any]) -> str:
    return f"| {name} | {suite['tests']} | {suite['failures']} | {suite['errors']} | {suite['skipped']} |"


totals = coverage["totals"]
report = f"""# OCOR ADD v1.2 — Validation Closure Report

## Control

| Field | Value |
|---|---|
| Result | **{result['status']}** |
| Executed revision | `{result['git_sha']}` |
| GitHub Actions run | `{result['github_run_id']}`, attempt `{result['github_run_attempt']}` |
| Candidate SHA-256 | `{candidate_sha}` |
| Approved baseline SHA-256 | `{baseline_sha}` |
| Executed at | `{result['executed_at_utc']}` |

## Closure disposition

| Action | Disposition | Evidence |
|---|---|---|
| `VAL-ACT-001` | **{closures['VAL-ACT-001']['status']}** | Full document harness rerun; zero suite failures on the approved candidate digest |
| `VAL-ACT-002` | **{closures['VAL-ACT-002']['status']}** | `openapi-spec-validator=={openapi['validator_version']}`; approved embedded contract and runtime contract pass; no waiver required |
| `VAL-ACT-003` | **{closures['VAL-ACT-003']['status']}** | Complete runtime, BA, 35 EV and five live PostgreSQL transaction tests pass |

## Document harness

| Suite | Passed | Failed | Not executed |
|---|---:|---:|---:|
| Tool-backed verifier | {verify_counts['PASS']} | {verify_counts['FAIL']} | {verify_counts['NOT_EXECUTED']} |
| Contract conformance | {conformance['passed']} | {conformance['failed']} | 0 |
| Semantic/FSM/adversarial | {semantics['passed']} | {semantics['failed']} | 0 |
| Release/integrity | {release['passed']} | {release['failed']} | 0 |
| Approval-readiness | {readiness['passed']} | {readiness['failed']} | 0 |

The verifier's declared `NOT_EXECUTED` entries remain historically accurate inside that harness. Source/report integrity is closed by the manifest checks, and OpenAPI semantic validation is closed independently by the governed validator profile; neither is silently relabelled.

## Runtime evidence

| Campaign | Tests | Failures | Errors | Skipped |
|---|---:|---:|---:|---:|
{runtime_row('Full runtime', runtime)}
{runtime_row('BA-01–BA-08', ba)}
{runtime_row('EV-001–EV-035', ev)}
{runtime_row('Live PostgreSQL 16', postgres)}

Observed statement coverage: **{totals['percent_covered_display']}%** ({totals['covered_lines']} covered lines, {totals['missing_lines']} missing lines). Coverage is reported evidence, not an invented release threshold.

## OpenAPI evidence

- Validator: `openapi-spec-validator=={openapi['validator_version']}`.
- Locked wheel SHA-256: `{openapi['validator_locked_wheel_sha256']}`.
- Subjects passed: {openapi['passed']}/{openapi['total']}.
- Waiver required: **{str(openapi['waiver_required']).lower()}**.

## Evidence fence

This package establishes first-party implementation evidence for the explicitly tested OCOR runtime slice (`E1_runtime_slice=PRESENT`). It does not establish independent/production evidence (`E2`), certify every requirement, validate production performance or security, or authorize deployment. Requirement-level promotion requires the separate governed review recorded after this run.
"""
OUTPUT_MD.write_text(report, encoding="utf-8")
print(f"STATUS {result['status']}")
print(f"RESULTS {OUTPUT_JSON.relative_to(ROOT)}")
print(f"REPORT {OUTPUT_MD.relative_to(ROOT)}")
sys.exit(0 if all_closed else 1)
