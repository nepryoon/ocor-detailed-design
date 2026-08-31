# OCOR LLD v1.0 ↔ ADD v1.2 Alignment Review

## Executive result

**Document alignment: PASS. Implementation conformance: OPEN / NO-GO.**

The reviewed `docs/OCOR_LLD_v1.0.md` now treats the approved ADD v1.2 as the controlling architecture. The former specification conflicts `LLD-BL-004`, `LLD-BL-005` and `LLD-BL-006` are closed in the LLD. No ADD, decision record, approved schema or immutable input was modified.

This result means that the LLD describes the approved architecture consistently. It does not claim that the current runtime implements all eight components or passes the ADD acceptance behaviours.

## Review basis

- `ocor-runtime/docs/governance_dossier/OCOR_ADD_v1.2_APPROVED_BASELINE.md`
- `ocor-runtime/docs/governance_dossier/ARA_DECISION_RECORD_v1.1.md`
- `ocor-runtime/docs/governance_dossier/ARA_VALIDATION_CLOSURE_RECORD_v1.0.md`
- `ocor-runtime/docs/governance_dossier/OCOR_ADD_v1.2_VALIDATION_CLOSURE_REPORT.md`
- approved OpenAPI 3.1, Proto3 and JSON Schema contracts
- current `docs/OCOR_LLD_v1.0.md`
- current runtime source and test evidence as implementation evidence only

## Divergences and rectifications

| Area | Previous LLD divergence | Rectification | Result |
|---|---|---|---|
| C1–C8 | legacy modules `c1_compiler.py`…`c8_agent.py` were mapped to incompatible component labels | canonical packages now follow the ADD components; legacy modules are compatibility façades | PASS |
| Governed Context Set | incomplete propagation and transport-principal rules | immutable GCS type plus boundary enforcement matrix and fail-closed rules | PASS |
| action FSM | legacy 32-transition model was presented beside the ADD requirement | exact ordered registry of 44 approved tuples, guards, precedence and indeterminate semantics | PASS |
| marking | only a generic join/clearance model was specified | restriction LUB, purpose intersection, unknown-deny and signed declassification transition specified | PASS |
| outbox/storage | PostgreSQL appeared to be the production C3 baseline | selected CIs are explicit; PostgreSQL is a reference atomic adapter; no implicit C3 fallback | PASS |
| BA namespace | BA-01–BA-08 named unrelated runtime primitive tests | BA is reserved for ADD CI acceptance; old tests are RBA-01–RBA-08 | PASS |
| wire protocols | runtime verification API/Proto appeared normative | six Named Query Gateway paths and `ocor.registry.v1` registry services are normative; legacy surface is compatibility-only | PASS |
| traceability | document and implementation status were conflated | ADD→LLD mapping is complete; implementation gaps have separate `LLD-IG-*` identifiers | PASS |

## Exact FSM finding

The normative LLD FSM table contains 44 and only 44 ordered transition tuples. It includes the suffix families `T09a/b`, `T10a/b`, `T17a/b`, `T18a/b`, `T20a/b/c`, `T21a/b/c/d/e`, `T23a/b`, and `T31a/b`. Startup integrity requires rejection of missing, extra, duplicate or mismatched tuples.

The legacy 32-transition implementation is retained only as `LLD-IG-002`; it is not accepted as ADD evidence.

## Acceptance namespace finding

The ADD meanings are preserved:

- BA-01 TerminusDB versioned asserted state and atomic outbox;
- BA-02 TypeDB facts/watermark atomicity;
- BA-03 TypeDB exact-at-commit sandbox;
- BA-04 Jena RDF/JSON-LD/SHACL round trip;
- BA-05 Temporal/PostgreSQL workflow semantics;
- BA-06 S3-compatible/PostgreSQL immutable scenario results;
- BA-07 Kafka/Strimzi ordering, replay, DLQ and registry;
- BA-08 OPA/Keycloak/SPIFFE/OpenBao fail-closed policy and ≤10-second revocation/expiry enforcement.

The earlier runtime behaviours use `RBA-*` compatibility identifiers and cannot satisfy ADD acceptance by name alone.

## Validation gate

`reports/tests/test_lld_add_alignment.py` performs a deterministic, standard-library-only comparison and emits JSON. The gate checks:

- all canonical C1–C8 names and packages;
- ordered equality of all 44 FSM tuples;
- BA/RBA separation and selected-CI names;
- the exact six OpenAPI paths;
- Proto package and service names;
- the five authoritative schema identifiers;
- GCS, canonicalization, marking, outbox, fence and lease tokens;
- closure of `LLD-BL-004`–`006`;
- retention of `LLD-IG-001`–`007`.

GitHub Actions workflow `.github/workflows/ocor-lld-add-alignment.yml` runs this gate on the alignment branch, relevant pull requests and manual dispatch, and uploads the JSON result.

## Residual implementation gates

| Gap | Production consequence |
|---|---|
| LLD-IG-001 | canonical packages and public ports are not fully executable |
| LLD-IG-002 | action implementation does not yet implement the approved FSM |
| LLD-IG-003 | BA-01–BA-08 selected-CI campaign remains incomplete |
| LLD-IG-004 | public ADD OpenAPI/Proto stubs and cross-wire tests remain incomplete |
| LLD-IG-005 | GCS and emission fence are not enforced on every boundary |
| LLD-IG-006 | C4, C5 and C7 are absent or partial |
| LLD-IG-007 | PostgreSQL evidence does not replace TerminusDB BA-01 |

These gaps block a claim of complete runtime conformance or production readiness. They do not re-open the document-level alignment result.

## Governance conclusion

The corrected LLD is coherent with the approved ADD v1.2 and is suitable as the implementation contract for subsequent remediation. The ADD remains unchanged and approved. Runtime implementation promotion remains subject to closure of every `LLD-IG-*` item and governed BA-01–BA-08 evidence.
