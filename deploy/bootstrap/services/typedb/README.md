# TypeDB provisioning qualification

`qualify.py` validates the already provisioned non-production TypeDB instance against
`infra/services.lock.json`. It fails closed unless the configured image is the exact
approved digest, both published ports are loopback-only, Docker reports the container
healthy, gRPC accepts a TCP connection, HTTP reports the exact locked distribution and
version, and unauthenticated database access returns TypeDB `AUT2`.

The mutating fault/recovery campaign requires both flags:

```bash
python3 deploy/bootstrap/services/typedb/qualify.py --fault-recovery --execute
```

It pauses the exact project container, requires bounded unavailability, always unpauses
in a `finally` block, then verifies both unpause and process-restart recovery. Commands
use argument vectors (never a shell), have finite timeouts, and emit a versioned JSON
result without environment variables, credentials, container logs, or response bodies.
The service is disposable and non-production. Ownership is WS-12 Infrastructure and
Operations; removal is allowed only after the TypeDB real-backend campaigns no longer
depend on this qualification contract.

Run the deterministic contract tests with:

```bash
python3 deploy/bootstrap/services/typedb/test_qualify.py
```
