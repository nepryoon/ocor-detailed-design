# OpenBao provisioning qualification

`qualify.py` validates only the disposable OpenBao service assigned to
`OCOR-DEV-0078`. It does not inspect, pause, restart, or depend on OPA, Keycloak,
SPIRE, or any other service.

The check requires the exact official digest and version from
`infra/services.lock.json`, Docker health, `no-new-privileges`, loopback-only API
publication, initialized/unsealed active state, rejection of an invalid token, and a
successful authenticated system API request. The disposable token is read into memory
from the already-running project container and is never emitted in JSON, logs, command
arguments, or errors.

Run the non-mutating check:

```bash
python3 deploy/bootstrap/services/openbao/qualify.py
```

Run bounded fault and recovery qualification explicitly:

```bash
python3 deploy/bootstrap/services/openbao/qualify.py --fault-recovery --execute
```

Pause is always reversed in a `finally` block. Unpause and restart must restore Docker
health plus authenticated and unauthenticated API contracts within the timeout. The
tool uses argument vectors, finite subprocess/HTTP timeouts, structured errors, and
versioned JSON output. Ownership is WS-12 Infrastructure and Operations; deprecation is
allowed only after dependent OpenBao campaigns have a governed replacement.
