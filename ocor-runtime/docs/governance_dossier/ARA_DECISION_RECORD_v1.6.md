# OCOR Architecture Review Authority Decision Record v1.6

## 1. Decision control

| Field | Value |
|---|---|
| Record identifier | `OCOR-ARA-DR-1.6` |
| Status | **APPROVED — EFFECTIVE ON EXACT-GREEN MERGE** |
| Decision | `DEC-212` |
| Title | OCOR Internal Implementation Language Policy |
| Effective date | 2026-09-12, on merge |
| Authority | Explicit Product Owner implementation authorization, current conversation |
| Change set | `CC-OCOR-LANGUAGE-POLICY` |
| Prior governing decision | `DEC-211` |
| Nature | Development-process policy fixing the internal implementation language per
project area and a fail-closed CI gate; no architecture semantic change |
| Evidence fence | `E1=0`, `E2=0`, zero requirements globally `Verified` |
| Runtime / Production | **NOT ESTABLISHED / NO-GO** |

## 2. Decision

The authority adopts `docs/development_methodology/OCOR_LANGUAGE_POLICY.md` as the
normative table of authorized implementation languages, patch-pinned versions,
requirement-anchored rationale, prohibited alternatives, and pre-registered Phase 3
migration thresholds for every area of the project: the canonical/digest kernel,
components C1–C8, the verification harness and validators, the `deploy/` service
qualifiers, the contract generator, the generated SDKs, the backend adapters, OPA
policy, infrastructure/CI, and the declarative contract formats. It also adopts
`scripts/validate_language_policy.py` as the fail-closed, executable gate that
enforces this table in CI.

## 3. Scope and supersession

`DEC-212` does not supersede any prior decision. No approved decision previously
fixed the internal implementation language of any component; `DEC-212` is the first
to do so, and it is the only decision that a future implementation-language
migration (mandate Phase 3) may amend, component by component, with a dedicated new
decision that preserves the public API and leaves the SDK profile untouched.

`DEC-212` explicitly leaves the SDK profile fixed by `DEC-075`/`FR-047`/`FR-048`
(Python and TypeScript generated SDKs, Rust deferred `CAPABILITY_DEFERRED`)
completely unmodified: that is a normative decision about the external interface,
distinct from the internal-implementation-language perimeter this decision fixes.
It does not accept G2 tasks, runtime evidence, or any requirement promotion.

## 4. Effectiveness gate

Effectiveness requires `scripts/validate_language_policy.py` to reject every
disallowed-extension-in-area case (RED demonstrated first) and to pass on the
authorized tree (GREEN), wired as a blocking CI job on every relevant workflow,
plus `scripts/validate_rccad.py` and `scripts/validate_ocor_change_scope.py`
remaining green on the exact-head commit and independent verification before merge.
