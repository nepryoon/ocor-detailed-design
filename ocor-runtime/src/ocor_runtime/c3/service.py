"""Retained C3 canonical commit slice.

Implements the sealed C3 ports (OCOR-DEV-0013, ``ocor_runtime.c3.ports``,
reused unmodified) as a thin orchestrator over ``PostgresC3Adapter``
(``ocor_runtime.c3.adapters.postgres``): state, revision, evidence,
idempotency and outbox commit atomically in one transaction, generalizing
the real-concurrency properties already proven by the sealed C3 spikes
(``spikes.c3_atomicity.oracle``, OCOR-DEV-0015; ``spikes.c3_backend``,
OCOR-DEV-0016) into a production-shaped ``GovernedCommitPort``/
``CanonicalReadPort``/``RevisionPort``/``RecoveryPort``/``OutboxRelayPort``
implementation that speaks the sealed dataclasses directly, not ad-hoc
dicts.

This module never imports a direct backend client (AFF-002/AFF-006):
every ``psycopg`` reference lives in the adapter it composes.

``_crash_after`` on ``commit`` is a keyword-only, underscore-prefixed
test-only fault-injection hook (mirrors ``spikes.c3_atomicity.oracle``'s
``crash_stage`` parameter, an already-accepted pattern in this codebase)
used exclusively by this task's own regression suite to prove real
process-crash recovery; it is never exercised by any caller through the
sealed ``GovernedCommitPort`` Protocol, which only declares ``commit(self,
command)``.
"""

from __future__ import annotations

from datetime import datetime

from .adapters.postgres import CrashStage, PostgresAdapterError, PostgresC3Adapter
from .ports import (
    C3Error,
    CanonicalSnapshot,
    CommitReceipt,
    GovernedCanonicalCommitCommand,
    OutboxEnvelope,
)

__all__ = ["CrashStage", "PostgresC3Service"]


class PostgresC3Service:
    """Real PostgreSQL-backed implementation of the sealed C3 ports."""

    def __init__(self, dsn: str) -> None:
        self._adapter = PostgresC3Adapter(dsn)

    def initialize(self) -> None:
        self._adapter.initialize()

    def reset(self) -> None:
        self._adapter.reset()

    def commit(
        self, command: GovernedCanonicalCommitCommand, *, _crash_after: CrashStage | None = None
    ) -> CommitReceipt:
        tenant_id, aggregate_type, aggregate_ref, idempotency_key = command.idempotency_scope
        try:
            outcome = self._adapter.commit_transaction(
                tenant_id=tenant_id,
                aggregate_type=aggregate_type,
                aggregate_ref=aggregate_ref,
                idempotency_key=idempotency_key,
                command_id=command.command_id,
                command_digest=command.command_digest,
                expected_revision=command.expected_revision,
                canonical_delta=command.canonical_delta,
                decision_ref=command.decision_ref,
                authority_ref=command.authority_ref,
                evidence_refs=command.evidence_refs,
                governed_context_digest=command.governed_context_digest,
                gate_package_digest=command.gate_package_digest,
                branch=command.branch,
                crash_after=_crash_after,
            )
        except PostgresAdapterError as error:
            raise C3Error(error.reason_code, str(error)) from error

        return CommitReceipt.from_command(
            command,
            commit_id=outcome.commit_id,
            state_digest=outcome.state_digest,
            outbox_event_id=outcome.outbox_event_id,
            outbox_payload_digest=outcome.outbox_payload_digest,
            committed_at=outcome.committed_at,
            replayed=outcome.replayed,
        )

    def read(
        self, tenant_id: str, aggregate_type: str, aggregate_ref: str
    ) -> CanonicalSnapshot | None:
        row = self._adapter.read_snapshot(tenant_id, aggregate_type, aggregate_ref)
        if row is None:
            return None
        return CanonicalSnapshot(
            tenant_id=tenant_id,
            aggregate_type=aggregate_type,
            aggregate_ref=aggregate_ref,
            revision=row.revision,
            state=row.state,
            state_digest=row.state_digest,
            commit_id=row.commit_id,
        )

    def current_revision(self, tenant_id: str, aggregate_type: str, aggregate_ref: str) -> int:
        return self._adapter.current_revision(tenant_id, aggregate_type, aggregate_ref)

    def claim_batch(self, *, limit: int) -> tuple[OutboxEnvelope, ...]:
        rows = self._adapter.claim_outbox_batch(limit=limit)
        return tuple(
            OutboxEnvelope(
                event_id=row.event_id,
                commit_id=row.commit_id,
                aggregate_ref=row.aggregate_ref,
                aggregate_revision=row.aggregate_revision,
                payload=row.payload,
                payload_digest=row.payload_digest,
                branch=row.branch,
                occurred_at=row.occurred_at,
            )
            for row in rows
        )

    def acknowledge(self, event_id: str, *, acknowledged_at: datetime) -> None:
        self._adapter.acknowledge_outbox(event_id, acknowledged_at=acknowledged_at)

    def reconcile(self, *, limit: int) -> int:
        return self._adapter.reconcile(limit=limit)
