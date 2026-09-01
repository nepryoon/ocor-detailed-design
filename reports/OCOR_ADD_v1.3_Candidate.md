# OCOR Architectural Design Document v1.3 — Candidate Amendment

## 1. Document control

| Field | Value |
|---|---|
| Identifier | `OCOR-ADD-1.3-CANDIDATE` |
| Status | `PROPOSED — USER-DIRECTED, AWAITING GOVERNED BASELINE PROMOTION` |
| Base | `OCOR-ADD-1.2` approved baseline |
| Base SHA-256 | `c3f432ae0d172f2b4f70be8220d0ae4a134ec14716bccc6a12d75dfee438b84f` |
| Change set | `CC-FULL-GOVERNED-AGENT-MEMORY` |
| Trigger | `IALLD-007` plus explicit requester disposition |
| Requirements | `FR-118`, `FR-119` remain Confirmed P0/PoC |
| Element | `ELM-084 = CORE / P0 / PoC` in this candidate |
| Evidence state | unchanged; no implementation or production claim |
| Effective from | only after governed approval and consolidated baseline publication |

This candidate amends ADD v1.2. Every ADD v1.2 clause remains unchanged except the replacements and additions below. It does not supersede the approved baseline until the competent authority promotes it. The previous bounded-memory proposal is withdrawn.

## 2. Normative replacements

### 2.1 Scope fence

Replace the `ELM-084` disposition in ADD v1.2 §§1.5 and 7.1 with:

| Element | Capability | PoC disposition | Later-release distinction |
|---|---|---|---|
| `ELM-084` — Agent Memory | full governed working, episodic, semantic, procedural, preference, reflection, dissent and team-shared memory | `CORE / P0 / PoC`; persistent cross-run, structured/full-text/vector/hybrid, consolidation and lifecycle included | MVP/Production increase scale, HA, SLO and E2 evidence; they do not introduce different memory semantics |

The PoC is functionally complete but resource-bounded. Production volume, multi-region continuity and production SLOs are not implied.

### 2.2 C8 subsystem replacement

C8 includes a logical `GovernedMemoryService` with `MemoryAdmissionPort`, `MemoryReadPort`, `MemorySearchPort`, `MemoryLifecyclePort`, `MemoryConsolidationPort`, `MemoryRepresentationPort`, `MemoryPromotionPort`, `MemoryDeletionPort` and `MemoryAuditPort`.

The subsystem persists item/version metadata, content-addressed payloads and lifecycle events. Full-text and vector stores are rebuildable projections. Audit is append-only. Backend identifiers do not cross the port boundary.

### 2.3 Memory taxonomy and scope

`memory_kind ∈ {WORKING, EPISODIC, SEMANTIC, PROCEDURAL, PREFERENCE, REFLECTION, DISSENT, TEAM_SHARED}`.

`memory_scope ∈ {RUN, TASK, AGENT, TEAM, PROJECT, DOMAIN, FEDERATED}`.

Kind defines semantics; scope defines visibility/lifetime ownership. They are independent. Each combination must be explicitly present in the capability matrix or fail with `UNSUPPORTED_CAPABILITY`.

Cross-run persistence is included. Cross-project or federated retrieval requires explicit Authority, compatible purpose, conservative marking and audit. Cross-tenant access remains deny-by-default and requires a separately approved federation policy.

### 2.4 Authority and epistemic separation

Memory is non-authoritative and never directly produces Canonical Assertion, Authority, Delegation, Approval, Decision, CapabilityLease, ActionCommand or policy change.

Claim, Observation, Hypothesis, Model Output, Decision, ExecutionResult and OutcomeAssessment remain distinct source types. A `SEMANTIC` memory item is derived knowledge, not accepted truth. `PROCEDURAL` memory is data until a separate approval authorizes instruction eligibility; live policy, capability, delegation and kill switch still apply at every use.

Hidden chain-of-thought, model scratchpads, credentials, tokens, secrets and unrestricted raw conversational history are prohibited memory payloads. `MemoryContextAssembly` records only selected item/version refs, policy decisions, ordering, redaction, truncation and final context digest.

### 2.5 GovernedMemoryItem contract

The closed contract in `reports/contracts/governed-memory-item.schema.json` and the rules of `OCOR_Change_Control_Full_Governed_Agent_Memory_v1.0.md` are incorporated by value. Undeclared fields and aliases are prohibited.

Every item is immutable and versioned. Correction, reclassification, consolidation, reflection, instruction-eligibility change or semantic update creates a new item version linked through `supersedes_ref`, `correction_of_ref`, `derived_from_refs` or `consolidates_refs`.

The item binds to exactly one canonical eleven-field ADD `GovernedContext`. The GCS digest is recalculated at admission, retrieval, context assembly, consolidation, promotion and deletion.

### 2.6 Storage and projection roles

| Logical store | Role | Constraint |
|---|---|---|
| Memory metadata | item/version/lifecycle/scope/digests | authority only for memory metadata |
| Object store | encrypted payloads and derived artifacts | content-addressed; no canonical-state authority |
| Full-text index | lexical retrieval | rebuildable, policy-partitioned projection |
| Vector index | embedding/ANN retrieval | rebuildable, representation-versioned projection |
| Event journal | lifecycle/access/consolidation/deletion events | replay source for memory projections |
| Audit store | access, denial and influence evidence | protected audit authority |

State, content, indexes, caches, queues, logs and backups use the full isolation tuple: tenant, organization, domain, compartments, marking, purpose, policy bundle, ontology release, memory scope and owner/project/team bindings.

### 2.7 Retrieval and non-interference

Supported modes are `STRUCTURED`, `FULL_TEXT`, `VECTOR` and `HYBRID`. Requests use a named, versioned query contract and declare kinds, scopes, consistency, time window, top-k and explanation profile.

Policy is evaluated before candidate lookup and again before materialisation. Unauthorized items do not enter ANN graphs, score normalization, ranking, diversity, counts, pagination, explanations or shared caches visible to the requester. Result marking is the conservative join of returned content and derivations.

Hybrid ranking records lexical, vector, recency, confidence, source-quality, diversity and policy factors independently. Scores are retrieval evidence, not confidence in truth or Authority.

### 2.8 Embedding and representation governance

Each embedding binds to item/version, content digest, model/version/digest, tokenizer, dimensions, normalization profile, purpose and marking. Model upgrade creates a parallel representation version and deterministic rebuild; it does not mutate source memory.

Representation generation executes under an authorized GCS. Cross-compartment centroids, global ANN graphs and shared vector caches are prohibited unless that exact profile passes non-interference tests. Raw vectors are not part of the default response contract.

### 2.9 Consolidation, reflection and dissent

Consolidation is an explicit job with input query/digest, algorithm/model pins, purpose, budget, target kind/scope and reviewer policy. It creates a new derived item with complete lineage and uncertainty. Source items remain immutable.

Contradictions produce conflict/dissent artifacts. Frequency or majority does not erase dissent. Reflection output is always tainted and instruction-ineligible by default. Automatic consolidation is limited to approved profiles and cannot promote memory to canonical state or activate procedures.

### 2.10 Lifecycle, forgetting and deletion

```text
PROPOSED → ACTIVE | QUARANTINED
ACTIVE → SUPERSEDED | REVOKED | EXPIRED | LEGAL_HOLD | DELETION_PENDING
QUARANTINED → ACTIVE | REVOKED | DELETION_PENDING
SUPERSEDED | REVOKED | EXPIRED → LEGAL_HOLD | DELETION_PENDING
LEGAL_HOLD → prior logical disposition | DELETION_PENDING
DELETION_PENDING → DELETED | DELETION_INCOMPLETE
DELETION_INCOMPLETE → DELETION_PENDING
```

`DELETED` is terminal. Forgetting may be triggered by expiry, purpose completion, revocation, supersession, confidence decay, quota pressure or authorized request. Legal hold blocks deletion. Deletion is a saga covering content, embeddings, indexes, caches, replicas, exports and restored backups. Partial completion blocks retrieval and remains visible as `DELETION_INCOMPLETE`.

### 2.11 Memory influence and canonical promotion

Every use in an agent/model context creates a `MemoryContextAssembly` receipt. Promotion follows only:

```text
GovernedMemoryItem
  → MemoryPromotionProposal
  → C6 Policy/Authority/Approval/Decision
  → GovernedCanonicalCommitCommand
  → C3 canonical commit
```

Rejected promotion is recorded separately and does not rewrite the memory item. Training or fine-tuning from memory is a distinct governed workflow and is not authorized by this amendment.

### 2.12 Security additions

Threat modelling and acceptance include prompt injection, memory poisoning, provenance laundering, confused deputy, delegation replay, capability escalation, agent collusion/conformity, dissent suppression, embedding inversion, membership inference, marking downgrade, stale policy, deletion resurrection and kill-switch races.

All untrusted/model-generated content is tainted. Rendering separates data from instructions. Tool invocation always re-evaluates live capability, delegation, policy, memory instruction eligibility and stop epoch.

### 2.13 Operations additions

Backup manifests include memory metadata, content refs, representation versions, lifecycle/deletion epochs, journal checkpoints and audit refs. Restore replays deletion tombstones before reopening retrieval, preventing resurrection of deleted content. Projection drift or stale deletion epoch blocks materialisation.

PoC resource limits are configuration values: item count, payload size, embedding dimensions, top-k, consolidation concurrency, index size and retention horizon. Exceeding them produces quota/backpressure behavior, never semantic downgrade.

## 3. Acceptance allocation

The `FGM-01`–`FGM-20` campaign in the change-control package is incorporated.

| Requirement | Required evidence |
|---|---|
| `FR-118` | all kinds/scopes, schema, persistence, cross-run retrieval, consolidation, vector/hybrid retrieval, versioning, lifecycle, legal hold, deletion, promotion and context-assembly tests |
| `FR-119` | cross-project/federated policy, poisoning, revocation/reclassification, cross-compartment non-interference and kill-switch/delegation race tests with zero leakage |

Passing schema tests alone is insufficient. `FR-118/119` remain `specified/planned` until the full campaign produces governed evidence.

## 4. Traceability

| Source | ADD realization | LLD obligation |
|---|---|---|
| `FR-118` | §§2.2–2.11, §3 | full record, store/index ports, algorithms, lifecycle and FGM suite |
| `FR-119` | §§2.6–2.8, 2.12 | pre/post policy, partitioned ranking/cache/index and non-interference |
| `ELM-084` | §2.1 | full PoC capability; scale/resilience only deferred |
| `FR-038` | §§2.3–2.4, 2.11 | memory never grants Authority or bypasses C6/C3 |
| `ARC-015`, `ARC-016` | §§2.4, 2.7, 2.12 | least privilege, taint, isolation, live enforcement and kill switch |

## 5. Compatibility

ADD v1.2 exposes no approved public memory API and has no production consumer. This change introduces a new versioned contract rather than silently changing an external interface. Existing OpenAPI, Registry Proto, Action, Event and MCP identifiers remain unchanged. The memory API is separately versioned as `1.0.0`.

## 6. Promotion conditions

This candidate may be consolidated only when:

1. `CC-FULL-GOVERNED-AGENT-MEMORY` is ratified through governed change control;
2. all five approved register snapshots are updated atomically;
3. `ELM-084` is recorded `CORE/P0/PoC` without retaining the bounded/deferred split;
4. memory JSON Schema and OpenAPI are validated and manifest-pinned;
5. LLD v1.1 implements every architectural rule above at design level;
6. the 285/285 alignment gate has zero gap and no stale bounded-profile reference;
7. a new manifest pins the consolidated baseline and dependencies.

Until then ADD v1.2 remains the only approved ADD baseline.
