from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from ocor_runtime.errors import ConcurrencyConflict
from ocor_runtime.canonical import canonical_sha256
from ocor_runtime.fallback.postgres_outbox import (
    OutboxReconciler,
    PostgreSQLTransactionalOutbox,
)

pytestmark = pytest.mark.backend_assumption


@dataclass
class FakeCursor:
    replay: tuple | None = None
    version: int | None = None
    reconciliation_rows: list[tuple] = field(default_factory=list)
    operations: list[tuple[str, tuple]] = field(default_factory=list)
    rowcount: int = 0
    _next: object = None
    closed: bool = False

    def execute(self, operation, parameters=()):
        normalized = " ".join(operation.split())
        self.operations.append((normalized, parameters))
        self.rowcount = 0
        if normalized.startswith("SELECT event_id"):
            self._next = self.replay
        elif normalized.startswith("SELECT version"):
            self._next = None if self.version is None else (self.version,)
        elif normalized.startswith("SELECT q.transaction_id"):
            self._next = list(self.reconciliation_rows)
        elif normalized.startswith("INSERT INTO ocor_outbox"):
            self.rowcount = 1

    def fetchone(self):
        return self._next

    def fetchall(self):
        return list(self._next or [])

    def close(self):
        self.closed = True


@dataclass
class FakeConnection:
    fake_cursor: FakeCursor
    commits: int = 0
    rollbacks: int = 0

    def cursor(self):
        return self.fake_cursor

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def test_ba01_postgresql_fallback_initializes_and_commits_aggregate_outbox_and_intent(fixed_now):
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    adapter = PostgreSQLTransactionalOutbox(lambda: connection)
    adapter.initialize()
    receipt = adapter.write(
        "aggregate-1",
        {"value": 1},
        expected_version=0,
        writer_id="ocor-core",
        event_type="created",
        payload={"value": 1},
        idempotency_key="fallback-1",
        occurred_at=fixed_now,
    )
    sql = "\n".join(operation for operation, _ in cursor.operations)
    assert "INSERT INTO ocor_aggregates" in sql
    assert "INSERT INTO ocor_outbox" in sql
    assert "INSERT INTO ocor_reconciliation_queue" in sql
    assert receipt.aggregate_version == 1
    assert not receipt.replayed
    assert connection.commits == 2
    assert connection.rollbacks == 0
    assert cursor.closed


def test_ba01_postgresql_fallback_replays_idempotency_receipt(fixed_now):
    request_digest = canonical_sha256(
        {
            "aggregateId": "aggregate-1",
            "document": {"value": 4},
            "eventType": "updated",
            "payload": {"value": 4},
        }
    )
    cursor = FakeCursor(
        replay=("event-1", "transaction-1", "aggregate-1", 4, request_digest)
    )
    connection = FakeConnection(cursor)
    receipt = PostgreSQLTransactionalOutbox(lambda: connection).write(
        "aggregate-1",
        {"value": 4},
        expected_version=3,
        writer_id="ocor-core",
        event_type="updated",
        payload={"value": 4},
        idempotency_key="fallback-replay",
        occurred_at=fixed_now,
    )
    assert receipt.replayed
    assert receipt.event_id == "event-1"
    assert receipt.aggregate_version == 4
    assert connection.commits == 1


def test_ba01_postgresql_fallback_rolls_back_stale_version(fixed_now):
    cursor = FakeCursor(version=7)
    connection = FakeConnection(cursor)
    with pytest.raises(ConcurrencyConflict):
        PostgreSQLTransactionalOutbox(lambda: connection).write(
            "aggregate-1",
            {"value": 8},
            expected_version=6,
            writer_id="ocor-core",
            event_type="updated",
            payload={"value": 8},
            idempotency_key="fallback-stale",
            occurred_at=fixed_now,
        )
    assert connection.rollbacks == 1
    assert cursor.closed


def test_ba01_reconciler_repairs_missing_event_from_durable_intent(fixed_now):
    cursor = FakeCursor(
        reconciliation_rows=[
            (
                "transaction-1",
                "aggregate-1",
                1,
                "event-1",
                {"value": 1},
                fixed_now,
            )
        ]
    )
    connection = FakeConnection(cursor)
    repaired = OutboxReconciler(lambda: connection).reconcile_once(limit=10)
    assert repaired == 1
    assert connection.commits == 1
    assert any(
        operation.startswith("UPDATE ocor_reconciliation_queue")
        for operation, _ in cursor.operations
    )


def test_ba01_reconciler_rejects_nonpositive_batch_limit():
    with pytest.raises(ValueError):
        OutboxReconciler(lambda: None).reconcile_once(limit=0)
