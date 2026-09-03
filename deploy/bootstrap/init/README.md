# Deterministic initialization

Initialization is idempotent and ordered: SPIRE trust bootstrap, Keycloak realm,
OPA policy, OpenBao development paths, then graph databases. Scripts must verify
existing state before mutation and reject version drift.
