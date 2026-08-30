from __future__ import annotations

from datetime import timedelta

import pytest

from ocor_runtime.c1_compiler import SemanticCompiler
from ocor_runtime.c3_store import AtomicOutboxStore, CrashWindow
from ocor_runtime.c4_marking import MarkingEngine, MarkingSchemeDefinition, MarkingSet
from ocor_runtime.errors import (
    ConcurrencyConflict,
    CrashInjected,
    SingleWriterViolation,
)

pytestmark = pytest.mark.acceptance


def _write(store, fixed_now, **overrides):
    arguments = {
        "aggregate_id": "aggregate-1",
        "document": {"value": 1},
        "expected_version": 0,
        "writer_id": "ocor-core",
        "event_type": "created",
        "idempotency_key": "create-1",
        "occurred_at": fixed_now,
    }
    arguments.update(overrides)
    return store.write(**arguments)


def test_ev_011_single_writer_boundary_rejects_replica_mutation(fixed_now):
    store = AtomicOutboxStore(authoritative_writer="leader")
    with pytest.raises(SingleWriterViolation):
        _write(store, fixed_now, writer_id="replica")
    assert store.snapshot_counts() == (0, 0)


def test_ev_012_optimistic_version_precondition_prevents_lost_update(fixed_now):
    store = AtomicOutboxStore()
    _write(store, fixed_now)
    with pytest.raises(ConcurrencyConflict):
        _write(
            store,
            fixed_now,
            document={"value": 2},
            idempotency_key="stale",
            expected_version=0,
        )
    assert store.get("aggregate-1").document["value"] == 1


def test_ev_013_all_five_crash_windows_preserve_atomic_visibility(fixed_now):
    for window in CrashWindow:
        store = AtomicOutboxStore()
        with pytest.raises(CrashInjected) as raised:
            _write(store, fixed_now, crash_window=window)
        expected = (1, 1) if raised.value.committed else (0, 0)
        assert store.snapshot_counts() == expected
        assert store.verify_atomicity()


def test_ev_014_idempotent_retry_cannot_duplicate_an_outbox_event(fixed_now):
    store = AtomicOutboxStore()
    first = _write(store, fixed_now)
    replay = _write(store, fixed_now)
    assert replay.replayed
    assert replay.event.event_id == first.event.event_id
    assert store.snapshot_counts() == (1, 1)


def test_ev_015_outbox_events_are_committed_integrity_bound_and_versioned(fixed_now):
    store = AtomicOutboxStore()
    first = _write(store, fixed_now)
    second = _write(
        store,
        fixed_now + timedelta(seconds=1),
        document={"value": 2},
        expected_version=1,
        event_type="updated",
        idempotency_key="update-2",
    )
    assert [event.aggregate_version for event in store.outbox()] == [1, 2]
    assert first.event.committed and second.event.committed
    assert all(event.verify_integrity() for event in store.outbox())


def test_ev_016_marking_total_order_join_is_the_least_upper_bound():
    scheme = MarkingSchemeDefinition(
        "classification", ["PUBLIC", "INTERNAL", "SECRET"]
    )
    assert scheme.join("PUBLIC", "INTERNAL") == "INTERNAL"
    assert scheme.leq("PUBLIC", "INTERNAL")
    assert not scheme.leq("SECRET", "INTERNAL")


def test_ev_017_marking_partial_lattice_join_combines_compartments():
    scheme = MarkingSchemeDefinition(
        "compartment",
        labels=["NONE", "A", "B", "AB"],
        relations=[("NONE", "A"), ("NONE", "B"), ("A", "AB"), ("B", "AB")],
    )
    assert scheme.join("A", "B") == "AB"
    assert scheme.dominates("AB", "A")


def test_ev_018_multi_scheme_join_is_monotonic_and_clearance_is_fail_closed():
    engine = MarkingEngine(
        [
            MarkingSchemeDefinition("classification", ["PUBLIC", "SECRET"]),
            MarkingSchemeDefinition("release", ["OPEN", "RESTRICTED"]),
        ]
    )
    combined = engine.join(
        MarkingSet({"classification": "SECRET"}),
        MarkingSet({"release": "RESTRICTED"}),
    )
    assert combined.values == {
        "classification": "SECRET",
        "release": "RESTRICTED",
    }
    insufficient = MarkingSet({"classification": "SECRET"})
    assert not engine.is_authorized(combined, insufficient)
    assert engine.disclose({"secret": 1}, combined, insufficient).payload is None


def test_ev_019_marking_non_interference_preserves_semantic_identity():
    compiler = SemanticCompiler()
    public = {
        "schemaVersion": "1.2",
        "kind": "Identity",
        "payload": {"name": "Alice"},
        "markings": {"classification": "PUBLIC"},
    }
    secret = {**public, "markings": {"classification": "SECRET"}}
    public_artifact = compiler.compile(public)
    secret_artifact = compiler.compile(secret)
    assert public_artifact.semantic_digest == secret_artifact.semantic_digest
    assert public_artifact.envelope_digest != secret_artifact.envelope_digest

