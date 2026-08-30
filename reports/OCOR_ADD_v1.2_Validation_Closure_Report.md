# OCOR ADD v1.2 — Validation Closure Report

## Control

| Field | Value |
|---|---|
| Result | **PASS** |
| Executed revision | `036b873d87cc8720d4134a237a8ea41d3b8817cf` |
| GitHub Actions run | `33334792715`, attempt `1` |
| Candidate SHA-256 | `4f84249b86150a0aa0ef5bf7fcc1a5c99388651e8aae132720dd784883b0426f` |
| Approved baseline SHA-256 | `c3f432ae0d172f2b4f70be8220d0ae4a134ec14716bccc6a12d75dfee438b84f` |
| Executed at | `2026-08-30T20:51:43.885671+00:00` |

## Closure disposition

| Action | Disposition | Evidence |
|---|---|---|
| `VAL-ACT-001` | **CLOSED** | Full document harness rerun; zero suite failures on the approved candidate digest |
| `VAL-ACT-002` | **CLOSED** | `openapi-spec-validator==0.9.0`; approved embedded contract and runtime contract pass; no waiver required |
| `VAL-ACT-003` | **CLOSED_FOR_RUNTIME_SLICE** | Complete runtime, BA, 35 EV and five live PostgreSQL transaction tests pass |

## Document harness

| Suite | Passed | Failed | Not executed |
|---|---:|---:|---:|
| Tool-backed verifier | 12 | 0 | 2 |
| Contract conformance | 105 | 0 | 0 |
| Semantic/FSM/adversarial | 29 | 0 | 0 |
| Release/integrity | 12 | 0 | 0 |
| Approval-readiness | 18 | 0 | 0 |

The verifier's declared `NOT_EXECUTED` entries remain historically accurate inside that harness. Source/report integrity is closed by the manifest checks, and OpenAPI semantic validation is closed independently by the governed validator profile; neither is silently relabelled.

## Runtime evidence

| Campaign | Tests | Failures | Errors | Skipped |
|---|---:|---:|---:|---:|
| Full runtime | 109 | 0 | 0 | 0 |
| BA-01–BA-08 | 38 | 0 | 0 | 0 |
| EV-001–EV-035 | 35 | 0 | 0 | 0 |
| Live PostgreSQL 16 | 5 | 0 | 0 | 0 |

Observed statement coverage: **89%** (1372 covered lines, 161 missing lines). Coverage is reported evidence, not an invented release threshold.

## OpenAPI evidence

- Validator: `openapi-spec-validator==0.9.0`.
- Locked wheel SHA-256: `222fecffc7714f6d0a6ad62c0e4b66cc2b7dbfafb7b93acfc6c308abbdb51af8`.
- Subjects passed: 3/3.
- Waiver required: **false**.

## Evidence fence

This package establishes first-party implementation evidence for the explicitly tested OCOR runtime slice (`E1_runtime_slice=PRESENT`). It does not establish independent/production evidence (`E2`), certify every requirement, validate production performance or security, or authorize deployment. Requirement-level promotion requires the separate governed review recorded after this run.
