"""OCOR-DEV-0027: SPIKE deterministic context-assembly replay.

Proves that a context-assembly receipt digest is a pure, deterministic
function of exactly five pinned dimensions -- item versions, ordering
(a real cosine-similarity ranking against Qdrant), redactions,
truncation and representation -- so replaying assembly against
identical pinned inputs reproduces the identical digest, and any
genuine change on one dimension changes it. Every backend is real
(a self-provisioned, ephemeral Qdrant container per OCOR-DEV-0023,
sealed and unmodified); no mocks. Reuses
spikes.non_interference.equivalence.assert_observationally_equivalent
(OCOR-DEV-0024, sealed) unmodified.
"""

from __future__ import annotations

import uuid

import pytest
from spikes.context_replay.replay import (
    AssemblyRequest,
    ContextReplayError,
    PinnedItem,
    assemble_context,
)
from spikes.non_interference.equivalence import assert_observationally_equivalent
from spikes.vector_partition.oracle import QdrantHarness

ITEM_A = PinnedItem("item-a", "v1", "title: Alpha\nsecret: alpha-token\nbody: first item")
ITEM_B = PinnedItem("item-b", "v1", "title: Bravo\nsecret: bravo-token\nbody: second item")
ITEM_C = PinnedItem("item-c", "v1", "title: Charlie\nsecret: charlie-token\nbody: third item")
PINNED_ITEMS = (ITEM_A, ITEM_B, ITEM_C)


@pytest.fixture
def campaign():
    qdrant = QdrantHarness.provision()
    collection = f"ocor_context_replay_{uuid.uuid4().hex[:12]}"
    qdrant.request("PUT", f"/collections/{collection}", {"vectors": {"size": 4, "distance": "Cosine"}})
    qdrant.request(
        "PUT",
        f"/collections/{collection}/points?wait=true",
        {
            "points": [
                {"id": 1, "vector": [1.0, 0.0, 0.0, 0.0], "payload": {"item_id": "item-a"}},
                {"id": 2, "vector": [0.9, 0.1, 0.0, 0.0], "payload": {"item_id": "item-b"}},
                {"id": 3, "vector": [0.0, 1.0, 0.0, 0.0], "payload": {"item_id": "item-c"}},
            ]
        },
    )
    try:
        yield qdrant, collection
    finally:
        qdrant.destroy()


def make_request(**overrides) -> AssemblyRequest:
    defaults = dict(
        query_vector=(1.0, 0.0, 0.0, 0.0),
        top_k=3,
        redact_fields=(),
        truncation_chars=10_000,
    )
    defaults.update(overrides)
    return AssemblyRequest(**defaults)


def test_replay_with_identical_pinned_inputs_reproduces_identical_receipt_digest(campaign):
    qdrant, collection = campaign
    request = make_request()

    first = assemble_context(qdrant, collection, request, PINNED_ITEMS)
    second = assemble_context(qdrant, collection, request, PINNED_ITEMS)

    assert first.receipt_digest == second.receipt_digest
    assert first.ordered_item_refs == second.ordered_item_refs


def test_changing_a_pinned_item_version_changes_the_digest(campaign):
    qdrant, collection = campaign
    request = make_request()
    bumped = tuple(
        PinnedItem(item.item_id, "v2", item.content) if item.item_id == "item-a" else item
        for item in PINNED_ITEMS
    )

    original = assemble_context(qdrant, collection, request, PINNED_ITEMS)
    changed = assemble_context(qdrant, collection, request, bumped)

    assert original.receipt_digest != changed.receipt_digest


def test_changing_redaction_changes_the_digest(campaign):
    qdrant, collection = campaign
    unredacted = assemble_context(qdrant, collection, make_request(redact_fields=()), PINNED_ITEMS)
    redacted = assemble_context(qdrant, collection, make_request(redact_fields=("secret",)), PINNED_ITEMS)

    assert unredacted.receipt_digest != redacted.receipt_digest
    assert redacted.redacted_fields == ("secret",)


def test_changing_the_query_vector_changes_ordering_and_the_digest(campaign):
    qdrant, collection = campaign
    ranked_toward_a = assemble_context(qdrant, collection, make_request(query_vector=(1.0, 0.0, 0.0, 0.0)), PINNED_ITEMS)
    ranked_toward_c = assemble_context(qdrant, collection, make_request(query_vector=(0.0, 1.0, 0.0, 0.0)), PINNED_ITEMS)

    assert ranked_toward_a.ordered_item_refs[0] == "item-a@v1"
    assert ranked_toward_c.ordered_item_refs[0] == "item-c@v1"
    assert ranked_toward_a.receipt_digest != ranked_toward_c.receipt_digest


def test_changing_truncation_changes_the_digest_and_sets_the_truncated_flag(campaign):
    qdrant, collection = campaign
    untruncated = assemble_context(qdrant, collection, make_request(truncation_chars=10_000), PINNED_ITEMS)
    truncated = assemble_context(qdrant, collection, make_request(truncation_chars=5), PINNED_ITEMS)

    assert untruncated.receipt_digest != truncated.receipt_digest
    assert untruncated.truncated is False
    assert truncated.truncated is True


def test_changing_representation_version_changes_the_digest(campaign):
    qdrant, collection = campaign
    v1 = assemble_context(qdrant, collection, make_request(representation_version="context-replay-v1"), PINNED_ITEMS)
    v2 = assemble_context(qdrant, collection, make_request(representation_version="context-replay-v2"), PINNED_ITEMS)

    assert v1.receipt_digest != v2.receipt_digest
    assert v1.ordered_item_refs == v2.ordered_item_refs


def test_two_independent_assemblies_are_observationally_equivalent_via_the_sealed_helper(campaign):
    qdrant, collection = campaign
    request = make_request()

    first = assemble_context(qdrant, collection, request, PINNED_ITEMS)
    second = assemble_context(qdrant, collection, request, PINNED_ITEMS)

    assert_observationally_equivalent(first.receipt_digest, second.receipt_digest, axis="context-replay-digest")
    assert_observationally_equivalent(first.ordered_item_refs, second.ordered_item_refs, axis="context-replay-ordering")


def test_an_unreachable_ranking_backend_fails_closed_never_a_silent_partial_context():
    # A real TCP connection refusal against a genuinely closed local
    # port -- not a mocked exception -- mirroring OCOR-DEV-0026's
    # deliberate choice of a low-blast-radius real network fault over
    # pausing a shared container.
    unreachable = QdrantHarness("unreachable", "http://127.0.0.1:1")

    with pytest.raises(ContextReplayError):
        assemble_context(unreachable, "irrelevant", make_request(), PINNED_ITEMS)
