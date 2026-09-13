"""Restore that reconciles a durable tombstone journal before ever
touching a target, proving deleted content never reappears even when a
backup or replay path would otherwise reintroduce it.

Composes OCOR-DEV-0025's sealed distributed deletion saga
(``spikes.memory_deletion.saga``, reused completely unmodified) with a
new, durable, real-PostgreSQL-backed tombstone journal:
``record_deletion`` only tombstones an item in the journal once the
saga has independently confirmed it is gone from every target, and
``restore_from_backup`` consults that journal FIRST, before writing
anything to any target. An unreachable journal is refused exactly like
a tombstoned item -- fail closed, never silently treated as "safe to
restore".
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import psycopg

from spikes.memory_deletion.saga import (
    DeletionReceipt,
    DeletionStatus,
    DeletionTarget,
    run_deletion_saga,
)

__all__ = [
    "DeletionReceipt",
    "DeletionStatus",
    "DeletionTarget",
    "RestoreOutcome",
    "RestoreStatus",
    "TombstoneJournal",
    "TombstoneJournalUnavailable",
    "record_deletion",
    "restore_from_backup",
    "run_deletion_saga",
]


class RestoreStatus(StrEnum):
    RESTORED = "RESTORED"
    REFUSED_TOMBSTONED = "REFUSED_TOMBSTONED"
    REFUSED_JOURNAL_UNAVAILABLE = "REFUSED_JOURNAL_UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class RestoreOutcome:
    item_id: str
    status: RestoreStatus
    confirmed: tuple[str, ...]


class TombstoneJournalUnavailable(RuntimeError):
    pass


class TombstoneJournal:
    """A durable, independently-queryable record of every item this
    delivery has confirmed deleted. A read that cannot reach the
    journal raises rather than returning a default -- callers must
    treat "unknown" as "refuse", never as "not tombstoned".
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def ensure_schema(self) -> None:
        """Separate from ``__init__`` so constructing a journal handle
        for a genuinely unreachable DSN (used to prove restore fails
        closed) never itself raises before the read path under test
        ever runs."""
        with psycopg.connect(self._dsn) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS spike_tombstone_journal "
                "(item_id TEXT PRIMARY KEY, tombstoned_at TIMESTAMPTZ NOT NULL DEFAULT now())"
            )

    def record(self, item_id: str) -> None:
        with psycopg.connect(self._dsn) as connection:
            connection.execute(
                "INSERT INTO spike_tombstone_journal (item_id) VALUES (%s) "
                "ON CONFLICT (item_id) DO NOTHING",
                (item_id,),
            )

    def is_tombstoned(self, item_id: str) -> bool:
        try:
            with psycopg.connect(self._dsn, connect_timeout=3) as connection:
                row = connection.execute(
                    "SELECT 1 FROM spike_tombstone_journal WHERE item_id = %s", (item_id,)
                ).fetchone()
        except psycopg.OperationalError as error:
            raise TombstoneJournalUnavailable(str(error)) from error
        return row is not None


def record_deletion(
    item_id: str, targets: list[DeletionTarget], journal: TombstoneJournal
) -> DeletionReceipt:
    """Run the sealed deletion saga, then tombstone the item in the
    journal ONLY once every target has independently confirmed it is
    gone. A saga that reports ``DELETION_INCOMPLETE`` never reaches the
    journal, so a still-partially-present item can never be mistaken
    for a genuinely deleted one by a later restore.
    """
    receipt = run_deletion_saga(item_id, targets)
    if receipt.status is DeletionStatus.DELETED:
        journal.record(item_id)
    return receipt


def restore_from_backup(
    item_id: str,
    targets: list[DeletionTarget],
    journal: TombstoneJournal,
) -> RestoreOutcome:
    """Reconcile the tombstone journal BEFORE ever writing backup
    content to any target. A tombstoned item is refused outright; a
    journal that cannot be reached is refused too (fail closed) -- no
    target is ever touched in either refusal case.
    """
    try:
        tombstoned = journal.is_tombstoned(item_id)
    except TombstoneJournalUnavailable:
        return RestoreOutcome(item_id, RestoreStatus.REFUSED_JOURNAL_UNAVAILABLE, ())
    if tombstoned:
        return RestoreOutcome(item_id, RestoreStatus.REFUSED_TOMBSTONED, ())
    confirmed: list[str] = []
    for target in targets:
        target.put(item_id)
        if target.contains(item_id):
            confirmed.append(target.name)
    return RestoreOutcome(item_id, RestoreStatus.RESTORED, tuple(confirmed))
