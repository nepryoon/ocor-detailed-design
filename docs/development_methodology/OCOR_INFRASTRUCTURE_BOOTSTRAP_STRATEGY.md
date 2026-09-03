# OCOR Infrastructure Bootstrap Strategy

The development profile uses a digest-pinned Compose stack for integration and a
Kubernetes overlay for Kubernetes-specific qualification. Bootstrap is staged:

1. validate host, locks, ports and secret-name availability;
2. restore the frozen Python environment and required CLIs;
3. acquire verified images or build Fuseki from the official Apache archive;
4. create disposable credentials outside version control;
5. start services on an internal network and wait for typed health contracts;
6. initialize trust, realms, policy, databases and synthetic fixtures idempotently;
7. execute positive, negative, concurrency, outage, latency and recovery campaigns;
8. collect redacted logs, versions and digests; reset exact project resources.

Compose volumes are ephemeral by default. Explicit backup tests use named,
project-prefixed volumes and restore into a fresh isolated network. Fault injection
is limited to process stop/restart, network disconnect/reconnect, latency and
read-only filesystem controls declared by the campaign. Every teardown verifies that
no project container, network or volume remains.

Kubernetes qualification uses a dedicated namespace, digest-pinned images, resource
requests/limits, NetworkPolicy and disposable Secrets. It does not convert Compose
evidence into Kubernetes evidence.
