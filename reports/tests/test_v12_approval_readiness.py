#!/usr/bin/env python3
"""Executable 18-check approval-readiness regression suite."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / "reports/OCOR_Architectural_Design_Document_v1.2_Candidate.md"
PACKAGE = ROOT / "reports/OCOR_ADD_v1.2_Change_Control_Package.md"
LEDGER = ROOT / "reports/OCOR_ADD_v1.2_Remediation_Ledger.md"
OUTPUT = ROOT / "reports/tests/v12_approval_readiness_results.json"

candidate = CANDIDATE.read_text(encoding="utf-8")
package = PACKAGE.read_text(encoding="utf-8")
ledger = LEDGER.read_text(encoding="utf-8")
records = []


def check(name: str, passed: bool, detail: str) -> None:
    records.append({"check": name, "status": "PASS" if passed else "FAIL", "detail": detail})


expected_mappings = {
    "V12-AM-02": ("DRF-001", "DRF-002", "ARF-001"),
    "V12-AM-03": ("DRF-003", "DRF-008", "RV-01"),
    "V12-AM-04": ("DRF-004", "ARF-006"),
    "V12-AM-05": ("DRF-005", "ARF-004", "ARF-012"),
    "V12-AM-06": ("DRF-013", "ARF-014"),
    "V12-AM-07": ("V12-RF-001", "ARF-009"),
    "V12-AM-08": ("DRF-008", "V12-RF-002", "ARF-005"),
    "V12-AM-09": ("DRF-007", "ARF-007"),
    "V12-AM-10": ("DRF-006", "ARF-018"),
    "V12-AM-11": ("DRF-012", "FR-095", "ELM-070"),
    "V12-AM-13": ("DRF-015",),
    "V12-AM-14": ("DRF-009", "BA-01"),
}
for amendment, tokens in expected_mappings.items():
    row = next((line for line in candidate.splitlines() if line.startswith(f"| `{amendment}` |")), "")
    check(f"{amendment} finding mapping", bool(row) and all(token in row for token in tokens), "/".join(tokens))

change_sets = re.findall(r"^## (CC-[A-Z0-9-]+)\b", package, re.MULTILINE)
check("change-set count", len(change_sets) == 10 and len(set(change_sets)) == 10, f"{len(change_sets)} decision-ready change sets")
check("DRAFT-C decision path", "## CC-SINGLE-WRITER-BRANCH-SCOPE" in package and "DRAFT-C" in package, "Dedicated CC-SINGLE-WRITER-BRANCH-SCOPE")
check("DRAFT-C DAG", all(edge in package for edge in ("CC-SINGLE-WRITER-BRANCH-SCOPE → CC-CANONICAL-PATH", "CC-BA01-ALTERNATIVE → CC-SINGLE-WRITER-BRANCH-SCOPE")), "Dependency chain complete")
check("BA-01 deterministic disposition", all(phrase in package for phrase in ("Nessun fallback è pre-approvato", "la release è `NO-GO`", "commit locale atomico")), "Atomic invariant; no fallback; NO-GO")
check("ledger dependency closure", "CC-SINGLE-WRITER-BRANCH-SCOPE" in ledger and "DRAFT-C" in ledger, "DRAFT-C closure path recorded")
check("authority fence preserved", "PROPOSED — AWAITING CHANGE CONTROL" in candidate and "Nessun identificativo" in candidate and "E1=0" in candidate and "E2=0" in candidate, "Immutable candidate retains historical authority fence")

failed = [item for item in records if item["status"] != "PASS"]
result = {
    "source_candidate": str(CANDIDATE.relative_to(ROOT)),
    "candidate_sha256": hashlib.sha256(CANDIDATE.read_bytes()).hexdigest(),
    "change_control_sha256": hashlib.sha256(PACKAGE.read_bytes()).hexdigest(),
    "remediation_ledger_sha256": hashlib.sha256(LEDGER.read_bytes()).hexdigest(),
    "total": len(records),
    "passed": len(records) - len(failed),
    "failed": len(failed),
    "scope": "Approval-readiness traceability, decision coverage, DAG, BA-01 disposition and immutable candidate authority fence.",
    "records": records,
}
OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
for item in records:
    print(f"{item['status']} — {item['check']}")
print(f"TOTAL {result['total']} PASS {result['passed']} FAIL {result['failed']}")
print(f"RESULTS {OUTPUT.relative_to(ROOT)}")
sys.exit(1 if failed else 0)
