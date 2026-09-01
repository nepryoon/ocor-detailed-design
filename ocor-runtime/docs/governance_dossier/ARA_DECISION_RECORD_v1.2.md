# OCOR Architecture Review Authority Decision Record v1.2

## 1. Decision control

| Field | Value |
|---|---|
| Record identifier | `OCOR-ARA-DR-1.2` |
| Status | **APPROVED — EFFECTIVE ON GREEN PROMOTION CI AND MERGE** |
| Decision | `DEC-208` |
| Title | Full Governed Agent Memory: design-baseline disposition and runtime evidence fence |
| Effective date | 2026-09-01, conditional on green CI and merge of the content-addressed update set |
| Authority | Luca Lillo, Product Owner and repository owner, acting as Architecture Review Authority |
| Product Owner approval evidence | Explicit instruction: «procedi con il passaggio autoritativo» |
| Architecture Review Authority approval evidence | The same explicit instruction, issued by Luca Lillo in the ARA capacity recorded by ARA Decision Record v1.1, followed by activation of the governed promotion exception for this exact change set |
| Change set | `CC-FULL-GOVERNED-AGENT-MEMORY` |
| Supersedes | Only the `ELM-084` deferral clause of `DEC-196` |
| Preserves | `DEC-116`; `DEC-197`–`DEC-207`; `FR-118/119` P0/PoC; all authority, epistemic and safety fences |
| Approved ADD | `OCOR_ADD_v1.3_APPROVED_BASELINE.md` |
| Approved LLD | `docs/OCOR_LLD_v1.1.md` |
| Evidence fence | `E1=0`, `E2=0`, zero requirements globally `Verified`; `E1_runtime_slice=PRESENT` confined to `DEC-207` |
| Runtime disposition | **FULL-MEMORY RUNTIME NO-GO pending governed closure of FGM-01–FGM-20** |

This record incorporates ARA Decision Record v1.1 and ARA Validation Closure Record
v1.0 by reference without modifying them.

## 2. DEC-208 — Approved decision

The Authority approves `ELM-084 — Agent Memory` as `CORE/P0/PoC` with profile
`FULL_GOVERNED_AGENT_MEMORY`.

The design PoC includes working, episodic, semantic, procedural, preference, reflection,
dissent and team-shared memory; run, task, agent, team, project, domain and federated
scope; cross-run persistence; structured, full-text, vector and hybrid retrieval;
immutable versioning; consolidation; correction; supersession; revocation; expiry;
forgetting; legal hold; deletion saga; and reproducible context-assembly receipts.

Memory remains tainted and non-authoritative. It cannot grant Authority, create an
Approval or Decision, activate a CapabilityLease, emit an ActionCommand, change policy
or write canonical state directly. Every memory-derived canonical proposal traverses
C6 control/approval/decision and the C3 single-writer commit path.

The decision changes design scope only. Scale, HA, multi-region resilience, production
SLO and E2 remain later-gate concerns. Runtime conformance requires a separate governed
closure accepting `FGM-01`–`FGM-20`; no FGM result is asserted here.

## 3. Atomic update set

The decision promotes together:

1. Requirement Register v1.1;
2. Requirement Traceability Index v1.1;
3. Decision Register v1.2;
4. Decision Traceability Index v1.2;
5. CAP/ELM Requirement Crosswalk v1.1;
6. ADD v1.3 approved composite baseline;
7. LLD v1.1 approved technical baseline;
8. six versioned contract files required by the LLD;
9. this Decision Record, approval report, checker and approval manifest.

No partial interpretation is valid. The manifest
`OCOR_ADD_v1.3_APPROVAL_SHA256SUMS` is the content-addressed authority for the exact
files in this set.

## 4. Preconditions P-01–P-12

| ID | Disposition | Basis |
|---|---|---|
| P-01 | PASS | authoritative register paths are unique and fail-loud |
| P-02 | PASS | five candidate base digests match main |
| P-03 | PASS | double clean-clone reproducibility 7/7 |
| P-04 | PASS | lineage and candidate manifests verified |
| P-05 | PASS | governed OpenAPI validation completed |
| P-06 | PASS | historical evidence report semantic content preserved |
| P-07 | PASS | DRAFT/DEC mapping and DEC-201/205/206 provenance verified |
| P-08 | PASS | complete registers, ADD, LLD and contracts are present in the atomic set |
| P-09 | PASS | promotion checker verifies referential consistency and manifest digests |
| P-10 | PASS | DEC-207 declares DEC-208 next; no approved DEC-208 allocation exists before this record |
| P-11 | PASS | Product Owner and ARA role attestations are recorded for this change set |
| P-12 | PENDING_THIS_PROMOTION_CI | becomes PASS only when GitHub Actions validates this exact revision; merge is forbidden otherwise |

## 5. Evidence and authority fences

This approval does not:

- establish implementation of the full-memory design;
- extend `E1_runtime_slice=PRESENT` beyond the DEC-207 runtime slice;
- increment `E1` or `E2`, or mark any requirement globally `Verified`;
- authorize PoC-START, PoC-PASS, real data, external effects, MVP or Production;
- activate `FR-048`, `ELM-011` or another deferred capability;
- select a vector database, embedding model or other Candidate Implementation;
- close `RSK-031`, `RSK-038` or `SL-01`–`SL-04`;
- assert compliance, accreditation, parity, superiority or Production readiness.

## 6. Effectiveness rule

Before the promotion CI is green, the state is `APPROVED — PENDING EFFECTIVENESS`.
After the exact revision passes the promotion checker and all required GitHub Actions
jobs, the decision becomes effective only when the pull request is merged into
`main`. A finalization commit records the successful run before merge.
