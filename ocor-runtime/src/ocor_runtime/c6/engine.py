"""C6 — retained governed-action slice.

The smallest contract-compliant slice of LLD v1.1 section 3's
normative 44-transition C6 workflow (OCOR-DEV-0020's sealed
``spikes.c6_fsm_fidelity.generator`` proves the full transition table's
fidelity to the approved LLD; this task builds retained, executable
code for the representative path a single risk-bearing action takes
through it, not the full FSM): a proposed action must cross, in strict
order, Authority (``G-AUTHORITY``, via the sealed
``ocor_runtime.c6_capabilities.CapabilityAuthority``), Human Gate
(``G-APPROVAL`` / "Human Gate richiesto", ``ACT-T06``/``ACT-T08``),
Decision (``G-DECISION``, ``ACT-T10b``) and EMISSION-FENCE (via the
sealed ``ocor_runtime.c7_emission.EmissionFence``, ``ACT-T12``/
``ACT-T29``) before any simulated external effect is applied. Any gate
failure denies the action before the durable canonical commit or the
simulated effect ever happen.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..c3_store import AtomicOutboxStore, OutboxEvent, require_aware
from ..c6_capabilities import CapabilityAuthority, CapabilityLease
from ..c7_emission import EmissionFence, EmissionReceipt, EventSink
from ..errors import AuthorizationError, EmissionBlocked, OCORError


class GovernedActionError(OCORError):
    """A governed action was denied at one of its four gates. ``reason_code``
    identifies which gate (AUTHORITY_DENIED, APPROVAL_MISSING,
    DECISION_MISSING or DECISION_REJECTED), mirroring the reason-code
    pattern already established by the retained C3 adapter."""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {message}")


@dataclass(frozen=True, slots=True)
class ActionProposal:
    action_id: str
    subject: str
    capability: str
    resource: str
    aggregate_id: str
    risk_bearing: bool


@dataclass(frozen=True, slots=True)
class Approval:
    """The Human Gate disposition (``ACT-T08``/``ACT-T09a``/``ACT-T09b``)."""

    action_id: str
    approver: str
    approved: bool
    approved_at: datetime

    def __post_init__(self) -> None:
        require_aware(self.approved_at, field="approved_at")
        if not self.approver:
            raise ValueError("an Approval requires an approver")


@dataclass(frozen=True, slots=True)
class Decision:
    """The Decision gate disposition (``ACT-T10a``/``ACT-T10b``)."""

    action_id: str
    decided_by: str
    accepted: bool
    rationale: str
    decided_at: datetime

    def __post_init__(self) -> None:
        require_aware(self.decided_at, field="decided_at")
        if not self.decided_by:
            raise ValueError("a Decision requires a decider")
        if not self.rationale:
            raise ValueError("a Decision requires a rationale")


@dataclass(frozen=True, slots=True)
class ActionOutcome:
    action_id: str
    emission_receipt: EmissionReceipt
    simulated_effect: Any


class GovernedActionEngine:
    """Authority -> Human Gate -> Decision -> EMISSION-FENCE -> simulated
    effect, evaluated strictly in that order and fail-closed at every
    gate. No simulated effect is ever applied unless all four gates are
    satisfied.
    """

    def __init__(
        self,
        *,
        authority: CapabilityAuthority,
        store: AtomicOutboxStore,
        fence: EmissionFence,
    ) -> None:
        self._authority = authority
        self._store = store
        self._fence = fence

    def execute(
        self,
        proposal: ActionProposal,
        *,
        lease: CapabilityLease | str,
        approval: Approval | None,
        decision: Decision | None,
        sink: EventSink | Callable[[OutboxEvent], Any],
        at: datetime,
    ) -> ActionOutcome:
        instant = require_aware(at, field="at")

        # G-AUTHORITY (ACT-T04): principal, capability and resource scope.
        try:
            self._authority.authorize(
                lease,
                proposal.capability,
                proposal.resource,
                at=instant,
                subject=proposal.subject,
                consume=True,
            )
        except AuthorizationError as error:
            raise GovernedActionError("AUTHORITY_DENIED", str(error)) from error

        # Human Gate (ACT-T06/ACT-T07/ACT-T08/ACT-T09a/ACT-T09b): only
        # risk-bearing actions require a resolved approval; a
        # non-risk-bearing action's gate disposition is NOT_REQUIRED.
        if proposal.risk_bearing:
            if approval is None or approval.action_id != proposal.action_id:
                raise GovernedActionError(
                    "APPROVAL_MISSING", "a risk-bearing action requires a resolved Human Gate approval"
                )
            if not approval.approved:
                raise GovernedActionError("APPROVAL_MISSING", "Human Gate approval was not granted")

        # G-DECISION (ACT-T10a/ACT-T10b): a signed Decision is always required.
        if decision is None or decision.action_id != proposal.action_id:
            raise GovernedActionError("DECISION_MISSING", "a governed action requires a signed Decision")
        if not decision.accepted:
            raise GovernedActionError("DECISION_REJECTED", decision.rationale)

        # Canonical commit (ACT-T29/T30): durable, atomic aggregate + outbox event.
        write_result = self._store.write(
            proposal.aggregate_id,
            {"action_id": proposal.action_id, "status": "EXECUTED"},
            expected_version=None,
            writer_id=self._store.authoritative_writer,
            event_type="governed-action-executed",
            idempotency_key=proposal.action_id,
            occurred_at=instant,
        )

        # EMISSION-FENCE (ACT-T12/ACT-T14): the final atomic gate
        # immediately before the simulated effect; blocks on
        # uncommitted/tampered/out-of-order events.
        try:
            receipt = self._fence.emit(write_result.event, sink, at=instant)
        except EmissionBlocked:
            raise

        return ActionOutcome(proposal.action_id, receipt, receipt.sink_result)
