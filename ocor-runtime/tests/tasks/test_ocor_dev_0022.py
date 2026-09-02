from __future__ import annotations

from dataclasses import replace

import pytest

from spikes.causal_reproducibility.oracle import (
    CausalQuery,
    CausalReproducibilityError,
    canonical_digest,
    execute,
    verify_reproduction,
)

MODEL = {"model_id": "synthetic-logistics-v1", "estimand": "ATE", "version": 1}
ROWS = [
    {"region": "north", "expedite": 0, "delay_hours": "10"},
    {"region": "north", "expedite": 1, "delay_hours": "6"},
    {"region": "south", "expedite": 0, "delay_hours": "12"},
    {"region": "south", "expedite": 1, "delay_hours": "8"},
]
INTERVENTION = {"treatment": "expedite", "value": 1, "valid_envelope": [0, 1]}


@pytest.fixture
def query() -> CausalQuery:
    release = "sha256:" + "a" * 64
    return CausalQuery(
        baseline_commit="urn:ocor:commit:synthetic:42",
        scenario_branch="scenario/expedite-what-if",
        model_digest=canonical_digest(MODEL),
        data_digest=canonical_digest(ROWS),
        intervention_digest=canonical_digest(INTERVENTION),
        ontology_release_digest=release,
        expected_release_digest=release,
        treatment="expedite",
        outcome="delay_hours",
        adjustment="region",
        seed=271828,
        correlation_id="018f2f95-01b2-7cc3-8d4e-123456789abc",
        causation_id="urn:ocor:causation:synthetic:42",
    )


def run(query: CausalQuery, *, rows=ROWS, intervention=INTERVENTION):
    return execute(query, model=MODEL, factual_rows=rows, intervention=intervention)


def test_same_pinned_inputs_reproduce_identical_sealed_identified_result(query):
    first = run(query)
    second = run(query)
    verify_reproduction(first, second)
    assert first.status == "IDENTIFIED"
    assert first.method == "STRATIFIED_BACKDOOR_ATE"
    assert first.effect == "-4"
    assert first.reproducibility_digest == second.reproducibility_digest
    assert first.lineage["seed"] == 271828


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("scenario_branch", "main", "MAIN_CONTAMINATED"),
        ("contaminated_main", True, "MAIN_CONTAMINATED"),
        ("expected_release_digest", "sha256:" + "b" * 64, "RELEASE_MISMATCH"),
        ("unresolved_confounding", True, "UNRESOLVED_CONFOUNDING"),
    ],
)
def test_identification_abstains_with_disjoint_reason_codes(query, field, value, reason):
    outcome = run(replace(query, **{field: value}))
    assert outcome.status == "ABSTAIN"
    assert outcome.reason_code == reason
    assert outcome.effect is None


def test_missing_factual_set_abstains_without_estimate(query):
    empty = []
    outcome = run(replace(query, data_digest=canonical_digest(empty)), rows=empty)
    assert (outcome.status, outcome.reason_code, outcome.effect) == (
        "ABSTAIN",
        "MISSING_FACTUAL_SET",
        None,
    )


def test_positivity_failure_abstains_without_estimate(query):
    rows = [row for row in ROWS if row["expedite"] == 1]
    outcome = run(replace(query, data_digest=canonical_digest(rows)), rows=rows)
    assert outcome.reason_code == "POSITIVITY_FAILURE"
    assert outcome.effect is None


def test_out_of_domain_intervention_abstains_without_estimate(query):
    intervention = {**INTERVENTION, "value": 2}
    outcome = run(
        replace(query, intervention_digest=canonical_digest(intervention)),
        intervention=intervention,
    )
    assert outcome.reason_code == "OUT_OF_DOMAIN"
    assert outcome.effect is None


@pytest.mark.parametrize("pin", ["model_digest", "data_digest", "intervention_digest"])
def test_pin_mismatch_fails_loudly(query, pin):
    with pytest.raises(CausalReproducibilityError, match="PIN_MISMATCH"):
        run(replace(query, **{pin: "0" * 64}))


def test_unexplained_result_drift_fails_reproducibility_check(query):
    first = run(query)
    changed = replace(first, effect="-3.999")
    with pytest.raises(CausalReproducibilityError, match="REPRODUCIBILITY"):
        verify_reproduction(first, changed)


def test_seed_is_part_of_the_reproducibility_seal(query):
    first = run(query)
    second = run(replace(query, seed=query.seed + 1))
    assert first.reproducibility_digest != second.reproducibility_digest
