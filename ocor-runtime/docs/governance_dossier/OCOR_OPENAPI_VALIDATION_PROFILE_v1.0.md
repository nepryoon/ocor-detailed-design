# OCOR OpenAPI 3.1 Governed Validation Profile v1.0

## Control

| Field | Value |
|---|---|
| Status | APPROVED VALIDATION PROFILE |
| Effective date | 2026-08-30 |
| Authority basis | ARA Decision Record v1.1, `VAL-ACT-002`; explicit Product Owner instruction to execute governed validation or waiver |
| Validator | `openapi-spec-validator==0.9.0` |
| Locked wheel SHA-256 | `222fecffc7714f6d0a6ad62c0e4b66cc2b7dbfafb7b93acfc6c308abbdb51af8` |
| Lock source | `ocor-runtime/uv.lock` |
| Runtime | CPython 3.12 |
| Waiver policy | A waiver is permitted only when the selected validator cannot execute for an environmental reason and must identify the unexecuted checks. A successful governed run requires no waiver. |

## Validation subjects

1. The OpenAPI 3.1 contract embedded by value in `OCOR_ADD_v1.2_APPROVED_BASELINE.md`.
2. The executable runtime contract `ocor-runtime/schemas/ocor.openapi.yaml`.

## Acceptance rules

A subject passes only when all of the following hold:

- UTF-8/YAML parsing succeeds;
- the document declares an `openapi` version matching `3.1.x`;
- `openapi-spec-validator` completes without exception;
- every referenced local resource resolves from the subject base URI;
- subject SHA-256, validator version, execution context and result are recorded in `reports/tests/openapi_31_validation_results.json`.

The two subjects are independent. A pass for one cannot mask a failure for the other. Any failure keeps `VAL-ACT-002` open and fails closed.

## Scope fence

This profile validates OpenAPI semantics and reference integrity. It does not prove authorization correctness, runtime behaviour, availability, performance, interoperability with every client generator, or production readiness.
