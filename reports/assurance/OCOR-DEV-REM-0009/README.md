# OCOR-DEV-REM-0009 assurance candidate

This directory seals reproducible evidence for the candidate remediation of
`OCOR-DEV-0009` at source commit
`13f274a7ddd503ab51e7e7e6e1287847b809da4a`.

The remediation binds authority to the verified delegation and exact Governed
Context, closes the governance fault taxonomy, validates provenance mappings,
and provides a lock-backed one-shot lease adapter. Trusted time, revocation,
stop epoch, fencing and consumption are evaluated at one atomic adapter
boundary. Contradictory or malformed adapter decisions fail closed.

Evidence:

- integrated focused campaign: 120 PASS, zero skipped;
- complete runtime campaign with the local live PostgreSQL fixture: 418 PASS,
  zero skipped;
- complete mechanical revert campaign: 400 PASS, zero skipped;
- independent read-only review: PASS with no remaining findings.

The in-memory adapter proves process-local semantics only. Durable
co-transaction with `DeliveryAttempt`, restart recovery, and multi-process
serialization remain requirements of a later governed durable adapter. This
candidate does not promote G1, runtime conformance, PoC readiness, E2, or
Production readiness.
