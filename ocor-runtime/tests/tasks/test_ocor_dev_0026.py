"""OCOR-DEV-0026: SPIKE restore without resurrection.

Proves that restoring content from a backup or replay path reconciles
a durable tombstone journal BEFORE ever touching a target, so a
genuinely deleted item never reappears -- and that an unreachable
journal is refused exactly like a tombstoned item, never silently
treated as "safe to restore". Every backend is real (PostgreSQL,
TypeDB, Qdrant); no mocks for qualifying evidence. Reuses
spikes.memory_deletion.saga (OCOR-DEV-0025) completely unmodified.
"""

from __future__ import annotations

import os
import uuid

import pytest
from spikes.memory_deletion.saga import (
    DeletionStatus,
    PostgresMetadataTarget,
    QdrantCacheTarget,
    TypeDBContentTarget,
)
from spikes.restore_no_resurrection.journal import (
    RestoreStatus,
    TombstoneJournal,
    record_deletion,
    restore_from_backup,
)
from spikes.vector_partition.oracle import QdrantHarness


@pytest.fixture(scope="session")
def postgres_dsn() -> str:
    dsn = os.environ.get("OCOR_LIVE_POSTGRES_DSN")
    if not dsn:
        pytest.fail("OCOR_LIVE_POSTGRES_DSN is mandatory qualifying evidence")
    return dsn


@pytest.fixture
def journal(postgres_dsn: str) -> TombstoneJournal:
    instance = TombstoneJournal(postgres_dsn)
    instance.ensure_schema()
    return instance


@pytest.fixture
def campaign(postgres_dsn: str):
    qdrant = QdrantHarness.provision()
    collection = f"ocor_restore_{uuid.uuid4().hex[:12]}"
    metadata = PostgresMetadataTarget(postgres_dsn)
    content = TypeDBContentTarget()
    cache = QdrantCacheTarget(qdrant, collection)
    try:
        yield [metadata, content, cache]
    finally:
        qdrant.destroy()


def test_restore_of_a_never_deleted_item_succeeds_across_all_real_backends(campaign, journal):
    targets = campaign
    item_id = f"urn:ocor:item:{uuid.uuid4()}"

    outcome = restore_from_backup(item_id, targets, journal)

    assert outcome.status is RestoreStatus.RESTORED
    assert set(outcome.confirmed) == {"metadata-postgres", "content-typedb", "cache-qdrant"}
    assert all(target.contains(item_id) for target in targets)


def test_restore_of_a_tombstoned_item_is_refused_and_content_never_reappears(campaign, journal):
    targets = campaign
    item_id = f"urn:ocor:item:{uuid.uuid4()}"
    for target in targets:
        target.put(item_id)

    receipt = record_deletion(item_id, targets, journal)
    assert receipt.status is DeletionStatus.DELETED
    assert journal.is_tombstoned(item_id)

    outcome = restore_from_backup(item_id, targets, journal)

    assert outcome.status is RestoreStatus.REFUSED_TOMBSTONED
    assert outcome.confirmed == ()
    assert not any(target.contains(item_id) for target in targets)


def test_record_deletion_only_tombstones_the_journal_when_every_target_confirms_deletion(
    postgres_dsn: str, journal: TombstoneJournal
):
    metadata = PostgresMetadataTarget(postgres_dsn)
    item_id = f"urn:ocor:item:{uuid.uuid4()}"
    metadata.put(item_id)

    class LyingTarget:
        """Claims tombstone success but the item remains findable --
        the saga's own re-check (not this class's honesty) is what the
        journal-write decision must depend on."""

        name = "lying-target"

        def tombstone(self, item_id: str) -> None:
            return None

        def contains(self, item_id: str) -> bool:
            return True

    receipt = record_deletion(item_id, [metadata, LyingTarget()], journal)

    assert receipt.status is DeletionStatus.DELETION_INCOMPLETE
    assert not journal.is_tombstoned(item_id), (
        "a saga that did not fully succeed must never tombstone the journal, "
        "or a later restore would wrongly refuse a still-partially-present item"
    )


def test_restore_reconciles_the_journal_before_touching_any_target(journal: TombstoneJournal):
    item_id = f"urn:ocor:item:{uuid.uuid4()}"
    journal.record(item_id)
    calls: list[str] = []

    class SpyTarget:
        name = "spy-target"

        def put(self, item_id: str) -> None:
            calls.append("put")

        def contains(self, item_id: str) -> bool:
            calls.append("contains")
            return True

        def tombstone(self, item_id: str) -> None:
            calls.append("tombstone")

    outcome = restore_from_backup(item_id, [SpyTarget()], journal)

    assert outcome.status is RestoreStatus.REFUSED_TOMBSTONED
    assert calls == [], "the journal check must happen before any target is ever touched"


def test_journal_unreachable_fails_closed_and_never_resurrects(campaign):
    targets = campaign
    item_id = f"urn:ocor:item:{uuid.uuid4()}"
    # A genuinely closed local port: a real TCP connection refusal from
    # the OS, not a simulated/mocked exception.
    unreachable_journal = TombstoneJournal("postgresql://ocor:x@127.0.0.1:1/ocor")

    outcome = restore_from_backup(item_id, targets, unreachable_journal)

    assert outcome.status is RestoreStatus.REFUSED_JOURNAL_UNAVAILABLE
    assert outcome.confirmed == ()
    assert not any(target.contains(item_id) for target in targets)


def test_restoring_a_different_never_tombstoned_item_is_unaffected_by_an_unrelated_tombstone(
    campaign, journal
):
    targets = campaign
    tombstoned_item = f"urn:ocor:item:{uuid.uuid4()}"
    other_item = f"urn:ocor:item:{uuid.uuid4()}"
    for target in targets:
        target.put(tombstoned_item)
    record_deletion(tombstoned_item, targets, journal)

    outcome = restore_from_backup(other_item, targets, journal)

    assert outcome.status is RestoreStatus.RESTORED
    assert all(target.contains(other_item) for target in targets)
    assert not any(target.contains(tombstoned_item) for target in targets)
