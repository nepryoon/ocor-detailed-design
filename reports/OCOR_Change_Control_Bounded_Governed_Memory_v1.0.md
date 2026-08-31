# OCOR — Change-Control Package: Bounded Governed Memory

## 1. Control

| Field | Value |
|---|---|
| Change set | `CC-BOUNDED-GOVERNED-MEMORY` |
| Status | `PROPOSED — AWAITING GOVERNED DECISION` |
| Base IRB | Initial Requirements Baseline v1.0, frozen by `DEC-196` |
| Base ADD | `OCOR-ADD-1.2`, SHA-256 `c3f432ae0d172f2b4f70be8220d0ae4a134ec14716bccc6a12d75dfee438b84f` |
| Trigger | `IALLD-007` in the exhaustive IRB→ADD→LLD audit |
| Requirements preserved | `FR-118`, `FR-119`, P0/PoC |
| Element affected | `ELM-084` — Agent Memory |
| Approval order | IRB disposition → ADD v1.3 candidate → contract baseline → LLD v1.1 candidate |
| Effective from | Only after a governed decision and versioned baseline promotion |
| Superseded by | Future approved decision record; unset while proposed |

No existing requirement identifier, priority or release is changed. No evidence state is promoted and no runtime implementation is asserted.

## 2. Problem

`FR-118` and `FR-119` are Confirmed P0/PoC requirements mapped to `ELM-084`. ADD v1.2 simultaneously defers `ELM-084` and states that the PoC has no persistent general memory. The two statements are incompatible unless the PoC memory profile is bounded explicitly.

## 3. Proposed disposition

Split the capability disposition without changing the element identity:

- `ELM-084/POC_BOUNDED_PROFILE`: active in the PoC;
- `ELM-084/GENERAL_PERSISTENT_PROFILE`: deferred to MVP.

The PoC profile is not a global agent memory, learning store, semantic vector memory or cross-project knowledge base. It is a governed run-scoped evidence index with bounded persistence.

## 4. Closed contract

```text
GovernedMemoryItem {
  memory_item_id
  owner_principal_id
  agent_run_id
  team_run_id
  task_id
  tenant_id
  organization_id
  domain_id
  compartments[]
  classification_marking_ref
  purpose
  source_kind
  source_ref
  source_digest
  evidence_refs[]
  provenance_refs[]
  created_at
  valid_from
  valid_until
  expires_at
  confidence
  retention_policy_ref
  policy_bundle_digest
  ontology_release_digest
  governed_context_digest
  instruction_eligible
  taint_labels[]
  content_ref
  content_digest
  status
}
```

Cardinality and constraints:

1. The record is closed; undeclared fields are rejected.
2. All scalar fields are exactly one except `valid_until`, which may be absent for an open observation interval bounded by `expires_at`.
3. `compartments`, `evidence_refs`, `provenance_refs` and `taint_labels` are non-empty, duplicate-free arrays.
4. `classification_marking_ref`, `source_digest`, `policy_bundle_digest`, `ontology_release_digest`, `governed_context_digest` and `content_digest` use canonical `urn:sha256:<64 lowercase hex>` form.
5. `created_at ≤ valid_from < expires_at`; when present, `valid_from < valid_until ≤ expires_at`.
6. `confidence` is finite and within `[0,1]`; it does not grant Authority.
7. `status ∈ {ACTIVE, EXPIRED, REVOKED, QUARANTINED, DELETED}`.
8. `instruction_eligible=false` by default. `true` requires an allow-listed source kind, policy decision, provenance and explicit taint validation; it still does not grant Authority.
9. Content is immutable. Correction or reclassification creates a new item linked through provenance.
10. Expiry and revocation make the item non-retrievable before result materialisation.

## 5. Admission algorithm

`admitMemory(candidate, transport_binding, governed_context)` executes:

1. authenticate the workload and bind the canonical ADD `GovernedContext`;
2. validate the closed schema and all digests;
3. prove source/evidence/provenance resolution under the same governed context;
4. calculate the conservative marking join;
5. reject any requested scope broader than the current run/task or authorized compartments;
6. enforce the configured maximum TTL and retention policy;
7. evaluate policy, purpose, storage class and quota;
8. persist the immutable item and append the audit record atomically;
9. return an opaque `memory_item_id`, never backend coordinates.

Any missing, ambiguous, expired, incomparable or policy-unknown value fails closed. External or untrusted content is admitted only as tainted and `instruction_eligible=false`.

## 6. Retrieval algorithm

`retrieveMemory(query, transport_binding, governed_context)` executes policy before index/cache lookup and again before materialisation:

```text
eligible =
  status == ACTIVE
  ∧ trusted_now < expires_at
  ∧ same tenant_id
  ∧ same organization_id
  ∧ same domain_id or explicit federation authority
  ∧ requested compartments ⊆ authorized compartments
  ∧ purpose compatible
  ∧ current policy bundle valid
  ∧ principal/delegation valid
  ∧ marking releasable
  ∧ run/task scope allowed
```

Search, sort, count, error, timing bucket, cache and audit are partitioned by the full ADD isolation tuple. Unauthorized items do not influence rank, count, pagination, explanation or observable error shape.

## 7. Explicit exclusions

The PoC profile excludes:

- cross-project or global memory;
- vector/embedding persistence and similarity retrieval;
- autonomous consolidation, summarisation or self-modification;
- training or fine-tuning from memory;
- hidden chain-of-thought storage;
- memory-derived Authority, Approval, Decision or Canonical Assertion;
- indefinite retention or automatic renewal;
- cross-tenant retrieval;
- use after expiry, revocation, policy change or marking incompatibility.

## 8. Acceptance obligations

| ID | Scenario | Oracle |
|---|---|---|
| `BGM-01` | valid run-scoped item | stored with exact scope, provenance, TTL and audit |
| `BGM-02` | missing owner/scope/source/time/marking/purpose/confidence/retention | rejected before persistence |
| `BGM-03` | expired or revoked item | absent from result, rank, count and explanation |
| `BGM-04` | cross-tenant or cross-compartment request | deny with zero content/existence leakage |
| `BGM-05` | policy or marking changes between search and materialisation | result invalidated |
| `BGM-06` | prompt-injection content | tainted, not instruction eligible, no tool authority |
| `BGM-07` | same item admitted twice | one immutable item/idempotent receipt |
| `BGM-08` | correction/declassification | new artifact; source remains immutable |
| `BGM-09` | TTL boundary | inclusive start, exclusive expiry |
| `BGM-10` | cache/index inspection | full isolation key and no unauthorized shared entry |

`FR-118` is satisfied only if `BGM-01`–`BGM-03`, `BGM-08` and `BGM-09` pass. `FR-119` is satisfied only if `BGM-04`, `BGM-05` and `BGM-10` pass with zero leakage.

## 9. Atomic update set on approval

Promotion requires one atomic change set updating:

1. Requirement Register annotation for `FR-118` and `FR-119` without changing priority/release;
2. Requirement Traceability Index;
3. Decision Register and Decision Traceability Index;
4. CAP/ELM Requirement Crosswalk;
5. ADD scope fence, C8 design, agent invariants, security propagation and acceptance allocation;
6. LLD contract, storage, policy enforcement and tests;
7. manifests and hashes.

Partial promotion is invalid.
