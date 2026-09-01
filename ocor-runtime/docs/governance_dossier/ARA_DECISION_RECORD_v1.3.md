# OCOR Architecture Review Authority Decision Record v1.3

## 1. Decision control

| Field | Value |
|---|---|
| Record identifier | `OCOR-ARA-DR-1.3` |
| Status | **APPROVED — EFFECTIVE ON MERGE** |
| Decision | `DEC-209` |
| Title | IRB–ADD–LLD authoritative documentation assurance and editorial authority seal |
| Effective date | 2026-09-01, on merge of the exact content-addressed change set |
| Authority | Luca Lillo, Product Owner and repository owner, acting also as Architecture Review Authority |
| Reviewer independence | One human in two recorded roles; not represented as two independent reviewers |
| Authorization evidence | Explicit current-conversation mandate to audit, correct, approve, promote, merge and independently recheck the complete IRB→ADD→LLD documentation chain |
| Change set | `CC-IRB-ADD-LLD-AUTHORITY-SEAL` |
| Prior governing decision | `DEC-208` |
| Nature | Editorial errata, derived traceability regeneration, assurance-gate strengthening and configuration seal; no new runtime or architectural semantics |
| Evidence fence | `E1=0`, `E2=0`, zero requirements globally `Verified`; historical `E1_runtime_slice=PRESENT` remains confined to `DEC-207` |
| Runtime disposition | **NOT ESTABLISHED / NO-GO** |
| Full-memory runtime | **NO-GO pending governed closure of FGM-01–FGM-20** |
| Production readiness | **NO-GO** |

## 2. Decision

The Authority approves the corrected documentation control state and assurance seal for the existing IRB, ADD v1.3 and LLD v1.1 baseline. The decision:

1. removes the residual pre-promotion disposition from the current LLD without changing its design;
2. records all 285 IRB requirements as `FULLY_SPECIFIED` at design level, including `FR-118` and `FR-119`;
3. preserves `FR-118` and `FR-119` as `specified/planned`, `E1=0`, `E2=0`, `NOT_VERIFIED` at evidence level;
4. assigns stable `ADD-OBL-<requirement-id>` obligation identifiers in the authoritative traceability matrix;
5. seals 285 forward mappings and reverse mappings for C1–C8, contracts, 44 C6 transitions, BA-01–BA-08 and FGM-01–FGM-20;
6. marks the ADD v1.2→LLD v1.0 failed audit as historical and superseded;
7. makes stale candidate/pending-promotion wording, placeholder tokens, incomplete traceability, contract drift and `inputs/` changes blocking failures.

## 3. Supersession boundary

`DEC-209` supersedes only obsolete document-control statements that describe already completed `DEC-208` actions as future or conditional. It does not rewrite or renumber any historical decision and does not change the normative behaviour, priority, release, capability allocation or contract semantics approved by `DEC-208`.

ADD v1.3 and LLD v1.1 remain the authoritative versions. The changes are therefore an editorial erratum under the current versions, not a cosmetic successor ADD and not a new runtime baseline.

## 4. Mandatory dispositions

```text
IRB baseline = APPROVED / COMPLETE AT DESIGN LEVEL
ADD baseline = APPROVED / ALIGNED TO IRB
LLD baseline = APPROVED / ALIGNED TO ADD
IRB–ADD–LLD documentation chain = PASS
runtime implementation conformance = NOT ESTABLISHED / NO-GO
full-memory runtime = NO-GO pending FGM-01–FGM-20
E2 = 0
Production readiness = NO-GO
```

## 5. Preserved fences

- `FR-048` remains deferred.
- `ELM-011` remains deferred.
- Technology selections remain `Candidate Implementation` unless separately governed.
- `ELM-084 = CORE/P0/PoC` and `FULL_GOVERNED_AGENT_MEMORY` remain fully specified in the PoC design.
- Only scale, HA, multi-region resilience, Production SLO and E2 remain outside the full PoC memory design.
- No BA or FGM result is accepted by this decision.
- Documentation and contract assurance do not create runtime evidence.

## 6. Effectiveness and sealing

The decision becomes effective only after the exact branch revision passes the repository-required checks and is merged without bypassing branch protection. The final sealing revision records the successful CI run and exact head SHA before merge; post-merge verification confirms the `main` SHA and unchanged `inputs/` tree.
