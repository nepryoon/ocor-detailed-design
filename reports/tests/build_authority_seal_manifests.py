#!/usr/bin/env python3
"""Build deterministic source and final manifests for the authority-seal change set."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOSSIER = ROOT / "ocor-runtime/docs/governance_dossier"
SOURCE_MANIFEST = DOSSIER / "OCOR_IRB_ADD_LLD_AUTHORITY_SEAL_SHA256SUMS"
FINAL_MANIFEST = ROOT / "reports/OCOR_IRB_ADD_LLD_FINAL_SHA256SUMS"

SOURCE_FILES = [
    "docs/OCOR_LLD_v1.1.md",
    "ocor-runtime/docs/governance_dossier/OCOR_ADD_v1.3_APPROVED_BASELINE.md",
    "ocor-runtime/docs/governance_dossier/contracts/capability-lease.schema.json",
    "ocor-runtime/docs/governance_dossier/contracts/governed-context.schema.json",
    "ocor-runtime/docs/governance_dossier/contracts/governed-memory-item.schema.json",
    "ocor-runtime/docs/governance_dossier/contracts/ocor-governed-memory.openapi.yaml",
    "ocor-runtime/docs/governance_dossier/contracts/ocor-named-query-gateway.openapi.yaml",
    "ocor-runtime/docs/governance_dossier/contracts/ocor_registry.proto",
    "ocor-runtime/docs/governance_dossier/registers/OCOR_Requirement_Register_v1.1_APPROVED.md",
    "ocor-runtime/docs/governance_dossier/registers/OCOR_Requirement_Traceability_Index_v1.1_APPROVED.md",
    "reports/OCOR_IRB_ADD_LLD_Exhaustive_Alignment_Audit_v1.0.md",
    "reports/OCOR_IRB_ADD_LLD_Remediation_Closure_v1.0.md",
    "reports/tests/irb_add_lld_audit_results.json",
    "reports/tests/irb_add_lld_initial_baseline_2026-09-01.json",
    "reports/traceability/OCOR_IRB_ADD_LLD_v1.1_Matrix.json",
    "reports/traceability/OCOR_IRB_ADD_LLD_v1.1_Matrix.md",
    "reports/tests/build_authoritative_chain_assurance.py",
    "reports/tests/build_authority_seal_manifests.py",
    "reports/tests/build_dec209_governance.py",
    "reports/tests/test_authoritative_contract_conformance.py",
    "reports/tests/validate_openapi_remediation_c.py",
]

GOVERNANCE_FILES = [
    "ocor-runtime/docs/governance_dossier/ARA_DECISION_RECORD_v1.3.md",
    "ocor-runtime/docs/governance_dossier/DEC_209_HUMAN_ROLE_ATTESTATIONS.md",
    "ocor-runtime/docs/governance_dossier/registers/OCOR_Decision_Register_v1.3_APPROVED.md",
    "ocor-runtime/docs/governance_dossier/registers/OCOR_Decision_Traceability_Index_v1.3_APPROVED.md",
    "reports/OCOR_DEC_209_Authoritative_Documentation_Assurance_Record.md",
]

FINAL_FILES = [
    "ocor-runtime/docs/governance_dossier/OCOR_IRB_ADD_LLD_AUTHORITY_SEAL_SHA256SUMS",
    "reports/OCOR_IRB_ADD_LLD_Authoritative_Audit_v1.1.md",
    "reports/tests/irb_add_lld_authoritative_audit_results.json",
    "reports/tests/authoritative_contract_conformance_results.json",
    "reports/tests/c5_openapi_validation_results.json",
    "reports/tests/v12_conformance_results.json",
    "reports/tests/v12_semantic_results.json",
    "reports/tests/v12_release_gate_results.json",
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_manifest(path: Path, names: list[str]) -> None:
    missing = [name for name in names if not (ROOT / name).is_file()]
    if missing:
        raise FileNotFoundError("missing manifest inputs: " + ", ".join(missing))
    path.write_text("\n".join(f"{digest(ROOT / name)}  {name}" for name in names) + "\n", encoding="utf-8")
    print(f"{path.relative_to(ROOT)}: {len(names)}/{len(names)} entries")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("source", "final"))
    args = parser.parse_args()
    if args.mode == "source":
        governed = [name for name in GOVERNANCE_FILES if (ROOT / name).is_file()]
        write_manifest(SOURCE_MANIFEST, SOURCE_FILES + governed)
    else:
        write_manifest(FINAL_MANIFEST, FINAL_FILES)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
