"""Pinned identify-or-abstain causal oracle with reproducibility sealing."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any


class CausalReproducibilityError(RuntimeError):
    """A pin, invariant, or reproducibility seal did not hold."""


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
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
    assumptions: tuple[str, ...]
    lineage: dict[str, Any]
    reproducibility_digest: str


def _sealed_outcome(
    *,
    query: CausalQuery,
    status: str,
    reason_code: str | None,
    method: str | None,
    effect: Decimal | None,
    assumptions: tuple[str, ...],
) -> CausalOutcome:
    lineage = {
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
    body = {
        "status": status,
        "reason_code": reason_code,
        "method": method,
        "effect": format(effect, "f") if effect is not None else None,
        "assumptions": assumptions,
        "lineage": lineage,
    }
    return CausalOutcome(
        status=status,
        reason_code=reason_code,
        method=method,
        effect=body["effect"],
        assumptions=assumptions,
        lineage=lineage,
        reproducibility_digest=canonical_digest(body),
    )


def _abstain(query: CausalQuery, reason_code: str) -> CausalOutcome:
    return _sealed_outcome(
        query=query,
        status="ABSTAIN",
        reason_code=reason_code,
        method=None,
        effect=None,
        assumptions=(),
    )


def execute(
    query: CausalQuery,
    *,
    model: dict[str, Any],
    factual_rows: list[dict[str, Any]],
    intervention: dict[str, Any],
) -> CausalOutcome:
    """Identify and estimate a stratified ATE or return a typed abstention."""

    if canonical_digest(model) != query.model_digest:
        raise CausalReproducibilityError("MODEL_PIN_MISMATCH")
    if canonical_digest(factual_rows) != query.data_digest:
        raise CausalReproducibilityError("DATA_PIN_MISMATCH")
    if canonical_digest(intervention) != query.intervention_digest:
        raise CausalReproducibilityError("INTERVENTION_PIN_MISMATCH")
    if query.scenario_branch == "main" or not query.scenario_branch.startswith("scenario/"):
        return _abstain(query, "MAIN_CONTAMINATED")
    if query.contaminated_main:
        return _abstain(query, "MAIN_CONTAMINATED")
    if query.ontology_release_digest != query.expected_release_digest:
        return _abstain(query, "RELEASE_MISMATCH")
    if not factual_rows:
        return _abstain(query, "MISSING_FACTUAL_SET")
    if query.unresolved_confounding:
        return _abstain(query, "UNRESOLVED_CONFOUNDING")

    treatment_value = intervention.get("value")
    envelope = intervention.get("valid_envelope")
    if (
        not isinstance(envelope, list)
        or len(envelope) != 2
        or not isinstance(treatment_value, (int, float))
        or treatment_value < envelope[0]
        or treatment_value > envelope[1]
    ):
        return _abstain(query, "OUT_OF_DOMAIN")

    strata: dict[str, dict[int, list[Decimal]]] = {}
    for row in factual_rows:
        try:
            stratum = str(row[query.adjustment])
            treated = int(row[query.treatment])
            observed = Decimal(str(row[query.outcome]))
        except (KeyError, TypeError, ValueError) as exc:
            raise CausalReproducibilityError("FACTUAL_SCHEMA_INVALID") from exc
        if treated not in {0, 1}:
            return _abstain(query, "POSITIVITY_FAILURE")
        strata.setdefault(stratum, {0: [], 1: []})[treated].append(observed)
    if any(not cells[0] or not cells[1] for cells in strata.values()):
        return _abstain(query, "POSITIVITY_FAILURE")

    effects: list[Decimal] = []
    for cells in strata.values():
        control = sum(cells[0], Decimal()) / len(cells[0])
        treated = sum(cells[1], Decimal()) / len(cells[1])
        effects.append(treated - control)
    effect = sum(effects, Decimal()) / len(effects)
    assumptions = (
        "consistency",
        "conditional_exchangeability",
        "positivity",
        f"adjustment:{query.adjustment}",
    )
    return _sealed_outcome(
        query=query,
        status="IDENTIFIED",
        reason_code=None,
        method="STRATIFIED_BACKDOOR_ATE",
        effect=effect,
        assumptions=assumptions,
    )


def verify_reproduction(first: CausalOutcome, second: CausalOutcome) -> None:
    """Reject unexplained drift between runs with identical pinned inputs."""

    if asdict(first) != asdict(second):
        raise CausalReproducibilityError("REPRODUCIBILITY_DIGEST_MISMATCH")

