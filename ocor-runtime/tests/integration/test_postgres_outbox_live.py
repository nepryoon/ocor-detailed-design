"""Live PostgreSQL 16 evidence for the ratified transactional outbox."""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

import psycopg
import pytest

from ocor_runtime.errors import ConcurrencyConflict
from ocor_runtime.fallback.postgres_outbox import OutboxReconciler, PostgreSQLTransactionalOutbox

DSN = os.environ.get("OCOR_LIVE_POSTGRES_DSN")


def connection():
    if not DSN:
        pytest.skip("OCOR_LIVE_POSTGRES_DSN is required for live backend evidence")
    return psycopg.connect(DSN)


@pytest.fixture(autouse=True)
def clean_tables():
    conn = connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("TRUNCATE ocor_reconciliation_queue, ocor_outbox, ocor_aggregates CASCADE")
        conn.commit()
    except psycopg.errors.UndefinedTable:
        conn.rollback()
    finally:
        conn.close()
    PostgreSQLTransactionalOutbox(connection).initialize()
    yield


def write(adapter: PostgreSQLTransactionalOutbox, aggregate: str, expected: int, key: str, value: int):
    return adapter.write(
        aggregate,
        {"value": value},
        expected_version=expected,
        writer_id="ocor-core",
        event_type="updated",
        payload={"value": value},
        idempotency_key=key,
        occurred_at=datetime.now(timezone.utc),
    )


def counts_and_version(aggregate: str) -> tuple[int, int, int, int]:
    conn = connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT version FROM ocor_aggregates WHERE aggregate_id = %s", (aggregate,))
            row = cursor.fetchone()
            cursor.execute("SELECT COUNT(*) FROM ocor_outbox WHERE aggregate_id = %s", (aggregate,))
            outbox = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM ocor_reconciliation_queue WHERE aggregate_id = %s", (aggregate,))
            queue = cursor.fetchone()[0]
        return (int(row[0]) if row else 0, 1 if row else 0, int(outbox), int(queue))
    finally:
        conn.close()


def test_live_pg_atomic_commit_contains_state_outbox_and_reconciliation_intent():
    receipt = write(PostgreSQLTransactionalOutbox(connection), "live-atomic", 0, "atomic-1", 1)
    assert receipt.aggregate_version == 1
    assert counts_and_version("live-atomic") == (1, 1, 1, 1)


def test_live_pg_idempotent_replay_preserves_single_event_and_receipt():
    adapter = PostgreSQLTransactionalOutbox(connection)
    first = write(adapter, "live-replay", 0, "replay-1", 1)
    replay = write(adapter, "live-replay", 0, "replay-1", 1)
    assert replay.replayed is True
    assert replay.event_id == first.event_id
    assert replay.transaction_id == first.transaction_id
    assert counts_and_version("live-replay") == (1, 1, 1, 1)


class FailingCursor:
    def __init__(self, delegate: Any) -> None:
        self.delegate = delegate

    @property
    def rowcount(self):
        return self.delegate.rowcount

    def execute(self, operation: str, parameters=()):
        if "INSERT INTO ocor_outbox" in operation:
            raise RuntimeError("injected post-state/pre-outbox failure")
        return self.delegate.execute(operation, parameters)

    def fetchone(self):
        return self.delegate.fetchone()

    def fetchall(self):
        return self.delegate.fetchall()

    def close(self):
        self.delegate.close()


class FailingConnection:
    def __init__(self, delegate: Any) -> None:
        self.delegate = delegate

    def cursor(self):
        return FailingCursor(self.delegate.cursor())

    def commit(self):
        return self.delegate.commit()

    def rollback(self):
        return self.delegate.rollback()


def test_live_pg_injected_outbox_failure_rolls_back_aggregate_and_intent():
    raw = connection()
    adapter = PostgreSQLTransactionalOutbox(lambda: FailingConnection(raw))
    with pytest.raises(RuntimeError, match="injected"):
        write(adapter, "live-rollback", 0, "rollback-1", 1)
    raw.close()
    assert counts_and_version("live-rollback") == (0, 0, 0, 0)


def test_live_pg_for_update_serializes_competing_existing_aggregate_writers():
    write(PostgreSQLTransactionalOutbox(connection), "live-concurrency", 0, "base", 0)

    def competing(key: str, value: int):
        return write(PostgreSQLTransactionalOutbox(connection), "live-concurrency", 1, key, value)

    outcomes: list[object] = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(competing, "writer-a", 1), pool.submit(competing, "writer-b", 2)]
        for future in futures:
            try:
                outcomes.append(future.result(timeout=10))
            except Exception as exc:
                outcomes.append(exc)

    assert sum(not isinstance(item, Exception) for item in outcomes) == 1
    assert sum(isinstance(item, ConcurrencyConflict) for item in outcomes) == 1
    assert counts_and_version("live-concurrency") == (2, 1, 2, 2)


def test_live_pg_reconciler_repairs_deleted_outbox_from_durable_intent():
    receipt = write(PostgreSQLTransactionalOutbox(connection), "live-reconcile", 0, "repair-1", 7)
    conn = connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM ocor_outbox WHERE event_id = %s", (receipt.event_id,))
        conn.commit()
    finally:
        conn.close()

    repaired = OutboxReconciler(connection).reconcile_once(limit=10)
    assert repaired == 1
    assert counts_and_version("live-reconcile") == (1, 1, 1, 1)
