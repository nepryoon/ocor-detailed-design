# OCOR Architecture Review Authority Decision Record v1.1

## 1. Decision control

| Field | Value |
|---|---|
| Record identifier | `OCOR-ARA-DR-1.1` |
| Effective date | 2026-08-30 |
| Authority | Luca Lillo, Product Owner and repository owner, acting as Architecture Review Authority |
| Human approval evidence | Explicit instruction: «puoi dichiararlo approvato» |
| Candidate reviewed | `reports/OCOR_Architectural_Design_Document_v1.2_Candidate.md` |
| Candidate SHA-256 | `4f84249b86150a0aa0ef5bf7fcc1a5c99388651e8aae132720dd784883b0426f` |
| Approved baseline | `OCOR_ADD_v1.2_APPROVED_BASELINE.md` |
| Approved baseline SHA-256 | `c3f432ae0d172f2b4f70be8220d0ae4a134ec14716bccc6a12d75dfee438b84f` |
| Change-Control Package | `reports/OCOR_ADD_v1.2_Change_Control_Package.md`, SHA-256 `f336b4d0b10942c3eeb6603bafff69b7e085edfa8bbd6dc0224266ee0e8aaa8c` |
| Approval-readiness evidence | 18 passed, 0 failed |
| Overall disposition | **APPROVED BASELINE — WITH ACCEPTED NON-BLOCKING VALIDATION LIMITATIONS** |

The Authority approves the ten change sets as an ordered and dependency-safe set. This record assigns `DEC-197`–`DEC-206`; the former `DRAFT-A`–`DRAFT-I` slugs cease to be independent authority sources and are retained only for provenance.

## 2. Approved decisions

### DEC-197 — Governed Context Set

- Change set: `CC-GCS`; ratifies and supersedes `DRAFT-A`.
- Status: **Approved**.
- Decision: `GovernedContext` §1.4 is the single normative governed-context record. The effective Principal derives exclusively from authenticated transport binding; body values are non-authoritative assertions. Every public surface produces the same canonical digest. Missing, mismatched or unverifiable context causes deny/quarantine plus audit and never fail-open reduction.
- Dependencies: none within this approval set.
- Effective from: 2026-08-30.

### DEC-198 — ACTION and EVENT contract baseline

- Change set: `CC-ACTION-EVENT-CONTRACTS`; ratifies and supersedes `DRAFT-G`.
- Status: **Approved**.
- Decision: MCP 1.2, Action 1.1 and Event 1.1 are the approved contract versions, including mandatory GCS, non-empty quorum/roles, coherent minimum Evidence, canonical bindings, deterministic C3 reason codes and a bounded replay window whenever replay is allowed.
- Dependency: `DEC-197`.
- Effective from: 2026-08-30.

### DEC-199 — Governed canonical mutation path

- Change set: `CC-CANONICAL-PATH`; ratifies and supersedes `DRAFT-B`.
- Status: **Approved**.
- Decision: `target=CANONICAL_COMMIT` is the only canonical-state mutation path. Every commit requires at least `R2_CONTROLLED`, Human Gate or Dual Control, non-empty quorum/roles, Decision, Authority, Evidence, claim/source binding, aggregate type/ref, expected revision, precondition/invariant bindings, idempotency key, GCS digest and immutable GatePackage. `approval.mode=NONE`, missing data or mismatch is rejected before mutation.
- Dependencies: `DEC-197`, `DEC-198`.
- Effective from: 2026-08-30.

### DEC-200 — Single writer, branch scope and relay

- Change set: `CC-SINGLE-WRITER-BRANCH-SCOPE`; ratifies and supersedes `DRAFT-C`.
- Status: **Approved**.
- Decision: C3 is the sole canonical writer to `main` per ownership boundary. Scenario overlays are written only by the C7 `ScenarioOverlayStore`, which has no `main.write`. The relay publishes only committed `main` outbox entries. Scenario entries never create `DeliveryAttempt` and are ignored by the reconciler.
- Dependency: `DEC-199`.
- Effective from: 2026-08-30.

### DEC-201 — BA-01 atomicity and no implicit fallback

- Change set: `CC-BA01-ALTERNATIVE`.
- Status: **Approved**.
- Decision: the local atomic commit of aggregate revision, canonical commit, idempotency binding and outbox is a hard invariant. No fallback is pre-approved. A backend is admissible only after crash-window, concurrency and fork-isolation tests. Failure to satisfy the invariant is `NO-GO`; RDBMS/event-log or two-log+reconciler alternatives require new change control with failure analysis and revised §2.3/§6.2.
- Dependency: `DEC-200`.
- Effective from: 2026-08-30.

### DEC-202 — Atomic EMISSION-FENCE

- Change set: `CC-EMISSION-FENCE`; ratifies and supersedes `DRAFT-E` and the safety-control content of `DRAFT-I`.
- Status: **Approved**.
- Decision: `EMISSION-FENCE := G-FRESHNESS ∧ G-DISPATCH` is evaluated atomically immediately before first send, retry and compensation. Revalidation covers state revision, policy digest/validity, Authority, Approval, ontology release, watermark, stop epoch, CapabilityLease, audit availability, command deadline, circuit breaker, adapter conformance and immutable GatePackage. Drift or evaluation error produces `INVALIDATED` before emission. CapabilityLease is distinct from deferred `ELM-080`, has TTL ≤5 s and works with independent revocation push toward the ≤10 s containment target.
- Dependency: `DEC-197`.
- Atomic-set rule: inseparable from `DEC-203` for dispatch during unresolved effects.
- Effective from: 2026-08-30.

### DEC-203 — Indeterminate-effect adjudication

- Change set: `CC-INDETERMINATE-ADJUDICATION`; ratifies and supersedes `DRAFT-F`.
- Status: **Approved**.
- Decision: `ConflictScope` is typed and `IndeterminateEffectAdjudication` is append-only. An indeterminate effect blocks conflicting effects; missing or ambiguous scope blocks the ownership boundary. Only a signed record with Authority, Decision and non-empty Evidence can recalculate the block. Silence, timeout and in-place mutation never mean “no effect”.
- Dependency: `DEC-202`.
- Atomic-set rule: approved atomically with `DEC-202`.
- Effective from: 2026-08-30.

### DEC-204 — Marking algebra

- Change set: `CC-MARKING-ALGEBRA`; ratifies and supersedes `DRAFT-D` and `DRAFT-H`.
- Status: **Approved**.
- Decision: `MarkingSchemeDefinition` defines restriction union/join toward more restrictive values, permission intersection, dominance, top, bottom, admitted values, mandatory markings, caveats, dissemination controls, permitted purposes, handling instructions and declassification authority. Unknown labels, incomparable labels and incompatible operators deny/quarantine. `OI-021` remains open for the concrete national taxonomy.
- Dependencies: none beyond the incorporated marking model.
- Effective from: 2026-08-30.

### DEC-205 — FR-095 / ELM-070 scope disposition

- Change set: `CC-FR095-SCOPE`.
- Status: **Approved**.
- Decision: `FR-095` is reclassified from P0/PoC to P0/MVP. `ELM-070` remains deferred outside the PoC. The PoC makes no AAP counterfactual claim. This decision supersedes only the `FR-095 ... P0/PoC` release clause of `DEC-103`; all other content of `DEC-103` remains effective.
- Register effect: Requirement Register, Requirement Traceability Index, Decision Register/Index and CAP/ELM Crosswalk are updated by the approved snapshots in this dossier.
- Effective from: 2026-08-30.

### DEC-206 — Decision allocation and global coverage

- Change set: `CC-DEC-ALLOCATION`.
- Status: **Approved**.
- Decision: `DEC-173` is allocated to Agent Kernel and role-oriented surfaces; `DEC-175` is allocated to Compiler & Gateway for documentation, sandbox and conformance kit. The global disposition keeps 183 subsystem/programme decisions separate from 13 document/programme decisions and preserves 196/196 coverage.
- Dependencies: none technical.
- Effective from: 2026-08-30.

## 3. Dependency and atomicity disposition

Approved order:

```text
DEC-197 → DEC-198 → DEC-199 → DEC-200 → DEC-201
DEC-197 → DEC-202 ⇄ DEC-203
DEC-204
DEC-205
DEC-206
```

The arrow means “must be effective before”. The bidirectional marker denotes the atomic approval set for emission and indeterminate-effect adjudication. No partial interpretation is valid.

## 4. Accepted limitations and mandatory follow-up

| ID | Limitation | Approval treatment | Due gate |
|---|---|---|---|
| `VAL-ACT-001` | Full post-remediation harness not rerun against the approved-baseline digest | Accepted as non-blocking because invariant-bearing schema/FSM blocks were unchanged; rerun is mandatory | Before implementation-gate promotion |
| `VAL-ACT-002` | Official OpenAPI 3.1 semantic validator `NOT_EXECUTED` | Execute the approved validator or record a tool-specific waiver | Before first external interface baseline |
| `VAL-ACT-003` | Backend assumptions and runtime evidence remain incomplete | No evidence promotion; relevant release profiles remain `NO-GO` until their tests pass | DDD/release gates |

## 5. Scope and evidence fence

This approval:

- approves the architectural baseline and the ten decisions above;
- does not close any `OI-*`, `ASM-*` or `RSK-*` except by an explicit future record;
- does not promote candidate technologies to verified implementations;
- does not authorize Production or real-world effects;
- leaves `E1=0`, `E2=0` and zero requirements `Verified`;
- preserves all deferred/out-of-scope dispositions except the explicit `FR-095` release change.

## 6. Final disposition

**OCOR ADD v1.2 is APPROVED as the architectural baseline effective 2026-08-30.**

The approved baseline SHA-256 is `c3f432ae0d172f2b4f70be8220d0ae4a134ec14716bccc6a12d75dfee438b84f`. Any later change requires a new decision beginning with `DEC-207` and a versioned baseline update.
