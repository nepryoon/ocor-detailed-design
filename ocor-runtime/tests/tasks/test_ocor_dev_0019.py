from __future__ import annotations

from dataclasses import replace

import pytest

from spikes.kafka_delivery.oracle import (
    ConflictingDuplicate,
    KafkaRecord,
    PoisonEvent,
    deduplicate,
    run_campaign,
)


@pytest.fixture(scope="module")
def campaign():
    return run_campaign()


def test_campaign_uses_real_healthy_kafka(campaign):
    assert "confluentinc/cp-kafka" in campaign.image
    assert "id: 1" in campaign.broker_id


def test_same_aggregate_remains_in_one_ordered_partition_across_restart(campaign):
    records = campaign.records_before_restart
    assert len({record.partition for record in records}) == 1
    assert [record.offset for record in records] == list(range(8))
    assert [record.value["sequence"] for record in records] == list(range(1, 9))


def test_replay_after_broker_restart_is_deterministic(campaign):
    before = campaign.records_before_restart
    after = campaign.records_after_restart
    assert [(r.partition, r.offset, r.key, r.value) for r in before] == [
        (r.partition, r.offset, r.key, r.value) for r in after
    ]


def test_consumer_crash_redelivery_has_one_visible_effect_per_event(campaign):
    recovered = campaign.deduplicated_after_consumer_crash
    assert len(recovered) == 8
    assert [record.value["event_id"] for record in recovered] == [
        f"event-{sequence:02d}" for sequence in range(1, 9)
    ]


def test_conflicting_duplicate_fails_closed(campaign):
    original = campaign.records_before_restart[0]
    conflict = replace(original, value={**original.value, "sequence": 99})
    with pytest.raises(ConflictingDuplicate, match="identity"):
        deduplicate((original, conflict))


@pytest.mark.parametrize(
    "value,key",
    [
        ({"event_id": "event-1", "aggregate_id": "aggregate-alpha"}, "aggregate-alpha"),
        ({"event_id": "event-1", "aggregate_id": "aggregate-alpha", "sequence": 0}, "aggregate-alpha"),
        ({"event_id": "event-1", "aggregate_id": "aggregate-beta", "sequence": 1}, "aggregate-alpha"),
    ],
)
def test_poison_event_is_rejected_without_visible_effect(value, key):
    record = KafkaRecord(partition=0, offset=0, key=key, value=value)
    with pytest.raises(PoisonEvent, match="envelope"):
        deduplicate((record,))
