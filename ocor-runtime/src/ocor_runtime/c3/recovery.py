"""C3 -- single-writer recovery and reconciliation.

Guarantees that reconciliation and outbox relay run under a single
writer at a time via a real PostgreSQL advisory lock
(``ocor_runtime.c3.adapters.recovery_lock``, new), so concurrent
worker processes racing the same recovery pass converge to the
identical repaired state without ever applying a duplicate repair, and
a claim-deliver-acknowledge cycle is never interleaved across workers.
Composes ``PostgresC3Service`` (OCOR-DEV-0029, sealed, reused
unmodified) exclusively through its own sealed public methods
(``reconcile``, ``claim_batch``, ``acknowledge``) -- neither this
module nor the service it composes is modified, so OCOR-DEV-0029's own
sealed evidence digest stays untouched.

``reconcile`` is the only sealed recovery entry point (``RecoveryPort``,
OCOR-DEV-0013, ``ocor_runtime.c3.ports``); it both detects and repairs
orphaned rows in one pass, so a genuine pre-flight, side-effect-free
health count is not part of the sealed contract. ``assert_healthy`` is
therefore itself a recovery pass: it reports UNHEALTHY (raises) for
the pass where anything needed repairing, and healthy on any
subsequent pass once nothing remains -- "unreconciled durable intent
blocks service health" is satisfied by the repair itself being the
signal, not a separate read-only probe outside the sealed contract.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from .adapters.recovery_lock import PostgresAdvisoryLock
from .ports import C3Error, OutboxEnvelope
from .service import PostgresC3Service

RECOVERY_LOCK_KEY = "urn:ocor:c3:single-writer-recovery"


@dataclass(frozen=True, slots=True)
class RecoveryReport:
    """Every recovery pass names exactly how many rows it repaired, so
    a caller never has to infer health from a bare success."""

    repaired: int


class SingleWriterRecoveryCoordinator:
    """Serializes reconciliation and outbox relay across every
    concurrently-running instance -- even in separate OS processes --
    via a real PostgreSQL advisory lock, so racing writers converge to
    the same final state without ever duplicating a repair or a
    delivery. A coordinator built after a real process restart (a
    fresh instance, since no state is held anywhere but Postgres)
    reacquires the identical lock and converges identically -- restart
    is not a special case."""

    def __init__(self, service: PostgresC3Service, lock: PostgresAdvisoryLock) -> None:
        self._service = service
        self._lock = lock

    def run_recovery_pass(self, *, limit: int = 1000) -> RecoveryReport:
        with self._lock.held(RECOVERY_LOCK_KEY):
            repaired = self._service.reconcile(limit=limit)
        return RecoveryReport(repaired=repaired)

    def assert_healthy(self, *, limit: int = 1000) -> RecoveryReport:
        report = self.run_recovery_pass(limit=limit)
        if report.repaired > 0:
            raise C3Error(
                "UNRECONCILED_DURABLE_INTENT",
                f"{report.repaired} commit(s) had unreconciled durable intent and were just repaired",
            )
        return report

    def claim_and_deliver(
        self, *, limit: int, deliver: Callable[[OutboxEnvelope], None]
    ) -> tuple[OutboxEnvelope, ...]:
        """Claims a batch and delivers each envelope to ``deliver``
        (the caller's own idempotent sink, keyed by ``event_id``),
        acknowledging only once delivery succeeds -- all inside the
        same single-writer critical section, so two concurrent workers
        can never both claim the same unacknowledged row before either
        has a chance to acknowledge it. A crash between delivery and
        acknowledgement (a lost ACK) leaves the row claimable again on
        the next pass; the row is redelivered, and it is ``deliver``'s
        own idempotency (by ``event_id``) that ensures no duplicate
        canonical effect results -- the standard outbox at-least-once
        contract, never silently upgraded to exactly-once by this
        coordinator itself."""
        with self._lock.held(RECOVERY_LOCK_KEY):
            envelopes = self._service.claim_batch(limit=limit)
            for envelope in envelopes:
                deliver(envelope)
                self._service.acknowledge(envelope.event_id, acknowledged_at=datetime.now(UTC))
        return envelopes
