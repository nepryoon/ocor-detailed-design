"""OCOR-DEV-0018: SPIKE Jena marking-safe projection.

Proves that a real Fuseki/Jena-backed RDF projection preserves marking
joins and filters existence/count paths: a resource is never disclosed
without its classification marking, count and existence are derived from
the same filtered list (so they can never diverge or leak), and a
forbidden resource is indistinguishable in shape from one that does not
exist. Every test drives a real, live Fuseki instance -- no mocks. Reuses
``ocor_runtime.c4_marking``'s sealed ``MarkingEngine`` unmodified for the
authorization decision.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from ocor_runtime.c4_marking import MarkingEngine, MarkingSchemeDefinition, MarkingSet

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from spikes.jena_marking.adapter import (  # noqa: E402 -- must follow sys.path.insert above
    JenaAdapterError,
    JenaMarkingProjectionAdapter,
)

CLASSIFICATION_SCHEME = MarkingSchemeDefinition(
    "classification", levels=("UNCLASSIFIED", "SECRET", "TOP_SECRET")
)


def clearance(level: str) -> MarkingSet:
    return MarkingSet({"classification": level})


@pytest.fixture(scope="session")
def fuseki_reachable() -> None:
    try:
        probe = JenaMarkingProjectionAdapter(MarkingEngine([CLASSIFICATION_SCHEME]))
        probe.reset()
    except (JenaAdapterError, OSError) as error:
        pytest.fail(f"a real, live Fuseki instance is mandatory qualifying evidence: {error}")


@pytest.fixture
def adapter(fuseki_reachable: None) -> JenaMarkingProjectionAdapter:
    value = JenaMarkingProjectionAdapter(MarkingEngine([CLASSIFICATION_SCHEME]))
    value.reset()
    return value


def test_list_authorized_returns_only_resources_at_or_below_the_clearance(
    adapter: JenaMarkingProjectionAdapter,
):
    adapter.ingest_marked("urn:ocor:resource:u1", "public memo", "UNCLASSIFIED")
    adapter.ingest_marked("urn:ocor:resource:s1", "secret briefing", "SECRET")
    adapter.ingest_marked("urn:ocor:resource:t1", "top secret plan", "TOP_SECRET")

    visible = adapter.list_authorized(clearance("SECRET"))
    resources = {row["resource"] for row in visible}
    assert resources == {"urn:ocor:resource:u1", "urn:ocor:resource:s1"}
    assert "urn:ocor:resource:t1" not in resources


def test_count_never_diverges_from_the_authorized_list_length(adapter: JenaMarkingProjectionAdapter):
    adapter.ingest_marked("urn:ocor:resource:u1", "a", "UNCLASSIFIED")
    adapter.ingest_marked("urn:ocor:resource:s1", "b", "SECRET")
    adapter.ingest_marked("urn:ocor:resource:t1", "c", "TOP_SECRET")

    for level in ("UNCLASSIFIED", "SECRET", "TOP_SECRET"):
        c = clearance(level)
        assert adapter.count_authorized(c) == len(adapter.list_authorized(c))


def test_raw_unfiltered_count_would_leak_but_the_public_api_never_exposes_it(
    adapter: JenaMarkingProjectionAdapter,
):
    adapter.ingest_marked("urn:ocor:resource:u1", "a", "UNCLASSIFIED")
    adapter.ingest_marked("urn:ocor:resource:s1", "b", "SECRET")
    adapter.ingest_marked("urn:ocor:resource:t1", "c", "TOP_SECRET")

    raw = adapter.raw_unfiltered_count()
    low_clearance_count = adapter.count_authorized(clearance("UNCLASSIFIED"))
    assert raw == 3
    assert low_clearance_count == 1
    assert low_clearance_count != raw, (
        "the raw, marking-blind SPARQL count differs from the authorized count -- this is "
        "exactly why the adapter's public API must never expose the raw number to a caller "
        "holding only UNCLASSIFIED clearance"
    )


def test_exists_authorized_is_false_and_indistinguishable_for_forbidden_vs_nonexistent(
    adapter: JenaMarkingProjectionAdapter,
):
    adapter.ingest_marked("urn:ocor:resource:t1", "top secret plan", "TOP_SECRET")

    forbidden = adapter.exists_authorized("urn:ocor:resource:t1", clearance("UNCLASSIFIED"))
    nonexistent = adapter.exists_authorized("urn:ocor:resource:never-existed", clearance("UNCLASSIFIED"))
    assert forbidden is False
    assert nonexistent is False
    assert type(forbidden) is type(nonexistent) is bool, (
        "a forbidden resource and a nonexistent one must be reported with the identical shape "
        "(a plain bool False), never a distinguishable exception or sentinel that would let a "
        "caller probe the existence of classified content"
    )


def test_resource_missing_its_marking_triple_is_never_disclosed_even_with_top_clearance(
    adapter: JenaMarkingProjectionAdapter,
):
    adapter.ingest_unmarked("urn:ocor:resource:bare", "no classification triple at all")

    visible = adapter.list_authorized(clearance("TOP_SECRET"))
    assert visible == [], (
        "a resource without a classification triple was disclosed even at the highest "
        "clearance -- the SPARQL marking join must be fail-closed (absence of a marking must "
        "never be treated as an implicit least-restrictive marking)"
    )
    assert adapter.exists_authorized("urn:ocor:resource:bare", clearance("TOP_SECRET")) is False


def test_unauthorized_content_never_appears_anywhere_in_the_returned_payload(
    adapter: JenaMarkingProjectionAdapter,
):
    adapter.ingest_marked("urn:ocor:resource:u1", "public memo", "UNCLASSIFIED")
    adapter.ingest_marked("urn:ocor:resource:t1", "classified plan alpha", "TOP_SECRET")

    visible = adapter.list_authorized(clearance("UNCLASSIFIED"))
    serialized = repr(visible)
    assert "urn:ocor:resource:t1" not in serialized
    assert "classified plan alpha" not in serialized
    assert "TOP_SECRET" not in serialized
