# OCOR Runtime Verification Evidence Report

Date: 2026-08-30  
Baseline authority: ADD v1.2 approval and ARA decisions DEC-197 through DEC-205, as stated in the execution mandate  
Result: **PASS — 104 passed, 0 failed, 0 skipped**

## Scope and source basis

This repository was initialized with zero-byte copies of
`OCOR_ADD_v1.2_APPROVED_BASELINE.md` and `ARA_DECISION_RECORD_v1.1.md`. The
executable traceability below therefore treats the supplied task contract and
ratification statement as the authoritative minimum. FR-095 is not claimed by
this PoC slice, and ELM-070 remains deferred as directed.

The delivered slice contains:

- C1 through C8 Python runtime modules and compatibility exports;
- eight JSON Schema 2020-12 documents, one OpenAPI 3.1 document, and one Proto3 contract;
- BA-01 through BA-08 executable backend-assumption tests;
- exactly 35 named EV acceptance tests;
- the ARA-approved PostgreSQL transactional-outbox and reconciler fallback.

## Verification execution

Primary command:

```text
uv run --extra test python -m pytest -v --cov=src tests/
```

Observed result:

```text
104 passed in 0.72s
1533 statements, 161 missed, 89% aggregate statement coverage
0 failures, 0 errors, 0 skips
```

Environment: CPython 3.12.14, pytest 9.1.1, pytest-cov 7.1.0.

Additional independent validations:

- OpenAPI 3.1 validated with `openapi-spec-validator` 0.9.0.
- Proto3 compiled successfully with `grpc_tools.protoc`; the descriptor set was 4,811 bytes.
- RFC 8785 number serialization was differentially checked against the independent `rfc8785` package over 10,011 finite IEEE-754 values with no mismatch.
- All JSON schemas passed `Draft202012Validator.check_schema`, local reference resolution, format checks, and representative positive/negative instance checks.
- Anti-RV-01 recursively checked every list-valued `required` keyword in JSON Schema and OpenAPI conditional structures; every required field is declared in the same branch's `properties`.

## C1–C8 implementation evidence

| Subsystem | Implementation | Verified semantics |
|---|---|---|
| C1 | `src/ocor_runtime/c1_compiler.py`, `canonical.py` | Offline schema validation, RFC 8785 canonicalization, content addressing, immutable compiled output, marking-independent semantic identity |
| C2 | `src/ocor_runtime/c2_identity.py` | Immutable identities, normalized exact aliases, evidence threshold/margin, Identify-or-Abstain |
| C3 | `src/ocor_runtime/c3_store.py` | Single-writer boundary, optimistic concurrency, atomic aggregate/outbox commit, idempotency, five crash windows |
| C4 | `src/ocor_runtime/c4_marking.py` | Validated finite total/partial lattices, least-upper-bound join, meet, monotonic multi-scheme marking, clearance checks |
| C5 | `src/ocor_runtime/c5_actions.py` | ACT-T01 through ACT-T31b, all concrete branches executed, temporal guards, hash-chained audit history, tamper rejection |
| C6 | `src/ocor_runtime/c6_capabilities.py` | Subject/operation/resource scope, inclusive start/exclusive expiry, revocation, delegation non-escalation, usage limits |
| C7 | `src/ocor_runtime/c7_emission.py` | Durable-event provenance, integrity and ordering checks, capability/marking gates, sink retry, deduplication, EMISSION-FENCE |
| C8 | `src/ocor_runtime/c8_agent.py` | AST-whitelist sandbox, trusted-tool boundary, resource limits, deterministic token reservations, structured responses, Identify-or-Abstain |

ACT-T31 is represented by its two ratified concrete outcomes, ACT-T31a and
ACT-T31b. The table therefore contains 31 conceptual decisions and 32 concrete
state/event edges; every edge is exercised by EV-020.

## Backend assumptions

| ID | Evidence | Result |
|---|---|---|
| BA-01 | Four pre-commit crash windows expose neither record; post-commit/pre-ack exposes both; retry replays one event. PostgreSQL fallback and reconciler SQL paths are exercised. | PASS |
| BA-02 | An identical idempotency retry returns the original receipt; key rebinding is rejected. | PASS |
| BA-03 | Non-authoritative writers are rejected; two concurrent writes against one version yield one commit and one conflict. | PASS |
| BA-04 | RFC 8785 vectors, UTF-16 key ordering, duplicate-key rejection, non-finite/unsafe-number rejection. | PASS |
| BA-05 | Action activation is `not_before <= now < expires_at`; explicit expiry and monotonic audit-clock guards are enforced. | PASS |
| BA-06 | Total and diamond lattices satisfy commutativity, associativity, idempotence, least-upper-bound, and no-downgrade properties. | PASS |
| BA-07 | Uncommitted, forged, tampered, premature, or out-of-order events cannot cross EMISSION-FENCE; sink failures remain retriable. | PASS |
| BA-08 | Lease start, exact expiry, revocation, parent revocation, delegation, resource scope, and usage exhaustion fail closed. | PASS |

The primary in-memory C3 backend reports and demonstrates atomic
multi-document writes. The fallback selector automatically chooses
`PostgreSQLTransactionalOutbox` when a candidate lacks that capability. The
fallback was verified through its DB-API transaction contract; no live
PostgreSQL service was required or provisioned.

## EV-001 through EV-035 acceptance evidence

| Criterion | Executable evidence | Result |
|---|---|---|
| EV-001 | Deterministic RFC 8785 object ordering and digest stability | PASS |
| EV-002 | ECMAScript number boundaries and JSON string escaping | PASS |
| EV-003 | Fail-closed rejection of non-I-JSON values | PASS |
| EV-004 | Content-addressed, immutable compiler output | PASS |
| EV-005 | Normative schema enforcement with offline external-reference registry | PASS |
| EV-006 | Exact canonical identity resolution | PASS |
| EV-007 | Unique normalized alias resolution | PASS |
| EV-008 | Unknown identity abstention | PASS |
| EV-009 | Ambiguous identity abstention without guessing | PASS |
| EV-010 | Evidence threshold/margin and identity immutability | PASS |
| EV-011 | Single-writer mutation boundary | PASS |
| EV-012 | Optimistic version conflict and lost-update prevention | PASS |
| EV-013 | Atomic visibility across all five C3 crash windows | PASS |
| EV-014 | Idempotent retry without duplicate event | PASS |
| EV-015 | Committed, integrity-bound, version-ordered outbox records | PASS |
| EV-016 | Total-order marking least upper bound | PASS |
| EV-017 | Partial-lattice compartment join | PASS |
| EV-018 | Monotonic multi-scheme join and fail-closed clearance | PASS |
| EV-019 | Marking non-interference: stable semantic digest, distinct envelope digest | PASS |
| EV-020 | Complete ACT-T01…ACT-T31b table and execution of every concrete edge | PASS |
| EV-021 | Successful lifecycle with complete tamper-evident audit chain | PASS |
| EV-022 | Undefined transition rejection without mutation | PASS |
| EV-023 | Inclusive-start/exclusive-end action guards | PASS |
| EV-024 | Audit evidence tamper detection and transition rejection | PASS |
| EV-025 | Explicit compensation and abstention FSM outcomes | PASS |
| EV-026 | Exact capability-lease expiry boundary | PASS |
| EV-027 | Subject, operation, and resource scope isolation | PASS |
| EV-028 | Delegation non-escalation, ancestor revocation, and usage exhaustion | PASS |
| EV-029 | EMISSION-FENCE rejection of uncommitted or integrity-broken events | PASS |
| EV-030 | Ordered and deduplicated external effects | PASS |
| EV-031 | Combined live-capability and marking-clearance emission gate | PASS |
| EV-032 | Strict sandbox allowed operations and escape rejection | PASS |
| EV-033 | Token-budget preflight and measured-output enforcement | PASS |
| EV-034 | Agent-kernel Identify-or-Abstain behavior | PASS |
| EV-035 | End-to-end C1→C8 marked action compilation, identity, persistence, authorization, and emission | PASS |

The named evidence functions are under `tests/acceptance_ev/`; pytest collected
exactly 35 `test_ev_*` functions.

## Normative schema inventory

- `action.schema.json`
- `agent-response.schema.json`
- `capability-lease.schema.json`
- `evidence.schema.json`
- `identity-record.schema.json`
- `marking-scheme-definition.schema.json`
- `outbox-event.schema.json`
- `semantic-envelope.schema.json`
- `ocor.openapi.yaml`
- `ocor_runtime.proto`

## SHA-256 implementation evidence

Individual implementation files:

| File | SHA-256 |
|---|---|
| `src/ocor_runtime/canonical.py` | `477643c8697383c66de66cc21250a75b3d5c0220916e41e642c5b33e7531556b` |
| `src/ocor_runtime/c1_compiler.py` | `dc2163c94984581dab80a508cd6381ebc37963a6b8dcc0c67e93388a934f2403` |
| `src/ocor_runtime/c2_identity.py` | `bbd7794ccc5a43d7e29f0941407edf8ad144acc42faaeec2f24690cfdfff987b` |
| `src/ocor_runtime/c3_store.py` | `ae512d45553f29e7de3d011e273f39f59ebb487d9db3b60f09c889f6c8cd4470` |
| `src/ocor_runtime/c4_marking.py` | `c47a105c68ab98fd55a47ac70e49b1f06972b7158ea2a8f6bd8b2a666bb5b174` |
| `src/ocor_runtime/c5_actions.py` | `67dd567fce6cc200ab17c95f81066121307c32b127d6371e3473718e95b712ba` |
| `src/ocor_runtime/c6_capabilities.py` | `d957edfd056c9b307d2f85a105be1ead1415123915bc73749a4ab6e3428d6cb8` |
| `src/ocor_runtime/c7_emission.py` | `30f41939aff56e514697297b7a21058eca1abb437d5e2dd42317085f7e66c933` |
| `src/ocor_runtime/c8_agent.py` | `d1fb3c77fe100891db4db04524333cef39d0f950b0dc43621234a7175feb532c` |
| `src/ocor_runtime/fallback/postgres_outbox.py` | `4841a7f84cada3a803eb84de2930d2041446b4ec90c9aceea57f66bfe1a3c629` |

Deterministic manifest digests were calculated by hashing each file with
`sha256sum`, sorting by relative path, then hashing that manifest:

| Manifest | SHA-256 |
|---|---|
| All Python implementation files under `src/` | `68f22870bd4afbe74775ccff88636990fee93036cc117e5e224d429d9099091f` |
| All normative files under `schemas/` | `3459220409af3f86bd56fd9dad1b44d03ab73a8e93904aaf07f53c0522cfcb3c` |
| All Python verification files under `tests/` | `8d208e41aad7e771400646d636047deed962114fe88eedafba62c8bd58910bdc` |
| `pyproject.toml` | `9253bb50ab3b3ce1dc6fc48bed285504b05ee83b2005321f00fb26377b580f3e` |
| `uv.lock` | `7cfe389e1d12995bcac6ee1ce0356c7054724b2eee03401c41bb2650ce859c69` |

These digests exclude this report and generated caches/coverage data.
