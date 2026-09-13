"""C2 -- policy-filtered planning: consistency and watermarks.

Implements the smallest contract-compliant slice of LLD v1.1 section
2.2's Unified Semantic Gateway algorithm step 3 ("valuta policy/
authority prima della query") combined with step 4's consistency
selection: a plan is computed entirely from the sealed
``PolicyDecisionPort`` (OCOR-DEV-0012/0034, reused unmodified) and
``WatermarkPort`` (OCOR-DEV-0012, reused unmodified) -- the real,
potentially expensive or disclosing backend data query
(``ProjectionReadPort.read``) is never issued to compute a plan. A
policy denial is decided before the watermark is ever consulted; a
watermark that does not satisfy the requested consistency yields
``PROJECTION_NOT_READY`` with the real, observable watermark that was
checked -- never a silent downgrade to ``BEST_AVAILABLE``, and never a
query against the actual backend data.
"""

from __future__ import annotations

from dataclasses import dataclass

from .ports import (
    C2Error,
    ConsistencyMode,
    NamedQueryRequest,
    PolicyDecisionPort,
    Watermark,
    WatermarkPort,
)

PERMIT = "PERMIT"


@dataclass(frozen=True, slots=True)
class ConsistencyPlan:
    """The outcome of planning: the requester's own required commit (or
    ``None`` for ``BEST_AVAILABLE``) alongside the real watermark that
    was consulted to produce it, so a caller can always show its work
    rather than trust a bare boolean."""

    required_commit: str | None
    observed_watermark: Watermark


class ConsistencyPlanner:
    """Plans whether a policy-permitted request's requested consistency
    can be honored, using only the sealed ``PolicyDecisionPort`` and
    ``WatermarkPort`` -- never the actual projection data query. Policy
    is evaluated first: an unregistered or otherwise denied query never
    even reaches the watermark check, let alone the backend."""

    def __init__(
        self,
        *,
        policy: PolicyDecisionPort,
        watermark_port: WatermarkPort,
        projection_id: str,
        branch: str,
    ) -> None:
        self._policy = policy
        self._watermark_port = watermark_port
        self._projection_id = projection_id
        self._branch = branch

    def plan(self, request: NamedQueryRequest) -> ConsistencyPlan:
        decision = self._policy.decide(request)
        if decision != PERMIT:
            raise C2Error("ARBITRARY_QUERY_FORBIDDEN", "named query is not a registered, authorized contract")

        observed = self._watermark_port.current(self._projection_id, self._branch)
        consistency = request.consistency
        if consistency.mode is ConsistencyMode.BEST_AVAILABLE:
            return ConsistencyPlan(required_commit=None, observed_watermark=observed)

        required_commit = consistency.required_commit
        if observed.canonical_commit != required_commit:
            raise C2Error(
                "PROJECTION_NOT_READY",
                f"watermark {observed.canonical_commit!r} does not yet satisfy required commit {required_commit!r}",
            )
        return ConsistencyPlan(required_commit=required_commit, observed_watermark=observed)
