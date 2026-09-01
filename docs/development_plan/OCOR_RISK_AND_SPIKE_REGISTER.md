# OCOR Risk and Spike Register

Spikes retire assumptions; they never constitute final implementation or PoC evidence. Time/token/compute figures are planning ranges.

## SPIKE-01 — C3 revision-state-idempotency-outbox atomicity

- Task: `OCOR-DEV-0015`; hypothesis: C3 can atomically bind state, revision, idempotency and outbox.
- Evidence/risk: baseline at `67cda4b44a8d27b831eb461b1e28d71e1d3398ab` shows the corresponding approved responsibility absent or compatibility-only; retires **Partial durable visibility**.
- Minimum implementation/classification: only the adapter and fault harness needed for the oracle; **retained contract harness**.
- Environment/fixtures: PostgreSQL disposable; 5 crash windows + concurrent retry.
- Test procedure: run the task validation commands against pinned real services, inject each named fault, hash raw logs and rerun from a clean state.
- Success oracle: state/outbox/idempotency counts and receipt digests. Failure oracle: partial visibility or divergent retry.
- Result decision: retain atomic port; choose backend only after task 16. Failure consequence: block dependent task and create an ARA decision item if architecture would change.
- Dependencies: OCOR-DEV-0013; time budget 4 agent-days; token budget 32k–70k; compute 20–40 CPU-h.
- Stop condition: first conclusive success/failure after at most two repair variants. Required evidence: `reports/evidence/G2/OCOR-DEV-0015.json` plus raw log hash.

## SPIKE-02 — selected C3 backend behaviour

- Task: `OCOR-DEV-0016`; hypothesis: The selected C3 backend meets approved isolation and recovery semantics.
- Evidence/risk: baseline at `67cda4b44a8d27b831eb461b1e28d71e1d3398ab` shows the corresponding approved responsibility absent or compatibility-only; retires **Wrong persistence choice**.
- Minimum implementation/classification: only the adapter and fault harness needed for the oracle; **harden if green**.
- Environment/fixtures: real selected C3 backend; concurrent writers, lost ACK, restart, reconciliation.
- Test procedure: run the task validation commands against pinned real services, inject each named fault, hash raw logs and rerun from a clean state.
- Success oracle: one commit and deterministic repair. Failure oracle: lost update or phantom success.
- Result decision: harden selection or raise blocking decision. Failure consequence: block dependent task and create an ARA decision item if architecture would change.
- Dependencies: OCOR-DEV-0006, OCOR-DEV-0013, OCOR-DEV-0015; time budget 5 agent-days; token budget 40k–90k; compute 30–70 service-h.
- Stop condition: first conclusive success/failure after at most two repair variants. Required evidence: `reports/evidence/G2/OCOR-DEV-0016.json` plus raw log hash.

## SPIKE-03 — TypeDB exact-at-commit semantics

- Task: `OCOR-DEV-0017`; hypothesis: TypeDB can expose exact-at-commit or explicit not-ready.
- Evidence/risk: baseline at `67cda4b44a8d27b831eb461b1e28d71e1d3398ab` shows the corresponding approved responsibility absent or compatibility-only; retires **Silent projection downgrade**.
- Minimum implementation/classification: only the adapter and fault harness needed for the oracle; **harden adapter kernel**.
- Environment/fixtures: real TypeDB; lagged projection and requested commit.
- Test procedure: run the task validation commands against pinned real services, inject each named fault, hash raw logs and rerun from a clean state.
- Success oracle: exact result or PROJECTION_NOT_READY. Failure oracle: older facts labeled exact.
- Result decision: retain adapter or govern alternative. Failure consequence: block dependent task and create an ARA decision item if architecture would change.
- Dependencies: OCOR-DEV-0006, OCOR-DEV-0012, OCOR-DEV-0013; time budget 5 agent-days; token budget 40k–85k; compute 25–60 service-h.
- Stop condition: first conclusive success/failure after at most two repair variants. Required evidence: `reports/evidence/G2/OCOR-DEV-0017.json` plus raw log hash.

## SPIKE-04 — Jena marking-safe projection

- Task: `OCOR-DEV-0018`; hypothesis: Jena projection can preserve markings and non-interference.
- Evidence/risk: baseline at `67cda4b44a8d27b831eb461b1e28d71e1d3398ab` shows the corresponding approved responsibility absent or compatibility-only; retires **RDF leakage**.
- Minimum implementation/classification: only the adapter and fault harness needed for the oracle; **harden mapper**.
- Environment/fixtures: real Jena; paired compartment RDF/SHACL fixtures.
- Test procedure: run the task validation commands against pinned real services, inject each named fault, hash raw logs and rerun from a clean state.
- Success oracle: authorized graph only and equal unauthorized observations. Failure oracle: triple/count/error leak.
- Result decision: retain mapper or block Jena profile. Failure consequence: block dependent task and create an ARA decision item if architecture would change.
- Dependencies: OCOR-DEV-0006, OCOR-DEV-0008, OCOR-DEV-0014; time budget 5 agent-days; token budget 40k–85k; compute 25–60 service-h.
- Stop condition: first conclusive success/failure after at most two repair variants. Required evidence: `reports/evidence/G2/OCOR-DEV-0018.json` plus raw log hash.

## SPIKE-05 — Kafka ordering replay and deduplication

- Task: `OCOR-DEV-0019`; hypothesis: Kafka provides required order/replay/dedup with OCOR envelope.
- Evidence/risk: baseline at `67cda4b44a8d27b831eb461b1e28d71e1d3398ab` shows the corresponding approved responsibility absent or compatibility-only; retires **Duplicate or reordered effects**.
- Minimum implementation/classification: only the adapter and fault harness needed for the oracle; **harden harness and adapter**.
- Environment/fixtures: Kafka/Strimzi; broker restart, rebalance, poison event.
- Test procedure: run the task validation commands against pinned real services, inject each named fault, hash raw logs and rerun from a clean state.
- Success oracle: ordered idempotent delivery and bounded quarantine. Failure oracle: visible reorder or unbounded retry.
- Result decision: retain settings or govern topology change. Failure consequence: block dependent task and create an ARA decision item if architecture would change.
- Dependencies: OCOR-DEV-0006, OCOR-DEV-0010, OCOR-DEV-0013; time budget 5 agent-days; token budget 45k–95k; compute 35–90 service-h.
- Stop condition: first conclusive success/failure after at most two repair variants. Required evidence: `reports/evidence/G2/OCOR-DEV-0019.json` plus raw log hash.

## SPIKE-06 — executable fidelity of 44 C6 transitions

- Task: `OCOR-DEV-0020`; hypothesis: The LLD 44-transition table is executable without reinterpretation.
- Evidence/risk: baseline at `67cda4b44a8d27b831eb461b1e28d71e1d3398ab` shows the corresponding approved responsibility absent or compatibility-only; retires **FSM semantic drift**.
- Minimum implementation/classification: only the adapter and fault harness needed for the oracle; **retained generator/equality suite**.
- Environment/fixtures: local + PostgreSQL; all tuples, every guard and durable effect.
- Test procedure: run the task validation commands against pinned real services, inject each named fault, hash raw logs and rerun from a clean state.
- Success oracle: 44 exact positive/negative cases. Failure oracle: missing/extra tuple or wrong effect.
- Result decision: implement exact table; conflict requires ARA decision. Failure consequence: block dependent task and create an ARA decision item if architecture would change.
- Dependencies: OCOR-DEV-0009, OCOR-DEV-0013, OCOR-DEV-0014; time budget 5 agent-days; token budget 45k–100k; compute 20–50 CPU-h.
- Stop condition: first conclusive success/failure after at most two repair variants. Required evidence: `reports/evidence/G2/OCOR-DEV-0020.json` plus raw log hash.

## SPIKE-07 — identity-policy latency and failure semantics

- Task: `OCOR-DEV-0021`; hypothesis: Security controls fail closed within bounded latency.
- Evidence/risk: baseline at `67cda4b44a8d27b831eb461b1e28d71e1d3398ab` shows the corresponding approved responsibility absent or compatibility-only; retires **Permit on control outage**.
- Minimum implementation/classification: only the adapter and fault harness needed for the oracle; **harden client policies**.
- Environment/fixtures: OPA/Keycloak/SPIFFE/OpenBao; latency, timeout, rotation and stale bundle.
- Test procedure: run the task validation commands against pinned real services, inject each named fault, hash raw logs and rerun from a clean state.
- Success oracle: typed deny/unavailable with audit. Failure oracle: permit or unbounded hang.
- Result decision: retain timeouts or govern availability trade-off. Failure consequence: block dependent task and create an ARA decision item if architecture would change.
- Dependencies: OCOR-DEV-0006, OCOR-DEV-0014; time budget 4 agent-days; token budget 40k–90k; compute 35–80 service-h.
- Stop condition: first conclusive success/failure after at most two repair variants. Required evidence: `reports/evidence/G2/OCOR-DEV-0021.json` plus raw log hash.

## SPIKE-08 — causal reproducibility

- Task: `OCOR-DEV-0022`; hypothesis: Causal results are reproducible when inputs and methods are pinned.
- Evidence/risk: baseline at `67cda4b44a8d27b831eb461b1e28d71e1d3398ab` shows the corresponding approved responsibility absent or compatibility-only; retires **Unverifiable causal claims**.
- Minimum implementation/classification: only the adapter and fault harness needed for the oracle; **retained reproducibility kernel**.
- Environment/fixtures: local causal runner + object store; seed/model/data/intervention variants.
- Test procedure: run the task validation commands against pinned real services, inject each named fault, hash raw logs and rerun from a clean state.
- Success oracle: same sealed digest or explained method-version change. Failure oracle: unexplained divergence.
- Result decision: retain method or abstain/govern replacement. Failure consequence: block dependent task and create an ARA decision item if architecture would change.
- Dependencies: OCOR-DEV-0007, OCOR-DEV-0009, OCOR-DEV-0013; time budget 5 agent-days; token budget 45k–100k; compute 20–80 CPU-h.
- Stop condition: first conclusive success/failure after at most two repair variants. Required evidence: `reports/evidence/G2/OCOR-DEV-0022.json` plus raw log hash.

## SPIKE-09 — vector-index partition isolation

- Task: `OCOR-DEV-0023`; hypothesis: Vector partitions prevent cross-scope influence.
- Evidence/risk: baseline at `67cda4b44a8d27b831eb461b1e28d71e1d3398ab` shows the corresponding approved responsibility absent or compatibility-only; retires **Semantic retrieval leakage**.
- Minimum implementation/classification: only the adapter and fault harness needed for the oracle; **harden partition adapter**.
- Environment/fixtures: real vector index; paired authorized/foreign embeddings.
- Test procedure: run the task validation commands against pinned real services, inject each named fault, hash raw logs and rerun from a clean state.
- Success oracle: no foreign influence on content/rank/count/cache/timing band. Failure oracle: any measurable forbidden influence.
- Result decision: retain backend or raise selection blocker. Failure consequence: block dependent task and create an ARA decision item if architecture would change.
- Dependencies: OCOR-DEV-0006, OCOR-DEV-0008, OCOR-DEV-0014; time budget 5 agent-days; token budget 45k–100k; compute 30–90 service-h.
- Stop condition: first conclusive success/failure after at most two repair variants. Required evidence: `reports/evidence/G2/OCOR-DEV-0023.json` plus raw log hash.

## SPIKE-10 — cross-compartment non-interference

- Task: `OCOR-DEV-0024`; hypothesis: The full retrieval path is non-interfering across compartments.
- Evidence/risk: baseline at `67cda4b44a8d27b831eb461b1e28d71e1d3398ab` shows the corresponding approved responsibility absent or compatibility-only; retires **Cross-compartment disclosure**.
- Minimum implementation/classification: only the adapter and fault harness needed for the oracle; **retained security suite**.
- Environment/fixtures: full retrieval stack; paired worlds differing only in forbidden data.
- Test procedure: run the task validation commands against pinned real services, inject each named fault, hash raw logs and rerun from a clean state.
- Success oracle: observational equivalence within preregistered timing bound. Failure oracle: content/existence/rank/count/cache/timing distinction.
- Result decision: block G5 until design-compatible control exists. Failure consequence: block dependent task and create an ARA decision item if architecture would change.
- Dependencies: OCOR-DEV-0018, OCOR-DEV-0021, OCOR-DEV-0023; time budget 6 agent-days; token budget 55k–120k; compute 50–120 service-h.
- Stop condition: first conclusive success/failure after at most two repair variants. Required evidence: `reports/evidence/G2/OCOR-DEV-0024.json` plus raw log hash.

## SPIKE-11 — distributed deletion saga

- Task: `OCOR-DEV-0025`; hypothesis: Deletion can converge across all memory representations.
- Evidence/risk: baseline at `67cda4b44a8d27b831eb461b1e28d71e1d3398ab` shows the corresponding approved responsibility absent or compatibility-only; retires **Incomplete deletion reported complete**.
- Minimum implementation/classification: only the adapter and fault harness needed for the oracle; **retained saga skeleton**.
- Environment/fixtures: metadata/content/index/cache/replica stack; fault at each saga participant.
- Test procedure: run the task validation commands against pinned real services, inject each named fault, hash raw logs and rerun from a clean state.
- Success oracle: DELETION_INCOMPLETE then deterministic completion. Failure oracle: success with surviving copy.
- Result decision: harden saga or govern backend limitation. Failure consequence: block dependent task and create an ARA decision item if architecture would change.
- Dependencies: OCOR-DEV-0016, OCOR-DEV-0017, OCOR-DEV-0018, OCOR-DEV-0019, OCOR-DEV-0023; time budget 6 agent-days; token budget 55k–120k; compute 50–130 service-h.
- Stop condition: first conclusive success/failure after at most two repair variants. Required evidence: `reports/evidence/G2/OCOR-DEV-0025.json` plus raw log hash.

## SPIKE-12 — restore without resurrection

- Task: `OCOR-DEV-0026`; hypothesis: Restore can reconcile tombstones before reads.
- Evidence/risk: baseline at `67cda4b44a8d27b831eb461b1e28d71e1d3398ab` shows the corresponding approved responsibility absent or compatibility-only; retires **Deleted memory resurrection**.
- Minimum implementation/classification: only the adapter and fault harness needed for the oracle; **retained restore gate**.
- Environment/fixtures: backup plus complete memory stack; backup-before-delete then restore.
- Test procedure: run the task validation commands against pinned real services, inject each named fault, hash raw logs and rerun from a clean state.
- Success oracle: deleted item absent from all read/influence paths. Failure oracle: any resurrection.
- Result decision: block restore and PoC campaign. Failure consequence: block dependent task and create an ARA decision item if architecture would change.
- Dependencies: OCOR-DEV-0025; time budget 5 agent-days; token budget 45k–100k; compute 40–100 service-h.
- Stop condition: first conclusive success/failure after at most two repair variants. Required evidence: `reports/evidence/G2/OCOR-DEV-0026.json` plus raw log hash.

## SPIKE-13 — deterministic context-assembly replay

- Task: `OCOR-DEV-0027`; hypothesis: Context assembly can replay exact model input.
- Evidence/risk: baseline at `67cda4b44a8d27b831eb461b1e28d71e1d3398ab` shows the corresponding approved responsibility absent or compatibility-only; retires **Non-reproducible agent decisions**.
- Minimum implementation/classification: only the adapter and fault harness needed for the oracle; **retained receipt kernel**.
- Environment/fixtures: retrieval stack; ranking/redaction/truncation permutations.
- Test procedure: run the task validation commands against pinned real services, inject each named fault, hash raw logs and rerun from a clean state.
- Success oracle: exact item versions/order/digest replay. Failure oracle: unrecorded or divergent context.
- Result decision: retain pinned pipeline or prohibit evidence claim. Failure consequence: block dependent task and create an ARA decision item if architecture would change.
- Dependencies: OCOR-DEV-0023, OCOR-DEV-0024; time budget 5 agent-days; token budget 45k–100k; compute 25–70 service-h.
- Stop condition: first conclusive success/failure after at most two repair variants. Required evidence: `reports/evidence/G2/OCOR-DEV-0027.json` plus raw log hash.
