#!/usr/bin/env python3
"""Verify the complete DEC-208 authoritative promotion set."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOSSIER = ROOT / "ocor-runtime/docs/governance_dossier"
REG = DOSSIER / "registers"
CONTRACTS = DOSSIER / "contracts"
MANIFEST = DOSSIER / "OCOR_ADD_v1.3_APPROVAL_SHA256SUMS"
RESULTS = ROOT / "reports/tests/dec208_authoritative_promotion_results.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def row_count(text: str, identifier: str) -> int:
    return len(re.findall(rf"^\|\s*`?{re.escape(identifier)}`?\s*\|", text, re.MULTILINE))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-no-git", action="store_true")
    args = parser.parse_args()
    checks: list[dict[str, object]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "status": "PASS" if passed else "FAIL", "detail": detail})

    required = [
        DOSSIER / "OCOR_ADD_v1.3_APPROVED_BASELINE.md",
        ROOT / "docs/OCOR_LLD_v1.1.md",
        DOSSIER / "ARA_DECISION_RECORD_v1.2.md",
        DOSSIER / "DEC_208_HUMAN_ROLE_ATTESTATIONS.md",
        REG / "OCOR_Requirement_Register_v1.1_APPROVED.md",
        REG / "OCOR_Requirement_Traceability_Index_v1.1_APPROVED.md",
        REG / "OCOR_Decision_Register_v1.2_APPROVED.md",
        REG / "OCOR_Decision_Traceability_Index_v1.2_APPROVED.md",
        REG / "OCOR_CAP_ELM_Requirement_Crosswalk_v1.1_APPROVED.md",
        CONTRACTS / "governed-memory-item.schema.json",
        CONTRACTS / "governed-context.schema.json",
        CONTRACTS / "ocor-governed-memory.openapi.yaml",
        MANIFEST,
    ]
    check("atomic_artifacts_present", all(p.is_file() for p in required), f"{sum(p.is_file() for p in required)}/{len(required)}")

    manifest_lines = MANIFEST.read_text(encoding="utf-8").splitlines() if MANIFEST.is_file() else []
    manifest_ok = True
    for line in manifest_lines:
        expected, rel = line.split("  ", 1)
        path = ROOT / rel
        manifest_ok &= path.is_file() and sha(path) == expected
    check("approval_manifest", manifest_ok and len(manifest_lines) == 19, f"{len(manifest_lines)}/19 entries")

    rr = (REG / "OCOR_Requirement_Register_v1.1_APPROVED.md").read_text(encoding="utf-8")
    rti = (REG / "OCOR_Requirement_Traceability_Index_v1.1_APPROVED.md").read_text(encoding="utf-8")
    dr = (REG / "OCOR_Decision_Register_v1.2_APPROVED.md").read_text(encoding="utf-8")
    dti = (REG / "OCOR_Decision_Traceability_Index_v1.2_APPROVED.md").read_text(encoding="utf-8")
    cw = (REG / "OCOR_CAP_ELM_Requirement_Crosswalk_v1.1_APPROVED.md").read_text(encoding="utf-8")
    add = (DOSSIER / "OCOR_ADD_v1.3_APPROVED_BASELINE.md").read_text(encoding="utf-8")
    lld = (ROOT / "docs/OCOR_LLD_v1.1.md").read_text(encoding="utf-8")
    ara = (DOSSIER / "ARA_DECISION_RECORD_v1.2.md").read_text(encoding="utf-8")

    req_ids = re.findall(r"^\|\s*`?((?:BR|FR|NFR)-\d{3})`?\s*\|", rr, re.MULTILINE)
    check("requirement_universe", len(set(req_ids)) == 285, f"{len(set(req_ids))}/285 unique")
    check("fr118_fr119_poc", all(row_count(rr, rid) == 1 for rid in ("FR-118", "FR-119")) and "`FGM-16`" in rr and "| PoC |" in next(x for x in rr.splitlines() if x.startswith("| `FR-118`")), "FR-118/119 preserved P0/PoC")
    check("rti_evidence_fence", "evidence state: specified/planned, E1=0, E2=0" in next(x for x in rti.splitlines() if x.startswith("| FR-118 |")) and "evidence state: specified/planned, E1=0, E2=0" in next(x for x in rti.splitlines() if x.startswith("| FR-119 |")), "specified/planned only")
    check("elm084_core_poc", row_count(cw, "ELM-084") == 1 and "`CORE/P0/PoC`" in next(x for x in cw.splitlines() if x.startswith("| `ELM-084`")), "ELM-084 promoted in crosswalk")
    check("dec208_register_rows", row_count(dr, "DEC-208") == 1 and row_count(dti, "DEC-208") == 1, "one DEC-208 row in DR and DTI")
    check("dec207_preserved", row_count(dr, "DEC-207") == 1 and row_count(dti, "DEC-207") == 1, "DEC-207 included without rewrite")
    check("add_lld_approved", "APPROVED ARCHITECTURAL BASELINE — DEC-208" in add and "APPROVED TECHNICAL BASELINE — DEC-208" in lld, "ADD v1.3 and LLD v1.1 approved")
    check("add_composition", "# Part I — ADD v1.2 incorporated verbatim" in add and "# Part II — DEC-208 Full Governed Agent Memory amendment" in add, "complete composite baseline")
    add_digest = sha(DOSSIER / "OCOR_ADD_v1.3_APPROVED_BASELINE.md")
    check("lld_add_digest", add_digest in lld, add_digest)

    memory = json.loads((CONTRACTS / "governed-memory-item.schema.json").read_text(encoding="utf-8"))
    check("memory_closed_schema", memory.get("additionalProperties") is False and len(memory.get("required", [])) >= 30, f"{len(memory.get('required', []))} required")
    check("memory_taxonomy", set(memory["properties"]["memory_kind"]["enum"]) == {"WORKING", "EPISODIC", "SEMANTIC", "PROCEDURAL", "PREFERENCE", "REFLECTION", "DISSENT", "TEAM_SHARED"}, "8/8 kinds")
    check("memory_scopes", set(memory["properties"]["memory_scope"]["enum"]) == {"RUN", "TASK", "AGENT", "TEAM", "PROJECT", "DOMAIN", "FEDERATED"}, "7/7 scopes")

    fence_text = "\n".join((rr, rti, dr, dti, cw, add, lld, ara))
    check("evidence_fence", all(token in fence_text for token in ("E1=0", "E2=0", "NO-GO")) and "evidence state: Verified" not in fence_text, "no evidence promotion")
    check("deferred_fences", all(token in ara for token in ("FR-048", "ELM-011", "Candidate Implementation")), "unrelated deferrals preserved")
    check("approval_attestations", "Product Owner approval evidence" in ara and "Architecture Review Authority approval evidence" in ara, "two role attestations")
    check("p01_p12", all(f"| P-{i:02d} | PASS |" in ara for i in range(1, 13)), "P-01..P-12 PASS")

    git_dir = ROOT / ".git"
    if git_dir.exists():
        proc = subprocess.run(["git", "diff", "--quiet", "origin/main", "--", "inputs"], cwd=ROOT)
        check("inputs_immutable", proc.returncode == 0, f"git diff exit={proc.returncode}")
    else:
        check("inputs_immutable", args.allow_no_git, "staging tree; enforced again in CI")

    failed = [item for item in checks if item["status"] == "FAIL"]
    payload = {
        "artifact": "DEC-208 authoritative promotion",
        "decision": "DEC-208",
        "verdict": "PASS" if not failed else "FAIL",
        "counts": {"checks": len(checks), "passed": len(checks) - len(failed), "failed": len(failed)},
        "runtime_disposition": "NO-GO pending FGM-01..FGM-20",
        "evidence_fence": {"E1": 0, "E2": 0, "global_verified": 0, "E1_runtime_slice": "confined_to_DEC-207"},
        "checks": checks,
    }
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload["counts"]))
    print(payload["verdict"])
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
