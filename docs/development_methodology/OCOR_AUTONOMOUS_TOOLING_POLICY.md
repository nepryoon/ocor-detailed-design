# OCOR Autonomous Tooling and Infrastructure Bootstrap Policy

Status: **EFFECTIVE under DEC-211 after exact-green merge**.

## Scope

During an explicit Product Owner implementation mandate, an agent may provision,
update, exercise and remove repository-scoped development tooling and disposable
non-production services. This authority never applies to `inputs/`, production,
shared external resources, paid resources without budget, or architecture semantics.

The agent follows this fallback order: repository tool; host tool; isolated
environment; official package manager; official binary; digest-pinned image;
rootless container; user-space install; repository-owned replacement; governed skill
or MCP server. A failed operation is diagnosed before a materially different retry.
Transient external operations use bounded exponential retry.

## Mandatory controls

- Acquire only from official projects, official registries or an explicitly approved
  mirror; pin version and immutable digest/checksum.
- Record source, version, digest, license, architecture and acquisition time in
  `infra/*.lock.json`.
- Inspect downloaded install scripts before execution. Prefer archives, packages and
  images with published checksum/signature.
- Keep credentials outside Git. Commit names and templates only; generate disposable
  values with a cryptographically secure generator.
- Enforce timeouts, structured errors, health/readiness probes, resource limits,
  dedicated networks with loopback-only host publications, deterministic
  initialization, reset and evidence capture.
- Never substitute a required backend. Mocks qualify only local failure handling.
- Preserve `E1=0`, `E2=0`, zero global `Verified` and all current `NO-GO`
  claims until their independent governed gates pass.

## Tool contract

Repository tools expose `--help`, validate inputs, default to non-mutating checks,
require `--execute` for mutation, produce JSON, use bounded timeouts/retries and
restrict destructive operations to the Compose project and paths defined here.
Ownership is Platform Engineering; review is annual or on every major dependency
change. Deprecation requires a successor and a governed migration.
