#!/usr/bin/env python3
"""Build the non-self-referential SHA-256 manifest for DEC-208 promotion."""

from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "ocor-runtime/docs/governance_dossier/OCOR_ADD_v1.3_APPROVAL_SHA256SUMS"

FILES = [
    ".github/workflows/ocor-validation-closure.yml",
    "docs/OCOR_LLD_v1.1.md",
    "ocor-runtime/docs/governance_dossier/ARA_DECISION_RECORD_v1.2.md",
    "ocor-runtime/docs/governance_dossier/DEC_208_HUMAN_ROLE_ATTESTATIONS.md",
    "ocor-runtime/docs/governance_dossier/OCOR_ADD_v1.3_APPROVED_BASELINE.md",
    "ocor-runtime/docs/governance_dossier/contracts/capability-lease.schema.json",
    "ocor-runtime/docs/governance_dossier/contracts/governed-context.schema.json",
    "ocor-runtime/docs/governance_dossier/contracts/governed-memory-item.schema.json",
    "ocor-runtime/docs/governance_dossier/contracts/ocor-governed-memory.openapi.yaml",
    "ocor-runtime/docs/governance_dossier/contracts/ocor-named-query-gateway.openapi.yaml",
    "ocor-runtime/docs/governance_dossier/contracts/ocor_registry.proto",
    "ocor-runtime/docs/governance_dossier/registers/OCOR_CAP_ELM_Requirement_Crosswalk_v1.1_APPROVED.md",
    "ocor-runtime/docs/governance_dossier/registers/OCOR_Decision_Register_v1.2_APPROVED.md",
    "ocor-runtime/docs/governance_dossier/registers/OCOR_Decision_Traceability_Index_v1.2_APPROVED.md",
    "ocor-runtime/docs/governance_dossier/registers/OCOR_Requirement_Register_v1.1_APPROVED.md",
    "ocor-runtime/docs/governance_dossier/registers/OCOR_Requirement_Traceability_Index_v1.1_APPROVED.md",
    "reports/OCOR_DEC_208_Authoritative_Promotion_Record.md",
    "reports/tests/build_dec208_approval_manifest.py",
    "reports/tests/verify_dec208_authoritative_promotion.py",
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    missing = [name for name in FILES if not (ROOT / name).is_file()]
    if missing:
        raise FileNotFoundError("missing manifest inputs: " + ", ".join(missing))
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(
        "\n".join(f"{digest(ROOT / name)}  {name}" for name in FILES) + "\n",
        encoding="utf-8",
    )
    print(f"DEC-208 approval manifest: {len(FILES)}/{len(FILES)} entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
