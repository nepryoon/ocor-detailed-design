# OCOR-DEV-REM-0008 assurance candidate

This directory seals reproducible evidence for the candidate remediation of
`OCOR-DEV-0008` on the integration-refreshed source commit
`33a9c0e93191d6383e0b96468246dfd7424eb4f8`.

The remediation aligns the Python Governed Context boundary with the approved
schema, rejects non-array coercion, validates generated protobuf bindings before
dereference, and preserves the schema's non-empty correlation identifier rule.

The evidence is a candidate only. It does not promote G1, runtime conformance,
PoC readiness, E2, or Production readiness. Integration remains fail-closed
until pull-request CI is green and the reopened programme G0 controls are
resolved or formally governed.

Test evidence:

- focused current-branch campaign: 119 PASS, zero skipped;
- complete runtime campaign with the local live PostgreSQL fixture: 382 PASS,
  zero skipped;
- mechanical revert campaign in a disposable, import-pinned worktree: 378 PASS,
  zero skipped;
- independent read-only review: PASS with no findings.

The rollback worktree was removed after the run. No approved baseline or
`inputs/**` content was modified.
