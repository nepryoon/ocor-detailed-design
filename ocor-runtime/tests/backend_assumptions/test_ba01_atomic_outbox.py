from __future__ import annotations

from dataclasses import replace

import pytest

from ocor_runtime.c3_store import AtomicOutboxStore, CrashWindow
from ocor_runtime.errors import CrashInjected
from ocor_runtime.fallback.postgres_outbox import (
    POSTGRESQL_DDL,
    OutboxReconciler,
    PostgreSQLTransactionalOutbox,
    select_atomic_backend,
)

pytestmark = pytest.mark.backend_assumption


@pytest.mark.parametrize(
    "window",
    [
        CrashWindow.BEFORE_TRANSACTION,
        CrashWindow.AFTER_TRANSACTION_BEGIN,
        CrashWindow.AFTER_AGGREGATE_STAGE,
        CrashWindow.AFTER_OUTBOX_STAGE,
    ],
)
def test_ba01_precommit_crash_windows_publish_neither_document_nor_event(window, fixed_now):
    store = AtomicOutboxStore()
    with pytest.raises(CrashInjected) as raised:
        store.write(
            "action-1",
            {"state": "DRAFT"},
            expected_version=0,
            writer_id="ocor-core",
            event_type="action.created",
            idempotency_key=f"BA01-{window.value}",
            occurred_at=fixed_now,
            crash_window=window,
        )
    assert raised.value.committed is False
    assert store.snapshot_counts() == (0, 0)
    assert store.verify_atomicity()


def test_ba01_postcommit_preack_crash_publishes_both_and_retry_is_idempotent(fixed_now):
    store = AtomicOutboxStore()
    arguments = dict(
        aggregate_id="action-1",
        document={"state": "DRAFT"},
        expected_version=0,
        writer_id="ocor-core",
        event_type="action.created",
        idempotency_key="BA01-postcommit",
        occurred_at=fixed_now,
    )
    with pytest.raises(CrashInjected) as raised:
        store.write(**arguments, crash_window=CrashWindow.AFTER_COMMIT_BEFORE_ACK)
    assert raised.value.committed is True
    assert store.snapshot_counts() == (1, 1)
    assert store.verify_atomicity()

    replay = store.write(**arguments)
    assert replay.replayed is True
    assert store.snapshot_counts() == (1, 1)


def test_ba01_ratified_postgresql_fallback_is_selectable_and_has_reconciler():
    class NonAtomicBackend:
        supports_atomic_multi_document_writes = False

    factory = lambda: None  # connection is acquired lazily by the scaffold
    selected = select_atomic_backend(
        NonAtomicBackend(), postgres_connection_factory=factory
    )
    assert isinstance(selected, PostgreSQLTransactionalOutbox)
    assert OutboxReconciler(factory)
    assert "CREATE TABLE IF NOT EXISTS ocor_outbox" in POSTGRESQL_DDL
    assert "ocor_reconciliation_queue" in POSTGRESQL_DDL
    assert "UNIQUE (aggregate_id, aggregate_version)" in POSTGRESQL_DDL


def test_ba01_atomic_backend_is_not_replaced():
    store = AtomicOutboxStore()
    assert select_atomic_backend(store) is store

