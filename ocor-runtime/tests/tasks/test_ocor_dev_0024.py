"""OCOR-DEV-0024: SPIKE cross-compartment non-interference.

Proves that paired fixtures are observationally equivalent across
content, existence, rank, count, cache and bounded timing: a
low-clearance observer's view never changes because a high-compartment
counterpart was populated (or removed) elsewhere. This composes three
previously sealed spikes, all reused completely unmodified --

* the Jena marking-safe projection (OCOR-DEV-0018,
  ``spikes.jena_marking.adapter``) for content/existence/count on a real
  Fuseki dataset;
* the Qdrant vector-partition oracle (OCOR-DEV-0023,
  ``spikes.vector_partition.oracle``) for content/rank/count/timing on a
  real, self-provisioned Qdrant instance;
* the identity/policy bounded probe (OCOR-DEV-0021,
  ``spikes.control_plane_latency.probe``) for cross-service timing
  non-interference between two real, live control-plane services.

Every test drives real backends -- no mocks.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from ocor_runtime.c4_marking import MarkingEngine, MarkingSchemeDefinition, MarkingSet
from ocor_runtime.security.ports import ControlName

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))
SCRIPTS_DIR = REPOSITORY_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from spikes.control_plane_latency.probe import (  # noqa: E402 -- must follow sys.path.insert above
    HEALTH_URLS,
    bounded_probe,
)
from spikes.jena_marking.adapter import JenaMarkingProjectionAdapter  # noqa: E402
from spikes.non_interference.equivalence import (  # noqa: E402
    NonInterferenceViolation,
    assert_observationally_equivalent,
)
from spikes.vector_partition.oracle import (  # noqa: E402
    PartitionAccessDenied,
    PartitionedVectorIndex,
    PartitionKey,
    QdrantHarness,
    TimingEnvelope,
)

_SPEC = importlib.util.spec_from_file_location(
    "fault_inject_test_environment_0024", SCRIPTS_DIR / "fault_inject_test_environment.py"
)
assert _SPEC is not None and _SPEC.loader is not None
fault_inject = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = fault_inject
_SPEC.loader.exec_module(fault_inject)

CLASSIFICATION_SCHEME = MarkingSchemeDefinition("classification", levels=("UNCLASSIFIED", "SECRET", "TOP_SECRET"))
LOW_CLEARANCE = MarkingSet({"classification": "UNCLASSIFIED"})
BOUNDED_TIMEOUT_SECONDS = 2.0


def qdrant_key(compartment: str) -> PartitionKey:
    return PartitionKey(
        tenant_id="urn:ocor:tenant:synthetic",
        domain_id="urn:ocor:domain:logistics",
        compartments=(compartment,),
        marking_ref=f"urn:ocor:marking:{compartment}",
        model_digest="sha256:" + "a" * 64,
        representation_version=1,
    )


def qdrant_point(identifier: int, partition: PartitionKey, vector: list[float], item: str) -> dict:
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


@pytest.fixture(scope="session")
def backends_reachable() -> None:
    try:
        jena = JenaMarkingProjectionAdapter(MarkingEngine([CLASSIFICATION_SCHEME]))
        jena.reset()
    except Exception as error:  # noqa: BLE001 -- fail closed to a clear message
        pytest.fail(f"a real, live Fuseki instance is mandatory qualifying evidence: {error}")
    for control, url in HEALTH_URLS.items():
        if not fault_inject.http_reachable(url, timeout=5.0):
            pytest.fail(f"a real, live {control.value} service is mandatory qualifying evidence")


@pytest.fixture
def jena(backends_reachable: None) -> JenaMarkingProjectionAdapter:
    adapter = JenaMarkingProjectionAdapter(MarkingEngine([CLASSIFICATION_SCHEME]))
    adapter.reset()
    return adapter


@pytest.fixture
def qdrant_campaign(backends_reachable: None):
    qdrant = QdrantHarness.provision()
    low = qdrant_key("low")
    high = qdrant_key("high")
    index = PartitionedVectorIndex(qdrant, {low.digest(), high.digest()})
    index.create_partition(low)
    index.create_partition(high)
    index.upsert(
        low,
        authority_digest=low.digest(),
        points=[
            qdrant_point(1, low, [1.0, 0.0, 0.0, 0.0], "urn:item:low:1"),
            qdrant_point(2, low, [0.8, 0.2, 0.0, 0.0], "urn:item:low:2"),
        ],
    )
    try:
        yield qdrant, index, low, high
    finally:
        qdrant.destroy()


def test_jena_low_view_is_unaffected_by_adding_a_high_compartment_resource(jena: JenaMarkingProjectionAdapter):
    jena.ingest_marked("urn:ocor:resource:low-1", "commit-1", "UNCLASSIFIED")
    before = (
        jena.list_authorized(LOW_CLEARANCE),
        jena.count_authorized(LOW_CLEARANCE),
        jena.exists_authorized("urn:ocor:resource:low-1", LOW_CLEARANCE),
        jena.exists_authorized("urn:ocor:resource:high-1", LOW_CLEARANCE),
    )

    jena.ingest_marked("urn:ocor:resource:high-1", "commit-1", "TOP_SECRET")

    after = (
        jena.list_authorized(LOW_CLEARANCE),
        jena.count_authorized(LOW_CLEARANCE),
        jena.exists_authorized("urn:ocor:resource:low-1", LOW_CLEARANCE),
        jena.exists_authorized("urn:ocor:resource:high-1", LOW_CLEARANCE),
    )

    assert_observationally_equivalent(before, after, axis="jena-content-count-existence")
    assert after[2] is True
    assert after[3] is False


def test_qdrant_low_partition_search_rank_and_count_are_unaffected_by_high_population(qdrant_campaign):
    _, index, low, high = qdrant_campaign
    query = [1.0, 0.0, 0.0, 0.0]
    before = (index.search(low, authority_digest=low.digest(), vector=query), index.count(low, authority_digest=low.digest()))

    foreign = [qdrant_point(n, high, [1.0, 0.0, 0.0, 0.0], f"urn:item:high:{n}") for n in range(1, 201)]
    index.upsert(high, authority_digest=high.digest(), points=foreign)

    after = (index.search(low, authority_digest=low.digest(), vector=query), index.count(low, authority_digest=low.digest()))
    assert_observationally_equivalent(before, after, axis="qdrant-rank-count")


def test_qdrant_low_partition_timing_envelope_holds_after_high_population(qdrant_campaign):
    _, index, low, high = qdrant_campaign
    query = [0.9, 0.1, 0.0, 0.0]
    baseline = index.timed_searches(low, authority_digest=low.digest(), vector=query)
    envelope = TimingEnvelope.from_samples(baseline)

    foreign = [qdrant_point(n, high, [0.9, 0.1, 0.0, 0.0], f"urn:item:high:timing:{n}") for n in range(1, 201)]
    index.upsert(high, authority_digest=high.digest(), points=foreign)

    observed = index.timed_searches(low, authority_digest=low.digest(), vector=query)
    assert envelope.admits(observed), "populating the high compartment perturbed the low partition's bounded timing"


def test_qdrant_access_to_high_compartment_is_denied_identically_whether_present_or_fabricated(qdrant_campaign):
    _, index, low, high = qdrant_campaign
    fabricated = qdrant_key("does-not-exist")
    for denied in (high, fabricated):
        with pytest.raises(PartitionAccessDenied) as excinfo:
            index.search(denied, authority_digest=low.digest(), vector=[1.0, 0.0, 0.0, 0.0])
        assert str(excinfo.value) == PartitionAccessDenied.reason_code


def test_opa_probe_outcome_and_timing_are_unaffected_by_pausing_an_unrelated_control(backends_reachable: None):
    opa_url = HEALTH_URLS[ControlName.POLICY]
    baseline_statuses = []
    baseline_latencies = []
    for index in range(5):
        status, audit = bounded_probe(
            ControlName.POLICY,
            opa_url,
            timeout_seconds=BOUNDED_TIMEOUT_SECONDS,
            correlation_id=f"baseline-{index}",
            causation_id=f"baseline-{index}",
        )
        baseline_statuses.append(status.is_available)
        baseline_latencies.append(audit.latency_ms / 1000)
    envelope = TimingEnvelope.from_samples(baseline_latencies)

    pause = fault_inject.run(
        fault_inject.fault_command("openbao", "pause"), cwd=REPOSITORY_ROOT, timeout=30
    )
    assert pause.returncode == 0, pause.stderr
    try:
        paused = fault_inject._poll(
            lambda: not fault_inject.http_reachable(HEALTH_URLS[ControlName.SECRETS], timeout=1.0), timeout=10.0
        )
        assert paused, "openbao was never observed unreachable after pause"

        during_statuses = []
        during_latencies = []
        for index in range(5):
            status, audit = bounded_probe(
                ControlName.POLICY,
                opa_url,
                timeout_seconds=BOUNDED_TIMEOUT_SECONDS,
                correlation_id=f"during-{index}",
                causation_id=f"during-{index}",
            )
            during_statuses.append(status.is_available)
            during_latencies.append(audit.latency_ms / 1000)
    finally:
        unpause = fault_inject.run(
            fault_inject.fault_command("openbao", "unpause"), cwd=REPOSITORY_ROOT, timeout=30
        )
        assert unpause.returncode == 0, unpause.stderr
        recovered = fault_inject._poll(
            lambda: fault_inject.http_reachable(HEALTH_URLS[ControlName.SECRETS], timeout=2.0), timeout=15.0
        )
        assert recovered, "openbao did not recover within the bounded window after unpause"

    assert_observationally_equivalent(all(baseline_statuses), all(during_statuses), axis="opa-availability")
    assert envelope.admits(during_latencies), (
        "pausing an unrelated control (openbao) perturbed OPA's own bounded-probe timing -- the "
        "control plane must not let one control's outage leak into another's observable latency"
    )


def test_repeated_low_queries_are_stable_across_both_backends_after_high_population(
    jena: JenaMarkingProjectionAdapter, qdrant_campaign
):
    jena.ingest_marked("urn:ocor:resource:cache-low", "commit-1", "UNCLASSIFIED")
    jena_first = jena.list_authorized(LOW_CLEARANCE)

    _, index, low, high = qdrant_campaign
    query = [1.0, 0.0, 0.0, 0.0]
    qdrant_first = index.search(low, authority_digest=low.digest(), vector=query)

    jena.ingest_marked("urn:ocor:resource:cache-high", "commit-1", "TOP_SECRET")
    index.upsert(
        high, authority_digest=high.digest(), points=[qdrant_point(500, high, [1.0, 0.0, 0.0, 0.0], "urn:item:high:cache")]
    )

    jena_second = jena.list_authorized(LOW_CLEARANCE)
    qdrant_second = index.search(low, authority_digest=low.digest(), vector=query)

    assert_observationally_equivalent(jena_first, jena_second, axis="jena-repeated-query-cache")
    assert_observationally_equivalent(qdrant_first, qdrant_second, axis="qdrant-repeated-query-cache")


def test_assert_observationally_equivalent_raises_on_a_real_divergence():
    with pytest.raises(NonInterferenceViolation, match="content"):
        assert_observationally_equivalent(["a"], ["a", "b"], axis="content")
