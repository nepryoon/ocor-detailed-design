# OCOR Architecture Review Authority Decision Record v1.5

## 1. Decision control

| Field | Value |
|---|---|
| Record identifier | `OCOR-ARA-DR-1.5` |
| Status | **APPROVED — EFFECTIVE ON EXACT-GREEN MERGE** |
| Decision | `DEC-211` |
| Title | OCOR Autonomous Tooling and Infrastructure Bootstrap Policy |
| Effective date | 2026-09-03, on merge |
| Authority | Explicit Product Owner implementation authorization, current conversation |
| Change set | `CC-AUTONOMOUS-TOOLING-INFRASTRUCTURE-BOOTSTRAP` |
| Prior governing decision | `DEC-210` |
| Nature | Development tooling and non-production infrastructure; no architecture semantic change |
| Evidence fence | `E1=0`, `E2=0`, zero requirements globally `Verified` |
| Runtime / Production | **NOT ESTABLISHED / NO-GO** |

## 2. Decision

The authority adopts the repository policy, lock manifests, bootstrap tools and
infrastructure workstream needed to provision approved real services. Missing local
tools and disposable services are remediation work, not external blockers. Acquisition
is restricted to official sources and cryptographically pinned artifacts.

## 3. Scope and supersession

`DEC-211` supersedes only the `DEC-210` operational disposition that treated freely
provisionable local tooling/services as external blockers. It preserves RCCAD,
IRB/ADD/LLD semantics, all technology selections and historical evidence. It does not
accept G2 tasks or runtime evidence.

## 4. Effectiveness gate

Effectiveness requires schema-valid canonical manifests, RED/GREEN acceptance evidence,
backlog/DAG integrity, immutable-input proof, independent verification and exact-head
CI. Registry/image digest capture and Apache Fuseki source SHA-512 are mandatory.
