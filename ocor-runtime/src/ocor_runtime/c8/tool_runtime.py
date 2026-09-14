"""C8 -- tool boundary: sandbox, budgets and kill switch.

Wires together, for every model/tool call, five real fail-closed
bindings, all enforced BEFORE any tool effect ever runs:

* **capability-bound** -- a real lease authorized by the sealed
  ``ocor_runtime.c6_capabilities.CapabilityAuthority`` (never
  self-granted; a revoked or unknown lease is refused here, before
  anything else, so nothing is charged or attempted on its behalf);
* **purpose-bound** -- a validated
  ``ocor_runtime.kernel.governed_context.GovernedContext`` (sealed,
  reused unmodified) that already fails closed on a missing purpose
  at construction, revalidated here defensively;
* **marking-bound** -- a real clearance check via the sealed
  ``ocor_runtime.c4_marking.MarkingEngine.require_authorized``;
* **stop-bound** -- a real emergency-stop epoch fence via
  OCOR-DEV-0044's sealed
  ``ocor_runtime.c6.safety.EmergencyStopController.guard_dispatch``;
* **budget-bound** -- a real token charge via the sealed
  ``ocor_runtime.c8_agent.TokenBudget.consume``, raised before the
  tool is ever attempted, never refunded or bypassed after the fact.

Only once every one of the five gates has passed does the actual tool
expression ever reach the sealed
``ocor_runtime.c8_agent.StrictSandbox`` for real AST-whitelisted
execution -- an escape-syntax attempt is refused there, exactly as it
always was, before the registered tool function itself is ever
called. A successful call returns an immutable ``ToolCallReceipt``
recording every gate it passed; a refused call never reaches the
sandbox at all for a capability/purpose/marking/stop/budget denial,
and never reaches the registered tool function for an escape-syntax
denial -- no tool effect in either case.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from ..c3_store import require_aware
from ..c4_marking import MarkingEngine, MarkingSet
from ..c6.safety import EmergencyStopController, SafetyError
from ..c6_capabilities import CapabilityAuthority, CapabilityLease
from ..c8_agent import StrictSandbox, TokenBudget
from ..errors import AuthorizationError, OCORError
from ..kernel.governed_context import GovernedContext


class ToolRuntimeError(OCORError):
    """A tool call was refused before producing any effect.
    ``reason_code`` identifies which of the five bindings denied it,
    mirroring the reason-code pattern already established by every
    other retained C1-C8 component this session."""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {message}")


@dataclass(frozen=True, slots=True)
class ToolCallReceipt:
    tool_name: str
    lease_id: str
    purpose: str
    tokens_spent: int
    stop_epoch: int
    result: Any
    called_at: datetime


class ToolCallRuntime:
    def __init__(
        self,
        *,
        sandbox: StrictSandbox,
        authority: CapabilityAuthority,
        marking_engine: MarkingEngine,
        stop: EmergencyStopController,
    ) -> None:
        self._sandbox = sandbox
        self._authority = authority
        self._marking_engine = marking_engine
        self._stop = stop

    def invoke(
        self,
        tool_name: str,
        expression: str,
        *,
        bindings: Mapping[str, Any] | None,
        lease: CapabilityLease | str,
        context: GovernedContext,
        content_marking: MarkingSet,
        clearance: MarkingSet,
        budget: TokenBudget,
        estimated_tokens: int,
        stop_epoch: int,
        at: datetime,
    ) -> ToolCallReceipt:
        instant = require_aware(at, field="at")

        try:
            authorized = self._authority.authorize(
                lease, f"tool:{tool_name}", tool_name, at=instant, subject=context.effective_principal_id, consume=True
            )
        except AuthorizationError as error:
            raise ToolRuntimeError("CAPABILITY_DENIED", str(error)) from error

        if not context.purpose:
            raise ToolRuntimeError("PURPOSE_REQUIRED", "a tool call requires a non-empty GovernedContext purpose")

        try:
            self._marking_engine.require_authorized(content_marking, clearance)
        except AuthorizationError as error:
            raise ToolRuntimeError("MARKING_DENIED", str(error)) from error

        try:
            self._stop.guard_dispatch(fenced_epoch=stop_epoch)
        except SafetyError as error:
            raise ToolRuntimeError("STOP_BOUND_DENIED", str(error)) from error

        charge = budget.consume(estimated_tokens, category=f"tool:{tool_name}")

        result = self._sandbox.execute(expression, bindings)

        return ToolCallReceipt(
            tool_name=tool_name,
            lease_id=authorized.lease_id,
            purpose=context.purpose,
            tokens_spent=charge.tokens,
            stop_epoch=stop_epoch,
            result=result,
            called_at=instant,
        )
