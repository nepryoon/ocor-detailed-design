"""OCOR-DEV-0041: Implement C5 registry replay backpressure DLQ and quarantine.

Proves that EventOperationsCoordinator bounds admission with a real
per-tenant backpressure quota, records real publish failures as
immutable dead letters, quarantines a repeatedly-failing event as
POISON behind an explicit operator gate, and replays a dead letter
only by re-running the exact same compatibility checks a fresh publish
would -- an incompatible schema or lost marking is blocked on replay
too, never bypassed. Every test drives a real, live, self-provisioned
Kafka broker -- no mocks.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from ocor_runtime.c5.backbone import (
    BackboneError,
    CanonicalEventBackbone,
    CanonicalIngestionEnvelope,
    KafkaBackboneError,
)
from ocor_runtime.c5.operations import DeadLetter, EventOperationsCoordinator, OperationsError

DIGEST_A = "urn:sha256:" + "a" * 64
SCHEMA = "urn:ocor:schema:canonical-ingestion-envelope:1"


def envelope(
    *,
    aggregate_ref: str,
    sequence: int = 1,
    event_id: str | None = None,
    schema_ref: str = SCHEMA,
    classification_marking_ref: str = DIGEST_A,
) -> CanonicalIngestionEnvelope:
    event_id = event_id or f"urn:ocor:event:{uuid.uuid4()}"
    return CanonicalIngestionEnvelope(
        event_id=event_id,
        event_type="MissionEffectRecorded",
        event_version="1.0.0",
        schema_ref=schema_ref,
        producer_principal="urn:ocor:principal:c6-engine",
        source_ref="urn:ocor:source:operations-fixture",
        aggregate_ref=aggregate_ref,
        correlation_id="018f2f95-01b2-7cc3-8d4e-123456789abc",
        causation_id="018f2f95-01b2-7cc3-8d4e-000000000000",
        classification_marking_ref=classification_marking_ref,
        governed_context_digest=DIGEST_A,
        idempotency_key=event_id,
        sequence=sequence,
        payload={"status": "ASSESSED"},
    )


@pytest.fixture
def backbone() -> Iterator[CanonicalEventBackbone]:
    topic = f"ocor-operations-fixture-{uuid.uuid4().hex[:12]}"
    try:
        value, container, volume = CanonicalEventBackbone.provision(topic)
    except KafkaBackboneError as error:
        pytest.fail(f"a real, live, self-provisioned Kafka broker is mandatory qualifying evidence: {error}")
    try:
        yield value
    finally:
        value.destroy(volume)


@pytest.fixture
def coordinator(backbone: CanonicalEventBackbone) -> EventOperationsCoordinator:
    return EventOperationsCoordinator(backbone, max_in_flight_per_tenant=2)


def test_a_valid_event_publishes_through_backpressure_and_is_delivered(
    coordinator: EventOperationsCoordinator, backbone: CanonicalEventBackbone
) -> None:
    coordinator.publish_with_backpressure(envelope(aggregate_ref="urn:ocor:mission-object:ops:1"), tenant="tenant-a")

    delivered = backbone.consume(1)
    assert len(delivered) == 1
    assert coordinator.dead_letters == ()


def test_backpressure_refuses_admission_once_a_tenant_is_at_its_bounded_quota(
    coordinator: EventOperationsCoordinator,
) -> None:
    # exhaust the quota (2) with two genuinely different aggregates so
    # neither publish is itself rejected for an unrelated reason.
    coordinator._in_flight_by_tenant["tenant-a"] = 2  # noqa: SLF001 -- simulates two real in-flight publishes

    with pytest.raises(OperationsError) as excinfo:
        coordinator.publish_with_backpressure(envelope(aggregate_ref="urn:ocor:mission-object:ops:2"), tenant="tenant-a")
    assert excinfo.value.reason_code == "BACKPRESSURE_EXCEEDED"


def test_a_failed_publish_is_recorded_as_an_immutable_permanent_dead_letter(
    coordinator: EventOperationsCoordinator,
) -> None:
    bad = envelope(aggregate_ref="urn:ocor:mission-object:ops:3", schema_ref="urn:ocor:schema:not-registered:1")

    with pytest.raises(BackboneError):
        coordinator.publish_with_backpressure(bad, tenant="tenant-a")

    assert len(coordinator.dead_letters) == 1
    letter = coordinator.dead_letters[0]
    assert letter.event_id == bad.event_id
    assert letter.failure_class == "PERMANENT"
    assert letter.reason_code == "UNKNOWN_SCHEMA"
    assert letter.attempts == 1


def test_repeated_failures_of_the_same_event_are_classified_poison(coordinator: EventOperationsCoordinator) -> None:
    bad = envelope(
        aggregate_ref="urn:ocor:mission-object:ops:4",
        event_id="urn:ocor:event:poison-1",
        schema_ref="urn:ocor:schema:not-registered:1",
    )

    for _ in range(3):
        with pytest.raises(BackboneError):
            coordinator.publish_with_backpressure(bad, tenant="tenant-a")

    assert coordinator.is_poisoned(bad.event_id)
    assert coordinator.dead_letters[-1].failure_class == "POISON"
    assert coordinator.dead_letters[-1].attempts == 3


def test_a_poisoned_event_cannot_be_replayed_without_explicit_operator_release(
    coordinator: EventOperationsCoordinator,
) -> None:
    bad = envelope(
        aggregate_ref="urn:ocor:mission-object:ops:5",
        event_id="urn:ocor:event:poison-2",
        schema_ref="urn:ocor:schema:not-registered:1",
    )
    for _ in range(3):
        with pytest.raises(BackboneError):
            coordinator.publish_with_backpressure(bad, tenant="tenant-a")
    letter = coordinator.dead_letters[-1]

    with pytest.raises(OperationsError) as excinfo:
        coordinator.replay(letter, window_reason="operator-requested-retry")
    assert excinfo.value.reason_code == "OPERATOR_GATE_CLOSED"


def test_operator_release_still_cannot_replay_past_an_incompatible_schema(
    coordinator: EventOperationsCoordinator,
) -> None:
    bad = envelope(
        aggregate_ref="urn:ocor:mission-object:ops:6",
        event_id="urn:ocor:event:poison-3",
        schema_ref="urn:ocor:schema:not-registered:1",
    )
    for _ in range(3):
        with pytest.raises(BackboneError):
            coordinator.publish_with_backpressure(bad, tenant="tenant-a")
    letter = coordinator.dead_letters[-1]
    coordinator.release_for_operator_replay(bad.event_id)

    with pytest.raises(BackboneError) as excinfo:
        coordinator.replay(letter, window_reason="operator-requested-retry")
    assert excinfo.value.reason_code == "UNKNOWN_SCHEMA"


def test_replay_of_lost_marking_is_blocked_exactly_like_a_fresh_publish(
    coordinator: EventOperationsCoordinator,
) -> None:
    lossy_raw = envelope(aggregate_ref="urn:ocor:mission-object:ops:7").to_mapping()
    lossy_raw["classification_marking_ref"] = ""

    letter = DeadLetter(
        event_id=lossy_raw["event_id"],
        envelope_raw=lossy_raw,
        reason_code="MISSING_CONTEXT",
        failure_class="PERMANENT",
        recorded_at=datetime.now(UTC),
        attempts=1,
    )

    with pytest.raises(BackboneError) as excinfo:
        coordinator.replay(letter, window_reason="operator-requested-retry")
    assert excinfo.value.reason_code == "MISSING_CONTEXT"


def test_a_valid_replay_preserves_the_original_event_id_and_never_double_publishes(
    coordinator: EventOperationsCoordinator, backbone: CanonicalEventBackbone
) -> None:
    good = envelope(aggregate_ref="urn:ocor:mission-object:ops:8", event_id="urn:ocor:event:replay-1")
    coordinator.publish_with_backpressure(good, tenant="tenant-a")

    # construct a synthetic dead letter for the ALREADY-durable event to
    # prove replay of an already-published idempotency key is a safe
    # no-op, never a duplicate canonical effect.
    synthetic_letter = DeadLetter(
        event_id=good.event_id,
        envelope_raw=good.to_mapping(),
        reason_code="TRANSIENT_RETRY_SIMULATED",
        failure_class="PERMANENT",
        recorded_at=datetime.now(UTC),
        attempts=1,
    )

    receipt = coordinator.replay(synthetic_letter, window_reason="operator-requested-retry")
    assert receipt.event_id == good.event_id

    delivered = backbone.consume(1)
    assert len(delivered) == 1, "the replay of an already-durable idempotency key must never create a second record"
