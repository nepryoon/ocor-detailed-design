#!/usr/bin/env python3
"""Build complete decision-register successors for DEC-209."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REG = ROOT / "ocor-runtime/docs/governance_dossier/registers"


def main() -> int:
    source_register = REG / "OCOR_Decision_Register_v1.2_APPROVED.md"
    source_trace = REG / "OCOR_Decision_Traceability_Index_v1.2_APPROVED.md"
    register = REG / "OCOR_Decision_Register_v1.3_APPROVED.md"
    trace = REG / "OCOR_Decision_Traceability_Index_v1.3_APPROVED.md"

    register.write_text(
        "# OCOR — Decision Register v1.3 — APPROVED\n\n"
        "> Snapshot autoritativo completo. Incorpora senza modifica il Decision Register v1.2 e aggiunge esclusivamente `DEC-209`, assegnato dopo verifica di `origin/main`, remoti, storia completa, registri, indici, ARA record, report e draft.\n\n"
        + source_register.read_text(encoding="utf-8")
        + "\n\n## DEC-209 — Documentation authority seal\n\n"
        + "| ID | Change set | Titolo | Disposizione | Razionale | Scope | Stato | Data efficacia | Supersedes | Evidence fence | Approval mode | Authorization |\n"
        + "|---|---|---|---|---|---|---|---|---|---|---|---|\n"
        + "| DEC-209 | CC-IRB-ADD-LLD-AUTHORITY-SEAL | IRB–ADD–LLD authoritative documentation assurance and editorial errata | APPROVED — EFFECTIVE ON MERGE | Elimina contraddizioni di stato residue, rende autoritativo l'audit corrente e rende bloccanti traceability, contract e stale-wording gate senza cambiare semantica | RR/RTI wording, LLD v1.1 errata, matrice 285/285, closure, audit, checker e manifest | Approved | 2026-09-01 on merge | Solo le disposition pre-promozione residue nei file correnti; preserva integralmente DEC-208 | E1=0; E2=0; global Verified=0; runtime e Production NO-GO | explicit human authorization; Product Owner and ARA dual-hat, one human not two independent reviewers | current conversation mandate dated 2026-09-01 |\n",
        encoding="utf-8",
    )
    trace.write_text(
        "# OCOR — Decision Traceability Index v1.3 — APPROVED\n\n"
        "> Snapshot autoritativo completo. Incorpora senza modifica il Decision Traceability Index v1.2 e aggiunge esclusivamente `DEC-209`.\n\n"
        + source_trace.read_text(encoding="utf-8")
        + "\n\n## DEC-209 — Traceability\n\n"
        + "| Decisione | Origine | Decisione/esito e condizioni | Approval / authorization | Obiettivi | Capability | Componenti | Requisiti | Registri collegati | Fonte di controllo |\n"
        + "|---|---|---|---|---|---|---|---|---|---|\n"
        + "| DEC-209 | `CC-IRB-ADD-LLD-AUTHORITY-SEAL` | Approva l'errata editoriale e il seal di assurance della catena IRB→ADD→LLD; zero variazioni normative a priorità, release, comportamento o capability; runtime `NO-GO` | explicit human authorization; Product Owner/ARA dual-hat; 2026-09-01 | OBJ-003, OBJ-004, OBJ-007 | CAP-001–CAP-026 preservate; ELM-084 CORE/P0/PoC preservata | Configuration Management; Documentation Assurance; C1–C8 design | 285/285 `FULLY_SPECIFIED` a design level; evidence specified/planned | RR v1.1; RTI v1.1; DR v1.3; DTI v1.3; ADD v1.3; LLD v1.1; matrix v2.0 | ARA Decision Record v1.3; authority-seal manifest; audit v1.1; contract conformance |\n",
        encoding="utf-8",
    )
    print("DEC-209 register successors: 2/2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
