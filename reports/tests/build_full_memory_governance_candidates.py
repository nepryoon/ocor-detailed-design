#!/usr/bin/env python3
"""Materialize and verify the atomic register update for full PoC memory.

The approved snapshots remain immutable.  This script creates complete candidate
snapshots under reports/, preserving historic decisions and reserving allocation
of the next DEC identifier to the competent approval authority.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve()
if HERE.parents[2].name == "remediation-output":
    ROOT = HERE.parents[3]
    OUT = ROOT / "remediation-output" / "reports"
else:
    ROOT = HERE.parents[2]
    OUT = ROOT / "reports"

DEST = OUT / "governance_candidates"
RESULTS = OUT / "tests" / "full_memory_governance_candidate_results.json"
MANIFEST = OUT / "OCOR_FULL_MEMORY_GOVERNANCE_CANDIDATE_SHA256SUMS"
SOURCE_REF = "origin/main"
REGISTER_ROOT_REL = Path("ocor-runtime/docs/governance_dossier/registers")
REGISTER_ROOT = ROOT / REGISTER_ROOT_REL


SOURCES = {
    "requirement_register": (
        "OCOR_Requirement_Register_v1.0_APPROVED.md",
        "OCOR_Requirement_Register_v1.1_FULL_MEMORY_CANDIDATE.md",
    ),
    "requirement_traceability": (
        "OCOR_Requirement_Traceability_Index_v1.0_APPROVED.md",
        "OCOR_Requirement_Traceability_Index_v1.1_FULL_MEMORY_CANDIDATE.md",
    ),
    "decision_register": (
        "OCOR_Decision_Register_v1.1_APPROVED.md",
        "OCOR_Decision_Register_v1.2_FULL_MEMORY_CANDIDATE.md",
    ),
    "decision_traceability": (
        "OCOR_Decision_Traceability_Index_v1.1_APPROVED.md",
        "OCOR_Decision_Traceability_Index_v1.2_FULL_MEMORY_CANDIDATE.md",
    ),
    "cap_elm_crosswalk": (
        "OCOR_CAP_ELM_Requirement_Crosswalk_v1.0_APPROVED.md",
        "OCOR_CAP_ELM_Requirement_Crosswalk_v1.1_FULL_MEMORY_CANDIDATE.md",
    ),
}


def git_bytes(*args: str) -> bytes:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {detail}")
    return completed.stdout


def source_commit() -> str:
    return git_bytes("rev-parse", f"{SOURCE_REF}^{{commit}}").decode("ascii").strip()


def source_path(name: str) -> Path:
    source = REGISTER_ROOT / name
    if not source.is_file():
        raise FileNotFoundError(f"required authoritative register is missing: {source}")
    relative = source.relative_to(ROOT)
    authoritative_bytes = git_bytes("show", f"{SOURCE_REF}:{relative.as_posix()}")
    working_bytes = source.read_bytes()
    if working_bytes != authoritative_bytes:
        raise RuntimeError(
            f"authoritative source mismatch for {relative}: working-tree bytes differ from {SOURCE_REF}"
        )
    return source


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_row(text: str, identifier: str, replacement: str) -> str:
    pattern = re.compile(rf"^\|\s*`?{re.escape(identifier)}`?\s*\|.*$", re.MULTILINE)
    matches = pattern.findall(text)
    if len(matches) != 1:
        raise ValueError(f"expected exactly one row for {identifier}, found {len(matches)}")
    return pattern.sub(replacement, text)


def candidate_header(kind: str, source: Path) -> str:
    relative = source.relative_to(ROOT).as_posix()
    return (
        f"# OCOR — {kind} — FULL GOVERNED MEMORY CANDIDATE\n\n"
        "> **Snapshot candidato completo; non ancora autoritativo.** Derivato senza modificare "
        f"`{SOURCE_REF}@{source_commit()}:{relative}` (SHA-256 `{sha256(source)}`) per il change set "
        "`CC-FULL-GOVERNED-AGENT-MEMORY`. Diventa efficace soltanto con promozione atomica "
        "dei cinque registri e assegnazione dell'identificativo decisionale da parte "
        "dell'autorità competente. Preserva `E1=0`, `E2=0` e non dichiara implementazione, "
        "verifica runtime o Production readiness.\n\n"
    )


def build_requirement_register(source: Path) -> str:
    text = source.read_text(encoding="utf-8")
    text = replace_row(
        text,
        "FR-118",
        "| `FR-118` | Memoria agentica governata completa | Ogni Governed Memory Item DEVE essere una versione immutabile e tipizzata come WORKING, EPISODIC, SEMANTIC, PROCEDURAL, PREFERENCE, REFLECTION, DISSENT o TEAM_SHARED; DEVE dichiarare owner, scope RUN/TASK/AGENT/TEAM/PROJECT/DOMAIN/FEDERATED, tenant/domain/compartment, source ed evidence/provenance, created/valid time, marking, purpose, confidence/uncertainty, taint, instruction eligibility, TTL/retention/legal hold, content e representation digest. Il PoC DEVE supportare persistenza cross-run, consolidamento, correzione, supersession, revoca, expiry, forgetting, deletion saga e promotion proposal; la memoria resta non canonica e non conferisce Authority. | FR | Dimostrare nel PoC l'architettura finale della memoria, limitando scala e resilienza ma non le capacità semantiche o di governance. | Fonte B §79; `DEC-116`; `CC-FULL-GOVERNED-AGENT-MEMORY` (candidate) | P0 | `FGM-01`–`FGM-04`, `FGM-06`–`FGM-15` e `FGM-18`–`FGM-20` superati; ogni versione è replayable e ogni influenza sul contesto ha receipt; nessuna promozione canonica diretta. | schema, lifecycle, replay, fault-injection e security test | C8 Memory Service; metadata/content stores; full-text/vector indexes; event journal; C6/C3 promotion path | Confermato | PoC | Q10.7 |",
    )
    text = replace_row(
        text,
        "FR-119",
        "| `FR-119` | Isolamento e non-interferenza del retrieval | Ogni retrieval STRUCTURED, FULL_TEXT, VECTOR o HYBRID DEVE essere policy-filtered prima della ricerca e prima della materializzazione, applicando identity, Authority, purpose, marking, lifecycle e scope anche a embedding, indici, cache, ranking e federazione. Elementi non autorizzati NON DEVONO influenzare contenuto, esistenza, count, rank, score, paginazione, spiegazione, cache hit, forma dell'errore o timing bucket osservabile. Cross-tenant è deny-by-default; cross-project/domain/federated richiede Authority esplicita e policy compatibile. | FR | Prevenire leakage diretto e laterale pur esercitando nel PoC l'intera superficie di retrieval della memoria. | `ARC-016`; Fonte B §§33,79; `DEC-116`; `CC-FULL-GOVERNED-AGENT-MEMORY` (candidate) | P0 | `FGM-05`, `FGM-08`, `FGM-10`, `FGM-16` e `FGM-17` producono zero cross-tenant/cross-compartment disclosure o influenza non autorizzata, incluse race di revoca e kill switch. | non-interference, adversarial, side-channel e security test | C8 Memory Service; Policy/Authority Engine; partitioned full-text/vector adapters; audit | Confermato | PoC | Q10.7 |",
    )
    return candidate_header("Requirement Register v1.1", source) + text


def build_requirement_traceability(source: Path) -> str:
    text = source.read_text(encoding="utf-8")
    text = replace_row(
        text,
        "FR-118",
        "| FR-118 | Q10.7; DEC-116; CC-FULL-GOVERNED-AGENT-MEMORY (candidate) | Fonte B §79; DEC-116; full-memory change-control package | OBJ-003, OBJ-006, OBJ-007 | CAP-020, CAP-022, ELM-084 | agenti governati; full governed memory | C8 Agent Kernel/Memory Service; metadata/content stores; full-text/vector projections; C6/C3 promotion path | `FGM-01`–`FGM-04`, `FGM-06`–`FGM-15` e `FGM-18`–`FGM-20`: tutti i kind/scope, cross-run persistence, versioning, consolidation, correction, lifecycle, deletion e context receipts; nessuna Authority o canonizzazione diretta. | schema + lifecycle + replay + fault-injection + security test; evidence state: specified/planned, E1=0, E2=0 | ARC-010; ARC-015; RSK-031; EV-026; memory contract; policy; clock; event journal | Confermato; PoC |",
    )
    text = replace_row(
        text,
        "FR-119",
        "| FR-119 | Q10.7; DEC-116; CC-FULL-GOVERNED-AGENT-MEMORY (candidate) | ARC-016; Fonte B §§33,79; DEC-116; full-memory change-control package | OBJ-003, OBJ-006, OBJ-007 | CAP-020, CAP-022, ELM-084 | agenti governati; full governed memory | C8 Memory Service; Policy/Authority Engine; policy-partitioned structured/full-text/vector/hybrid adapters; audit | `FGM-05`, `FGM-08`, `FGM-10`, `FGM-16` e `FGM-17`: zero leakage o influenza non autorizzata su contenuto, esistenza, count, rank, score, cache, errori e timing; revoca/kill switch fail-closed. | non-interference + adversarial + side-channel test; evidence state: specified/planned, E1=0, E2=0 | ARC-016; RSK-031; EV-026; marking lattice; GCS; authority and federation policies | Confermato; PoC |",
    )
    return candidate_header("Requirement Traceability Index v1.1", source) + text


DECISION_PROPOSAL = """

## Candidate change-control entry — identifier allocation reserved to the authority

The following row is a proposal carried by this complete candidate snapshot. It is not an
approved `DEC-*` entry and has no effective date until the five-register atomic promotion.
Historic `DEC-116` and `DEC-196` remain unchanged; on promotion, the allocated decision
supersedes only the `ELM-084` deferral recorded by `DEC-196`, not its approval of the IRB.

| Change set | Proposed disposition | Candidate status | Supersedes on promotion | Approval / authorization |
|---|---|---|---|---|
| `CC-FULL-GOVERNED-AGENT-MEMORY` | Promote `ELM-084` to `CORE/P0/PoC` with the `FULL_GOVERNED_AGENT_MEMORY` profile. The PoC implements all memory kinds/scopes, cross-run persistence, structured/full-text/vector/hybrid retrieval, governed consolidation/lifecycle/deletion, context receipts and C6/C3-only promotion. Only scale, HA, SLO and E2 remain later-gate concerns. | `PROPOSED — DECISION ID UNASSIGNED` | The `ELM-084` deferral clause of `DEC-196`; retains `DEC-116`, `FR-118`, `FR-119`, all epistemic/authority fences and `E1=0`, `E2=0`. | Explicit requester direction dated 2026-08-31; formal identifier and effective date reserved to Product Owner / ARA. |
"""


TRACE_PROPOSAL = """

## Candidate decision trace — identifier allocation reserved to the authority

| Change set | Origin | Proposed outcome and conditions | Approval state | Objectives | Capability / element | Components | Requirements | Registers and tests | Control source |
|---|---|---|---|---|---|---|---|---|---|
| `CC-FULL-GOVERNED-AGENT-MEMORY` | Requester disposition 2026-08-31; IALLD-007 | `ELM-084 = CORE/P0/PoC`; full governed memory semantics and governance in PoC; bounded only by scale/resilience; memory remains tainted/non-authoritative and promotion uses C6/C3. | `PROPOSED — DECISION ID UNASSIGNED`; atomic promotion required | OBJ-003, OBJ-006, OBJ-007 | CAP-020, CAP-022, ELM-084 | C8 Memory Service; C6 control; C3 canonical writer; Policy/Authority Engine | FR-038, FR-113, FR-115, FR-118, FR-119, FR-140, NFR-016, NFR-048 | five register candidates; ADD v1.3; LLD v1.1; Memory JSON Schema/OpenAPI; FGM-01–FGM-20 | DEC-116; DEC-196 deferral superseded only on promotion; CC-FULL-GOVERNED-AGENT-MEMORY |
"""


def build_decision_register(source: Path) -> str:
    return candidate_header("Decision Register v1.2", source) + source.read_text(encoding="utf-8") + DECISION_PROPOSAL


def build_decision_traceability(source: Path) -> str:
    return candidate_header("Decision Traceability Index v1.2", source) + source.read_text(encoding="utf-8") + TRACE_PROPOSAL


def build_crosswalk(source: Path) -> str:
    text = source.read_text(encoding="utf-8")
    text = replace_row(
        text,
        "ELM-084",
        "| `ELM-084` | Full Governed Agent Memory — Memory Policy e Memory Item | `FR-038`, `FR-113`, `FR-115`, `FR-118`, `FR-119`, `FR-140`, `NFR-016`, `NFR-048` | `CORE/P0/PoC`: working, episodic, semantic, procedural, preference, reflection, dissent e team-shared memory; scope run/task/agent/team/project/domain/federated; persistenza cross-run; retrieval structured/full-text/vector/hybrid; lifecycle, consolidation, forgetting, legal hold, deletion e context receipts. Memory resta non canonica, tainted e priva di Authority; promozione soltanto via C6/C3. Copertura di design candidata, non evidenza runtime. |",
    )
    return candidate_header("CAP/ELM Requirement Crosswalk v1.1", source) + text


def check(name: str, passed: bool, detail: str) -> dict[str, object]:
    return {"check": name, "status": "PASS" if passed else "FAIL", "detail": detail}


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    builders = {
        "requirement_register": build_requirement_register,
        "requirement_traceability": build_requirement_traceability,
        "decision_register": build_decision_register,
        "decision_traceability": build_decision_traceability,
        "cap_elm_crosswalk": build_crosswalk,
    }
    paths: dict[str, Path] = {}
    base_digests: dict[str, str] = {}
    source_paths: dict[str, str] = {}
    for key, (source_name, output_name) in SOURCES.items():
        source = source_path(source_name)
        output = DEST / output_name
        output.write_text(builders[key](source), encoding="utf-8")
        paths[key] = output
        base_digests[key] = sha256(source)
        source_paths[key] = source.relative_to(ROOT).as_posix()

    texts = {key: path.read_text(encoding="utf-8") for key, path in paths.items()}
    approved_decisions = set(
        re.findall(r"\bDEC-\d{3}\b", source_path(SOURCES["decision_register"][0]).read_text(encoding="utf-8"))
    )
    candidate_decisions = set(re.findall(r"\bDEC-\d{3}\b", texts["decision_register"] + texts["decision_traceability"]))
    new_decisions = sorted(candidate_decisions - approved_decisions)
    rr_ids = re.findall(r"^\|\s*`?((?:BR|FR|NFR)-\d{3})`?\s*\|", texts["requirement_register"], re.MULTILINE)
    source_rr_ids = re.findall(
        r"^\|\s*`?((?:BR|FR|NFR)-\d{3})`?\s*\|",
        source_path(SOURCES["requirement_register"][0]).read_text(encoding="utf-8"),
        re.MULTILINE,
    )

    checks = [
        check("five_complete_candidates", len(paths) == 5 and all(p.exists() for p in paths.values()), ", ".join(p.name for p in paths.values())),
        check("requirement_universe_preserved", rr_ids == source_rr_ids and len(set(rr_ids)) == 285, f"candidate={len(set(rr_ids))}, source={len(set(source_rr_ids))}"),
        check("fr118_full_poc", "FGM-01" in texts["requirement_register"] and "| P0 |" in re.search(r"^\| `FR-118`.*$", texts["requirement_register"], re.MULTILINE).group(0) and "| PoC |" in re.search(r"^\| `FR-118`.*$", texts["requirement_register"], re.MULTILINE).group(0), "FR-118 P0/PoC with full-memory acceptance"),
        check("fr119_non_interference", "timing bucket" in texts["requirement_register"] and "FGM-16" in texts["requirement_traceability"], "retrieval side channels and non-interference covered"),
        check("elm084_core_poc", "`CORE/P0/PoC`" in texts["cap_elm_crosswalk"] and "FULL_GOVERNED_AGENT_MEMORY" in texts["decision_register"], "ELM-084 promoted in candidate disposition"),
        check("historic_decisions_preserved", "Historic `DEC-116` and `DEC-196` remain unchanged" in texts["decision_register"], "history preserved; deferral superseded prospectively"),
        check("no_unilateral_decision_id", not new_decisions and "DECISION ID UNASSIGNED" in texts["decision_register"] and "DECISION ID UNASSIGNED" in texts["decision_traceability"], f"new DEC identifiers={new_decisions}"),
        check("evidence_fence", all("E1=0" in text and "E2=0" in text for text in texts.values()), "all candidates preserve E1=0/E2=0"),
        check("no_verified_promotion", not any(re.search(r"evidence state:\s*Verified", text, re.IGNORECASE) for text in texts.values()), "no evidence state promoted"),
        check("atomic_change_set", all("CC-FULL-GOVERNED-AGENT-MEMORY" in text for text in texts.values()), "same change-set identity in five snapshots"),
        check("full_memory_surface", all(token in (texts["requirement_register"] + texts["cap_elm_crosswalk"]) for token in ["EPISODIC", "SEMANTIC", "PROCEDURAL", "REFLECTION", "DISSENT", "VECTOR", "FEDERATED", "legal hold", "deletion"]), "types, scopes, retrieval and lifecycle present"),
    ]
    payload = {
        "artifact": "OCOR full-memory five-register candidate update",
        "change_set": "CC-FULL-GOVERNED-AGENT-MEMORY",
        "status": "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL",
        "source_ref": SOURCE_REF,
        "source_commit": source_commit(),
        "source_paths": source_paths,
        "base_sha256": base_digests,
        "candidate_sha256": {key: sha256(path) for key, path in paths.items()},
        "counts": {"checks": len(checks), "pass": sum(item["status"] == "PASS" for item in checks), "fail": sum(item["status"] == "FAIL" for item in checks)},
        "checks": checks,
    }
    RESULTS.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    manifest_paths = sorted(paths.values()) + [RESULTS]
    MANIFEST.write_text(
        "\n".join(f"{sha256(path)}  {path.relative_to(OUT.parent).as_posix()}" for path in manifest_paths) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload["counts"], ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
