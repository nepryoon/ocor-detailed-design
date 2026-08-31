# OCOR Architectural Design Document v1.3 — Candidate Amendment

## 1. Document control

| Field | Value |
|---|---|
| Identifier | `OCOR-ADD-1.3-CANDIDATE` |
| Status | `PROPOSED — AWAITING GOVERNED DECISION` |
| Base | `OCOR-ADD-1.2` approved baseline |
| Base SHA-256 | `c3f432ae0d172f2b4f70be8220d0ae4a134ec14716bccc6a12d75dfee438b84f` |
| Change set | `CC-BOUNDED-GOVERNED-MEMORY` |
| Trigger | `IALLD-007` |
| Requirements | `FR-118`, `FR-119` remain Confirmed P0/PoC |
| Evidence state | unchanged; no implementation or production claim |
| Effective from | only after governed approval and consolidated baseline publication |

This candidate is a normative amendment to ADD v1.2. Every ADD v1.2 clause remains unchanged except the explicit replacements below. Candidate text does not supersede the approved baseline until promoted by the competent authority.

## 2. Normative replacements

### 2.1 Scope fence replacement

Replace the `ELM-084` disposition in ADD v1.2 §§1.5 and 7.1 with:

| Element | PoC disposition | Deferred disposition |
|---|---|---|
| `ELM-084` — Agent Memory | `POC_BOUNDED_PROFILE`: run/task-scoped `GovernedMemoryItem`, TTL-bounded, evidence-reconstructible, policy-filtered and compartment-isolated | General persistent, cross-run, vector, learning and cross-project memory remains deferred to MVP |

No claim of general agent memory is permitted in the PoC.

### 2.2 C8 storage and authority replacement

C8 may persist only:

- run, task, assignment, commitment and handoff records;
- bounded `GovernedMemoryItem` records;
- opaque content references to content-addressed storage;
- policy/audit/provenance bindings.

C8 may not persist global memory, backend credentials, hidden reasoning, unrestricted embeddings or unbounded conversational history. Memory is non-authoritative and cannot directly produce a Canonical Assertion, Decision, Approval, Delegation, CapabilityLease or ActionCommand.

### 2.3 GovernedMemoryItem contract

The closed contract and admission/retrieval algorithms in `OCOR_Change_Control_Bounded_Governed_Memory_v1.0.md` are incorporated by value into this candidate. The canonical field names are normative. Aliases and undeclared extensions are prohibited.

The record is bound to exactly one canonical ADD `GovernedContext` v1.2. Its `governed_context_digest` must equal the digest calculated from the closed eleven-field ADD record; the memory contract does not redefine or extend `GovernedContext`.

### 2.4 Isolation and leakage control

Memory storage, indexes, caches, queues, logs and content prefixes use the isolation key:

```text
(tenant_id,
 organization_id,
 domain_id,
 compartments,
 purpose,
 classification_marking_ref,
 ontology_release_digest,
 policy_bundle_digest,
 agent_run_id)
```

Policy evaluation occurs before lookup and before materialisation. Unauthorized items cannot influence content, existence, count, rank, pagination, cache hit, explanation, error or observable timing bucket. Any ambiguity produces `DENY` without payload.

### 2.5 Lifecycle

```text
PROPOSED → ACTIVE
PROPOSED → QUARANTINED
ACTIVE → EXPIRED
ACTIVE → REVOKED
ACTIVE → QUARANTINED
EXPIRED | REVOKED | QUARANTINED → DELETED
```

No transition returns an item to `ACTIVE`. Correction, sanitisation or declassification produces a new item with new digest and provenance. Physical deletion follows the approved retention policy while the audit tombstone remains.

### 2.6 Agent invariants replacement

Replace the memory portion of ADD v1.2 §4.3.1 invariant 9 with:

1. `ELM-080` remains deferred; budget/quota do not become semantic reservation.
2. `ELM-084/POC_BOUNDED_PROFILE` is active only through the closed `GovernedMemoryItem` contract.
3. Memory is tainted and non-authoritative; retrieval cannot change authority, policy, marking or capability.
4. General persistent and vector memory remains deferred.
5. CapabilityLease remains the distinct short-lived security token defined by ADD v1.2 and is not a Memory or `ELM-080` lease.

### 2.7 Acceptance allocation replacement

Add to the Agent Kernel and Security & Governance acceptance rows:

| Requirement | Method | Evidence | Gate |
|---|---|---|---|
| `FR-118` | schema/lifecycle/TTL/admission negative suite | immutable item, audit, expiry and correction records | all `BGM-01`–`03`, `08`, `09` pass |
| `FR-119` | cross-tenant/compartment leakage campaign including rank/count/cache/error/timing | denied traces and non-interference report | `BGM-04`, `05`, `10` pass with zero leakage |

## 3. Traceability

| Source | ADD v1.3 realization | LLD obligation |
|---|---|---|
| `FR-118` | §§2.2–2.5 | exact record, constraints, store, lifecycle, expiry worker and tests |
| `FR-119` | §2.4 | pre/post policy, full isolation key, cache/index partition and non-interference tests |
| `ELM-084` | §2.1 bounded/deferred split | bounded adapter only; general profile rejected as deferred |
| `FR-038` | §2.6 | memory cannot grant authority or bypass the agent kernel |
| `ARC-015`, `ARC-016` | §§2.2, 2.4, 2.6 | least privilege, taint, compartment isolation and kill switch |

## 4. Backward compatibility

ADD v1.2 has no approved public memory contract and no production consumer. This amendment adds a bounded PoC contract without changing the existing approved OpenAPI, Proto, Action, Event or MCP identifiers. Any future public memory API requires independent contract versioning and compatibility review.

## 5. Promotion conditions

This candidate may be consolidated as an approved ADD baseline only when:

1. the bounded profile disposition is ratified through governed change control;
2. all five approved register snapshots are updated atomically;
3. the authoritative memory schema is materialised and hashed;
4. LLD v1.1 uses the exact ADD `GovernedContext` and memory contract;
5. the 285/285 semantic alignment gate reports no blocker;
6. a new manifest pins the consolidated baseline and dependencies.

Until then ADD v1.2 remains the only approved ADD baseline.
