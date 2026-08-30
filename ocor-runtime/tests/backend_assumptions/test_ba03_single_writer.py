from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from ocor_runtime.c3_store import AtomicOutboxStore
from ocor_runtime.errors import ConcurrencyConflict, SingleWriterViolation

pytestmark = pytest.mark.backend_assumption


def test_ba03_non_authoritative_writer_is_rejected(fixed_now):
    store = AtomicOutboxStore(authoritative_writer="leader-1")
    with pytest.raises(SingleWriterViolation):
        store.write(
            "aggregate-1",
            {"value": 1},
            expected_version=0,
            writer_id="replica-1",
            event_type="created",
            idempotency_key="unauthorized",
            occurred_at=fixed_now,
        )
    assert store.snapshot_counts() == (0, 0)


def test_ba03_optimistic_version_allows_only_one_concurrent_update(fixed_now):
    store = AtomicOutboxStore()
    store.write(
        "aggregate-1",
        {"value": 0},
        expected_version=0,
        writer_id="ocor-core",
        event_type="created",
        idempotency_key="create",
        occurred_at=fixed_now,
    )

    def update(value: int) -> str:
        try:
            store.write(
                "aggregate-1",
                {"value": value},
                expected_version=1,
                writer_id="ocor-core",
                event_type="updated",
                idempotency_key=f"update-{value}",
                occurred_at=fixed_now,
            )
            return "committed"
        except ConcurrencyConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(update, (1, 2)))
    assert sorted(outcomes) == ["committed", "conflict"]
    assert store.get("aggregate-1").version == 2
    assert store.snapshot_counts() == (1, 2)

