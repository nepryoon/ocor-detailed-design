# OCOR ADD v1.2 — Approval Record

**Disposition:** APPROVED  
**Effective date:** 2026-08-30  
**Authority:** Luca Lillo, Product Owner and repository owner, acting as Architecture Review Authority  
**Authorization evidence:** explicit instruction in the governed review thread: “puoi dichiararlo approvato”  
**Decision range:** `DEC-197`–`DEC-206`  
**Next available decision:** `DEC-207`

## Approved artifacts

| Artifact | SHA-256 | Purpose |
|---|---|---|
| `ocor-runtime/docs/governance_dossier/OCOR_ADD_v1.2_APPROVED_BASELINE.md` | `c3f432ae0d172f2b4f70be8220d0ae4a134ec14716bccc6a12d75dfee438b84f` | Authoritative ADD v1.2 baseline |
| `ocor-runtime/docs/governance_dossier/ARA_DECISION_RECORD_v1.1.md` | `35579536a67122700ff09f6be33874163f5872a199f853b557d28c71af9a0eae` | Approval decisions and authority |
| `ocor-runtime/docs/governance_dossier/registers/OCOR_Decision_Register_v1.1_APPROVED.md` | `521e328e76d9723d7ad035684df49c0183c754f8029f20c522a744b4d2a5f7dd` | Decision register snapshot |
| `ocor-runtime/docs/governance_dossier/registers/OCOR_Decision_Traceability_Index_v1.1_APPROVED.md` | `e6b4f45d96c323c44fb09370dc2396b8bd73ff7de1e2c0632a1f551b5dfe7d5a` | Decision traceability snapshot |
| `ocor-runtime/docs/governance_dossier/registers/OCOR_Requirement_Register_v1.0_APPROVED.md` | `eb3c3bca4c0e88a2a7c70a6c5a7c45ab1cf51fd72329a2b6c2d877939c43b7d2` | Requirement register snapshot |
| `ocor-runtime/docs/governance_dossier/registers/OCOR_Requirement_Traceability_Index_v1.0_APPROVED.md` | `44b54a577a6d6c3342af85fced1ee98662b79f783a8b22ab5c655feca113c0f7` | Requirement traceability snapshot |
| `ocor-runtime/docs/governance_dossier/registers/OCOR_CAP_ELM_Requirement_Crosswalk_v1.0_APPROVED.md` | `89a365262909e734c19512e799d78632b72ab6452ad0f5e7c11661f5819f101e` | CAP/ELM crosswalk snapshot |

## Scope of approval

The approved baseline incorporates the corrected ADD v1.2 candidate by value. It promotes the architectural invariants, the ACTION FSM including `ACT-T01`–`ACT-T31b`, marking lattice rules, RFC 8785 canonicalization, transactional outbox/BA-01 atomicity, EMISSION-FENCE and CapabilityLease temporal guards.

`DEC-205` resolves the only release-placement inconsistency: `FR-095` is P0/MVP; `ELM-070` remains deferred outside the PoC. No counterfactual AAP capability is claimed for PoC.

## Accepted non-blocking validation limitations

| ID | Limitation | Required closure gate |
|---|---|---|
| VAL-ACT-001 | The full post-remediation verification harness was not rerun before architecture approval. | Must pass before implementation promotion / LLD implementation gate. |
| VAL-ACT-002 | An official OpenAPI 3.1 semantic validator was not executed in the review environment. | Execute the validator or record a specific waiver before the first external interface baseline. |
| VAL-ACT-003 | Backend/runtime evidence remains incomplete by design at architectural approval. | Close through implementation evidence; no runtime conformance is implied by this approval. |

These limitations do not invalidate the architecture approval. They prevent claims of implementation readiness, validator completion, or runtime conformance until their respective gates are satisfied.
