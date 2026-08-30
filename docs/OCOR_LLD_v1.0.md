# OCOR Runtime — Low-Level Design v1.0

## 0. Document control

| Field | Value |
|---|---|
| Document | `OCOR_LLD_v1.0.md` |
| Repository | `nepryoon/ocor-detailed-design` |
| Inspected branch/commit | `main` / `ddfa97d1cacec23afdf767702c7c0fd816e66431` |
| Inspection date | 2026-08-30 |
| Runtime | CPython ≥3.11; package `ocor-runtime` 0.1.0 |
| LLD status | **ENGINEERING CANDIDATE — BASELINE AUTHORITY NOT CONFIRMED** |
| Release effect | None; this document does not approve a baseline, close risk, or promote evidence |

This document is the complete implementation-level specification for the runtime slice at the inspected commit. It is intentionally fail-closed about authority: it can guide implementation and review, but cannot become an approved LLD until §1.4 is closed by the Architecture Review Authority (ARA).

“Existing” identifies executable code at the inspected commit. “Target” identifies a concrete alignment obligation derived from the ADD v1.2 Candidate; a target is not implementation evidence.

## 1. Prerequisites and authority decision

### 1.1 Repository evidence

| Required deliverable | Git object | Size | Result |
|---|---:|---:|---|
| `ocor-runtime/docs/governance_dossier/OCOR_ADD_v1.2_APPROVED_BASELINE.md` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | **FAIL** — empty file |
| `ocor-runtime/docs/governance_dossier/ARA_DECISION_RECORD_v1.1.md` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 | **FAIL** — empty file |
| `ocor-runtime/VERIFICATION_EVIDENCE_REPORT.md` | `aa7efd09ea9f2841e7e934eea9ed173e006a94c7` | 10,161 | Present; self-reports 104 passed |
| `ocor-runtime/schemas/` | 10 files | 24,048 | Present: 8 JSON Schemas, OpenAPI 3.1, Proto3 |
| `reports/OCOR_Architectural_Design_Document_v1.2_Candidate.md` | `8d6bf00eeb9dd81cb217ba4c05dbb6ce8cd353f2` | 224,714 | Present, not approved |
| `reports/OCOR_ADD_v1.2_Final_Review.md` | `2299995c97f67bd3fde08101b244c2d424e0c217` | 6,724 | Present; conditional verdict |

The Final Review labels the candidate `PROPOSED — AWAITING CHANGE CONTROL` and concludes `READY FOR DDD AFTER CHANGE-CONTROL APPROVAL`. The runtime evidence report states it relied on the execution mandate because the approved baseline and decision record were zero-byte files. Repository evidence therefore does not confirm ADD v1.2 approval.

### 1.2 Authority hierarchy

1. Non-empty, signed or digest-pinned approved ADD and ARA decision record.
2. Approved decision/register entries referenced by that baseline.
3. Versioned contracts approved with the baseline.
4. This LLD.
5. Runtime code, tests, and generated verification reports.

Levels 4–5 MUST NOT infer approval when levels 1–2 are absent. A higher-level conflict makes the lower-level artifact a remediation target.

### 1.3 Decision

The authoritative prerequisite gate is **BLOCKED**. Engineering continues through this conditional LLD so progress is not lost. Every divergence is represented explicitly; none is converted into assumed approval.

### 1.4 Baseline blockers

| ID | Blocker | Consequence | Closure evidence |
|---|---|---|---|
| `LLD-BL-001` | Approved ADD is empty | No authoritative text/digest | Non-empty baseline with approval metadata and immutable digest |
| `LLD-BL-002` | ARA record is empty | DEC-197–205 cannot be independently verified | Decisions, dispositions, authority, date, signatures/digests |
| `LLD-BL-003` | Candidate awaits change control | Candidate cannot be promoted by implementation inference | Approved package and updated registers |
| `LLD-BL-004` | Runtime C1–C8 labels diverge from candidate container meanings | Nominal coverage is not conformance | Approved mapping or package realignment |
| `LLD-BL-005` | Candidate audit says 44 FSM tuples; runtime has 32 edges | Conflicting `ACT-T*` meanings | ARA-selected table and regenerated contracts/tests |
| `LLD-BL-006` | Candidate and runtime reuse BA-01–08 for different properties | Evidence namespace ambiguous | Versioned assumption register and unique IDs |

## 2. Non-negotiable invariants

### 2.1 RFC 8785 and SHA-256

1. Digest-bearing JSON MUST be valid I-JSON and canonicalized by RFC 8785/JCS.
2. Object keys MUST be ordered by unsigned UTF-16 code units.
3. Lone surrogates, duplicate members, NaN, infinities, non-string keys, and integers outside `[-9007199254740991,9007199254740991]` MUST be rejected.
4. `-0.0` serializes as `0`; exponent notation follows ECMAScript thresholds ≥21 or ≤-7.
5. `canonical_sha256(x) = lowercase_hex(SHA-256(UTF8(JCS(x))))`.
6. Semantic identity excludes top-level `markings`, `$markings`, and `operationalMetadata`; envelope identity includes the complete admitted envelope.
7. Proto bytes, source JSON formatting, JSONB representation, and Python `repr` MUST NOT be semantic-digest inputs.

Anchors: `canonical.py::{load_i_json,canonicalize_json,canonicalize,canonical_sha256}`, `c1_compiler.py::{semantic_view,SemanticCompiler.compile}`; EV-001–005 and runtime BA-04.

### 2.2 Single writer, optimistic concurrency, atomic outbox

For each `(branch, aggregate_id)` there is one current writer epoch. A mutation satisfies:

\[
expected\_version=current\_version \land writer\_epoch=current\_epoch
\]

and atomically creates:

\[
(aggregate\_version+1,\ canonical\_state,\ transaction\_id,\ outbox\_event,\ idempotency\_binding)
\]

Readers observe both state and outbox or neither. Same key/same request digest returns the original receipt; same key/different digest raises `ConcurrencyConflict`. The broker never joins the database transaction. Delivery is at-least-once; consumer idempotency is mandatory.

Anchors: `AtomicOutboxStore.write`, `PostgreSQLTransactionalOutbox.write`, `OutboxReconciler.reconcile_once`; EV-011–015 and runtime BA-01–03.

### 2.3 Marking lattice

Each scheme is a finite partial order with unique labels, bottom, top, join and meet for every pair. The constructor enforces antisymmetry and closure. Restriction aggregation uses least-upper-bound join and satisfies commutativity, associativity, idempotence and monotonicity. Unknown schemes/labels, non-lattices and missing clearance dimensions fail closed. Disclosure requires clearance to dominate every marking.

Anchors: `MarkingSchemeDefinition::{leq,dominates,join,meet}`, `MarkingEngine::{validate,join,is_authorized,disclose}`; EV-016–019 and runtime BA-06.

### 2.4 ACT-T01 through ACT-T31b

| ID | Source | Event | Target | Window |
|---|---|---|---|---|
| ACT-T01 | DRAFT | SUBMIT | PROPOSED | — |
| ACT-T02 | DRAFT | CANCEL | CANCELLED | — |
| ACT-T03 | PROPOSED | VALIDATE | VALIDATED | — |
| ACT-T04 | PROPOSED | REJECT | REJECTED | — |
| ACT-T05 | PROPOSED | CANCEL | CANCELLED | — |
| ACT-T06 | VALIDATED | AUTHORIZE | AUTHORIZED | — |
| ACT-T07 | VALIDATED | REJECT | REJECTED | — |
| ACT-T08 | VALIDATED | CANCEL | CANCELLED | — |
| ACT-T09 | AUTHORIZED | SCHEDULE | SCHEDULED | — |
| ACT-T10 | AUTHORIZED | DISPATCH | READY | active |
| ACT-T11 | AUTHORIZED | REVOKE | CANCELLED | — |
| ACT-T12 | SCHEDULED | ACTIVATE | READY | active |
| ACT-T13 | SCHEDULED | RESCHEDULE | SCHEDULED | — |
| ACT-T14 | SCHEDULED | EXPIRE | EXPIRED | expired |
| ACT-T15 | SCHEDULED | CANCEL | CANCELLED | — |
| ACT-T16 | READY | START | RUNNING | active |
| ACT-T17 | READY | DEFER | SCHEDULED | — |
| ACT-T18 | READY | EXPIRE | EXPIRED | expired |
| ACT-T19 | READY | CANCEL | CANCELLED | — |
| ACT-T20 | RUNNING | PAUSE | PAUSED | — |
| ACT-T21 | RUNNING | SUCCEED | SUCCEEDED | — |
| ACT-T22 | RUNNING | FAIL | FAILED | — |
| ACT-T23 | RUNNING | CANCEL | CANCELLED | — |
| ACT-T24 | PAUSED | RESUME | RUNNING | active |
| ACT-T25 | PAUSED | FAIL | FAILED | — |
| ACT-T26 | PAUSED | CANCEL | CANCELLED | — |
| ACT-T27 | FAILED | RETRY | READY | — |
| ACT-T28 | FAILED | COMPENSATE | COMPENSATING | — |
| ACT-T29 | SUCCEEDED | COMPENSATE | COMPENSATING | — |
| ACT-T30 | COMPENSATING | COMPLETE | COMPENSATED | — |
| ACT-T31a | COMPENSATING | FAIL | FAILED | — |
| ACT-T31b | READY | ABSTAIN | ABSTAINED | — |

The runtime has 31 conceptual decisions and 32 concrete edges. Active means `not_before <= occurred_at < expires_at`; expired means `occurred_at >= expires_at`. Audit time is non-decreasing. Every transition appends a hash-chained immutable entry. Invalid event, stale version, time violation or bad history leaves the action unchanged. The candidate’s 44-tuple FSM is not merged; `LLD-BL-005` remains open.

### 2.5 Capability lease guards

A lease is active exactly when:

\[
not\_before \le now < expires\_at \land (revoked\_at=\varnothing \lor now<revoked\_at)
\]

Authorization also requires authoritative registration, subject match, operation/resource scope, active ancestry and remaining uses. Delegation cannot widen capability, resource or time. Parent revocation/expiry invalidates descendants. Consuming a use is atomic with the protected local operation when they share persistence.

### 2.6 EMISSION-FENCE

An effect crosses only if:

\[
G_{emit}=Committed \land Integrity \land Ordered \land Fresh \land Authorized \land MarkingAllowed \land AuditAvailable
\]

Existing code enforces committed status, digest integrity, aggregate order, occurrence time, optional capability, optional marking and in-process deduplication. Target code also validates state revision, policy digest/validity, release, watermark, stop epoch, deadline, circuit breaker, adapter conformance, immutable GatePackage and audit availability immediately before first send, retry and compensation. Sink failure leaves the event pending; receipt follows acknowledgement only.

## 3. Package and C1–C8 allocation

### 3.1 Existing surface versus candidate ADD

| Runtime module | Existing responsibility | Candidate allocation | Status |
|---|---|---|---|
| `c1_compiler.py` | Schema/JCS/content-addressed artifact | C1 Compiler | PARTIAL |
| `c2_identity.py` | Identity and abstention | C2/C8 support | MISLABELLED/PARTIAL; Gateway absent |
| `c3_store.py` | Aggregate/outbox reference store | C3 State/Outbox | PARTIAL |
| `c4_marking.py` | Marking lattice | Cross-cutting security | MISLABELLED; Projection C4 absent |
| `c5_actions.py` | Action FSM/audit | C6 Action Engine | MISLABELLED; Event Backbone C5 absent |
| `c6_capabilities.py` | Capability leases | C2/C6/C8 control | MISLABELLED/PARTIAL |
| `c7_emission.py` | Emission fence | C3/C5/C6 boundary | MISLABELLED; Causal C7 absent |
| `c8_agent.py` | Sandbox, budget, agent kernel | C8 Agent Kernel | PARTIAL |

Top-level `src/c1_compiler.py` through `src/c8_agent.py` are compatibility re-export shims.

### 3.2 Target layout

```text
src/ocor_runtime/
  canonical.py, errors.py, contracts.py
  c1_compiler.py, c2_identity.py, c3_store.py, c4_marking.py
  c5_actions.py, c6_capabilities.py, c7_emission.py, c8_agent.py
  gateway/{service.py,router.py,consistency.py,interceptors.py}
  projection/{ports.py,projector.py,watermark.py,reconciler.py}
  eventing/{ports.py,dispatcher.py,replay.py,quarantine.py}
  actions/{coordinator.py,gate.py,dispatcher.py,reconciliation.py}
  causal/{models.py,overlay.py,runtime.py,jobs.py,sealing.py}
  persistence/{ports.py,postgres.py,embedded.py,migrations/0001_runtime.sql}
  workers/{supervisor.py,lease_expiry.py}
  wire/{json_codec.py,protobuf_codec.py,grpc_service.py,http_service.py}
```

Existing public classes remain stable. Domain modules depend only on contracts/ports; adapters depend on domain modules; composition depends on both. No circular dependencies.

### 3.3 Typed exceptions

| Exception | Trigger | HTTP | gRPC | Retry |
|---|---|---:|---|---|
| `CanonicalizationError` | Non-I-JSON | 422 | INVALID_ARGUMENT | no |
| `SchemaValidationError` | Contract violation | 422 | INVALID_ARGUMENT | no |
| `IdentityConflictError` | Immutable identity conflict | 409 | ALREADY_EXISTS | adjudicate |
| `SingleWriterViolation` | Wrong writer/epoch | 403 | PERMISSION_DENIED | refresh authority |
| `ConcurrencyConflict` | Version/idempotency conflict | 409 | ABORTED | conditional |
| `MarkingError` | Invalid lattice/label | 422 | FAILED_PRECONDITION | no |
| `InvalidTransition` | Undefined edge/bad history | 409 | FAILED_PRECONDITION | no |
| `TemporalGuardViolation` | Bad/out-of-window time | 409 | FAILED_PRECONDITION | re-evaluate |
| `AuthorizationError` | Invalid capability | 403 | PERMISSION_DENIED | reacquire |
| `EmissionBlocked` | Fence false | 409 | FAILED_PRECONDITION | bounded |
| `SandboxViolation` | Forbidden operation/result | 403 | PERMISSION_DENIED | no |
| `TokenBudgetExceeded` | Budget exhausted | 429 | RESOURCE_EXHAUSTED | approved increase |

Wire errors include `code`, safe `message`, `correlation_id`, `retryable`; never SQL, stacks, credentials, policy internals or marked payload.

## 4. Concrete classes and extensions

### 4.1 C1 compiler

Existing: frozen `CompiledArtifact`; `SemanticCompiler` with offline Draft 2020-12 registry, deterministic validation and `compile`; `semantic_view`.

Target: `CompilerPort.compile`, `ReleaseVerifier.verify`, content-addressed `ArtifactRepository.put_if_absent`, and `SemanticDiff.compare` returning `NO_CHANGE`, `NON_BREAKING`, `BREAKING` or `INDETERMINATE`. Cache key is `(schema_digest,semantic_digest,compiler_version)`.

### 4.2 C2 identity and Gateway

Existing: `IdentityRecord`, `ResolutionOutcome`, `IdentityRegistry`, `normalize_identifier` (NFKC/trim/casefold, no fuzzy guessing).

Target: `SemanticGateway.get_object/query_object_set/search/traverse/explain/get_provenance`; `TransportIdentityInterceptor`; `PolicyAuthorityInterceptor`; `ConsistencyPlanner`; `ResultSanitizer`; `NamedContractRouter`. Public raw SQL/Cypher/Datalog/TypeQL/WOQL/SPARQL is rejected. Cache keys include governed-context, branch, release, policy, named query, parameters and consistency target.

### 4.3 C3 state/outbox

Existing: `StoredDocument`, `OutboxEvent`, `WriteResult`, `CrashWindow`, `AtomicOutboxStore`, PostgreSQL fallback and reconciler.

Target ports have the following exact async signatures:

| Port | Method signature |
|---|---|
| `AtomicStateStore` | `commit(command: CommitCommand) -> WriteResult` |
| `AtomicStateStore` | `get(aggregate_id: str, branch: str = "main") -> StoredDocument or None` |
| `OutboxRepository` | `claim_batch(worker_id: str, limit: int, lease_seconds: int) -> immutable sequence of OutboxEvent` |
| `OutboxRepository` | `acknowledge(event_id: str, emitted_at: datetime, sink_receipt: str) -> None` |
| `OutboxRepository` | `release(event_id: str, next_attempt_at: datetime, error_code: str) -> None` |

`CommitCommand` carries aggregate/branch/document, expected version, writer ID/epoch, event/payload, idempotency key, time, Decision, Authority, Evidence refs and GatePackage digest. Missing governance rejects before persistence.

### 4.4 C4 marking/projections

Marking classes remain cross-cutting. Candidate C4 adds `ProjectionAdapter.project/get_watermark/rebuild`, `ProjectionReconciler.compare`, and `CapabilityProbe.run`. Projectors deduplicate `(projection_id,branch,commit_id)`, commit facts plus watermark locally, and never reverse-write canonical state.

### 4.5 C5 Event Backbone

`c5_actions.py` remains compatibility code logically owned by C6. Target C5 adds `EventEnvelopeValidator`, deterministic `Partitioner`, `EventJournal`, `OutboxDispatcher`, bounded `ReplayController`, and append-only `QuarantineRepository`. Ordering is per key/partition; end-to-end exactly-once is never claimed.

### 4.6 C6 Action Engine

Existing: FSM/audit and capability classes. Target: `ActionCoordinator`, `GatePackageVerifier`, `FencedActionDispatcher`, `ExecutionReconciler`, `CompensationCoordinator`. Transition, audit, state and outbox persist atomically. Ambiguous timeout remains blocked/adjudication-required. The 16-state runtime FSM is no-go for production until authority chooses the table.

### 4.7 C7 Causal Runtime

`c7_emission.py` remains a compatibility location, not Candidate C7. Target adds `ScenarioRunSpec`, capability-isolated `ScenarioOverlayStore`, `CausalRuntime`, durable `CausalJobController`, and `ResultSealer`. Non-identifiability, OOD, invalid validity or stale context returns `ABSTAIN`. C7 emits only SimulationResult/Recommendation/DecisionProposal, never ActionCommand or `main` mutation.

### 4.8 C8 Agent Kernel

Existing: `TokenBudget`, `StrictSandbox`, `AgentResponse`, `ModelResult`, `AgentModel`, `AgentKernel`. Exact sandbox defaults: 4,096 source chars, 256 AST nodes, 1,024 operations, 65,536 result chars; exponent magnitude ≤16. No imports, attributes, mutation, comprehensions, lambdas, builtins or unregistered calls.

Target adds `RunLedger`, `CapabilityBroker`, `TaintFirewall`, `HandoffBroker`, `KillSwitchListener`. Memory/retrieval/tool output remain tainted and cannot grant authority or change pins.

## 5. Storage engine and DAL

### 5.1 PostgreSQL 16 DDL

```sql
CREATE SCHEMA IF NOT EXISTS ocor;

CREATE TABLE IF NOT EXISTS ocor.aggregate_state (
  branch text NOT NULL DEFAULT 'main',
  aggregate_id text NOT NULL,
  aggregate_version bigint NOT NULL CHECK (aggregate_version > 0),
  writer_id text NOT NULL,
  writer_epoch bigint NOT NULL CHECK (writer_epoch > 0),
  document jsonb NOT NULL,
  semantic_digest char(64) NOT NULL CHECK (semantic_digest ~ '^[0-9a-f]{64}$'),
  envelope_digest char(64) NOT NULL CHECK (envelope_digest ~ '^[0-9a-f]{64}$'),
  last_transaction_id uuid NOT NULL,
  occurred_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (branch, aggregate_id),
  UNIQUE (branch, aggregate_id, aggregate_version)
);

CREATE TABLE IF NOT EXISTS ocor.idempotency_binding (
  idempotency_key text PRIMARY KEY,
  request_digest char(64) NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
  transaction_id uuid NOT NULL UNIQUE,
  event_id uuid NOT NULL UNIQUE,
  aggregate_id text NOT NULL,
  aggregate_version bigint NOT NULL CHECK (aggregate_version > 0),
  created_at timestamptz NOT NULL,
  expires_at timestamptz,
  CHECK (expires_at IS NULL OR expires_at > created_at)
);

CREATE TABLE IF NOT EXISTS ocor.outbox_event (
  event_id uuid PRIMARY KEY,
  transaction_id uuid NOT NULL UNIQUE,
  branch text NOT NULL CHECK (branch = 'main'),
  aggregate_id text NOT NULL,
  aggregate_version bigint NOT NULL CHECK (aggregate_version > 0),
  event_type text NOT NULL,
  payload jsonb NOT NULL,
  payload_digest char(64) NOT NULL CHECK (payload_digest ~ '^[0-9a-f]{64}$'),
  request_digest char(64) NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
  idempotency_key text NOT NULL UNIQUE,
  governed_context_digest char(64) NOT NULL CHECK (governed_context_digest ~ '^[0-9a-f]{64}$'),
  gate_package_digest char(64) NOT NULL CHECK (gate_package_digest ~ '^[0-9a-f]{64}$'),
  occurred_at timestamptz NOT NULL,
  status text NOT NULL DEFAULT 'PENDING'
    CHECK (status IN ('PENDING','CLAIMED','EMITTED','QUARANTINED')),
  attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
  next_attempt_at timestamptz NOT NULL,
  claim_owner text,
  claim_expires_at timestamptz,
  emitted_at timestamptz,
  sink_receipt text,
  last_error_code text,
  UNIQUE (branch, aggregate_id, aggregate_version),
  FOREIGN KEY (branch, aggregate_id)
    REFERENCES ocor.aggregate_state(branch, aggregate_id) DEFERRABLE INITIALLY DEFERRED,
  CHECK ((status = 'EMITTED') = (emitted_at IS NOT NULL)),
  CHECK ((status = 'CLAIMED') = (claim_owner IS NOT NULL AND claim_expires_at IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS ocor.reconciliation_intent (
  transaction_id uuid PRIMARY KEY,
  branch text NOT NULL,
  aggregate_id text NOT NULL,
  aggregate_version bigint NOT NULL CHECK (aggregate_version > 0),
  expected_event_id uuid NOT NULL UNIQUE,
  created_at timestamptz NOT NULL,
  reconciled_at timestamptz,
  failure_code text
);

CREATE TABLE IF NOT EXISTS ocor.capability_lease (
  lease_id uuid PRIMARY KEY,
  subject text NOT NULL,
  issuer text NOT NULL,
  capabilities jsonb NOT NULL,
  resources jsonb NOT NULL,
  issued_at timestamptz NOT NULL,
  not_before timestamptz NOT NULL,
  expires_at timestamptz NOT NULL,
  revoked_at timestamptz,
  parent_lease_id uuid REFERENCES ocor.capability_lease(lease_id),
  max_uses bigint CHECK (max_uses > 0),
  use_count bigint NOT NULL DEFAULT 0 CHECK (use_count >= 0),
  CHECK (issued_at <= not_before AND not_before < expires_at),
  CHECK (revoked_at IS NULL OR revoked_at >= issued_at),
  CHECK (max_uses IS NULL OR use_count <= max_uses)
);

CREATE TABLE IF NOT EXISTS ocor.action_instance (
  action_id text PRIMARY KEY,
  state text NOT NULL,
  version bigint NOT NULL CHECK (version >= 0),
  not_before timestamptz,
  expires_at timestamptz,
  last_entry_hash char(64) NOT NULL CHECK (last_entry_hash ~ '^[0-9a-f]{64}$'),
  gate_package_digest char(64) NOT NULL CHECK (gate_package_digest ~ '^[0-9a-f]{64}$'),
  updated_at timestamptz NOT NULL,
  CHECK (not_before IS NULL OR expires_at IS NULL OR not_before < expires_at)
);

CREATE TABLE IF NOT EXISTS ocor.action_audit (
  action_id text NOT NULL REFERENCES ocor.action_instance(action_id),
  version bigint NOT NULL CHECK (version > 0),
  transition_id text NOT NULL,
  source_state text NOT NULL,
  event_name text NOT NULL,
  target_state text NOT NULL,
  occurred_at timestamptz NOT NULL,
  actor text NOT NULL,
  evidence jsonb NOT NULL,
  previous_hash char(64) NOT NULL CHECK (previous_hash ~ '^[0-9a-f]{64}$'),
  entry_hash char(64) NOT NULL CHECK (entry_hash ~ '^[0-9a-f]{64}$'),
  PRIMARY KEY (action_id, version),
  UNIQUE (entry_hash)
);

CREATE INDEX IF NOT EXISTS outbox_dispatch_idx
  ON ocor.outbox_event (next_attempt_at, occurred_at, event_id) WHERE status='PENDING';
CREATE INDEX IF NOT EXISTS outbox_claim_expiry_idx
  ON ocor.outbox_event (claim_expires_at, event_id) WHERE status='CLAIMED';
CREATE INDEX IF NOT EXISTS outbox_aggregate_order_idx
  ON ocor.outbox_event (branch, aggregate_id, aggregate_version);
CREATE INDEX IF NOT EXISTS reconciliation_pending_idx
  ON ocor.reconciliation_intent (created_at, transaction_id) WHERE reconciled_at IS NULL;
CREATE INDEX IF NOT EXISTS capability_expiry_idx
  ON ocor.capability_lease (expires_at, lease_id) WHERE revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS action_state_idx
  ON ocor.action_instance (state, updated_at, action_id);
```

### 5.2 Transactions and locking

Mutation sequence on one connection: idempotency lookup/digest compare; aggregate `FOR UPDATE`; version/epoch/time/governance validation; conditional upsert; insert outbox, idempotency and reconciliation intent; one commit. Zero-row update is `ConcurrencyConflict`. No broker/network call occurs inside.

Dispatcher claims with `FOR UPDATE SKIP LOCKED`, batch 100, setting claim owner/expiry and incrementing attempts. Publish occurs after claim commit. A short transaction acknowledges or releases with bounded exponential backoff ≤60 seconds. Only the minimum non-emitted aggregate version is claimable. Database time governs claims/leases.

Lock order: aggregate/action row → capability row → outbox/idempotency rows. Deadlock `40P01` and serialization `40001` receive at most three jittered retries when idempotency makes retry safe.

### 5.3 Fallbacks

`AtomicOutboxStore` is test/single-process only: copy-on-commit plus `RLock`, no durability or multi-process safety.

Embedded durable mode is SQLite ≥3.45, WAL, `foreign_keys=ON`, `synchronous=FULL`, one writer, `BEGIN IMMEDIATE`. Because no `SKIP LOCKED`, exactly one dispatcher process is allowed. A second dispatcher lock is refused. Semantics and crash tests remain identical.

A non-atomic adapter is never auto-selected for production. PostgreSQL fallback requires an explicit connection factory and release-profile permission.

## 6. Concurrency, workers, memory

One `asyncio` loop per process serves HTTP/gRPC and workers. CPU-heavy canonicalization/schema/causal work uses a bounded pool. Domain `RLock` is never held over network I/O. Current `EmissionFence.emit` calls a sink while locked; production uses durable claim/publish/ack instead.

| Worker | Cadence | Batch | Shutdown |
|---|---:|---:|---|
| Outbox dispatcher | notify + 100 ms idle | 100 | stop claims; finish ≤20 s; release rest |
| Reconciler | 5 s | 100 | finish transaction |
| Lease expiry | 1 s | 500 | inline auth still checks expiry |
| Action reconciliation | 2 s | 100 | persist cursor |
| Scenario TTL | 10 s | 100 | expire/release idempotently |

Cancellation is checked before claim, after each item and before sleep. Supervisor restart backoff: 1,2,4,8,16,30 seconds; five failures/60 s opens the worker circuit.

Memory bounds: request 4 MiB; canonical JSON 8 MiB; 200 in-flight events/process; schema cache 256 entries/15 min; max 100 identity candidates; receipt cache 10,000/30 min; causal in-memory result 64 MiB. Sandbox bounds are §4.8. CPython cyclic GC stays enabled; no hot-loop manual collection. At 85% memory readiness fails, 90% stops expensive jobs, 95% for 60 s triggers orchestration restart after active DB transactions finish.

## 7. Wire protocol

`load_i_json` is the sole text admission parser for digest-bearing JSON. Digests are domain-specific:

| Digest | Canonical input |
|---|---|
| `semantic_digest` | `semantic_view(document)` |
| `envelope_digest` | full admitted envelope |
| `payload_digest` | outbox payload |
| `request_digest` | `{aggregateId,document,eventType,payload}` |
| action `entry_hash` | audit fields + version + previous hash |
| governed-context digest | complete canonical context |
| GatePackage digest | all immutable pins and authority/evidence refs |

OpenAPI is 3.1.0/API 1.2.0 with `/compile`, `/identities:resolve`, `/actions/{actionId}/transitions`, `/outbox/{eventId}:emit`. JSON is camelCase. Timestamps are RFC3339 UTC and timezone-aware. Mutations require `Idempotency-Key` and `If-Match`.

Proto package is `ocor.runtime.v1`; services: `CompilerService`, `IdentityService`, `ActionService`, `EmissionService`. Zero enum values are rejected. `Struct` passes I-JSON validation. Map/wire serialization never supplies digests. JSON↔Proto round trips yield the same domain object and JCS digest. Unknown/default/presence semantics are tested explicitly.

## 8. Test harness

### 8.1 Fixtures

`fixed_now = 2026-08-30T12:00:00Z`; no wall-clock sleeps. Other fixtures: fresh authoritative store; total classification lattice; diamond compartment lattice; empty capability authority; live `agent-1` lease (`+1s` to `+11s`); two ordered aggregate events; offline sibling-schema registry; fake DB-API connection; deterministic recording/failing sink.

### 8.2 BA matrix

| ID | Methods | Parameters | Oracle |
|---|---|---|---|
| BA-01 | Store/PostgreSQL/reconciler | 4 pre-commit windows, post-commit/pre-ack, stale, replay, limits 10/0 | both-or-neither; one replay; rollback stale; repair 1; reject 0 |
| BA-02 | `write` | same key same/different request | prior receipt / conflict |
| BA-03 | writer/version | wrong writer; 2 threads expect v1 | no state; one commit + one conflict |
| BA-04 | JCS | RFC vector, UTF-16 keys, NaN/Inf/2**53, duplicate | exact bytes or canonical error |
| BA-05 | FSM time | start-1µs/start/expiry, expire before/at, backward/naive | inclusive/exclusive, monotonic |
| BA-06 | lattice | total, diamond, duplicate, non-lattice | algebra holds; invalid rejected |
| BA-07 | fence | uncommitted/tampered, v2 first, sink fail/retry | blocked/order/pending/dedup |
| BA-08 | lease | bounds, wrong scope, escalation, one use | fail closed |

Candidate BA identifiers mean different things and must be renamed or versioned after authority resolution.

### 8.3 EV-001–EV-035

| EV | Test function (suffix) | Method/oracle |
|---|---|---|
| EV-001 | `rfc8785_object_order_is_deterministic` | exact canonical order/digest |
| EV-002 | `ecmascript_number_boundaries_and_escaping` | exact thresholds/escapes |
| EV-003 | `non_i_json_values_fail_closed` | invalid values rejected |
| EV-004 | `compiler_is_content_addressed_and_output_is_immutable` | frozen artifact |
| EV-005 | `compiler_enforces_normative_schema_and_external_references` | offline valid/invalid |
| EV-006 | `canonical_identity_is_resolved_exactly` | exact ID, confidence 1 |
| EV-007 | `unique_normalized_alias_resolves` | trim/casefold unique |
| EV-008 | `unknown_identity_produces_explicit_abstention` | no ID |
| EV-009 | `ambiguous_identity_produces_abstention_not_a_guess` | ordered candidates |
| EV-010 | `identity_evidence_requires_threshold_and_margin_and_records_are_immutable` | 0.79 abstains; 0.95/0.20 wins; mutation conflicts |
| EV-011 | `single_writer_boundary_rejects_replica_mutation` | no state/event |
| EV-012 | `optimistic_version_precondition_prevents_lost_update` | stale conflict |
| EV-013 | `all_five_crash_windows_preserve_atomic_visibility` | both-or-neither |
| EV-014 | `idempotent_retry_cannot_duplicate_an_outbox_event` | same event, counts (1,1) |
| EV-015 | `outbox_events_are_committed_integrity_bound_and_versioned` | versions [1,2] |
| EV-016 | `marking_total_order_join_is_the_least_upper_bound` | PUBLIC∨INTERNAL=INTERNAL |
| EV-017 | `marking_partial_lattice_join_combines_compartments` | A∨B=AB |
| EV-018 | `multi_scheme_join_is_monotonic_and_clearance_is_fail_closed` | missing clearance denies/no payload |
| EV-019 | `marking_non_interference_preserves_semantic_identity` | same semantic, different envelope digest |
| EV-020 | `all_act_t01_through_act_t31b_transitions_are_executable_contracts` | exact 32 IDs/targets |
| EV-021 | `happy_path_transition_history_is_complete_and_tamper_evident` | six-step SUCCEEDED |
| EV-022 | `undefined_transition_is_rejected_without_mutating_action` | DRAFT unchanged |
| EV-023 | `temporal_execution_guards_use_inclusive_start_exclusive_end` | -1µs deny/start allow/expiry deny |
| EV-024 | `audit_hash_chain_detects_evidence_tampering` | forged ticket blocks |
| EV-025 | `compensation_and_identify_abstention_are_explicit_fsm_outcomes` | COMPENSATED and T31b |
| EV-026 | `capability_lease_expiration_is_enforced_at_exact_boundary` | exact expiry deny |
| EV-027 | `capability_subject_operation_and_resource_scopes_do_not_leak` | 3 wrong-scope denies |
| EV-028 | `delegation_revocation_and_usage_limits_cannot_be_bypassed` | use/revoke/escalation deny |
| EV-029 | `emission_fence_blocks_uncommitted_or_integrity_broken_events` | both rejected |
| EV-030 | `emission_fence_orders_and_deduplicates_external_effects` | v2-first reject; two deliveries |
| EV-031 | `emission_requires_both_capability_and_marking_clearance` | PUBLIC deny; SECRET ack |
| EV-032 | `strict_sandbox_allows_pure_tools_and_blocks_escape_syntax` | add works; five escapes reject |
| EV-033 | `token_budget_preflights_and_enforces_actual_model_output` | preflight avoids model; reservation cleared |
| EV-034 | `agent_kernel_identifies_only_uniquely_and_otherwise_abstains` | unique identify; ambiguous/unknown abstain |
| EV-035 | `end_to_end_c1_through_c8_semantic_action_emission` | one marked event, key `EV-035` |

Additional release gates: live PostgreSQL crash/restart; two-process writer epoch/claim recovery; lost acknowledgement with sink idempotency; JSON↔Proto digest equality; ≥100,000 random finite float differential cases; lattice properties; approved full FSM; full fence drift matrix; async cancellation; memory bounds.

## 9. Traceability and gates

| Candidate source | LLD | Existing evidence | Status |
|---|---|---|---|
| §2.2 C1, §3.1 | §§2.1,4.1,7 | EV-001–005 | PARTIAL |
| §2.2 C2, §3.0.1/3.3 | §4.2 | EV-006–010 identity only | Gateway GAP |
| §2.2 C3, §2.3/6.2 | §§2.2,4.3,5 | EV-011–015, runtime BA-01–03 | PARTIAL |
| §2.2 C4, §2.4 | §4.4 | marking tests do not prove projections | GAP |
| §2.2 C5, §3.8 | §§4.5,6 | emission tests only | GAP |
| §2.2 C6, §4.1 | §§2.4–2.6,4.6 | EV-020–031 | FSM conflict |
| §2.2 C7, §4.2 | §4.7 | none | GAP |
| §2.2 C8, §7 | §§4.8,6 | EV-032–035 | PARTIAL |
| §5.3 marking | §§2.3,4.4 | EV-016–019, BA-06 | permission/intersection GAP |
| `CC-EMISSION-FENCE` | §§2.6,4.6,5 | EV-029–031, BA-07 | freshness GAP |
| Candidate BA-01–08 | §§5–8 | runtime BA IDs not equivalent | NOT VERIFIED |

Executed during this pass: GitHub tree/path/blob validation and `python3 -m compileall` on imported source/tests. Runtime pytest is **NOT EXECUTED** because pytest is not installed and repository rules prohibit installing packages. The command failed once with `No module named pytest` and was not retried. The report’s “104 passed” remains historical self-report, not independently reproduced evidence.

Production is **NO-GO** while baseline blockers are open, container gaps remain, full fence predicates are absent, live PostgreSQL failure semantics are unproven, or contracts/FSM are not regenerated from the approved authority set.

## 10. Configuration baseline

| Key | Default | Range |
|---|---:|---:|
| dispatcher batch / idle poll | 100 / 100 ms | 1–1000 / 25–5000 |
| claim / maximum backoff | 30 s / 60 s | 5–300 / 1–600 |
| max in-flight | 200 | 1–2000 |
| reconciler / lease sweep | 5 s / 1 s | 1–300 / 1–10 |
| shutdown grace | 20 s | 1–120 |
| request / canonical value | 4 MiB / 8 MiB | 64 KiB–16 MiB / 64 KiB–32 MiB |
| sandbox source/nodes/operations/result | 4096/256/1024/65536 | increases require change control |

Unknown keys, invalid ranges or unsafe sandbox increases fail startup.

## 11. Completion statement

This LLD completely specifies the inspected runtime surface, target class allocation, deterministic protocols, PostgreSQL/embedded persistence, locks, async workers, memory bounds and BA/EV method matrix. Bidirectional traceability is preserved by representing non-conformance instead of equating filenames with ADD containers.

The engineering document is complete. Its authority status remains conditional until the approved ADD and ARA record are restored as non-empty verifiable artifacts and `LLD-BL-001`–`006` close.

## Appendix A — Exact existing Python API inventory

All dataclasses below are `frozen=True, slots=True` unless stated otherwise.

| Module | Type/function | Exact public signature or fields |
|---|---|---|
| `canonical` | `canonicalize_json` | `(value: Any) -> str` |
| `canonical` | `canonicalize` | `(value: Any) -> bytes` |
| `canonical` | `canonical_sha256` | `(value: Any) -> str` |
| `canonical` | `load_i_json` | `(document: str | bytes | bytearray) -> Any` |
| `c1_compiler` | `CompiledArtifact` | `artifact_id, semantic_digest, envelope_digest, canonical_payload, document, schema_id=None` |
| `c1_compiler` | `SemanticCompiler` | `__init__(schema=None, *, registry=None)`; `from_schema_file(path)`; `validate(document)`; `compile(document)` |
| `c2_identity` | `IdentityRecord` | `canonical_id, aliases=frozenset(), attributes={}` |
| `c2_identity` | `ResolutionOutcome` | `status, canonical_id, confidence, reason, candidates=()`; property `identified` |
| `c2_identity` | `IdentityRegistry` | `register(record)`; `get(canonical_id)`; `add_alias(canonical_id, alias)`; `candidates(identifier)`; `resolve(identifier, *, evidence=None, minimum_confidence=.80, minimum_margin=.10)`; `all_records()` |
| `c3_store` | `StoredDocument` | `aggregate_id, document, version, writer_id, transaction_id, semantic_digest, updated_at` |
| `c3_store` | `OutboxEvent` | `event_id, aggregate_id, aggregate_version, event_type, payload, payload_digest, request_digest, idempotency_key, transaction_id, occurred_at, committed=True, emitted_at=None`; `verify_integrity()` |
| `c3_store` | `WriteResult` | `document, event, replayed=False` |
| `c3_store` | `AtomicOutboxStore` | `__init__(*, authoritative_writer='ocor-core')`; `write(aggregate_id, document, *, expected_version, writer_id, event_type, event_payload=None, idempotency_key, occurred_at=None, crash_window=None)`; `get`; `get_event`; `outbox(*, include_emitted=False)`; `mark_emitted`; `snapshot_counts`; `verify_atomicity` |
| `c4_marking` | `MarkingSchemeDefinition` | `__init__(scheme_id, levels=None, *, labels=None, relations=None)`; `from_dict`; `leq`; `dominates`; `join`; `meet` |
| `c4_marking` | `MarkingSet` | `values`; `__getitem__(scheme_id)` |
| `c4_marking` | `DisclosureDecision` | `allowed, reason, payload=None` |
| `c4_marking` | `MarkingEngine` | `__init__(schemes)`; property `schemes`; `validate`; `join`; `is_authorized`; `require_authorized`; `disclose` |
| `c5_actions` | `TransitionSpec` | `transition_id, source, event, target, enforces_action_window=False` |
| `c5_actions` | `ActionAuditEntry` | `transition_id, source, event, target, occurred_at, actor, evidence, previous_hash, entry_hash` |
| `c5_actions` | `Action` | `action_id, state=DRAFT, version=0, not_before=None, expires_at=None, history=()` |
| `c5_actions` | `ActionFSM` | `allowed_events(state)`; `transition(action,event,*,occurred_at,actor,evidence=None,expected_version=None)`; `transition_by_id`; `verify_history` |
| `c6_capabilities` | `CapabilityLease` | `lease_id, subject, capabilities, resources, not_before, expires_at, issued_at, issuer, revoked_at=None, parent_lease_id=None, max_uses=None`; `is_active`; `allows` |
| `c6_capabilities` | `CapabilityAuthority` | `__init__(issuer='ocor-capability-authority')`; `issue`; `get`; `revoke`; `authorize`; `usage` |
| `c7_emission` | `EventSink` | `emit(event, *, idempotency_key)` |
| `c7_emission` | `EmissionReceipt` | `event_id, aggregate_id, aggregate_version, emitted_at, sink_result=None, deduplicated=False` |
| `c7_emission` | `EmissionFence` | `__init__(*,store=None,capability_authority=None,require_capability=False,marking_engine=None)`; `register`; `emit`; `drain`; `receipt` |
| `c8_agent` | `TokenCharge` | `category, tokens` |
| `c8_agent` | `BudgetReservation` | `reservation_id, category, tokens` |
| `c8_agent` | `TokenBudget` | `__init__(limit, *, tokenizer=deterministic_token_count)`; properties `used,reserved,remaining,charges`; `count`; `consume`; `consume_text`; `reserve`; `commit`; `cancel` |
| `c8_agent` | `StrictSandbox` | `__init__(tools=None, *, max_source_characters=4096, max_ast_nodes=256, max_operations=1024, max_result_characters=65536)`; `tool_names`; `register_tool`; `execute` |
| `c8_agent` | `AgentResponse` | `decision, identity_id, confidence, reason, content=None` |
| `c8_agent` | `ModelResult` | `response, output_tokens=None` |
| `c8_agent` | `AgentModel` | `__call__(prompt: str, *, max_output_tokens: int) -> ModelResult` |
| `c8_agent` | `AgentKernel` | `__init__(*,identity_registry=None,sandbox=None,capability_authority=None,subject='ocor-agent')`; `identify_or_abstain`; `execute_sandboxed`; `invoke` |
| `fallback.postgres_outbox` | `PostgreSQLWriteReceipt` | `transaction_id, event_id, aggregate_id, aggregate_version, replayed=False` |
| `fallback.postgres_outbox` | `PostgreSQLTransactionalOutbox` | `__init__(connection_factory)`; `initialize`; `write` |
| `fallback.postgres_outbox` | `OutboxReconciler` | `__init__(connection_factory)`; `reconcile_once(*, limit=100)` |
| `fallback.postgres_outbox` | `select_atomic_backend` | `(candidate, *, postgres_connection_factory=None) -> Any` |

Aliases retained by compatibility contract: `Compiler=SemanticCompiler`, `IdentityResolver=IdentityRegistry`, `DocumentStore=AtomicOutboxStore`, `LatticeSolver=MarkingSchemeDefinition`, `FSM=ActionFSM`, `LeaseRegistry=CapabilityAuthority`, `EMISSION_FENCE=EmissionFence`, and `Sandbox=StrictSandbox`.
