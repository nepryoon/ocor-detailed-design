from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

import pytest

from ocor_runtime.c3_store import AtomicOutboxStore
from ocor_runtime.c4_marking import MarkingEngine, MarkingSchemeDefinition
from ocor_runtime.c6_capabilities import CapabilityAuthority
from ocor_runtime.c7_emission import EmissionFence
from ocor_runtime.errors import EmissionBlocked


def _event(fixed_now):
    store = AtomicOutboxStore()
    event = store.write(
        "aggregate",
        {"value": 1},
        expected_version=0,
        writer_id="ocor-core",
        event_type="created",
        idempotency_key="runtime-c7",
        occurred_at=fixed_now,
    ).event
    return store, event


def test_store_bound_fence_drains_pending_events_and_exposes_receipts(fixed_now):
    store, first = _event(fixed_now)
    second = store.write(
        "aggregate",
        {"value": 2},
        expected_version=1,
        writer_id="ocor-core",
        event_type="updated",
        idempotency_key="runtime-c7-2",
        occurred_at=fixed_now + timedelta(seconds=1),
    ).event
    delivered = []
    fence = EmissionFence(store=store)
    receipts = fence.drain(delivered.append, at=second.occurred_at)
    assert [event.event_id for event in delivered] == [first.event_id, second.event_id]
    assert tuple(fence.receipt(receipt.event_id) for receipt in receipts) == receipts
    assert store.outbox() == ()


def test_fence_rejects_bad_configuration_collision_and_premature_delivery(fixed_now):
    with pytest.raises(ValueError):
        EmissionFence(require_capability=True)
    _, event = _event(fixed_now)
    fence = EmissionFence()
    fence.register(event)
    with pytest.raises(EmissionBlocked):
        fence.register(replace(event, event_type="different"))
    with pytest.raises(EmissionBlocked):
        fence.emit(
            event,
            lambda item: None,
            at=fixed_now - timedelta(microseconds=1),
        )
    store, durable = _event(fixed_now)
    delivered = []
    with pytest.raises(EmissionBlocked):
        EmissionFence(store=store).emit(
            replace(durable, event_id="forged-event"),
            delivered.append,
            at=fixed_now,
        )
    assert delivered == []


def test_store_bound_fence_discovers_unregistered_earlier_events(fixed_now):
    store, first = _event(fixed_now)
    second = store.write(
        "aggregate",
        {"value": 2},
        expected_version=1,
        writer_id="ocor-core",
        event_type="updated",
        idempotency_key="runtime-c7-unregistered",
        occurred_at=fixed_now + timedelta(seconds=1),
    ).event
    with pytest.raises(EmissionBlocked):
        EmissionFence(store=store).emit(
            second, lambda item: None, at=second.occurred_at
        )
    assert store.get_event(first.event_id).emitted_at is None


def test_previously_emitted_durable_event_is_not_redelivered_after_fence_restart(fixed_now):
    store, event = _event(fixed_now)
    emitted = store.mark_emitted(event.event_id, fixed_now)
    delivered = []
    fence = EmissionFence(store=store)
    fence.register(emitted)
    receipt = fence.emit(emitted, delivered.append, at=fixed_now)
    assert receipt.deduplicated
    assert delivered == []


def test_fence_fails_closed_when_required_security_context_is_missing(fixed_now):
    store, event = _event(fixed_now)
    authority = CapabilityAuthority()
    capability_fence = EmissionFence(
        store=store,
        capability_authority=authority,
        require_capability=True,
    )
    with pytest.raises(EmissionBlocked):
        capability_fence.emit(event, lambda item: None, at=fixed_now)

    engine = MarkingEngine(
        [MarkingSchemeDefinition("classification", ["PUBLIC", "SECRET"])]
    )
    marking_fence = EmissionFence(store=store, marking_engine=engine)
    with pytest.raises(EmissionBlocked):
        marking_fence.emit(event, lambda item: None, at=fixed_now)
