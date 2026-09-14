"""OCOR-DEV-0045: Implement C7 scenario and causal runtime.

Proves that ocor_runtime.c7.runtime's four sealed, reproducible causal
operations (intervention, counterfactual, uncertainty, sensitivity)
all share OCOR-DEV-0022's sealed identify-or-abstain fail-closed gate:
a query against main or any non-scenario/ branch always abstains with
no authoritative causal claim, for every one of the four operations,
not only the intervention path the sealed spike itself computes.
Cross-validates the reimplemented intervention path against
OCOR-DEV-0022's sealed spikes.causal_reproducibility.oracle (reused
unmodified, imported only here in the test, per the established
spikes/-outside-runtime-pythonpath precedent) using the identical
fixture data, proving no drift between the two independent
implementations. Pure, in-memory, deterministic component (no
external service needed, like OCOR-DEV-0028/0030/0042/0043/0044's own
C1/C6/C7 slices).
"""

from __future__ import annotations

import sys
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest
from ocor_runtime.c7.runtime import (
    CausalOutcome,
    CausalQuery,
    CausalRuntimeError,
    canonical_digest,
    estimate_counterfactual,
    estimate_intervention,
    estimate_sensitivity,
    estimate_uncertainty,
    verify_reproduction,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from spikes.causal_reproducibility.oracle import execute as sealed_execute  # noqa: E402

MODEL = {"model_id": "synthetic-logistics-v1", "estimand": "ATE", "version": 1}
ROWS = [
    {"region": "north", "expedite": 0, "delay_hours": "10"},
    {"region": "north", "expedite": 1, "delay_hours": "6"},
    {"region": "south", "expedite": 0, "delay_hours": "12"},
    {"region": "south", "expedite": 1, "delay_hours": "8"},
]
INTERVENTION = {"treatment": "expedite", "value": 1, "valid_envelope": [0, 1]}
RELEASE = "sha256:" + "a" * 64


@pytest.fixture
def query() -> CausalQuery:
    return CausalQuery(
        baseline_commit="urn:ocor:commit:synthetic:42",
        scenario_branch="scenario/expedite-what-if",
        model_digest=canonical_digest(MODEL),
        data_digest=canonical_digest(ROWS),
        intervention_digest=canonical_digest(INTERVENTION),
        ontology_release_digest=RELEASE,
        expected_release_digest=RELEASE,
        treatment="expedite",
        outcome="delay_hours",
        adjustment="region",
        seed=271828,
        correlation_id="018f2f95-01b2-7cc3-8d4e-123456789abc",
        causation_id="urn:ocor:causation:synthetic:42",
    )


def run_intervention(query: CausalQuery, *, rows: list[dict] = ROWS, intervention: dict = INTERVENTION) -> CausalOutcome:
    return estimate_intervention(query, model=MODEL, factual_rows=rows, intervention=intervention)


# --- cross-validation against the sealed spike -------------------------------


def test_reimplemented_intervention_reproduces_the_sealed_spikes_oracle_bit_for_bit(query: CausalQuery) -> None:
    sealed = sealed_execute(query, model=MODEL, factual_rows=ROWS, intervention=INTERVENTION)
    retained = run_intervention(query)

    assert retained.status == sealed.status == "IDENTIFIED"
    assert retained.method == sealed.method == "STRATIFIED_BACKDOOR_ATE"
    assert retained.effect == sealed.effect == "-4"
    assert retained.assumptions == sealed.assumptions


# --- intervention (population ATE) -------------------------------------------


def test_same_pinned_inputs_reproduce_identical_sealed_identified_result(query: CausalQuery) -> None:
    first = run_intervention(query)
    second = run_intervention(query)
    verify_reproduction(first, second)
    assert first.status == "IDENTIFIED"
    assert first.effect == "-4"
    assert first.reproducibility_digest == second.reproducibility_digest
    assert first.lineage["seed"] == 271828


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("scenario_branch", "main", "MAIN_CONTAMINATED"),
        ("scenario_branch", "feature/not-a-scenario", "MAIN_CONTAMINATED"),
        ("contaminated_main", True, "MAIN_CONTAMINATED"),
        ("expected_release_digest", "sha256:" + "b" * 64, "RELEASE_MISMATCH"),
        ("unresolved_confounding", True, "UNRESOLVED_CONFOUNDING"),
    ],
)
def test_intervention_abstains_with_disjoint_reason_codes(query: CausalQuery, field: str, value: object, reason: str) -> None:
    outcome = run_intervention(replace(query, **{field: value}))
    assert outcome.status == "ABSTAIN"
    assert outcome.reason_code == reason
    assert outcome.effect is None
    assert outcome.details == {}


def test_missing_factual_set_abstains_without_estimate(query: CausalQuery) -> None:
    empty: list[dict] = []
    outcome = run_intervention(replace(query, data_digest=canonical_digest(empty)), rows=empty)
    assert (outcome.status, outcome.reason_code, outcome.effect) == ("ABSTAIN", "MISSING_FACTUAL_SET", None)


def test_positivity_failure_abstains_without_estimate(query: CausalQuery) -> None:
    rows = [row for row in ROWS if row["expedite"] == 1]
    outcome = run_intervention(replace(query, data_digest=canonical_digest(rows)), rows=rows)
    assert outcome.reason_code == "POSITIVITY_FAILURE"
    assert outcome.effect is None


def test_out_of_domain_intervention_abstains_without_estimate(query: CausalQuery) -> None:
    intervention = {**INTERVENTION, "value": 2}
    outcome = run_intervention(replace(query, intervention_digest=canonical_digest(intervention)), intervention=intervention)
    assert outcome.reason_code == "OUT_OF_DOMAIN"
    assert outcome.effect is None


@pytest.mark.parametrize("pin", ["model_digest", "data_digest", "intervention_digest"])
def test_pin_mismatch_fails_loudly(query: CausalQuery, pin: str) -> None:
    with pytest.raises(CausalRuntimeError, match="PIN_MISMATCH"):
        run_intervention(replace(query, **{pin: "0" * 64}))


def test_unexplained_result_drift_fails_reproducibility_check(query: CausalQuery) -> None:
    first = run_intervention(query)
    changed = replace(first, effect="-3.999")
    with pytest.raises(CausalRuntimeError, match="REPRODUCIBILITY"):
        verify_reproduction(first, changed)


def test_seed_is_part_of_the_reproducibility_seal(query: CausalQuery) -> None:
    first = run_intervention(query)
    second = run_intervention(replace(query, seed=query.seed + 1))
    assert first.reproducibility_digest != second.reproducibility_digest


# --- counterfactual -----------------------------------------------------------


def test_counterfactual_imputes_a_specific_units_outcome_under_the_opposite_treatment(query: CausalQuery) -> None:
    outcome = estimate_counterfactual(query, model=MODEL, factual_rows=ROWS, intervention=INTERVENTION, unit_index=0)

    assert outcome.status == "IDENTIFIED"
    assert outcome.method == "STRATIFIED_BACKDOOR_COUNTERFACTUAL"
    # unit 0: region=north, expedite=0, delay_hours=10 -- the opposite
    # treatment (expedite=1) north mean is 6, the actual (expedite=0)
    # north mean is 10, so the imputed counterfactual is 10 + (6-10) = 6.
    assert outcome.effect == "6"
    assert outcome.details["actual_treatment"] == "0"


def test_counterfactual_abstains_identically_to_intervention_on_main(query: CausalQuery) -> None:
    outcome = estimate_counterfactual(replace(query, scenario_branch="main"), model=MODEL, factual_rows=ROWS, intervention=INTERVENTION, unit_index=0)
    assert outcome.status == "ABSTAIN"
    assert outcome.reason_code == "MAIN_CONTAMINATED"
    assert outcome.effect is None


def test_counterfactual_rejects_an_out_of_range_unit_index(query: CausalQuery) -> None:
    with pytest.raises(CausalRuntimeError, match="UNIT_INDEX_OUT_OF_RANGE"):
        estimate_counterfactual(query, model=MODEL, factual_rows=ROWS, intervention=INTERVENTION, unit_index=99)


def test_counterfactual_is_reproducible_for_identical_pinned_inputs(query: CausalQuery) -> None:
    first = estimate_counterfactual(query, model=MODEL, factual_rows=ROWS, intervention=INTERVENTION, unit_index=1)
    second = estimate_counterfactual(query, model=MODEL, factual_rows=ROWS, intervention=INTERVENTION, unit_index=1)
    verify_reproduction(first, second)


# --- uncertainty (bootstrap CI) -----------------------------------------------


def test_uncertainty_produces_a_deterministic_bootstrap_interval_around_the_ate(query: CausalQuery) -> None:
    first = estimate_uncertainty(query, model=MODEL, factual_rows=ROWS, intervention=INTERVENTION)
    second = estimate_uncertainty(query, model=MODEL, factual_rows=ROWS, intervention=INTERVENTION)

    assert first.status == "IDENTIFIED"
    assert first.method == "BOOTSTRAP_CI"
    assert first.effect == "-4"
    assert Decimal(first.details["ci_low"]) <= Decimal(first.details["ci_high"])
    verify_reproduction(first, second)
    assert first.reproducibility_digest == second.reproducibility_digest


def test_uncertainty_differs_deterministically_with_a_different_seed(query: CausalQuery) -> None:
    first = estimate_uncertainty(query, model=MODEL, factual_rows=ROWS, intervention=INTERVENTION)
    second = estimate_uncertainty(replace(query, seed=query.seed + 1), model=MODEL, factual_rows=ROWS, intervention=INTERVENTION)
    assert first.reproducibility_digest != second.reproducibility_digest


def test_uncertainty_abstains_identically_to_intervention_on_main(query: CausalQuery) -> None:
    outcome = estimate_uncertainty(replace(query, scenario_branch="main"), model=MODEL, factual_rows=ROWS, intervention=INTERVENTION)
    assert outcome.status == "ABSTAIN"
    assert outcome.reason_code == "MAIN_CONTAMINATED"
    assert outcome.effect is None
    assert outcome.details == {}


# --- sensitivity (additive confounding shift) ---------------------------------


def test_sensitivity_reports_the_shifted_effect_and_whether_the_sign_flips(query: CausalQuery) -> None:
    outcome = estimate_sensitivity(query, model=MODEL, factual_rows=ROWS, intervention=INTERVENTION, confounding_shift=Decimal("1"))

    assert outcome.status == "IDENTIFIED"
    assert outcome.method == "ADDITIVE_CONFOUNDING_SHIFT_SENSITIVITY"
    assert outcome.effect == "-4"
    assert outcome.details["confounding_shift"] == "1"
    assert Decimal(outcome.details["shifted_effect"]) != Decimal(outcome.effect)


def test_a_large_enough_confounding_shift_flips_the_effects_sign(query: CausalQuery) -> None:
    outcome = estimate_sensitivity(query, model=MODEL, factual_rows=ROWS, intervention=INTERVENTION, confounding_shift=Decimal("-10"))
    assert outcome.details["sign_flipped"] == "True"


def test_sensitivity_abstains_identically_to_intervention_on_main(query: CausalQuery) -> None:
    outcome = estimate_sensitivity(
        replace(query, scenario_branch="main"), model=MODEL, factual_rows=ROWS, intervention=INTERVENTION, confounding_shift=Decimal("1")
    )
    assert outcome.status == "ABSTAIN"
    assert outcome.reason_code == "MAIN_CONTAMINATED"
    assert outcome.effect is None


def test_sensitivity_is_reproducible_for_identical_pinned_inputs(query: CausalQuery) -> None:
    first = estimate_sensitivity(query, model=MODEL, factual_rows=ROWS, intervention=INTERVENTION, confounding_shift=Decimal("2"))
    second = estimate_sensitivity(query, model=MODEL, factual_rows=ROWS, intervention=INTERVENTION, confounding_shift=Decimal("2"))
    verify_reproduction(first, second)


# --- immutability --------------------------------------------------------------


def test_outcome_details_and_lineage_are_immutable() -> None:
    outcome = estimate_sensitivity(
        CausalQuery(
            baseline_commit="urn:ocor:commit:synthetic:42",
            scenario_branch="scenario/expedite-what-if",
            model_digest=canonical_digest(MODEL),
            data_digest=canonical_digest(ROWS),
            intervention_digest=canonical_digest(INTERVENTION),
            ontology_release_digest=RELEASE,
            expected_release_digest=RELEASE,
            treatment="expedite",
            outcome="delay_hours",
            adjustment="region",
            seed=1,
            correlation_id="c1",
            causation_id="ca1",
        ),
        model=MODEL,
        factual_rows=ROWS,
        intervention=INTERVENTION,
        confounding_shift=Decimal("0"),
    )
    with pytest.raises(TypeError):
        outcome.details["confounding_shift"] = "tampered"  # type: ignore[index]
    with pytest.raises(TypeError):
        outcome.lineage["seed"] = 999  # type: ignore[index]
