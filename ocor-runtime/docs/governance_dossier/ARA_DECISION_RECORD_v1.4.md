# OCOR Architecture Review Authority Decision Record v1.4

## 1. Decision control

| Field | Value |
|---|---|
| Record identifier | `OCOR-ARA-DR-1.4` |
| Status | **APPROVED — EFFECTIVE ON MERGE** |
| Decision | `DEC-210` |
| Title | Adoption of OCOR-RCCAD v1.0 development methodology |
| Effective date | 2026-09-02, on merge of the exact green change set |
| Authority | Product Owner authorization in the current conversation |
| Change set | `CC-RCCAD-METHODOLOGY-ADOPTION` |
| Prior governing decision | `DEC-209` |
| Nature | Development-process decision; no architecture semantic change |
| Evidence fence | `E1=0`, `E2=0`, zero requirements globally `Verified` |
| Runtime / Production | **NOT ESTABLISHED / NO-GO** |

## 2. Decision

The Product Owner adopts `OCOR-RCCAD v1.0` as the mandatory execution refinement of
the approved G0–G7 lifecycle. Existing IRB, ADD, LLD, decisions, contracts, backlog
and DAG retain their authority and precedence. RCCAD adds risk-first selection,
contract-first implementation, TDD/ATDD where applicable, architecture fitness
functions, evidence-as-code, clean-context verification and durable handoff.

## 3. Supersession and non-scope

`DEC-210` supersedes only development-process practices inconsistent with the RCCAD
controls. It does not supersede or modify architectural semantics, approved technology
choices, capability priority, evidence status, human signature requirements or any
historical decision. It does not accept any G gate, BA, FGM, EV or runtime result.

## 4. Effectiveness gate

Effectiveness requires the exact change set to pass the methodology/schema validator,
immutable-input guard, fitness declarations, test-control checks, independent verifier
and repository CI before merge. Missing infrastructure is recorded `NOT_EXECUTED` and
cannot be represented as `PASS`.
