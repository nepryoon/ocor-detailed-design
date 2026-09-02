from __future__ import annotations

import subprocess

import pytest

from spikes.vector_partition.oracle import (
    QDRANT_IMAGE,
    PartitionAccessDenied,
    PartitionedVectorIndex,
    PartitionKey,
    QdrantHarness,
    ScopeMismatch,
    TimingEnvelope,
)


def key(compartment: str) -> PartitionKey:
    return PartitionKey(
        tenant_id="urn:ocor:tenant:synthetic",
        domain_id="urn:ocor:domain:logistics",
        compartments=(compartment,),
        marking_ref=f"urn:ocor:marking:{compartment}",
        model_digest="sha256:" + "a" * 64,
        representation_version=1,
    )


def point(identifier: int, partition: PartitionKey, vector, item: str):
    return {
        "id": identifier,
        "vector": vector,
        "payload": {
            "item_ref": item,
            "version": 1,
            "marking_ref": partition.marking_ref,
            "partition_digest": partition.digest(),
        },
    }


@pytest.fixture(scope="module")
def campaign():
    qdrant = QdrantHarness.provision()
    alpha = key("alpha")
    bravo = key("bravo")
    index = PartitionedVectorIndex(qdrant, {alpha.digest(), bravo.digest()})
    index.create_partition(alpha)
    index.create_partition(bravo)
    index.upsert(
        alpha,
        authority_digest=alpha.digest(),
        points=[
            point(1, alpha, [1.0, 0.0, 0.0, 0.0], "urn:item:alpha:1"),
            point(2, alpha, [0.8, 0.2, 0.0, 0.0], "urn:item:alpha:2"),
            point(3, alpha, [0.0, 1.0, 0.0, 0.0], "urn:item:alpha:3"),
        ],
    )
    try:
        yield qdrant, index, alpha, bravo
    finally:
        qdrant.destroy()


def test_campaign_uses_pinned_real_qdrant(campaign):
    qdrant, _, _, _ = campaign
    inspect = subprocess.run(
        ["docker", "inspect", qdrant.container, "--format", "{{.Config.Image}}"],
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()
    assert inspect == QDRANT_IMAGE


def test_authorized_partition_returns_stable_ranked_results(campaign):
    _, index, alpha, _ = campaign
    first = index.search(alpha, authority_digest=alpha.digest(), vector=[1, 0, 0, 0])
    second = index.search(alpha, authority_digest=alpha.digest(), vector=[1, 0, 0, 0])
    assert first == second
    assert [result.item_ref for result in first] == [
        "urn:item:alpha:1",
        "urn:item:alpha:2",
        "urn:item:alpha:3",
    ]
    assert all(result.marking_ref == alpha.marking_ref for result in first)


def test_foreign_nearest_vectors_do_not_change_results_rank_or_count(campaign):
    _, index, alpha, bravo = campaign
    query = [1, 0, 0, 0]
    before = index.search(alpha, authority_digest=alpha.digest(), vector=query)
    count_before = index.count(alpha, authority_digest=alpha.digest())
    foreign = [
        point(number, bravo, [1.0, 0.0, 0.0, 0.0], f"urn:item:bravo:{number}")
        for number in range(1, 201)
    ]
    index.upsert(bravo, authority_digest=bravo.digest(), points=foreign)
    after = index.search(alpha, authority_digest=alpha.digest(), vector=query)
    assert after == before
    assert index.count(alpha, authority_digest=alpha.digest()) == count_before == 3


def test_foreign_population_does_not_cross_timing_envelope(campaign):
    _, index, alpha, _ = campaign
    query = [0.9, 0.1, 0, 0]
    baseline = index.timed_searches(
        alpha, authority_digest=alpha.digest(), vector=query
    )
    envelope = TimingEnvelope.from_samples(baseline)
    observed = index.timed_searches(
        alpha, authority_digest=alpha.digest(), vector=query
    )
    assert envelope.admits(observed)


def test_denied_existing_and_fabricated_partition_have_same_error_and_no_backend_call(
    campaign,
):
    _, index, alpha, bravo = campaign
    fabricated = key("does-not-exist")
    before = index.backend_requests
    for denied in (bravo, fabricated):
        with pytest.raises(PartitionAccessDenied) as captured:
            index.search(
                denied,
                authority_digest=alpha.digest(),
                vector=[1, 0, 0, 0],
            )
        assert str(captured.value) == PartitionAccessDenied.reason_code
    assert index.backend_requests == before


def test_cross_scope_vector_admission_fails_before_backend(campaign):
    _, index, alpha, bravo = campaign
    wrong = point(999, bravo, [1, 0, 0, 0], "urn:item:bravo:999")
    before = index.backend_requests
    with pytest.raises(ScopeMismatch, match="VECTOR_SCOPE_MISMATCH"):
        index.upsert(alpha, authority_digest=alpha.digest(), points=[wrong])
    assert index.backend_requests == before


def test_raw_vectors_are_not_returned_by_public_result(campaign):
    _, index, alpha, _ = campaign
    result = index.search(alpha, authority_digest=alpha.digest(), vector=[1, 0, 0, 0])[0]
    assert set(result.__dataclass_fields__) == {"item_ref", "version", "score", "marking_ref"}


def test_partition_identity_is_stable_and_order_normalized():
    first = key("alpha")
    second = PartitionKey(
        tenant_id=first.tenant_id,
        domain_id=first.domain_id,
        compartments=("zulu", "alpha"),
        marking_ref=first.marking_ref,
        model_digest=first.model_digest,
        representation_version=first.representation_version,
    )
    reordered = PartitionKey(
        tenant_id=first.tenant_id,
        domain_id=first.domain_id,
        compartments=("alpha", "zulu"),
        marking_ref=first.marking_ref,
        model_digest=first.model_digest,
        representation_version=first.representation_version,
    )
    assert second.digest() == reordered.digest()
    assert first.digest() != second.digest()
