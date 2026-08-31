# OCOR Runtime — Low-Level Design v1.0

## 0. Document control

| Field | Value |
|---|---|
| Document | `docs/OCOR_LLD_v1.0.md` |
| Repository | `nepryoon/ocor-detailed-design` |
| Normative baseline | `ocor-runtime/docs/governance_dossier/OCOR_ADD_v1.2_APPROVED_BASELINE.md` |
| Governance authority | `ARA_DECISION_RECORD_v1.1.md`, DEC-197–DEC-206 |
| Validation closure | `ARA_VALIDATION_CLOSURE_RECORD_v1.0.md`, DEC-207 |
| LLD status | **ADD v1.2 ALIGNED — IMPLEMENTATION CONFORMANCE OPEN** |
| Effective date | 2026-08-31 |
| Runtime target | CPython ≥3.11; PostgreSQL 16 reference adapter; selected ADD CIs as specified below |

This LLD is normative for implementation detail below ADD v1.2. It neither changes the approved ADD nor asserts that unimplemented components have passed acceptance. “Required” means required by the approved baseline; “implemented” is established only by executable evidence.

## 1. Authority, scope and closure register

### 1.1 Precedence

Conflicts are resolved in this order:

1. approved ADD v1.2 and DEC-197–DEC-206;
2. DEC-207 validation closure and pinned contract artifacts;
3. OpenAPI 3.1, Proto3 and JSON Schemas under `ocor-runtime/schemas/`;
4. this LLD;
5. current source and tests.

Source code or tests that conflict with levels 1–4 are implementation gaps, not amendments.

### 1.2 Authoritative inputs

| Artifact | Purpose | LLD use |
|---|---|---|
| `OCOR_ADD_v1.2_APPROVED_BASELINE.md` | architecture, invariants, C1–C8 allocation, BA-01–BA-08 | primary requirements source |
| `ARA_DECISION_RECORD_v1.1.md` | approval authority and conditions | governance binding |
| `ARA_VALIDATION_CLOSURE_RECORD_v1.0.md` | validation closure | evidence scope |
| `schemas/openapi/ocor-named-query-gateway.openapi.yaml` | public query protocol | C2 wire contract |
| `schemas/proto/ocor_registry.proto` | function/model registry protocol | C1/C7/C8 wire contract |
| five ADD-embedded JSON contracts | canonical domain envelopes | C1/C5/C6/C8 validation |
| other runtime schemas | versioned verification surface | compatibility only |

### 1.3 Alignment closure register

| ID | Former divergence | Rectification in this revision | Status |
|---|---|---|---|
| LLD-BL-004 | legacy filenames were treated as C1–C8 allocation | §4 makes the ADD component names and packages canonical; legacy modules move behind compatibility façades | **CLOSED_IN_LLD** |
| LLD-BL-005 | 32-edge legacy action FSM conflicted with the ADD FSM | §3.4 defines the exact 44 approved transition tuples and guards | **CLOSED_IN_LLD** |
| LLD-BL-006 | runtime behavioural tests reused ADD BA identifiers | §9 reserves BA-01–BA-08 for ADD acceptance and renames legacy assertions RBA-01–RBA-08 | **CLOSED_IN_LLD** |

### 1.4 Implementation gap register

| ID | Concrete gap | Closure evidence |
|---|---|---|
| LLD-IG-001 | canonical package/container layout in §4 is not fully implemented | import/API tests for every required port and class |
| LLD-IG-002 | current runtime action code implements a legacy 32-transition FSM | exact-tuple test against all 44 rows in §3.4 |
| LLD-IG-003 | ADD backend acceptance BA-01–BA-08 is incomplete | governed adapter runs and immutable evidence bundle |
| LLD-IG-004 | current runtime verification OpenAPI/Proto differs from the approved public contracts | generated stubs plus bidirectional conformance tests for §8 |
| LLD-IG-005 | Governed Context Set and full emission fence are not enforced on every boundary | negative matrix covering every row of §2.3 and §3.5 |
| LLD-IG-006 | C4, C5 and C7 production components are absent or partial | component, integration and BA evidence |
| LLD-IG-007 | PostgreSQL proves atomic invariants but is not the selected C3 VersionedAssertedState CI | TerminusDB BA-01 or approved architectural change record |

The LLD is coherent with the ADD; the implementation remains **NO-GO for production conformance** until all `LLD-IG-*` items are closed.

## 2. Cross-cutting types and Governed Context Set

### 2.1 Canonical scalar types

```python
from typing import NewType
Digest = NewType("Digest", str)          # lowercase urn:sha256:<64 hex>
ObjectId = NewType("ObjectId", str)
CommitId = NewType("CommitId", str)
Revision = NewType("Revision", int)      # non-negative
EventId = NewType("EventId", str)
LeaseId = NewType("LeaseId", str)
Instant = NewType("Instant", str)        # RFC 3339 UTC, microsecond precision
```

Digests are semantic identities only when calculated from RFC 8785 canonical JSON bytes. Protobuf bytes, database bytes and transport compression never define semantic identity.

### 2.2 Governed Context Set

`GovernedContext` is immutable and contains:

```python
@dataclass(frozen=True, slots=True)
class GovernedContext:
    principal_id: str
    tenant_id: str
    purpose_ids: tuple[str, ...]
    authority_refs: tuple[str, ...]
    policy_snapshot_digest: Digest
    marking_ref: str
    capability_lease_ids: tuple[LeaseId, ...]
    correlation_id: str
    causation_id: str | None
    request_time: datetime
    deadline: datetime | None
    schema_pins: tuple[str, ...]
    ontology_release_digest: Digest
    trace_id: str
```

`governed_context_digest = sha256(jcs(to_semantic_dict(context)))`. The authenticated transport principal is authoritative. A principal or tenant supplied in a body is comparison-only; absence, mismatch, unverifiable authority, stale policy, invalid marking, expired lease, missing purpose or schema-pin mismatch fails closed before domain processing.

### 2.3 Enforcement matrix

| Boundary | Required propagation | Failure |
|---|---|---|
| ingestion / C3 claim | context digest in claim, commit and outbox entry | reject claim; no state/outbox mutation |
| C2 query | context digest in cache key, plan, response provenance | deny with typed reason; no payload |
| registry invocation | context digest in `InvocationContext` and result evidence | abstain/deny |
| MCP/tool call | context digest in signed tool request | deny before execution |
| C6 action | context digest in proposal, GatePackage, decision and command | transition to approved failure state |
| C5 event/replay | context digest in envelope and replay authorization | quarantine or deny |
| C7 scenario | context digest in scenario, job and sealed result | reject/cancel |
| C8 handoff | context digest before/after handoff | deny or escalate |
| audit/telemetry | digest and decision only; sensitive context fields redacted | fail closed if mandatory audit cannot commit |

No component may silently synthesize missing context. Derived context must carry signed derivation evidence and a new digest.

## 3. Non-negotiable formal invariants

### 3.1 RFC 8785 and SHA-256

`CanonicalJsonEngine.canonicalize(value) -> bytes` implements RFC 8785/JCS:

- input values are restricted to the I-JSON domain;
- object keys are ordered by UTF-16 code units;
- strings use JSON escaping with invalid Unicode rejected;
- finite IEEE-754 numbers use ECMAScript-compatible shortest round-trip formatting; `NaN`, infinities and negative zero ambiguity are rejected or normalized exactly as the pinned implementation profile specifies;
- UTF-8 output has no BOM or insignificant whitespace.

`semantic_digest(value) = "urn:sha256:" + sha256(canonicalize(value)).hexdigest()`. Verification recomputes and uses constant-time comparison. Signing signs domain-separated canonical bytes: `b"OCOR:<contract>:<version>\x00" + canonical_bytes`.

### 3.2 Atomic single-writer/outbox invariant

For one aggregate and one transaction:

\[
Commit = (aggregate\_delta, revision+1, canonical\_commit\_id, OutboxEntry[])
\]

Visibility is both-or-neither. Only C3 may mutate authoritative asserted state. Every command supplies `expected_revision` and `writer_epoch`; stale revisions or epochs fail without side effects. Broker publication is outside the state transaction. There is no distributed 2PC. An outbox entry becomes externally eligible only after its enclosing canonical commit is durable.

### 3.3 Marking algebra

The only canonical policy carrier is the `marking` object. Every `*_marking_ref` has form `urn:sha256:<marking_digest>` and must resolve through `GetProvenance`.

`SecurityContext` is an evaluation result over a marking, never an alternative marking model.

- Restriction families `classification`, `mandatory_markings`, `caveats`, `dissemination_controls`, and `handling_instructions` combine by union/least upper bound.
- `permitted_purposes` is a permission set and combines by intersection. Empty intersection means DENY.
- Unknown or incomparable values mean DENY unless an explicit governed top element exists.
- Release is allowed iff the evaluated principal clearance dominates every restriction and the requested purpose belongs to the effective permission set.
- Declassification is never a meet, subtraction or in-place edit. It is a separate signed transition containing authority, Human Gate decision, evidence, before digest and after digest.

Marking changes do not alter the semantic payload digest; they alter the governed envelope digest.

### 3.4 Approved C6 action FSM — exact 44 tuples

The tuple identity, source and destination are normative.

| ID | Source | Destination |
|---|---|---|
| ACT-T01 | `[*]` | `PROPOSAL_RECORDED` |
| ACT-T02 | `PROPOSAL_RECORDED` | `PROPOSAL_RECORDED` |
| ACT-T03 | `[*]` | `DENIED` |
| ACT-T04 | `PROPOSAL_RECORDED` | `CONTROL_CHECK` |
| ACT-T05 | `CONTROL_CHECK` | `DENIED` |
| ACT-T06 | `CONTROL_CHECK` | `APPROVAL_PENDING` |
| ACT-T07 | `CONTROL_CHECK` | `APPROVAL_RESOLVED` |
| ACT-T08 | `APPROVAL_PENDING` | `APPROVAL_RESOLVED` |
| ACT-T09a | `APPROVAL_PENDING` | `APPROVAL_REJECTED` |
| ACT-T09b | `APPROVAL_PENDING` | `APPROVAL_EXPIRED` |
| ACT-T10a | `DECISION_PENDING` | `DECISION_REJECTED` |
| ACT-T10b | `DECISION_PENDING` | `INTENT_RECORDED` |
| ACT-T11 | `INTENT_RECORDED` | `PRE_DISPATCH_CHECK` |
| ACT-T12 | `PRE_DISPATCH_CHECK` | `COMMAND_READY` |
| ACT-T13 | `PRE_DISPATCH_CHECK` | `INVALIDATED` |
| ACT-T14 | `COMMAND_READY` | `DISPATCHED` |
| ACT-T15 | `DISPATCHED` | `ACKNOWLEDGED` |
| ACT-T16 | `ACKNOWLEDGED` | `EXECUTION_CONFIRMED` |
| ACT-T17a | `DISPATCHED` | `EXECUTION_FAILED` |
| ACT-T17b | `ACKNOWLEDGED` | `EXECUTION_FAILED` |
| ACT-T18a | `DISPATCHED` | `EXECUTION_UNKNOWN` |
| ACT-T18b | `ACKNOWLEDGED` | `EXECUTION_UNKNOWN` |
| ACT-T19 | `COMMAND_READY` | `DISPATCHED` |
| ACT-T20a | `EXECUTION_UNKNOWN` | `EXECUTION_CONFIRMED` |
| ACT-T20b | `EXECUTION_UNKNOWN` | `EXECUTION_FAILED` |
| ACT-T20c | `EXECUTION_UNKNOWN` | `EXECUTION_UNKNOWN` |
| ACT-T21 | `EXECUTION_FAILED` | `COMPENSATING` |
| ACT-T21a | `COMPENSATING` | `COMPENSATED` |
| ACT-T21b | `COMPENSATING` | `COMPENSATION_FAILED` |
| ACT-T21c | `COMPENSATING` | `COMPENSATION_UNKNOWN` |
| ACT-T21d | `COMPENSATION_UNKNOWN` | `COMPENSATED` |
| ACT-T21e | `COMPENSATION_UNKNOWN` | `COMPENSATION_FAILED` |
| ACT-T22 | `OUTCOME_PENDING` | `OUTCOME_ASSESSED` |
| ACT-T23a | `PRE_DISPATCH_CHECK` | `CANCELLED` |
| ACT-T23b | `COMMAND_READY` | `CANCELLED` |
| ACT-T24 | `EXECUTION_UNKNOWN` | `EXECUTION_INDETERMINATE` |
| ACT-T25 | `COMPENSATION_UNKNOWN` | `COMPENSATION_INDETERMINATE` |
| ACT-T26 | `APPROVAL_RESOLVED` | `DECISION_PENDING` |
| ACT-T27 | `EXECUTION_CONFIRMED` | `OUTCOME_PENDING` |
| ACT-T28 | `OUTCOME_PENDING` | `OUTCOME_UNOBSERVED` |
| ACT-T29 | `COMMAND_READY` | `CANONICAL_COMMIT_PENDING` |
| ACT-T30 | `CANONICAL_COMMIT_PENDING` | `EXECUTION_CONFIRMED` |
| ACT-T31a | `CANONICAL_COMMIT_PENDING` | `EXECUTION_FAILED` |
| ACT-T31b | `CANONICAL_COMMIT_PENDING` | `INVALIDATED` |

The transition registry is an immutable map keyed by these IDs. Duplicate IDs, missing tuples, extra tuples or a source/destination mismatch fail process startup.

### 3.5 Guards, precedence and indeterminacy

Mandatory guards are `G-CONTRACT`, `G-AUTHORITY`, `G-APPROVAL`, `G-DECISION`, `G-FRESHNESS`, and `G-DISPATCH`.

\[
EMISSION\text{-}FENCE := G\text{-}FRESHNESS \land G\text{-}DISPATCH
\]

The fence is evaluated atomically immediately before every external or internal send, including first dispatch, retry and compensation. `ACT-T23a/b` cancellation wins over `ACT-T14`, `ACT-T19` and `ACT-T29`. `EXECUTION_UNKNOWN` and `COMPENSATION_UNKNOWN` never imply success or failure; they either reconcile from evidence or terminate in the corresponding `*_INDETERMINATE` state with a separate adjudication case. Canonical mutations traverse `ACT-T29`–`ACT-T31b`.

### 3.6 Capability lease temporal guards

A lease is valid only when:

```text
not_before <= trusted_now < expires_at
and not revoked
and subject == authenticated principal
and operation in allowed_operations
and resource matches governed scope
and usage_count < usage_limit
and parent chain is valid
and policy_snapshot_digest is current
```

The end boundary is exclusive. Validation and usage consumption are atomic. Wall-clock rollback cannot extend a lease; scheduling uses monotonic time anchored to a signed trusted-wall-clock sample. Revocation and expiry invalidate cached authorization within 10 seconds. Denial emits no sensitive payload.

## 4. Canonical C1–C8 package and class breakdown

Canonical Python root:

```text
src/ocor_runtime/
  compiler/       # C1 Ontology Compiler & IR Pipeline
  gateway/        # C2 Unified Semantic Gateway
  state/          # C3 Canonical State Service & Outbox Worker
  projection/     # C4 Projection Adapters
  eventing/       # C5 Event Backbone
  actions/        # C6 Action Engine & Saga Coordinator
  causal/         # C7 Causal Runtime & Scenario Orchestrator
  agents/         # C8 Governed Agent Kernel
  governance/ security/ wire/ persistence/ workers/
  compat/         # legacy c1_compiler.py ... c8_agent.py façades only
```

Dependencies flow through ports. No component imports a concrete adapter owned by another component.

### 4.1 C1 — Ontology Compiler & IR Pipeline

| Module / concrete type | Required methods | Contract |
|---|---|---|
| `compiler/ports.py::CompilerPort` | `validate_package`, `compile`, `semantic_diff`, `package_release`, `verify_release` | public C1 port |
| `compiler/meta_schema.py::MetaSchemaValidator` | `validate(package, governed_context)` | offline, all violations returned in deterministic order |
| `compiler/locks.py::DependencyLockResolver` | `resolve(manifest, lockfile)` | no floating dependency or network lookup |
| `compiler/compiler.py::DeterministicOntologyCompiler` | `compile(package, pins, context) -> CanonicalIR` | pure for identical bytes/pins/context |
| `compiler/ir.py::CanonicalIREmitter` | `emit(graph) -> SignedCanonicalIR` | schema-valid, JCS-addressed |
| `compiler/generators.py::{JsonSchemaGenerator, ProtoGenerator, ApiGenerator}` | `generate(ir)` | deterministic sorted outputs |
| `compiler/release.py::{ReleasePackager,SbomBuilder,ReleaseSigner}` | `package`, `build`, `sign`, `verify` | content addressed, immutable release |

Types: `OntologyPackage`, `DependencyPin`, `CanonicalIR`, `SemanticDiff`, `ReleaseBundle`, `SignatureEnvelope`. Exceptions: `MetaSchemaViolation`, `UnpinnedDependency`, `CompilationConflict`, `NonDeterministicOutput`, `SignatureVerificationError`.

### 4.2 C2 — Unified Semantic Gateway

| Module / concrete type | Required methods | Contract |
|---|---|---|
| `gateway/ports.py::SemanticGatewayPort` | `get_object`, `query_object_set`, `search`, `traverse`, `explain`, `get_provenance` | exactly the six OpenAPI operations |
| `gateway/auth.py::TransportAuthInterceptor` | `authenticate`, `bind_context` | transport principal authoritative |
| `gateway/router.py::NamedQueryRouter` | `route(query_name, version)` | allow-listed named queries only |
| `gateway/policy.py::AuthorityPolicyEvaluator` | `authorize(context, query)` | fail closed on timeout/unknown |
| `gateway/planner.py::ConsistencyPlanner` | `plan(commit_pin, projection_watermarks)` | exact/stale semantics explicit |
| `gateway/sanitize.py::ResponseSanitizer` | `sanitize(result, effective_marking)` | no partial unauthorized payload |
| `gateway/provenance.py::ProvenanceResolver` | `resolve(ref, context)` | resolves marking and evidence references |

Types: `NamedQuery`, `ConsistencyRequirement`, `QueryPlan`, `GatewayResult`, `ProvenanceBundle`, `Abstention`. Exceptions: `AuthenticationRequired`, `ContextMismatch`, `AuthorityDenied`, `QueryNotAllowlisted`, `ConsistencyUnavailable`, `ProvenanceUnresolvable`.

### 4.3 C3 — Canonical State Service & Outbox Worker

| Module / concrete type | Required methods | Contract |
|---|---|---|
| `state/ports.py::VersionedAssertedStatePort` | `admit_claim`, `commit_aggregate`, `get_commit`, `reconcile_outbox` | authoritative C3 port |
| `state/admission.py::ClaimAdmissionService` | `validate`, `adjudicate` | contract/context/authority before mutation |
| `state/aggregate.py::AggregateProcessor` | `apply(current, command)` | deterministic delta |
| `state/commit.py::AtomicCommitCoordinator` | `commit(delta, expected_revision, entries, context)` | state+revision+commit+outbox atomically |
| `state/fence.py::WriterFence` | `acquire`, `validate_epoch`, `release` | one active writer epoch |
| `state/outbox.py::{OutboxRepository,OutboxDispatcher}` | `claim_batch`, `mark_published`, `mark_retry`, `dispatch_once` | skip-locked, idempotent sink |
| `state/reconcile.py::OutboxReconciler` | `reconcile(commit_id)` | repairs metadata, never invents publication |

Types: `Claim`, `Adjudication`, `AggregateDelta`, `CanonicalCommit`, `OutboxEntry`, `WriterEpoch`. Exceptions: `StaleRevision`, `WriterFenced`, `AtomicCommitFailure`, `DuplicateIdempotencyKey`, `OutboxIntegrityError`.

### 4.4 C4 — Projection Adapters

| Module / concrete type | Required methods | Contract |
|---|---|---|
| `projection/ports.py::ProjectionPort` | `project`, `get_watermark`, `rebuild`, `run_adapter_conformance` | public C4 port |
| `projection/mapping.py::ProjectionMappingExecutor` | `map_commit(commit)` | pinned mapping release |
| `projection/typedb.py::TypeDBProjector` | `project_batch` | facts and watermark atomically |
| `projection/rdf.py::JenaBoundaryAdapter` | `export_jsonld`, `import_jsonld`, `validate_shacl` | canonical round trip |
| `projection/watermark.py::WatermarkStore` | `compare_and_advance`, `checksum` | monotonic per projection |
| `projection/drift.py::ProjectionDriftDetector` | `scan`, `quarantine` | no authoritative-state mutation |

Types: `ProjectionBatch`, `ProjectionWatermark`, `ProjectionChecksum`, `DriftReport`, `AdapterConformanceResult`. Exceptions: `ProjectionConflict`, `WatermarkRegression`, `MappingPinMismatch`, `ProjectionDrift`, `ShapeViolation`.

### 4.5 C5 — Event Backbone

| Module / concrete type | Required methods | Contract |
|---|---|---|
| `eventing/ports.py::EventBackbonePort` | `publish`, `subscribe`, `replay`, `quarantine`, `reprocess_authorized` | public C5 port |
| `eventing/envelope.py::EventEnvelopeValidator` | `validate`, `verify_digest` | JSON schema, context and marking required |
| `eventing/partition.py::AggregatePartitioner` | `partition_key(event)` | stable aggregate ordering |
| `eventing/journal.py::KafkaEventJournal` | `append`, `read_from` | idempotent producer, bounded consumer |
| `eventing/registry.py::SchemaRegistryClient` | `resolve`, `check_compatibility` | pinned schemas |
| `eventing/retry.py::{RetryScheduler,DlqManager}` | `schedule`, `quarantine`, `reprocess` | bounded attempts; governed reprocess |
| `eventing/replay.py::ReplayCoordinator` | `authorize`, `stream` | original semantics plus new replay context |

Types: `CanonicalEventEnvelope`, `Subscription`, `ReplayRequest`, `DlqRecord`, `DeliveryReceipt`. Exceptions: `EnvelopeInvalid`, `SchemaPinMismatch`, `OrderingViolation`, `ReplayDenied`, `QuarantinedEvent`.

### 4.6 C6 — Action Engine & Saga Coordinator

| Module / concrete type | Required methods | Contract |
|---|---|---|
| `actions/ports.py::ActionEnginePort` | `submit_proposal`, `record_approval`, `record_decision`, `dispatch`, `reconcile_execution` | public C6 port |
| `actions/ledger.py::{ProposalLedger,DecisionLedger}` | `append`, `get` | immutable hash-chained records |
| `actions/human_gate.py::HumanGateClient` | `request`, `verify_decision` | signed decision bound to context/digest |
| `actions/fsm.py::ApprovedActionStateMachine` | `transition(action_id, transition_id, evidence)` | exact §3.4 registry |
| `actions/saga.py::SagaCoordinator` | `advance`, `compensate` | state persisted before/after effects |
| `actions/dispatch.py::FencedDispatcher` | `dispatch`, `retry` | §3.5 fence at send instant |
| `actions/reconcile.py::ExecutionReconciler` | `poll_evidence`, `adjudicate_indeterminate` | never infer unknown outcomes |

Types: `ActionProposal`, `GatePackage`, `ApprovalRecord`, `DecisionRecord`, `ActionIntent`, `Command`, `ExecutionEvidence`, `CompensationPlan`. Exceptions: `InvalidTransition`, `GuardFailed`, `ApprovalExpired`, `DecisionRejected`, `EmissionFenceClosed`, `IndeterminateExecution`.

### 4.7 C7 — Causal Runtime & Scenario Orchestrator

| Module / concrete type | Required methods | Contract |
|---|---|---|
| `causal/ports.py::CausalRuntimePort` | `create_scenario`, `run_causal_query`, `simulate_intervention`, `get_job`, `cancel_job` | public C7 port |
| `causal/scenario.py::ScenarioValidator` | `validate`, `pin_inputs` | immutable commit/schema/model pins |
| `causal/overlay.py::ScenarioOverlayStore` | `create`, `read`, `seal` | never writes C3 main |
| `causal/scm.py::StructuralCausalModelWorker` | `query`, `intervene` | deterministic seed and resource budget |
| `causal/jobs.py::{JobLedger,JobScheduler}` | `submit`, `claim`, `heartbeat`, `cancel` | durable job state |
| `causal/seal.py::ResultSealer` | `seal`, `verify` | immutable S3 object plus ledger digest |

Types: `Scenario`, `Intervention`, `CausalQuery`, `CausalJob`, `ResourceBudget`, `SealedResult`. Exceptions: `ScenarioInvalid`, `ModelPinMismatch`, `BudgetExceeded`, `JobCancelled`, `ResultIntegrityError`.

### 4.8 C8 — Governed Agent Kernel

| Module / concrete type | Required methods | Contract |
|---|---|---|
| `agents/ports.py::AgentKernelPort` | `start_run`, `assign_task`, `call_tool`, `handoff`, `escalate`, `stop_run` | public C8 port |
| `agents/run.py::RunManager` | `start`, `checkpoint`, `stop` | durable run and context |
| `agents/capability.py::CapabilityBroker` | `issue`, `validate_and_consume`, `revoke` | §3.6 temporal and scope guards |
| `agents/taint.py::TaintFirewall` | `label`, `check_flow`, `sanitize` | marking monotonicity |
| `agents/budget.py::BudgetController` | `reserve`, `commit`, `release` | atomic token/time/tool budgets |
| `agents/handoff.py::HandoffCoordinator` | `prepare`, `accept`, `abort` | context, marking and lease rebound |
| `agents/monitor.py::{RunMonitor,KillSwitch}` | `observe`, `trip`, `terminate` | bounded cancellation and audit |

Types: `AgentRun`, `TaskAssignment`, `ToolCall`, `HandoffPackage`, `BudgetReservation`, `CapabilityLease`. Exceptions: `CapabilityDenied`, `LeaseExpired`, `TaintViolation`, `BudgetExhausted`, `HandoffRejected`, `RunTerminated`.

## 5. Storage engine and data-access layer

### 5.1 Logical roles and selected CIs

| Role | Selected CI | Writer | Required semantics |
|---|---|---|---|
| `VersionedAssertedState` | TerminusDB | C3 only | versioned commits, optimistic revision, atomic commit+outbox; BA-01 |
| `LogicProjection` | TypeDB | C4 only | facts+watermark atomicity; BA-02/03 |
| `W3CBoundary` | Jena/TDB2 | C4 boundary | RDF/JSON-LD/SHACL round trip; BA-04 |
| `ActionWorkflowLedger` | Temporal + PostgreSQL | C6 | durable FSM/saga; BA-05 |
| `ScenarioResultStore` | S3-compatible + PostgreSQL | C7 | immutable sealed result and job ledger; BA-06 |
| `EventJournal` | Kafka/Strimzi | C5 | order/replay/DLQ/schema registry; BA-07 |
| `SecurityState` | OPA/Keycloak/SPIFFE/OpenBao | governance | fail-closed policy and lease/revocation; BA-08 |

A non-TerminusDB authoritative C3 implementation is not a fallback. It requires an approved architecture change and new BA-01 evidence.

### 5.2 Reference PostgreSQL atomic adapter DDL

The following DDL is the executable verification adapter for the atomic C3 invariant and the C6 ledger. It does not supersede the selected CIs.

```sql
CREATE TABLE ocor_writer_epoch (
  scope text PRIMARY KEY,
  epoch bigint NOT NULL CHECK (epoch > 0),
  owner_id uuid NOT NULL,
  lease_until timestamptz NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE ocor_aggregate (
  tenant_id text NOT NULL,
  aggregate_id text NOT NULL,
  revision bigint NOT NULL CHECK (revision >= 0),
  writer_epoch bigint NOT NULL CHECK (writer_epoch > 0),
  state_json jsonb NOT NULL,
  state_digest text NOT NULL CHECK (state_digest ~ '^urn:sha256:[0-9a-f]{64}$'),
  governed_context_digest text NOT NULL CHECK (governed_context_digest ~ '^urn:sha256:[0-9a-f]{64}$'),
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (tenant_id, aggregate_id)
);

CREATE TABLE ocor_canonical_commit (
  commit_id text PRIMARY KEY CHECK (commit_id ~ '^urn:sha256:[0-9a-f]{64}$'),
  tenant_id text NOT NULL,
  aggregate_id text NOT NULL,
  prior_revision bigint NOT NULL,
  revision bigint NOT NULL CHECK (revision = prior_revision + 1),
  aggregate_delta jsonb NOT NULL,
  delta_digest text NOT NULL CHECK (delta_digest ~ '^urn:sha256:[0-9a-f]{64}$'),
  governed_context_digest text NOT NULL,
  writer_epoch bigint NOT NULL,
  committed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE (tenant_id, aggregate_id, revision),
  FOREIGN KEY (tenant_id, aggregate_id)
    REFERENCES ocor_aggregate(tenant_id, aggregate_id)
    DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE ocor_outbox (
  event_id text PRIMARY KEY,
  commit_id text NOT NULL REFERENCES ocor_canonical_commit(commit_id),
  tenant_id text NOT NULL,
  aggregate_id text NOT NULL,
  aggregate_revision bigint NOT NULL,
  partition_key text NOT NULL,
  schema_ref text NOT NULL,
  payload_json jsonb NOT NULL,
  payload_digest text NOT NULL,
  marking_ref text NOT NULL,
  governed_context_digest text NOT NULL,
  idempotency_key text NOT NULL UNIQUE,
  status text NOT NULL CHECK (status IN ('PENDING','CLAIMED','PUBLISHED','RETRY','QUARANTINED')),
  attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
  available_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  claimed_by uuid,
  claim_until timestamptz,
  published_at timestamptz,
  sink_receipt jsonb,
  last_error_code text,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE (tenant_id, aggregate_id, aggregate_revision, schema_ref)
);

CREATE INDEX ocor_outbox_dispatch_idx
  ON ocor_outbox (available_at, created_at)
  WHERE status IN ('PENDING','RETRY');
CREATE INDEX ocor_outbox_claim_recovery_idx
  ON ocor_outbox (claim_until)
  WHERE status = 'CLAIMED';
CREATE INDEX ocor_commit_aggregate_idx
  ON ocor_canonical_commit (tenant_id, aggregate_id, revision DESC);

CREATE TABLE ocor_action_transition (
  action_id uuid NOT NULL,
  sequence_no bigint NOT NULL,
  transition_id text NOT NULL,
  source_state text NOT NULL,
  destination_state text NOT NULL,
  evidence_json jsonb NOT NULL,
  governed_context_digest text NOT NULL,
  previous_hash text,
  record_hash text NOT NULL,
  recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (action_id, sequence_no),
  UNIQUE (action_id, transition_id, record_hash)
);
```

### 5.3 Transaction and locking algorithm

`commit_aggregate` runs at `SERIALIZABLE` or equivalent CI semantics:

1. authenticate and validate `GovernedContext`;
2. validate writer epoch;
3. lock aggregate row (`SELECT ... FOR UPDATE`);
4. compare `expected_revision`;
5. calculate delta, canonical commit ID and event digests in memory;
6. update aggregate, insert canonical commit and all outbox rows in one transaction;
7. commit; only then signal the dispatcher.

Serialization failure retries use bounded exponential backoff with jitter and recompute from a fresh snapshot. Business conflicts do not retry. Dispatcher claims use `FOR UPDATE SKIP LOCKED`, a bounded lease and stable `(available_at, created_at, event_id)` order. Sink calls use the event id as idempotency key. A lost acknowledgement leaves the row retryable; a verified sink receipt marks it published.

### 5.4 Embedded and in-memory adapters

`InMemoryVersionedStateAdapter` is deterministic, process-local, lock-protected and injectable only in unit/property tests. `SQLiteVerificationAdapter` is single-process integration-only with WAL and `BEGIN IMMEDIATE`. Neither may be selected in a production profile, used as automatic failover, or reported as BA-01 evidence.

## 6. Concurrency, execution and memory model

All network and storage ports are async. CPU-bound canonicalization, schema validation and causal work run in bounded executors or isolated workers.

| Loop | Ownership | Claim/batch | Cancellation and recovery |
|---|---|---|---|
| outbox dispatcher | one task per partition group | bounded batch, skip-locked lease | finish/abandon current receipt, release claims, recover expired claims |
| outbox reconciler | singleton per C3 shard | commit/event page | checkpoint after page; idempotent restart |
| lease expiry/revocation | singleton per security shard | indexed expiry page | invalidates cache ≤10s; persistent cursor |
| C6 execution reconciler | partitioned by action ID | bounded due-action batch | unknown remains unknown; no inferred result |
| C7 job scheduler | durable worker pool | one leased job per worker | heartbeat; cooperative cancel; lease recovery |

Rules:

- task groups provide structured concurrency; no fire-and-forget tasks;
- queues are bounded and apply backpressure to callers;
- per-tenant and global semaphores cap concurrent I/O and CPU jobs;
- cancellation is observed at each await and before every emission fence;
- critical commit/fence sections are shielded only for the minimum atomic duration;
- retries are capped, classified and persisted;
- blocking libraries execute outside the event-loop thread;
- every worker exposes queue depth, oldest age, attempts, lease age and memory gauges.

Memory bounds are configured as `max_batch_items`, `max_payload_bytes`, `max_queue_items`, `max_inflight_bytes`, and `max_result_bytes`. Payloads above threshold stream to content-addressed storage. Caches are weighted LRU/TTL and key on governed-context digest. Large references are released after each batch; cycles are not retained in registries. A sustained RSS breach stops admission, drains queues, requests GC once, and terminates the worker for supervised restart if the hard limit remains exceeded.

## 7. Deterministic cryptographic implementation

`wire/canonical_json.py::CanonicalJsonEngine` is the sole RFC 8785 implementation. Callers cannot inject pre-serialized JSON. `wire/digest.py::DigestService` exposes:

```python
canonicalize(value: JsonValue) -> bytes
semantic_digest(value: JsonValue) -> Digest
verify_digest(value: JsonValue, expected: Digest) -> None
domain_separated_bytes(contract: str, version: str, value: JsonValue) -> bytes
```

Known-answer vectors cover UTF-16 ordering, escapes, exponent thresholds, integer precision boundaries, negative zero and rejection of non-finite numbers/unpaired surrogates. Differential tests run at least 100,000 randomly generated finite floats against the pinned reference.

Signatures record algorithm, key ID, signed-at, contract/version, semantic digest and governed-context digest. Verification validates key status at signed-at, trust chain, domain separation and digest before schema use. SHA-256 input is always canonical semantic bytes; transport hashes are separate fields.

## 8. Wire protocols and schema authority

### 8.1 Public OpenAPI 3.1 surface

The normative C2 API is `OCOR Named Query Gateway`, API version 1.2.0, with exactly:

- `POST /v1/queries/get-object`
- `POST /v1/queries/query-object-set`
- `POST /v1/queries/search`
- `POST /v1/queries/traverse`
- `POST /v1/queries/explain`
- `POST /v1/queries/get-provenance`

Generated server/client stubs validate OpenAPI 3.1 request and response schemas. Authentication is transport-bound. Every request/response carries or resolves the governed-context digest, consistency requirement, schema pins, marking/provenance references and typed fail-closed result. Undocumented paths are not part of the ADD public interface.

### 8.2 Proto3 registry surface

The normative package is `ocor.registry.v1` with services `FunctionRegistry` and `ModelRegistry`. Implementations preserve `VersionPin`, `SchemaPin`, `TypedValue`, `InvocationContext`, `ResourceBudget`, descriptors, publish/resolve/invoke requests, result validity, uncertainty and abstention.

JSON↔Proto mapping is schema-defined. Unknown enum values and fields are preserved where Proto rules allow but rejected when semantic validation cannot establish meaning. Semantic digest is computed from the canonical logical JSON projection, never raw Protobuf serialization; equivalent JSON and Proto values must produce the same digest.

### 8.3 Authoritative domain schemas

| Contract | Canonical schema ID |
|---|---|
| Signed Canonical IR | `urn:ocor:schema:signed-canonical-ir:1.0` |
| Canonical Ingestion Envelope | `urn:ocor:schema:canonical-ingestion-envelope:1.2` |
| MCP Tool Contract | `urn:ocor:schema:mcp-tool-contract:1.2` |
| Action Type Contract | `urn:ocor:schema:action-type-contract:1.1` |
| Event Subscription Contract | `urn:ocor:schema:event-subscription-contract:1.1` |

Schemas are loaded offline by digest, with external references allow-listed and pinned. Compile-time and runtime validators use the same schema bundle. The existing `/compile`, `/identities:resolve`, `/actions/...`, `/outbox/...` OpenAPI paths and `ocor.runtime.v1` Proto services remain a compatibility/verification surface only and cannot be advertised as ADD v1.2 public contracts.

## 9. Test harness and verification matrix

### 9.1 Deterministic fixtures

| Fixture | Construction | Reset/oracle |
|---|---|---|
| `frozen_clock` / `monotonic_clock` | exact UTC and monotonic instants | no host clock access |
| `governed_context_factory` | signed transport principal, pins, marking and leases | digest recomputed |
| `canonical_vectors` | RFC 8785 known answers plus invalid I-JSON | exact bytes/digests |
| `writer_epoch` | unique owner/epoch per test | stale writer rejected |
| `aggregate_factory` | revision 0 with canonical state | state/outbox both-or-neither |
| `crash_injector` | five BA-01 crash windows | durable post-restart inspection |
| `sink_stub` | idempotency ledger and lost-ack mode | delivery count and receipt |
| `marking_factory` | total, partial, multi-scheme and unknown values | algebra/property oracle |
| `lease_factory` | start/end/revocation/delegation/use bounds | inclusive-start/exclusive-end |
| `action_factory` | each approved state and signed evidence | exact tuple/history hash |
| `projection_fixture` | disposable TypeDB/Jena instances | watermark/checksum/round trip |
| `kafka_fixture` | disposable Strimzi-compatible broker/registry | partition order/replay/DLQ |
| `scenario_fixture` | pinned SCM, seed, budget, object store | immutable sealed result |

### 9.2 ADD acceptance behaviours — reserved BA namespace

| ID | CI / method-level scenario | Required oracle |
|---|---|---|
| BA-01 | TerminusDB `commit_aggregate`; inject crash before transaction, after state staging, after outbox staging, after durable commit before response, after response loss | aggregate delta, revision, canonical commit and outbox are all visible or all absent; retry is idempotent; stale writer/revision rejected |
| BA-02 | TypeDB `project_batch` with failure between fact and watermark stages | facts and watermark advance atomically; replay produces identical checksum |
| BA-03 | TypeDB `query_exact_at_commit` in isolated sandbox | result uses exactly the pinned commit and cannot observe later facts |
| BA-04 | Jena `export_jsonld` → `import_jsonld` → `validate_shacl` | canonical RDF/JSON-LD round trip, SHACL validity and matching watermark |
| BA-05 | Temporal/PostgreSQL run of ACT-T14, T18a/b, T19 and T29–T31b with lost acknowledgements | durable workflow history matches §3.4; fence and indeterminate semantics hold |
| BA-06 | S3/PostgreSQL `submit/cancel/seal/verify` | job ledger is durable; cancellation bounded; sealed object immutable and digest-verifiable |
| BA-07 | Kafka/Strimzi `publish/replay/quarantine/reprocess_authorized` | per-aggregate order, deterministic replay, schema enforcement, DLQ and governed reprocess |
| BA-08 | OPA/Keycloak/SPIFFE/OpenBao policy timeout, revocation and lease expiration | timeout fails closed; principal binding holds; revocation/expiry enforcement latency ≤10s |

No test with a different meaning may use `BA-*`.

### 9.3 Runtime behavioural assertions — compatibility namespace

Existing filenames that formerly used BA identifiers are interpreted as:

| Compatibility ID | Behaviour |
|---|---|
| RBA-01 | PostgreSQL reference adapter atomic commit/outbox |
| RBA-02 | idempotent retry |
| RBA-03 | single-writer/optimistic conflict |
| RBA-04 | RFC 8785/SHA-256 determinism |
| RBA-05 | legacy FSM temporal behaviour |
| RBA-06 | marking lattice |
| RBA-07 | emission fence |
| RBA-08 | capability lease |

RBA evidence is useful implementation evidence but never substitutes for ADD BA evidence.

### 9.4 EV-001–EV-035 method-level matrix

| EV | Method / function under test | Oracle |
|---|---|---|
| EV-001 | `CanonicalJsonEngine.canonicalize` object ordering | exact UTF-16 key order and digest |
| EV-002 | number/string canonicalization | pinned ECMAScript thresholds and escaping |
| EV-003 | canonical input validator | non-I-JSON rejected |
| EV-004 | `DeterministicOntologyCompiler.compile` | identical content address; immutable output |
| EV-005 | `MetaSchemaValidator.validate` / lock resolver | offline schema; unpinned refs rejected |
| EV-006 | identity resolution named query | exact ID and evidence |
| EV-007 | normalized alias resolution | unique match only |
| EV-008 | unknown identity | explicit abstention |
| EV-009 | ambiguous identity | ordered candidates; no guess |
| EV-010 | evidence threshold/margin | boundary cases and immutable record |
| EV-011 | `WriterFence.validate_epoch` | replica/stale mutation produces no state/event |
| EV-012 | `commit_aggregate` optimistic precondition | lost update prevented |
| EV-013 | BA-01 crash injector | all five windows, both-or-neither |
| EV-014 | retry by idempotency key | one outbox event |
| EV-015 | commit/outbox integrity | version sequence and digest binding |
| EV-016 | marking total-order LUB | least upper bound |
| EV-017 | marking partial-order LUB | compartments union |
| EV-018 | multi-scheme marking + purposes | restrictions union, permissions intersection, unknown denies |
| EV-019 | marking non-interference | semantic digest stable; envelope digest changes |
| EV-020 | `ApprovedActionStateMachine.registry` | exact 44 IDs and exact source/destination tuples |
| EV-021 | approved happy path | transition history complete and hash-chain valid |
| EV-022 | undefined transition | typed rejection without mutation |
| EV-023 | temporal guards | inclusive start, exclusive end |
| EV-024 | decision/audit evidence | tampering detected before transition |
| EV-025 | compensation and unknown outcomes | explicit compensated/failed/unknown/indeterminate paths |
| EV-026 | lease exact expiry | expiry instant denied |
| EV-027 | subject/operation/resource checks | wrong scope denied without leakage |
| EV-028 | delegation/revocation/usage | atomic consume; no bypass |
| EV-029 | emission fence integrity | uncommitted or invalid digest blocked |
| EV-030 | ordering/idempotency | out-of-order blocked; retry deduplicated |
| EV-031 | capability + marking + purpose | all required; no payload on deny |
| EV-032 | sandbox/tool contract | pure allow-list works; escapes rejected |
| EV-033 | `BudgetController` | preflight and actual usage bounded; reservation released |
| EV-034 | C8 governed identity use | unique result or abstention |
| EV-035 | end-to-end C1→C8 | canonical contracts, GCS, exact FSM, commit/outbox, marked event and provenance |

EV-020 is not satisfied by the legacy 32-transition registry. EV-013 supports BA-01 only when executed against the selected TerminusDB CI.

## 10. Bidirectional traceability

| ADD v1.2 requirement | LLD realization | Verification | Implementation state |
|---|---|---|---|
| C1–C8 canonical allocation | §4.1–§4.8 | import/API/component tests | OPEN: LLD-IG-001/006 |
| Governed Context Set | §2.2–§2.3 | negative boundary matrix, EV-031/035 | OPEN: LLD-IG-005 |
| RFC 8785 / SHA-256 | §3.1, §7 | EV-001–005, differential float campaign | partial evidence |
| single writer / atomic outbox | §3.2, §5 | BA-01, EV-011–015 | reference adapter proven; LLD-IG-007 |
| marking algebra/declassification | §3.3 | EV-016–019 and signed declassification cases | partial evidence |
| ACT-T01–ACT-T31b | §3.4–§3.5 | EV-020–025, BA-05 | OPEN: LLD-IG-002/003 |
| capability lease | §3.6 | EV-026–028, BA-08 | partial; full CI open |
| EMISSION-FENCE | §3.5, C6 dispatcher | EV-029–031, BA-05/07 | OPEN: LLD-IG-005 |
| public OpenAPI/Proto/contracts | §8 | lint, generated-stub and cross-wire digest tests | OPEN: LLD-IG-004 |
| selected CIs | §5.1 | BA-01–BA-08 | OPEN: LLD-IG-003/007 |
| concurrency/memory | §6 | cancellation, saturation, soak and RSS gates | open release gate |

Reverse traceability is enforced by requiring every public port, state transition, database constraint, schema operation and EV/BA test to cite one row above in code metadata or test markers. Orphaned LLD elements and unimplemented ADD requirements fail the alignment checker.

## 11. Configuration baseline

| Key | Type / rule | Default |
|---|---|---|
| `OCOR_ENV` | `dev|test|staging|prod` | `dev` |
| `OCOR_STATE_CI` | production must be `terminusdb` until changed by decision | `inmemory` only for dev/test |
| `OCOR_DATABASE_DSN` | secret reference, never logged | unset |
| `OCOR_OUTBOX_BATCH` | 1–1000 | 100 |
| `OCOR_OUTBOX_CLAIM_SECONDS` | 1–300 | 30 |
| `OCOR_MAX_INFLIGHT_BYTES` | positive integer | 67,108,864 |
| `OCOR_POLICY_TIMEOUT_MS` | 1–5000; timeout denies | 500 |
| `OCOR_REVOCATION_MAX_STALENESS_SECONDS` | must be ≤10 | 10 |
| `OCOR_CLOCK_SKEW_SECONDS` | non-negative; evidence-bound | 2 |
| `OCOR_SCHEMA_BUNDLE_DIGEST` | required `urn:sha256:*` in staging/prod | unset |
| `OCOR_ONTOLOGY_RELEASE_DIGEST` | required `urn:sha256:*` in staging/prod | unset |
| `OCOR_LOG_LEVEL` | standard level | `INFO` |

Production startup validates all required pins, exact FSM registry, trusted clock, policy provider, durable stores, TLS identity, key resolver and telemetry sink. Any invalid or missing value terminates startup.

## 12. Release gates and completion statement

The document-level ADD alignment gate passes only if an automated checker confirms:

1. all eight canonical component names and packages;
2. exact equality of the 44 FSM tuples;
3. exclusive ADD use of BA-01–BA-08 and explicit RBA compatibility names;
4. exact six public OpenAPI paths, Proto package/services and five schema IDs;
5. GCS, marking, outbox, fence and lease invariants;
6. bidirectional traceability without an unclassified divergence.

Implementation release remains blocked until `LLD-IG-001`–`LLD-IG-007` are closed with immutable evidence and BA-01–BA-08 pass against the selected CIs. The 109-test runtime campaign, 35 EV results, 38 legacy BA/RBA results, live PostgreSQL tests, OpenAPI validation and coverage remain valid historical evidence for their tested surface; they do not prove the missing ADD components or selected-CI acceptance.

This revision closes the former LLD specification conflicts without altering the approved ADD, its decision records or immutable input artifacts.
