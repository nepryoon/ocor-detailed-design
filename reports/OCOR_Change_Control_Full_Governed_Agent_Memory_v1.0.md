# OCOR — Change-Control Package: Full Governed Agent Memory

## 1. Control

| Field | Value |
|---|---|
| Change set | `CC-FULL-GOVERNED-AGENT-MEMORY` |
| Status | `PROPOSED — USER-DIRECTED, AWAITING GOVERNED BASELINE PROMOTION` |
| Base IRB | Initial Requirements Baseline v1.0, frozen by `DEC-196` |
| Base ADD | `OCOR-ADD-1.2`, SHA-256 `c3f432ae0d172f2b4f70be8220d0ae4a134ec14716bccc6a12d75dfee438b84f` |
| Trigger | `IALLD-007` and explicit requester disposition to implement complete memory in the PoC |
| Requirements preserved | `FR-118`, `FR-119`, P0/PoC |
| Element affected | `ELM-084` — Agent Memory |
| Scope principle | complete PoC functionality; bounded PoC scale and resilience |
| Effective from | only after governed decision and versioned baseline promotion |

This package replaces `CC-BOUNDED-GOVERNED-MEMORY`. No existing `DEC-*` identifier is reused or invented. No runtime implementation, production readiness, HA, legal compliance or evidence promotion is asserted.

## 2. Decision and rationale

The PoC shall exercise the complete governed-memory architecture rather than a temporary run-only subset. Deferring persistent, vector or cross-run memory would validate a different architecture and create a likely redesign between PoC and MVP.

Completeness applies to semantics and governance. It does not require production volume, multi-region availability, production SLOs or E2 evidence. The PoC uses synthetic fixtures and constrained resource envelopes while preserving the final contracts, trust boundaries and failure semantics.

## 3. Normative capability disposition

`ELM-084` becomes `CORE / P0 / PoC` with the profile `FULL_GOVERNED_AGENT_MEMORY`. No memory capability is deferred merely because it is persistent, cross-run, vector-backed, consolidated or shared. Unsupported combinations fail explicitly and remain visible in the capability matrix.

The PoC includes:

- working memory for current context and plans;
- episodic memory for immutable run/task experiences;
- semantic memory for governed derived knowledge;
- procedural memory for versioned strategies and procedures;
- preference memory for explicit, revocable preferences without authority amplification;
- reflection memory for model-generated critiques, always tainted;
- dissent memory preserving unresolved competing positions;
- team-shared and project memory;
- cross-run persistence and policy-governed cross-project/federated retrieval;
- structured, full-text and vector/hybrid retrieval;
- consolidation, summarisation, correction, supersession, revocation, expiry, forgetting, legal hold and deletion;
- promotion proposals into the canonical path without direct promotion.

## 4. Non-negotiable invariants

1. Memory is non-authoritative. It cannot directly create Canonical Assertion, Authority, Delegation, Approval, Decision, CapabilityLease, ActionCommand or policy.
2. Claim, Observation, Hypothesis, Model Output, Decision, ExecutionResult and OutcomeAssessment remain distinct types. Memory never collapses their semantics.
3. Every item retains source, evidence, provenance, marking, policy, validity, uncertainty, lifecycle and content digests.
4. Content from humans, tools, models or external sources is data by default, not executable instruction.
5. Hidden chain-of-thought, model scratchpads, credentials, raw tokens and secret material are prohibited content classes.
6. Consolidation, summarisation, embedding and reflection produce new derived artifacts; they never overwrite source items.
7. Retrieval policy is evaluated before candidate lookup and again before materialisation.
8. Unauthorized items cannot influence existence, count, rank, score, pagination, explanation, cache hit, error shape or observable timing bucket.
9. Cross-project or federated retrieval requires explicit Authority, compatible purpose, conservative marking and auditable federation policy. Cross-tenant retrieval is deny-by-default.
10. Training or fine-tuning from memory is a separate governed workflow. Mere persistence never authorizes learning.
11. Deletion removes content, embeddings, cache/index entries and replicas; an opaque non-content audit tombstone is retained only when policy or legal hold requires it.
12. A memory-derived canonical change must enter C6 as a new proposal with evidence, Decision, Authority and C3 commit invariants.

## 5. Memory taxonomy

| Kind | Semantics | Minimum authority treatment |
|---|---|---|
| `WORKING` | mutable logical workspace represented by immutable versions | run/task scope; short default TTL |
| `EPISODIC` | event or experience tied to a run and time | immutable source episode; cross-run retrieval policy-controlled |
| `SEMANTIC` | derived statement or relationship | evidence and derivation mandatory; never canonical by itself |
| `PROCEDURAL` | versioned strategy, playbook or procedure | instruction eligibility requires separate approval and capability check |
| `PREFERENCE` | explicit user/team preference | revocable; cannot override policy or Authority |
| `REFLECTION` | model-generated critique or lesson | tainted; instruction-ineligible by default |
| `DISSENT` | unresolved alternative or objection | preserved until governed resolution; cannot be silently consolidated away |
| `TEAM_SHARED` | coordination knowledge visible to an authorized team | team membership, purpose and compartment checks |

Scope is independently declared as `RUN`, `TASK`, `AGENT`, `TEAM`, `PROJECT`, `DOMAIN` or `FEDERATED`. Kind and scope are not aliases.

## 6. Closed `GovernedMemoryItem` contract

```text
GovernedMemoryItem {
  memory_item_id, memory_version, memory_kind, memory_scope,
  owner_principal_id, agent_run_id?, team_run_id?, task_id?,
  agent_id?, team_id?, project_id?, tenant_id, organization_id, domain_id,
  compartments[], classification_marking_ref, purpose,
  content_schema_ref, content_ref, content_digest, language?,
  source_kind, source_ref, source_digest,
  evidence_refs[], provenance_refs[], derived_from_refs[], consolidates_refs[],
  supersedes_ref?, correction_of_ref?,
  created_at, valid_from, valid_until?, expires_at?,
  retention_policy_ref, legal_hold_ref?,
  confidence, uncertainty_ref?,
  policy_bundle_digest, ontology_release_digest, governed_context_digest,
  instruction_eligible, taint_labels[],
  representation_kinds[], embedding_model_ref?, embedding_model_digest?,
  embedding_ref?, embedding_digest?,
  lifecycle_status
}
```

The JSON Schema in `reports/contracts/governed-memory-item.schema.json` is normative for field names, cardinality and conditional requirements. Undeclared properties and aliases are rejected.

## 7. Storage architecture

The logical Memory Service is part of C8 and uses ports rather than backend-specific contracts:

| Store | Logical role | Authority |
|---|---|---|
| Metadata store | item versions, lifecycle, scope, digests, policies and links | authoritative for memory metadata only |
| Content-addressed object store | encrypted memory payloads and derived summaries | content store; never canonical state authority |
| Full-text index | policy-partitioned lexical retrieval | rebuildable projection |
| Vector index | policy-partitioned embeddings and ANN retrieval | rebuildable projection |
| Event journal | lifecycle, access, consolidation and deletion events | audit/replay evidence |
| Audit store | append-only access and influence records | audit authority |

Backend IDs never appear on public contracts. Indexes are derived projections and must be rebuildable from metadata/content plus event journal. Every index entry carries item/version, content digest, representation digest, marking, policy, scope and deletion epoch.

## 8. Admission and versioning

`admitMemory(candidate, authenticated_binding, governed_context)`:

1. constructs and validates the exact eleven-field canonical GCS;
2. validates closed schema, content class and all digests;
3. rejects hidden reasoning, secrets, credentials and unbounded raw conversation capture;
4. resolves source, evidence and provenance under the same GCS;
5. calculates conservative marking and taint;
6. verifies scope, retention, quota and storage class;
7. evaluates policy and Authority without treating content as instruction;
8. writes item metadata, content reference, lifecycle event and audit atomically;
9. schedules full-text/vector projections using the same item/version digest;
10. returns an opaque receipt.

Idempotency is keyed by `(tenant_id, memory_scope, source_digest, content_digest, operation_id)`. Same key/digest returns the original receipt; different digest returns `MEMORY_IDEMPOTENCY_CONFLICT`.

Every correction, reclassification, change of instruction eligibility or consolidation creates a new immutable version. `supersedes_ref` and `correction_of_ref` preserve history; consumers use the latest authorized non-terminal version unless an exact version is requested.

## 9. Retrieval and ranking

The contract supports `STRUCTURED`, `FULL_TEXT`, `VECTOR` and `HYBRID` modes. A request declares query contract/version, memory kinds/scopes, consistency, top-k, time window and explanation requirement.

Execution order is mandatory:

1. authenticate and validate GCS/digest;
2. evaluate pre-query policy and derive an authorized search partition;
3. reject unavailable or unapproved representation capability;
4. execute search only in that partition;
5. post-filter every candidate using current identity, Authority, marking, purpose, lifecycle and policy;
6. apply deterministic ranking profile/version;
7. materialize content, evidence and policy-safe explanation;
8. audit candidate influence, returned items and denied count only in the protected audit channel.

Hybrid ranking records lexical score, vector score, recency, confidence, source quality, diversity and policy penalties separately. Scores are never interpreted as truth or Authority. Unauthorized candidates cannot affect normalization or ranking.

## 10. Embeddings and vector governance

- Embeddings are derived artifacts bound to content digest, model ID/version/digest, tokenizer, dimensions and normalization profile.
- Embedding generation uses only content authorized for the worker's GCS and writes to a partition with equal or stricter marking.
- Model changes create a new representation version; reindex never mutates source memory.
- Raw vectors are not returned by default and cannot be used to infer inaccessible items.
- Cross-compartment shared centroids, global ANN graphs and shared caches are prohibited unless non-interference is proven for that profile.
- Deleted, revoked, expired or reclassified items are removed from active indexes before subsequent retrieval; stale index evidence blocks materialisation.

## 11. Consolidation, reflection and forgetting

`MemoryConsolidationJob` declares input query/digest, algorithm/model pins, purpose, budget, target kind/scope and reviewer policy. It produces a new item with all input refs and an uncertainty descriptor. Contradictions generate separate conflict/dissent records; majority frequency does not erase minority evidence.

Automatic consolidation is allowed only inside pre-approved profiles and cannot make content instruction-eligible. Procedural memory activation requires a governed approval record and remains subordinate to live policy, capability, delegation and kill switch.

Forgetting policies may use expiry, age, purpose completion, revocation, supersession, confidence decay, quota pressure or user request. They select candidates but do not delete under legal hold. Deletion is a durable saga covering content, embeddings, full-text/vector indexes, caches, replicas and exports. Partial deletion is `DELETION_INCOMPLETE`, blocks retrieval and remains operationally visible.

## 12. Lifecycle

```text
PROPOSED → ACTIVE | QUARANTINED
ACTIVE → SUPERSEDED | REVOKED | EXPIRED | LEGAL_HOLD | DELETION_PENDING
QUARANTINED → ACTIVE | REVOKED | DELETION_PENDING
SUPERSEDED | REVOKED | EXPIRED → LEGAL_HOLD | DELETION_PENDING
LEGAL_HOLD → ACTIVE | SUPERSEDED | REVOKED | EXPIRED | DELETION_PENDING
DELETION_PENDING → DELETED | DELETION_INCOMPLETE
DELETION_INCOMPLETE → DELETION_PENDING
```

Returning from legal hold restores the prior logical disposition, never blindly `ACTIVE`. `DELETED` is terminal. Lifecycle transition, audit and projection invalidation are committed atomically or reconciled fail-closed.

## 13. Promotion and influence control

Memory may influence model context only through a `MemoryContextAssembly` record containing query digest, returned item/version refs, policy decisions, ordering, truncation, redactions and final context digest. This makes downstream influence replayable without storing hidden reasoning.

Promotion to canonical state follows:

```text
MemoryItem → MemoryPromotionProposal → C6 control/approval/decision
           → GovernedCanonicalCommitCommand → C3 canonical commit
```

No shortcut is permitted. A rejected proposal does not invalidate the memory item; it records the decision separately.

## 14. Security and adversarial model

The acceptance campaign covers:

- direct and indirect prompt injection;
- memory poisoning and provenance laundering;
- embedding inversion and membership inference;
- cross-tenant, cross-domain and cross-compartment leakage;
- ranking/count/cache/timing side channels;
- confused deputy, capability escalation and delegation replay;
- agent collusion, conformity pressure and dissent suppression;
- malicious consolidation and procedural-memory activation;
- stale policy, marking downgrade and declassification race;
- incomplete deletion, replica resurrection and backup restore of deleted content;
- kill-switch race and use after revocation.

## 15. Acceptance obligations

| ID | Scenario | Oracle |
|---|---|---|
| `FGM-01` | every kind/scope valid fixture | closed schema, immutable version, provenance and audit |
| `FGM-02` | malformed/missing field or forbidden content class | rejected before persistence |
| `FGM-03` | working→episodic/semantic consolidation | new derived item; sources unchanged and linked |
| `FGM-04` | cross-run retrieval | authorized result with exact version and influence trace |
| `FGM-05` | cross-project/federated retrieval | explicit Authority and zero unauthorized leakage |
| `FGM-06` | structured/full-text/vector/hybrid equivalence | policy-filtered result; pinned ranking/representation |
| `FGM-07` | embedding model upgrade | parallel representation version; deterministic rebuild |
| `FGM-08` | prompt injection/poisoning | tainted, non-executable, quarantined or safely rendered |
| `FGM-09` | correction/supersession | new immutable version; exact-version replay preserved |
| `FGM-10` | revocation/expiry/reclassification | absent from result, rank, count, cache and explanation |
| `FGM-11` | legal hold then release | deletion blocked; prior disposition restored correctly |
| `FGM-12` | deletion saga with injected partial failure | fail-closed `DELETION_INCOMPLETE`, eventually complete |
| `FGM-13` | consolidation conflict/dissent | conflicting sources preserved; no silent majority merge |
| `FGM-14` | procedural activation | separate approval; live policy/capability still enforced |
| `FGM-15` | memory→canonical promotion | complete C6/C3 path; no direct write |
| `FGM-16` | cross-compartment non-interference | zero content/existence/rank/count/cache/timing leakage |
| `FGM-17` | kill switch and delegation revocation race | no later retrieval/tool influence |
| `FGM-18` | backup/restore after deletion | deleted content does not resurrect; tombstone reconciled |
| `FGM-19` | quota and retention pressure | deterministic policy selection; legal hold protected |
| `FGM-20` | context assembly | exact item/version/redaction/order/truncation digest replay |

`FR-118` requires FGM-01–04, 06–15 and 18–20. `FR-119` requires FGM-05, 08, 10, 16 and 17 with zero leakage.

## 16. Atomic update set on promotion

Promotion requires one governed change set updating:

1. Requirement Register annotations while preserving `FR-118/119` P0/PoC;
2. Requirement Traceability Index;
3. Decision Register and Decision Traceability Index;
4. CAP/ELM Requirement Crosswalk with `ELM-084 = CORE/P0/PoC`;
5. ADD scope fence, C8 design, security, operations and acceptance allocation;
6. LLD contracts, storage, algorithms, lifecycle, threat model and tests;
7. memory OpenAPI/JSON Schemas, manifests and digests.

Partial promotion or retaining the bounded profile beside this change set is invalid.
