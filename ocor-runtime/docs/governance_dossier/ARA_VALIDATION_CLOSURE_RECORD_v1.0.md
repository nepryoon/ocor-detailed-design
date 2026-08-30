# OCOR ADD v1.2 — ARA Validation Closure Record v1.0

## Control

| Field | Value |
|---|---|
| Status | **APPROVED VALIDATION CLOSURE** |
| Effective date | 2026-08-30 |
| Authority | Luca Lillo, Product Owner and repository owner, acting as Architecture Review Authority |
| Authorization evidence | Explicit instruction: “procedi con rerun completo post-remediation, validazione/waiver OpenAPI governata e completamento delle evidenze runtime” |
| Decision | `DEC-207` |
| Execution revision | `036b873d87cc8720d4134a237a8ea41d3b8817cf` |
| GitHub Actions run | [33334792715](https://github.com/nepryoon/ocor-detailed-design/actions/runs/33334792715), attempt 1, conclusion `success` |
| Workflow artifact SHA-256 | `ce90c697b2a204fd8db77f4637bc4948f482864e752e8664c3d819f20c36b904` |
| Evidence manifest SHA-256 | `fde0611b9aa1f950b9c599a3ee3d71d89ac353a21cb40b9e0ebe8efeffbdc073` |

## DEC-207 — Acceptance of post-approval validation evidence

The ARA accepts the evidence package produced from the approved ADD v1.2 baseline and records the following dispositions:

| Action | Disposition | Exact basis |
|---|---|---|
| `VAL-ACT-001` | **CLOSED** | Full post-remediation document campaign rerun on candidate SHA-256 `4f84249b86150a0aa0ef5bf7fcc1a5c99388651e8aae132720dd784883b0426f`: verifier 12 PASS/0 FAIL, contract conformance 105/105, semantics/FSM 29/29, release gate 12/12 and approval-readiness 18/18. |
| `VAL-ACT-002` | **CLOSED — NO WAIVER REQUIRED** | Governed profile using locked `openapi-spec-validator==0.9.0`; profile preflight, approved embedded OpenAPI 3.1.0 and runtime OpenAPI 3.1.0 all pass (3/3). |
| `VAL-ACT-003` | **CLOSED FOR THE VERSIONED RUNTIME SLICE** | Full runtime 109/109; BA campaign 38/38 covering BA-01–BA-08; EV campaign exactly 35/35 covering EV-001–EV-035; live PostgreSQL 16 campaign 5/5; zero failures, errors or skips. |

## Evidence objects

| Object | SHA-256 |
|---|---|
| `reports/OCOR_ADD_v1.2_Validation_Closure_Report.md` | `f327937f2de596ba9092b71fc93450f6a7bf3e6f5707f4051baf1739e4354c10` |
| `reports/tests/validation_closure_results.json` | `c633a81e1222fb56e5604db566a0e3f32c9573f1ff08feda44ddea2e62ad8ee6` |
| `reports/tests/openapi_31_validation_results.json` | `757782771564f3cfa87ccefa23f7899929d02493a29d41f5bbdff4d037ab0dca` |
| `reports/tests/runtime_junit_post_approval.xml` | `b43bcbef9fd30e984f140b5d49016b8836854f9386a2e069f09e80ee95f0cba6` |
| `reports/tests/ba_junit_post_approval.xml` | `01d72495475163f5123acc69349afc3f2f95f91c21904b8720862b393758405f` |
| `reports/tests/ev_junit_post_approval.xml` | `7d6016334829d8753d107a776f0333c703ecf089a39ca8781ed5395157794aff` |
| `reports/tests/postgres_junit_post_approval.xml` | `79540b12267094ebd8fb9ea4995f99de2e1593595d79248e9fac7daff124349c` |

## Evidence-state disposition

This decision establishes `E1_runtime_slice=PRESENT` for the exact revision and tested surface above. It does not rewrite the architecture-cut-off statements embedded in the approved baseline, which remain historically correct as of that cut-off.

`E2` independent/production evidence is not established. No requirement is automatically promoted to global `Verified`; no production performance, security accreditation, operational resilience, external interoperability breadth or deployment authorization is claimed.

## Residual gates

`LLD-BL-004`–`LLD-BL-006` remain separate implementation-alignment issues. Their continued existence does not reopen `VAL-ACT-001`–`003`, and this validation closure does not close them.

The next available decision identifier is `DEC-208`.
