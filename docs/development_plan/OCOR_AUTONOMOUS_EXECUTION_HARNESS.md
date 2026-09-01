# OCOR Autonomous Execution Harness

## Dispatch loop

1. Verify `origin/main`, approved artifact hashes, clean task worktree and current `OCOR_PLAN_RUN_STATE.json`.
2. Validate the backlog; select only tasks whose hard dependencies have accepted evidence.
3. Materialize the task context pack from `OCOR_AGENT_CONTEXT_MANIFEST.json`; reject hash drift.
4. Create `task/<ID>-<slug>` from the current integration branch; never reuse a dirty worktree.
5. Implement only `expected_file_areas`; a pre-commit guard rejects `prohibited_file_areas`.
6. Run named narrow positive/negative/fault checks, then integration checks. Record nonzero exits and at most two materially different repairs.
7. Emit `reports/evidence/<gate>/<ID>.json`, raw logs and a structured handoff with commit, commands, environment, hashes, limitations and rollback.
8. Independent review checks requirement, contract, negative-test, real-backend and evidence coverage.
9. Integration Agent incorporates through the gate integration branch and runs mandatory CI. Red, skipped-mandatory or unavailable results return to repair.
10. Promote only when the gate authority accepts the exact green commit; never infer E1, PoC-GO or Production readiness.

## Logical roles

| Role | Allowed/prohibited scope | Output contract and validation | Escalation |
|---|---|---|---|
| Delivery Coordinator | Select dependency-ready tasks, own task ledger and integration barriers; cannot waive red gates. | Hash-bound handoff, commands, results, risks, rollback | Missing authority, normative conflict, two failed repairs, mandatory service unavailable |
| Contract and Shared-Kernel Agent | Own WS-01 and generated boundaries; cannot select backend semantics. | Hash-bound handoff, commands, results, risks, rollback | Missing authority, normative conflict, two failed repairs, mandatory service unavailable |
| Component Implementation Agent | Own one C1-C8 task/file area; cannot edit other components or approved design. | Hash-bound handoff, commands, results, risks, rollback | Missing authority, normative conflict, two failed repairs, mandatory service unavailable |
| Governed Memory Agent | Own WS-10; cannot defer any kind/scope/lifecycle or bypass C6/C3. | Hash-bound handoff, commands, results, risks, rollback | Missing authority, normative conflict, two failed repairs, mandatory service unavailable |
| Security and Policy Agent | Own WS-11 and cross-compartment review; cannot add permit-on-failure paths. | Hash-bound handoff, commands, results, risks, rollback | Missing authority, normative conflict, two failed repairs, mandatory service unavailable |
| Infrastructure and Operations Agent | Own WS-12 and disposable services; cannot promote environment availability as conformance. | Hash-bound handoff, commands, results, risks, rollback | Missing authority, normative conflict, two failed repairs, mandatory service unavailable |
| Verification and Evidence Agent | Own qualifying fixtures/manifests; cannot accept mocks/skips as final evidence. | Hash-bound handoff, commands, results, risks, rollback | Missing authority, normative conflict, two failed repairs, mandatory service unavailable |
| Integration Agent | Own integration branches and collision zones; cannot bypass branch protection. | Hash-bound handoff, commands, results, risks, rollback | Missing authority, normative conflict, two failed repairs, mandatory service unavailable |
| Independent Conformance Reviewer | Reproduce G6/G7 evidence without using implementation summaries as sole evidence; cannot author implementation under review. | Hash-bound handoff, commands, results, risks, rollback | Missing authority, normative conflict, two failed repairs, mandatory service unavailable |

## Handoff schema

Each handoff contains `task_id`, `base_sha`, `head_sha`, `context_manifest_sha256`, changed paths, requirement IDs, test commands with exit/pass/fail/skip/not-executed counts, raw evidence hashes, migration/rollback result, security/observability notes, assumptions and unresolved blockers. A field omission is a failed handoff.

## Git and repair protocol

Use isolated worktrees and non-force task branches. Do not stash or discard user changes. Rebase only before review; after evidence sealing, merge without rewriting the task commit. Concurrent agents may not own the same exact file area in one wave. Two failed repair cycles, a normative conflict, a real-service blocker or an architecture substitution ends local retry and creates an escalation record. Rollback is a new revert commit plus explicit data forward/down procedure.

## Completion rule

G7 can prepare a PoC-GO candidate only after all 285 mappings, 44 transitions, BA-01–08, FGM-01–20, memory taxonomy/scopes/lifecycle, mission thread and recovery tests are qualifying and reproducible. A candidate is not approval. Production remains a separate campaign.
