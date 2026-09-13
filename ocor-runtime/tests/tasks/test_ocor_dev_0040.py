"""OCOR-DEV-0040: Implement C5 canonical event backbone.

Proves that schema-bound events published through CanonicalEventBackbone
preserve partition order, correlation, causation, markings and
idempotency on a real, live, self-provisioned Kafka broker, and that an
unknown schema, missing governed context, or an out-of-order aggregate
effect is quarantined rather than published. Every test drives a real
broker -- no mocks. No CI workflow provisions a shared Kafka service, so
this task self-provisions its own isolated broker per test, the same
real configuration OCOR-DEV-0019's spike already proved.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from ocor_runtime.c5.backbone import (
    BackboneError,
    CanonicalEventBackbone,
    CanonicalIngestionEnvelope,
    KafkaBackboneError,
)

DIGEST_A = "urn:sha256:" + "a" * 64
SCHEMA = "urn:ocor:schema:canonical-ingestion-envelope:1"


def envelope(
    *,
    aggregate_ref: str,
    sequence: int,
    event_id: str | None = None,
    idempotency_key: str | None = None,
    schema_ref: str = SCHEMA,
) -> CanonicalIngestionEnvelope:
    event_id = event_id or f"urn:ocor:event:{uuid.uuid4()}"
    idempotency_key = idempotency_key or event_id
    return CanonicalIngestionEnvelope(
        event_id=event_id,
        event_type="MissionEffectRecorded",
        event_version="1.0.0",
        schema_ref=schema_ref,
        producer_principal="urn:ocor:principal:c6-engine",
        source_ref="urn:ocor:source:backbone-fixture",
        aggregate_ref=aggregate_ref,
        correlation_id="018f2f95-01b2-7cc3-8d4e-123456789abc",
        causation_id="018f2f95-01b2-7cc3-8d4e-000000000000",
        classification_marking_ref=DIGEST_A,
        governed_context_digest=DIGEST_A,
        idempotency_key=idempotency_key,
        sequence=sequence,
        payload={"status": "ASSESSED"},
    )


@pytest.fixture
def backbone() -> Iterator[CanonicalEventBackbone]:
    topic = f"ocor-backbone-fixture-{uuid.uuid4().hex[:12]}"
    try:
        value, container, volume = CanonicalEventBackbone.provision(topic)
    except KafkaBackboneError as error:
        pytest.fail(f"a real, live, self-provisioned Kafka broker is mandatory qualifying evidence: {error}")
    try:
        yield value
    finally:
        value.destroy(volume)


def test_a_registered_schema_event_publishes_and_is_consumed_preserving_all_fields(
    backbone: CanonicalEventBackbone,
) -> None:
    sent = envelope(aggregate_ref="urn:ocor:mission-object:backbone:1", sequence=1)
    backbone.publish(sent)

    delivered = backbone.consume(1)
    assert len(delivered) == 1
    received = delivered[0].envelope
    assert received.event_id == sent.event_id
    assert received.correlation_id == sent.correlation_id
    assert received.causation_id == sent.causation_id
    assert received.classification_marking_ref == sent.classification_marking_ref
    assert received.idempotency_key == sent.idempotency_key


def test_partition_order_is_preserved_for_a_single_aggregate(backbone: CanonicalEventBackbone) -> None:
    aggregate_ref = "urn:ocor:mission-object:backbone:2"
    for sequence in range(1, 6):
        backbone.publish(envelope(aggregate_ref=aggregate_ref, sequence=sequence))

    delivered = backbone.consume(5)
    partitions = {record.partition for record in delivered}
    assert len(partitions) == 1, "every event for one aggregate must land in the identical real Kafka partition"
    sequences = [record.envelope.sequence for record in delivered]
    assert sequences == sorted(sequences), "within one partition, real Kafka delivery order matches publish order"


def test_an_unknown_schema_is_quarantined_and_never_published(backbone: CanonicalEventBackbone) -> None:
    bad = envelope(
        aggregate_ref="urn:ocor:mission-object:backbone:3", sequence=1, schema_ref="urn:ocor:schema:not-registered:1"
    )
    with pytest.raises(BackboneError) as excinfo:
        backbone.publish(bad)
    assert excinfo.value.reason_code == "UNKNOWN_SCHEMA"
    assert len(backbone.quarantine) == 1
    assert backbone.quarantine[0].reason_code == "UNKNOWN_SCHEMA"


def test_missing_governed_context_is_quarantined_before_publication(backbone: CanonicalEventBackbone) -> None:
    raw = envelope(aggregate_ref="urn:ocor:mission-object:backbone:4", sequence=1).to_mapping()
    del raw["correlation_id"]

    with pytest.raises(BackboneError) as excinfo:
        backbone.publish_from_mapping(raw)
    assert excinfo.value.reason_code == "MISSING_CONTEXT"
    assert len(backbone.quarantine) == 1
    assert backbone.quarantine[0].reason_code == "MISSING_CONTEXT"


def test_an_out_of_order_aggregate_effect_is_quarantined_and_never_published(
    backbone: CanonicalEventBackbone,
) -> None:
    aggregate_ref = "urn:ocor:mission-object:backbone:5"
    backbone.publish(envelope(aggregate_ref=aggregate_ref, sequence=3))

    with pytest.raises(BackboneError) as excinfo:
        backbone.publish(envelope(aggregate_ref=aggregate_ref, sequence=2))
    assert excinfo.value.reason_code == "OUT_OF_ORDER"
    assert backbone.quarantine[-1].reason_code == "OUT_OF_ORDER"

    delivered = backbone.consume(1)
    assert delivered[0].envelope.sequence == 3, "the out-of-order attempt must never have reached the real topic"


def test_a_replayed_idempotency_key_is_a_safe_no_op_not_a_duplicate_publish(
    backbone: CanonicalEventBackbone,
) -> None:
    first = envelope(aggregate_ref="urn:ocor:mission-object:backbone:6", sequence=1, idempotency_key="idem-key-1")
    backbone.publish(first)
    # the same idempotency key, replayed (e.g. a retried producer call) --
    # must not create a second real record on the topic.
    replay = envelope(
        aggregate_ref="urn:ocor:mission-object:backbone:6",
        sequence=1,
        event_id=first.event_id,
        idempotency_key="idem-key-1",
    )
    backbone.publish(replay)

    delivered = backbone.consume(1)
    assert len(delivered) == 1


def test_a_real_kafka_unreachability_fails_closed() -> None:
    backbone = CanonicalEventBackbone(
        f"ocor-backbone-unreachable-{uuid.uuid4().hex[:12]}", container="ocor-nonexistent-container-for-fault-injection"
    )

    with pytest.raises(KafkaBackboneError):
        backbone.initialize()
