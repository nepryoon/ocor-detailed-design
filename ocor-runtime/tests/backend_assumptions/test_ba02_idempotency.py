from __future__ import annotations

import pytest

from ocor_runtime.c3_store import AtomicOutboxStore
from ocor_runtime.errors import ConcurrencyConflict

pytestmark = pytest.mark.backend_assumption


def test_ba02_identical_retry_replays_the_original_receipt(fixed_now):
    store = AtomicOutboxStore()
    kwargs = dict(
        aggregate_id="aggregate-1",
        document={"value": 1},
        expected_version=0,
        writer_id="ocor-core",
        event_type="created",
        idempotency_key="retry-key",
        occurred_at=fixed_now,
    )
    first = store.write(**kwargs)
    replay = store.write(**kwargs)
    assert replay.replayed
    assert replay.document == first.document
    assert replay.event == first.event


def test_ba02_idempotency_key_cannot_be_rebound(fixed_now):
    store = AtomicOutboxStore()
    store.write(
        "aggregate-1",
        {"value": 1},
        expected_version=0,
        writer_id="ocor-core",
        event_type="created",
        idempotency_key="same-key",
        occurred_at=fixed_now,
    )
    with pytest.raises(ConcurrencyConflict):
        store.write(
            "aggregate-1",
            {"value": 2},
            expected_version=1,
            writer_id="ocor-core",
            event_type="updated",
            idempotency_key="same-key",
            occurred_at=fixed_now,
        )

