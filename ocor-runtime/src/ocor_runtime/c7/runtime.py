"""C7 -- retained causal/scenario runtime: intervention, counterfactual,
uncertainty and sensitivity queries.

The retained, non-spike counterpart of OCOR-DEV-0022's sealed
identify-or-abstain causal oracle (``spikes.causal_reproducibility.oracle``,
already reused unmodified by OCOR-DEV-0031's real mission thread),
reimplementing its pinned, fail-closed identification pipeline as
production code (``spikes/`` lies outside ``ocor-runtime``'s own
pythonpath in production, the OCOR-DEV-0028/0037/0040/0042 precedent)
and extending it with three additional sealed, reproducible
operations the spike itself never computed: a per-unit counterfactual
outcome, a deterministic bootstrap uncertainty interval, and an
additive-confounding-shift sensitivity check. All four operations
share the identical fail-closed identification gate the spike's own
ATE estimator uses (branch, pin, release, confounding, positivity),
so every one of them abstains under precisely the same conditions --
in particular, a query against ``main`` or any non-``scenario/``
branch always abstains with ``MAIN_CONTAMINATED``, before any
computation, structurally realizing "branches cannot write main" and
"unsupported identification returns abstain and no authoritative
causal claim" for every operation, not only the intervention path.

This is unrelated to ``ocor_runtime.c7_emission.EmissionFence`` (a
different, sealed C7 concern -- durable, ordered effect emission,
reused unmodified elsewhere and never touched here); the two share a
component letter, nothing else.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Any, Mapping

from ..errors import OCORError

BOOTSTRAP_RESAMPLES = 200
_ASSUMPTIONS = ("consistency", "conditional_exchangeability", "positivity")


class CausalRuntimeError(OCORError):
    """A pin, invariant, or reproducibility seal did not hold. Distinct
    from an ``ABSTAIN`` outcome: raised only when the caller's own
    declared pins or factual-row schema are internally inconsistent,
    never for a genuinely unsupported identification, which abstains
    instead."""


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class CausalQuery:
    baseline_commit: str
    scenario_branch: str
    model_digest: str
    data_digest: str
    intervention_digest: str
    ontology_release_digest: str
    expected_release_digest: str
    treatment: str
    outcome: str
    adjustment: str
    seed: int
    correlation_id: str
    causation_id: str
    contaminated_main: bool = False
    unresolved_confounding: bool = False


@dataclass(frozen=True, slots=True)
class CausalOutcome:
    status: str
    reason_code: str | None
    method: str | None
    effect: str | None
    details: Mapping[str, str]
    assumptions: tuple[str, ...]
    lineage: Mapping[str, Any]
    reproducibility_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "details", MappingProxyType(dict(self.details)))
        object.__setattr__(self, "lineage", MappingProxyType(dict(self.lineage)))


class _Abstain(Exception):
    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code


def _lineage(query: CausalQuery) -> dict[str, Any]:
    return {
        "baseline_commit": query.baseline_commit,
        "scenario_branch": query.scenario_branch,
        "model_digest": query.model_digest,
        "data_digest": query.data_digest,
        "intervention_digest": query.intervention_digest,
        "ontology_release_digest": query.ontology_release_digest,
        "seed": query.seed,
        "correlation_id": query.correlation_id,
        "causation_id": query.causation_id,
    }


def _seal(
    *,
    query: CausalQuery,
    status: str,
    reason_code: str | None,
    method: str | None,
    effect: Decimal | None,
    details: Mapping[str, str] | None,
    assumptions: tuple[str, ...],
) -> CausalOutcome:
    lineage = _lineage(query)
    resolved_details = dict(details or {})
    formatted_effect = format(effect, "f") if effect is not None else None
    body: dict[str, Any] = {
        "status": status,
        "reason_code": reason_code,
        "method": method,
        "effect": formatted_effect,
        "details": resolved_details,
        "assumptions": assumptions,
        "lineage": lineage,
    }
    return CausalOutcome(
        status=status,
        reason_code=reason_code,
        method=method,
        effect=formatted_effect,
        details=resolved_details,
        assumptions=assumptions,
        lineage=lineage,
        reproducibility_digest=canonical_digest(body),
    )


def _abstain_outcome(query: CausalQuery, reason_code: str) -> CausalOutcome:
    return _seal(query=query, status="ABSTAIN", reason_code=reason_code, method=None, effect=None, details=None, assumptions=())


def _validate_and_stratify(
    query: CausalQuery,
    *,
    model: dict[str, Any],
    factual_rows: list[dict[str, Any]],
    intervention: dict[str, Any],
) -> tuple[Decimal, dict[str, dict[int, list[Decimal]]]]:
    """Every shared fail-closed check the spike's own ATE estimator
    already proved: raises CausalRuntimeError on an internally
    inconsistent caller-declared pin/schema, raises _Abstain (caught
    by every public operation) on a genuinely unsupported
    identification, or returns the validated population ATE plus its
    per-stratum treated/control observations on success."""

    if canonical_digest(model) != query.model_digest:
        raise CausalRuntimeError("MODEL_PIN_MISMATCH")
    if canonical_digest(factual_rows) != query.data_digest:
        raise CausalRuntimeError("DATA_PIN_MISMATCH")
    if canonical_digest(intervention) != query.intervention_digest:
        raise CausalRuntimeError("INTERVENTION_PIN_MISMATCH")
    if query.scenario_branch == "main" or not query.scenario_branch.startswith("scenario/"):
        raise _Abstain("MAIN_CONTAMINATED")
    if query.contaminated_main:
        raise _Abstain("MAIN_CONTAMINATED")
    if query.ontology_release_digest != query.expected_release_digest:
        raise _Abstain("RELEASE_MISMATCH")
    if not factual_rows:
        raise _Abstain("MISSING_FACTUAL_SET")
    if query.unresolved_confounding:
        raise _Abstain("UNRESOLVED_CONFOUNDING")

    treatment_value = intervention.get("value")
    envelope = intervention.get("valid_envelope")
    if (
        not isinstance(envelope, list)
        or len(envelope) != 2
        or not isinstance(treatment_value, (int, float))
        or treatment_value < envelope[0]
        or treatment_value > envelope[1]
    ):
        raise _Abstain("OUT_OF_DOMAIN")

    strata: dict[str, dict[int, list[Decimal]]] = {}
    for row in factual_rows:
        try:
            stratum = str(row[query.adjustment])
            treated = int(row[query.treatment])
            observed = Decimal(str(row[query.outcome]))
        except (KeyError, TypeError, ValueError) as exc:
            raise CausalRuntimeError("FACTUAL_SCHEMA_INVALID") from exc
        if treated not in {0, 1}:
            raise _Abstain("POSITIVITY_FAILURE")
        strata.setdefault(stratum, {0: [], 1: []})[treated].append(observed)
    if any(not cells[0] or not cells[1] for cells in strata.values()):
        raise _Abstain("POSITIVITY_FAILURE")

    effects: list[Decimal] = []
    for cells in strata.values():
        control_mean = sum(cells[0], Decimal()) / len(cells[0])
        treated_mean = sum(cells[1], Decimal()) / len(cells[1])
        effects.append(treated_mean - control_mean)
    effect = sum(effects, Decimal()) / len(effects)
    return effect, strata


def estimate_intervention(
    query: CausalQuery, *, model: dict[str, Any], factual_rows: list[dict[str, Any]], intervention: dict[str, Any]
) -> CausalOutcome:
    """The population average treatment effect under the pinned
    intervention -- the same STRATIFIED_BACKDOOR_ATE the spike proved."""
    try:
        effect, _strata = _validate_and_stratify(query, model=model, factual_rows=factual_rows, intervention=intervention)
    except _Abstain as abstain:
        return _abstain_outcome(query, abstain.reason_code)
    return _seal(
        query=query,
        status="IDENTIFIED",
        reason_code=None,
        method="STRATIFIED_BACKDOOR_ATE",
        effect=effect,
        details=None,
        assumptions=(*_ASSUMPTIONS, f"adjustment:{query.adjustment}"),
    )


def estimate_counterfactual(
    query: CausalQuery,
    *,
    model: dict[str, Any],
    factual_rows: list[dict[str, Any]],
    intervention: dict[str, Any],
    unit_index: int,
) -> CausalOutcome:
    """A specific unit's imputed outcome under the opposite treatment:
    its observed outcome, adjusted by the within-stratum difference
    between the opposite and actual treatment-arm means -- the
    individual-level projection of the same stratified backdoor
    identification the population ATE uses."""
    try:
        _population_effect, strata = _validate_and_stratify(query, model=model, factual_rows=factual_rows, intervention=intervention)
    except _Abstain as abstain:
        return _abstain_outcome(query, abstain.reason_code)
    if not (0 <= unit_index < len(factual_rows)):
        raise CausalRuntimeError("UNIT_INDEX_OUT_OF_RANGE")
    unit = factual_rows[unit_index]
    stratum_key = str(unit[query.adjustment])
    actual_treatment = int(unit[query.treatment])
    observed_outcome = Decimal(str(unit[query.outcome]))
    cells = strata[stratum_key]
    opposite_treatment = 1 - actual_treatment
    opposite_mean = sum(cells[opposite_treatment], Decimal()) / len(cells[opposite_treatment])
    actual_mean = sum(cells[actual_treatment], Decimal()) / len(cells[actual_treatment])
    counterfactual_outcome = observed_outcome + (opposite_mean - actual_mean)
    return _seal(
        query=query,
        status="IDENTIFIED",
        reason_code=None,
        method="STRATIFIED_BACKDOOR_COUNTERFACTUAL",
        effect=counterfactual_outcome,
        details={
            "unit_index": str(unit_index),
            "observed_outcome": format(observed_outcome, "f"),
            "actual_treatment": str(actual_treatment),
        },
        assumptions=(*_ASSUMPTIONS, f"adjustment:{query.adjustment}"),
    )


def estimate_uncertainty(
    query: CausalQuery, *, model: dict[str, Any], factual_rows: list[dict[str, Any]], intervention: dict[str, Any]
) -> CausalOutcome:
    """A deterministic bootstrap confidence interval around the ATE:
    resamples each stratum's treated/control observations with
    replacement using a PRNG seeded by the pinned query.seed, so
    identical pinned inputs always reproduce identical bounds."""
    try:
        effect, strata = _validate_and_stratify(query, model=model, factual_rows=factual_rows, intervention=intervention)
    except _Abstain as abstain:
        return _abstain_outcome(query, abstain.reason_code)
    rng = random.Random(query.seed)
    bootstrap_effects: list[Decimal] = []
    for _ in range(BOOTSTRAP_RESAMPLES):
        resampled_effects: list[Decimal] = []
        for cells in strata.values():
            control_sample = [rng.choice(cells[0]) for _ in cells[0]]
            treated_sample = [rng.choice(cells[1]) for _ in cells[1]]
            control_mean = sum(control_sample, Decimal()) / len(control_sample)
            treated_mean = sum(treated_sample, Decimal()) / len(treated_sample)
            resampled_effects.append(treated_mean - control_mean)
        bootstrap_effects.append(sum(resampled_effects, Decimal()) / len(resampled_effects))
    ordered = sorted(bootstrap_effects)
    low_index = int(0.025 * len(ordered))
    high_index = min(len(ordered) - 1, int(0.975 * len(ordered)))
    return _seal(
        query=query,
        status="IDENTIFIED",
        reason_code=None,
        method="BOOTSTRAP_CI",
        effect=effect,
        details={
            "ci_low": format(ordered[low_index], "f"),
            "ci_high": format(ordered[high_index], "f"),
            "resamples": str(BOOTSTRAP_RESAMPLES),
        },
        assumptions=(*_ASSUMPTIONS, f"adjustment:{query.adjustment}"),
    )


def estimate_sensitivity(
    query: CausalQuery,
    *,
    model: dict[str, Any],
    factual_rows: list[dict[str, Any]],
    intervention: dict[str, Any],
    confounding_shift: Decimal,
) -> CausalOutcome:
    """An additive-confounding-shift sensitivity check: recomputes the
    ATE after shifting every control-arm observation by a hypothesized
    unmeasured-confounder-driven amount, reporting whether the
    effect's sign survives the shift."""
    try:
        effect, strata = _validate_and_stratify(query, model=model, factual_rows=factual_rows, intervention=intervention)
    except _Abstain as abstain:
        return _abstain_outcome(query, abstain.reason_code)
    shifted_effects: list[Decimal] = []
    for cells in strata.values():
        shifted_control = [value + confounding_shift for value in cells[0]]
        control_mean = sum(shifted_control, Decimal()) / len(shifted_control)
        treated_mean = sum(cells[1], Decimal()) / len(cells[1])
        shifted_effects.append(treated_mean - control_mean)
    shifted_effect = sum(shifted_effects, Decimal()) / len(shifted_effects)
    return _seal(
        query=query,
        status="IDENTIFIED",
        reason_code=None,
        method="ADDITIVE_CONFOUNDING_SHIFT_SENSITIVITY",
        effect=effect,
        details={
            "confounding_shift": format(confounding_shift, "f"),
            "shifted_effect": format(shifted_effect, "f"),
            "sign_flipped": str((effect > 0) != (shifted_effect > 0)),
        },
        assumptions=(*_ASSUMPTIONS, f"adjustment:{query.adjustment}"),
    )


def verify_reproduction(first: CausalOutcome, second: CausalOutcome) -> None:
    """Reject unexplained drift between runs with identical pinned inputs."""
    if (
        first.status != second.status
        or first.reason_code != second.reason_code
        or first.method != second.method
        or first.effect != second.effect
        or dict(first.details) != dict(second.details)
        or first.assumptions != second.assumptions
        or dict(first.lineage) != dict(second.lineage)
        or first.reproducibility_digest != second.reproducibility_digest
    ):
        raise CausalRuntimeError("REPRODUCIBILITY_DIGEST_MISMATCH")
