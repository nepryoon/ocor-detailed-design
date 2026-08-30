from __future__ import annotations

from dataclasses import replace

import pytest

from ocor_runtime.c3_store import AtomicOutboxStore
from ocor_runtime.c7_emission import EmissionFence
from ocor_runtime.errors import EmissionBlocked

pytestmark = pytest.mark.backend_assumption


def _two_events(fixed_now):
    store = AtomicOutboxStore()
    first = store.write(
        "aggregate-1",
        {"value": 1},
        expected_version=0,
        writer_id="ocor-core",
        event_type="created",
        idempotency_key="first",
        occurred_at=fixed_now,
    ).event
    second = store.write(
        "aggregate-1",
        {"value": 2},
        expected_version=1,
        writer_id="ocor-core",
        event_type="updated",
        idempotency_key="second",
        occurred_at=fixed_now,
    ).event
    return store, first, second


def test_ba07_uncommitted_and_tampered_events_never_cross_the_fence(fixed_now):
    _, first, _ = _two_events(fixed_now)
    with pytest.raises(EmissionBlocked):
        EmissionFence().emit(
            replace(first, committed=False), lambda event: None, at=fixed_now
        )
    with pytest.raises(EmissionBlocked):
        EmissionFence().emit(
            replace(first, payload={"value": 999}), lambda event: None, at=fixed_now
        )


def test_ba07_aggregate_events_cross_in_version_order(fixed_now):
    store, first, second = _two_events(fixed_now)
    delivered = []
    fence = EmissionFence(store=store)
    fence.register(first)
    fence.register(second)
    with pytest.raises(EmissionBlocked):
        fence.emit(second, delivered.append, at=fixed_now)
    fence.emit(first, delivered.append, at=fixed_now)
    fence.emit(second, delivered.append, at=fixed_now)
    assert [event.aggregate_version for event in delivered] == [1, 2]


def test_ba07_sink_failure_leaves_event_pending_and_retry_is_deduplicated(fixed_now):
    store, first, _ = _two_events(fixed_now)
    fence = EmissionFence(store=store)

    def failing_sink(event):
        raise RuntimeError("sink unavailable")

    with pytest.raises(RuntimeError):
        fence.emit(first, failing_sink, at=fixed_now)
    assert store.get_event(first.event_id).emitted_at is None
    delivered = []
    receipt = fence.emit(first, delivered.append, at=fixed_now)
    duplicate = fence.emit(first, delivered.append, at=fixed_now)
    assert len(delivered) == 1
    assert not receipt.deduplicated
    assert duplicate.deduplicated

