# SPIRE provisioning qualification

`qualify.py` validates the exact digest-pinned SPIRE server and agent, their
closed local configuration, runtime identity and workload X.509-SVID delivery.
The default invocation is strictly read-only. With `--recover-agent
--workload-svid --invalid-token --fault --execute --env-file PATH`, it performs
bounded, task-scoped mutation: generate a short-lived join token without logging it,
atomically update the gitignored mode-0600 environment file, recreate only the
SPIRE agent, verify readiness, create a deterministic disposable workload
entry, fetch its SVID and remove the entry.

The tool never changes OPA, Keycloak, OpenBao or production resources. The
environment file is external to version control and must already contain all
Compose variables. Ownership: OCOR Platform Engineering. Version: 1.0.
Deprecation requires replacement evidence for OCOR-DEV-0077.
