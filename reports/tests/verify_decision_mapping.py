#!/usr/bin/env python3
"""Verify DRAFT-to-approved-decision mapping and non-draft provenance."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARA = ROOT / "ocor-runtime/docs/governance_dossier/ARA_DECISION_RECORD_v1.1.md"
DECISION_REGISTER = ROOT / "ocor-runtime/docs/governance_dossier/registers/OCOR_Decision_Register_v1.1_APPROVED.md"
CHANGE_CONTROL = ROOT / "reports/OCOR_ADD_v1.2_Change_Control_Package.md"
ADD_CANDIDATE = ROOT / "reports/OCOR_Architectural_Design_Document_v1.2_Candidate.md"
OUTPUT = ROOT / "reports/tests/c7_decision_mapping_results.json"

EXPECTED_BY_DECISION = {
    "DEC-197": ["DRAFT-A"],
    "DEC-198": ["DRAFT-G"],
    "DEC-199": ["DRAFT-B"],
    "DEC-200": ["DRAFT-C"],
    "DEC-201": [],
    "DEC-202": ["DRAFT-E", "DRAFT-I"],
    "DEC-203": ["DRAFT-F"],
    "DEC-204": ["DRAFT-D", "DRAFT-H"],
    "DEC-205": [],
    "DEC-206": [],
}
EXPECTED_BY_DRAFT = {
    "DRAFT-A": "DEC-197",
    "DRAFT-B": "DEC-199",
    "DRAFT-C": "DEC-200",
    "DRAFT-D": "DEC-204",
    "DRAFT-E": "DEC-202",
    "DRAFT-F": "DEC-203",
    "DRAFT-G": "DEC-198",
    "DRAFT-H": "DEC-204",
    "DRAFT-I": "DEC-202",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decision_sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"^### (DEC-\d{3}) — .*?$", text, re.MULTILINE))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1)] = text[match.start():end]
    return sections


def check(name: str, passed: bool, detail: str) -> dict[str, object]:
    return {"check": name, "status": "PASS" if passed else "FAIL", "detail": detail}


def main() -> int:
    ara_text = ARA.read_text(encoding="utf-8")
    register_text = DECISION_REGISTER.read_text(encoding="utf-8")
    change_control_text = CHANGE_CONTROL.read_text(encoding="utf-8")
    add_text = ADD_CANDIDATE.read_text(encoding="utf-8")
    sections = decision_sections(ara_text)

    observed_by_decision: dict[str, list[str]] = {}
    register_row_counts: dict[str, int] = {}
    for decision in EXPECTED_BY_DECISION:
        section = sections.get(decision, "")
        observed_by_decision[decision] = sorted(set(re.findall(r"DRAFT-[A-I]", section)))
        register_row_counts[decision] = len(
            re.findall(rf"^\|\s*`?{re.escape(decision)}`?\s*\|", register_text, re.MULTILINE)
        )

    observed_by_draft = {
        draft: decision
        for decision, drafts in observed_by_decision.items()
        for draft in drafts
    }
    provenance_checks = {
        "DEC-201": all(
            token in (sections.get("DEC-201", "") + change_control_text + add_text)
            for token in ("CC-BA01-ALTERNATIVE", "DRF-009", "BA-01", "V12-AM-14")
        ),
        "DEC-205": all(
            token in (sections.get("DEC-205", "") + change_control_text + add_text)
            for token in ("CC-FR095-SCOPE", "DRF-012", "V12-AM-11", "DEC-103")
        ),
        "DEC-206": all(
            token in (sections.get("DEC-206", "") + change_control_text + add_text)
            for token in ("CC-DEC-ALLOCATION", "DRF-015", "V12-AM-13", "DEC-173", "DEC-175")
        ),
    }

    checks = [
        check(
            "ten_unique_ara_sections",
            set(EXPECTED_BY_DECISION).issubset(sections) and len(EXPECTED_BY_DECISION) == 10,
            f"expected={len(EXPECTED_BY_DECISION)}, present={sum(decision in sections for decision in EXPECTED_BY_DECISION)}",
        ),
        check(
            "one_register_row_per_decision",
            all(count == 1 for count in register_row_counts.values()),
            json.dumps(register_row_counts, sort_keys=True),
        ),
        check(
            "approved_mapping_matches_ara",
            observed_by_decision == EXPECTED_BY_DECISION,
            json.dumps(observed_by_decision, sort_keys=True),
        ),
        check(
            "all_nine_drafts_ratified_once",
            observed_by_draft == EXPECTED_BY_DRAFT and len(observed_by_draft) == 9,
            json.dumps(observed_by_draft, sort_keys=True),
        ),
        check(
            "combined_ratifications_are_single_records",
            register_row_counts["DEC-202"] == 1
            and register_row_counts["DEC-204"] == 1
            and observed_by_decision["DEC-202"] == ["DRAFT-E", "DRAFT-I"]
            and observed_by_decision["DEC-204"] == ["DRAFT-D", "DRAFT-H"],
            "DEC-202 and DEC-204 each have one record and two explicit provenance slugs",
        ),
        check(
            "non_draft_decision_provenance",
            all(provenance_checks.values()),
            json.dumps(provenance_checks, sort_keys=True),
        ),
    ]
    failed = [item for item in checks if item["status"] == "FAIL"]
    payload = {
        "artifact": "OCOR FASE C.7 decision mapping verification",
        "status": "PASS" if not failed else "FAIL",
        "sources": {
            str(ARA.relative_to(ROOT)): digest(ARA),
            str(DECISION_REGISTER.relative_to(ROOT)): digest(DECISION_REGISTER),
            str(CHANGE_CONTROL.relative_to(ROOT)): digest(CHANGE_CONTROL),
            str(ADD_CANDIDATE.relative_to(ROOT)): digest(ADD_CANDIDATE),
        },
        "mapping_by_draft": EXPECTED_BY_DRAFT,
        "mapping_by_decision": EXPECTED_BY_DECISION,
        "combined_ratifications": {
            "DEC-202": ["DRAFT-E", "DRAFT-I"],
            "DEC-204": ["DRAFT-D", "DRAFT-H"],
        },
        "non_draft_provenance": {
            "DEC-201": ["DRF-009", "BA-01", "V12-AM-14", "CC-BA01-ALTERNATIVE"],
            "DEC-205": ["DRF-012", "V12-AM-11", "CC-FR095-SCOPE"],
            "DEC-206": ["DRF-015", "V12-AM-13", "CC-DEC-ALLOCATION"],
        },
        "checks": checks,
        "counts": {"checks": len(checks), "passed": len(checks) - len(failed), "failed": len(failed)},
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload["counts"], ensure_ascii=False))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
