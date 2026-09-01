# OCOR AI-First Development Plan

## Control and outcome

Base: `67cda4b44a8d27b831eb461b1e28d71e1d3398ab` (`origin/main`, expected=actual). Authority: DEC-209, ADD v1.3 and LLD v1.1. This is an implementation plan only: runtime conformance, PoC-GO, E1/E2 and Production readiness remain unchanged and `NO-GO` where applicable.

## Factual baseline

The repository contains 247 base files, a Python 0.1.0 reference slice and 104 locally executable non-live tests. The current component labels are historical compatibility surfaces: C2 is identity-only, C4 is marking-only, C5 hosts a 32-transition action FSM, C6 is leases, C7 is emission fencing and C8 is a sandbox/model wrapper. Approved C2/C4/C5/C7 duties, 12 of 44 C6 transitions, real-service breadth and all Full Governed Agent Memory are absent. See `reports/planning/OCOR_CURRENT_STATE_BASELINE.md`.

## Strategy decision

Scores use 1 (poor/high risk) to 5 (strong/low risk); weights total 100.

| Criterion | Weight | A component-first | B foundation-first | C risk-first vertical | D evidence-derived hybrid |
|---|---:|---:|---:|---:|---:|
| Compliance preservation | 10 | 3 | 4 | 4 | 5 |
| Architectural regression probability | 9 | 2 | 4 | 4 | 5 |
| Early risk retirement | 10 | 2 | 3 | 5 | 5 |
| Autonomous executability | 7 | 4 | 4 | 4 | 5 |
| Bounded agent context | 5 | 3 | 4 | 5 | 5 |
| Dependency complexity | 5 | 2 | 4 | 3 | 4 |
| Feedback speed | 8 | 2 | 3 | 5 | 5 |
| Testability | 8 | 3 | 5 | 4 | 5 |
| Rollback safety | 5 | 3 | 4 | 5 | 5 |
| CI integration | 5 | 3 | 5 | 4 | 5 |
| Token efficiency | 4 | 3 | 4 | 5 | 5 |
| Compute cost | 3 | 4 | 3 | 4 | 4 |
| Merge-conflict probability | 4 | 2 | 3 | 4 | 5 |
| Time to first mission thread | 5 | 1 | 2 | 5 | 5 |
| Time to PoC conformance | 6 | 2 | 3 | 4 | 5 |
| Incremental evidence suitability | 4 | 2 | 4 | 5 | 5 |
| Compatibility migration risk | 2 | 2 | 4 | 4 | 5 |
| **Weighted total** | **100** | **50.4** | **74.4** | **87.2** | **98.4** |

Selected: **D — evidence-derived hybrid**. It constrains shared foundation to canonical contracts and evidence mechanics, executes 13 real-service/fidelity spikes before irreversible choices, establishes an early real C1–C8 thread, then expands in bounded vertical increments. Sensitivity: D remains first when any single criterion weight changes by ±20%; C becomes competitive only if contract/regression and real-backend evidence weights are jointly reduced, a disqualifying governance posture.

Disqualifiers: A defers integration; B overbuilds before backend proof; C risks duplicated contracts; D is invalid if spike results are promoted as final evidence.

## Workstreams

All WS-00–WS-13 are represented in the 69-task backlog. WS-00 protects deterministic delivery; WS-01 fixes cross-cutting contracts; WS-02..WS-09 implement C1..C8; WS-10 implements all governed memory; WS-11 integrates security; WS-12 owns deployment/recovery; WS-13 owns independent verification and evidence.

## Gates

| Gate | Required tasks | Entry | Exit | Required tests | Real services | Evidence | Rollback | Failure path | Promotion authority | Prohibited claims |
|---|---|---|---|---|---|---|---|---|---|---|
| G0 | OCOR-DEV-0001, OCOR-DEV-0002, OCOR-DEV-0003, OCOR-DEV-0004, OCOR-DEV-0005, OCOR-DEV-0006 | DEC-209 authority and clean origin/main are verified. | Deterministic environment, branch protection contract, task ledger and baseline results exist. | immutable-path guard, clean-environment reproducibility, mandatory-red CI probe, manifest self-test | GitHub Actions | `reports/evidence/G0/MANIFEST.json` | Revert planning/bootstrap commits; no data migration exists. | Freeze implementation task dispatch and repair baseline reproducibility. | Delivery Coordinator plus Configuration Manager | No runtime-conformance, E1, PoC-GO or Production claim. |
| G1 | OCOR-DEV-0007, OCOR-DEV-0008, OCOR-DEV-0009, OCOR-DEV-0010, OCOR-DEV-0011, OCOR-DEV-0012, OCOR-DEV-0013, OCOR-DEV-0014 | G0 is green and approved contracts are hash-pinned. | Canonical types, GCS, leases, errors, evidence envelopes, generated-boundary rules and contract tests are green. | JSON Schema positive/negative branches, OpenAPI 3.1 validation, Proto3 compilation, cross-language canonical-byte vectors, generated SDK drift | local schema validators, protoc | `reports/evidence/G1/MANIFEST.json` | Revert contract implementation while retaining compatibility adapters and stored-version readers. | Block component work; resolve contract drift through governed decision if semantics differ. | Contract Authority and Integration Agent | No backend selection or runtime verification from schema validation. |
| G2 | OCOR-DEV-0015, OCOR-DEV-0016, OCOR-DEV-0017, OCOR-DEV-0018, OCOR-DEV-0019, OCOR-DEV-0020, OCOR-DEV-0021, OCOR-DEV-0022, OCOR-DEV-0023, OCOR-DEV-0024, OCOR-DEV-0025, OCOR-DEV-0026, OCOR-DEV-0027 | G1 contracts are fixed and disposable environments are available. | All critical spikes have reproducible evidence and an explicit retain/harden/discard disposition. | each spike's real-service positive, negative and fault oracle, clean rerun reproducibility, retain/harden/discard disposition validation | PostgreSQL, TypeDB, Jena, Kafka/Strimzi, OPA, Keycloak, SPIFFE/SPIRE, OpenBao | `reports/evidence/G2/MANIFEST.json` | Destroy disposable spike environments; retain only manifests and decision inputs. | Create a blocking governance decision; do not silently substitute technology. | Architecture Review Authority for architecture-affecting outcomes | Spike success is not final implementation evidence or PoC conformance. |
| G3 | OCOR-DEV-0028, OCOR-DEV-0029, OCOR-DEV-0030, OCOR-DEV-0031 | Relevant G2 risks are resolved and qualifying services are pinned. | One synthetic thread traverses real C1-C8 boundaries with fail-closed controls and reproducible receipts. | real C1-C8 thin mission thread, control-plane outage, stale GCS/lease/decision, correlation and evidence-chain checks | PostgreSQL, TypeDB, Jena, Kafka, OPA/Keycloak | `reports/evidence/G3/MANIFEST.json` | Revert the slice release and restore the pre-slice schema snapshot. | Return failing boundary to its owning workstream; no partial mission-thread claim. | Integration Agent and Independent Conformance Reviewer | No E1 or PoC-GO; a thin slice does not cover the 285-requirement universe. |
| G4 | OCOR-DEV-0032, OCOR-DEV-0033, OCOR-DEV-0034, OCOR-DEV-0035, OCOR-DEV-0036, OCOR-DEV-0037, OCOR-DEV-0038, OCOR-DEV-0039, OCOR-DEV-0040, OCOR-DEV-0041, OCOR-DEV-0042, OCOR-DEV-0043, OCOR-DEV-0044, OCOR-DEV-0045, OCOR-DEV-0046, OCOR-DEV-0047, OCOR-DEV-0048, OCOR-DEV-0049 | G3 thread is repeatable and compatibility boundaries are explicit. | C1-C8 responsibilities, the 44-transition FSM and security/operations integrations meet task-level oracles. | component unit/property/contract tests, real-service integration, 44-transition implementation equality, fault and compatibility migration | all selected PoC services | `reports/evidence/G4/MANIFEST.json` | Rollback per component release and replay from the last compatible canonical checkpoint. | Quarantine the component increment; keep prior compatible slice active. | Delivery Coordinator after independent task review | No global Verified state before qualifying campaigns. |
| G5 | OCOR-DEV-0050, OCOR-DEV-0051, OCOR-DEV-0052, OCOR-DEV-0053, OCOR-DEV-0054, OCOR-DEV-0055, OCOR-DEV-0056, OCOR-DEV-0057, OCOR-DEV-0058, OCOR-DEV-0059 | C3, C4, C6, C8 and security controls required by memory are green. | All kinds, scopes and lifecycle semantics are implemented; preparatory tests are green. | all kind/scope admission cases, retrieval and non-interference, lifecycle/deletion/restore, context replay and C6/C3 promotion | PostgreSQL, object store, full-text index, vector index, OPA/Keycloak | `reports/evidence/G5/MANIFEST.json` | Disable new memory admissions, preserve immutable versions/tombstones and restore prior readers. | Full-memory runtime remains NO-GO; no kind or scope may be deferred. | Governed Memory Lead plus Security Reviewer | No full-memory claim until FGM-01–FGM-20 qualify at G6. |
| G6 | OCOR-DEV-0060, OCOR-DEV-0061, OCOR-DEV-0062, OCOR-DEV-0063, OCOR-DEV-0064, OCOR-DEV-0065, OCOR-DEV-0066 | G4 and G5 are green; environments and fixtures are content-addressed. | BA-01–BA-08, FGM-01–FGM-20, 44 FSM transitions and mission thread all have qualifying non-skipped results. | BA-01–BA-08, FGM-01–FGM-20, 44 transition positive/negative/effect cases, security faults, full mission thread, backup/restore/air-gap | complete selected-component PoC stack | `reports/evidence/G6/MANIFEST.json` | Invalidate the campaign manifest and preserve raw results for diagnosis. | Any failed/unavailable mandatory case keeps PoC runtime NO-GO. | Independent Conformance Reviewer | No skipped/mock result counts as PASS; no Production readiness claim. |
| G7 | OCOR-DEV-0067, OCOR-DEV-0068, OCOR-DEV-0069 | G6 qualifying evidence is complete and traceable to all P0/PoC requirements. | A governed decision package states results, limitations, residual risks and exact evidence scope. | 285-row evidence validation, independent reproduction sample, manifest and decision-package integrity | GitHub protected CI, evidence archive | `reports/evidence/G7/MANIFEST.json` | Withdraw the candidate decision package; do not rewrite evidence or decisions. | Remain PoC NO-GO and issue scoped remediation tasks. | Product Owner and Architecture Review Authority under recorded governance | PoC-GO cannot imply Production readiness, E2, scale, HA or multi-region qualification. |

The separate Production campaign is deliberately absent from implementation tasks: production scale, HA, multi-region, Production SLO and E2 remain out of PoC conformance.

## Dependency and parallelisation model

The machine DAG has 28 waves. Critical path (161 nominal agent-days): `OCOR-DEV-0001 → OCOR-DEV-0002 → OCOR-DEV-0003 → OCOR-DEV-0007 → OCOR-DEV-0008 → OCOR-DEV-0009 → OCOR-DEV-0010 → OCOR-DEV-0013 → OCOR-DEV-0015 → OCOR-DEV-0016 → OCOR-DEV-0029 → OCOR-DEV-0030 → OCOR-DEV-0031 → OCOR-DEV-0046 → OCOR-DEV-0050 → OCOR-DEV-0051 → OCOR-DEV-0052 → OCOR-DEV-0054 → OCOR-DEV-0055 → OCOR-DEV-0057 → OCOR-DEV-0058 → OCOR-DEV-0059 → OCOR-DEV-0062 → OCOR-DEV-0065 → OCOR-DEV-0066 → OCOR-DEV-0067 → OCOR-DEV-0068 → OCOR-DEV-0069`. Near-critical paths run through TypeDB/Jena/Kafka and the memory deletion/restore chain; they converge at `OCOR-DEV-0065` and must not be delayed behind component-local polish.

| Wave | Ready tasks | Maximum safe concurrency |
|---:|---:|---:|
| 1 | 1 | 1 |
| 2 | 2 | 2 |
| 3 | 3 | 3 |
| 4 | 1 | 1 |
| 5 | 1 | 1 |
| 6 | 1 | 1 |
| 7 | 1 | 1 |
| 8 | 4 | 4 |
| 9 | 8 | 6 |
| 10 | 2 | 2 |
| 11 | 4 | 4 |
| 12 | 2 | 2 |
| 13 | 1 | 1 |
| 14 | 9 | 6 |
| 15 | 7 | 6 |
| 16 | 2 | 2 |
| 17 | 3 | 3 |
| 18 | 2 | 2 |
| 19 | 3 | 3 |
| 20 | 2 | 2 |
| 21 | 1 | 1 |
| 22 | 1 | 1 |
| 23 | 3 | 3 |
| 24 | 1 | 1 |
| 25 | 1 | 1 |
| 26 | 1 | 1 |
| 27 | 1 | 1 |
| 28 | 1 | 1 |

Shared-file collision zones are canonical contracts, evidence manifests, C3 migrations, C6 FSM tables and deployment charts. They have one owner per wave; other tasks consume versioned interfaces. Isolated worktrees are recommended for every dependency-ready task except integration barriers 0031, 0049, 0065 and 0067–0069.

Conditional governance decisions are mandatory after any G2 failure that would change PostgreSQL/C3, TypeDB, Jena, Kafka, security-control or vector-index semantics; after any mismatch between the LLD 44-transition table and executable interpretation; and before any replacement of a Candidate Implementation. The decision input is the failed spike manifest, not an agent preference.

## AI-first execution and cost model

Use task-specific context manifests and source hashes; read normative excerpts plus owned ports/tests, not the whole repository. Run narrow tests before service suites; stop after two materially different repairs and escalate normative conflicts.

- Optimistic: 1.6–2.2M model tokens, 250–400 CPU-h, 180–300 real-service hours.
- Expected: 2.8–4.2M tokens, 400–750 CPU-h, 300–650 service hours, 10–40 optional GPU-h for embedding fixtures.
- Conservative: 5.5–8.0M tokens, 800–1,400 CPU-h, 700–1,400 service hours, 20–80 GPU-h.

Assumptions: frontier coding model for contracts, C3/C6, causal, security and memory lifecycle; smaller coding model for isolated adapters, fixtures, manifests and documentation. Main cost drivers are retries across real services, non-interference timing, deletion/restore fault matrices and integration failures. Recommended concurrency is 3 agents before G3, 4–6 in G4, 3 in G5 and 2 plus an independent reviewer in G6/G7.

## Governance and rollback

No task may edit `inputs/`, ADD v1.3 or LLD v1.1. Technology-changing spike outcomes require a governed decision. Every merge uses a task branch, structured handoff, independent review, integration branch and mandatory CI. Evidence generation records commit/environment/command/inputs/hashes; the generating code path is never the sole independent verifier. Rollback uses revert commits and forward-compatible migrations—never history rewrite or force-push.
