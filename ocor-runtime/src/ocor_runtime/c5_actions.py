"""C5 — the complete ACT-T01…ACT-T31b action state machine."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from .canonical import canonical_sha256
from .c3_store import freeze_json, require_aware
from .errors import ConcurrencyConflict, InvalidTransition, TemporalGuardViolation


class ActionState(str, Enum):
    DRAFT = "DRAFT"
    PROPOSED = "PROPOSED"
    VALIDATED = "VALIDATED"
    AUTHORIZED = "AUTHORIZED"
    SCHEDULED = "SCHEDULED"
    READY = "READY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    COMPENSATING = "COMPENSATING"
    COMPENSATED = "COMPENSATED"
    REJECTED = "REJECTED"
    ABSTAINED = "ABSTAINED"


class ActionEvent(str, Enum):
    SUBMIT = "SUBMIT"
    CANCEL = "CANCEL"
    VALIDATE = "VALIDATE"
    REJECT = "REJECT"
    AUTHORIZE = "AUTHORIZE"
    SCHEDULE = "SCHEDULE"
    DISPATCH = "DISPATCH"
    REVOKE = "REVOKE"
    ACTIVATE = "ACTIVATE"
    RESCHEDULE = "RESCHEDULE"
    EXPIRE = "EXPIRE"
    START = "START"
    DEFER = "DEFER"
    PAUSE = "PAUSE"
    SUCCEED = "SUCCEED"
    FAIL = "FAIL"
    RESUME = "RESUME"
    RETRY = "RETRY"
    COMPENSATE = "COMPENSATE"
    COMPLETE = "COMPLETE"
    ABSTAIN = "ABSTAIN"


@dataclass(frozen=True, slots=True)
class TransitionSpec:
    transition_id: str
    source: ActionState
    event: ActionEvent
    target: ActionState
    enforces_action_window: bool = False


_SPECS = (
    TransitionSpec("ACT-T01", ActionState.DRAFT, ActionEvent.SUBMIT, ActionState.PROPOSED),
    TransitionSpec("ACT-T02", ActionState.DRAFT, ActionEvent.CANCEL, ActionState.CANCELLED),
    TransitionSpec("ACT-T03", ActionState.PROPOSED, ActionEvent.VALIDATE, ActionState.VALIDATED),
    TransitionSpec("ACT-T04", ActionState.PROPOSED, ActionEvent.REJECT, ActionState.REJECTED),
    TransitionSpec("ACT-T05", ActionState.PROPOSED, ActionEvent.CANCEL, ActionState.CANCELLED),
    TransitionSpec("ACT-T06", ActionState.VALIDATED, ActionEvent.AUTHORIZE, ActionState.AUTHORIZED),
    TransitionSpec("ACT-T07", ActionState.VALIDATED, ActionEvent.REJECT, ActionState.REJECTED),
    TransitionSpec("ACT-T08", ActionState.VALIDATED, ActionEvent.CANCEL, ActionState.CANCELLED),
    TransitionSpec("ACT-T09", ActionState.AUTHORIZED, ActionEvent.SCHEDULE, ActionState.SCHEDULED),
    TransitionSpec(
        "ACT-T10",
        ActionState.AUTHORIZED,
        ActionEvent.DISPATCH,
        ActionState.READY,
        True,
    ),
    TransitionSpec("ACT-T11", ActionState.AUTHORIZED, ActionEvent.REVOKE, ActionState.CANCELLED),
    TransitionSpec(
        "ACT-T12",
        ActionState.SCHEDULED,
        ActionEvent.ACTIVATE,
        ActionState.READY,
        True,
    ),
    TransitionSpec("ACT-T13", ActionState.SCHEDULED, ActionEvent.RESCHEDULE, ActionState.SCHEDULED),
    TransitionSpec("ACT-T14", ActionState.SCHEDULED, ActionEvent.EXPIRE, ActionState.EXPIRED),
    TransitionSpec("ACT-T15", ActionState.SCHEDULED, ActionEvent.CANCEL, ActionState.CANCELLED),
    TransitionSpec(
        "ACT-T16", ActionState.READY, ActionEvent.START, ActionState.RUNNING, True
    ),
    TransitionSpec("ACT-T17", ActionState.READY, ActionEvent.DEFER, ActionState.SCHEDULED),
    TransitionSpec("ACT-T18", ActionState.READY, ActionEvent.EXPIRE, ActionState.EXPIRED),
    TransitionSpec("ACT-T19", ActionState.READY, ActionEvent.CANCEL, ActionState.CANCELLED),
    TransitionSpec("ACT-T20", ActionState.RUNNING, ActionEvent.PAUSE, ActionState.PAUSED),
    TransitionSpec("ACT-T21", ActionState.RUNNING, ActionEvent.SUCCEED, ActionState.SUCCEEDED),
    TransitionSpec("ACT-T22", ActionState.RUNNING, ActionEvent.FAIL, ActionState.FAILED),
    TransitionSpec("ACT-T23", ActionState.RUNNING, ActionEvent.CANCEL, ActionState.CANCELLED),
    TransitionSpec(
        "ACT-T24", ActionState.PAUSED, ActionEvent.RESUME, ActionState.RUNNING, True
    ),
    TransitionSpec("ACT-T25", ActionState.PAUSED, ActionEvent.FAIL, ActionState.FAILED),
    TransitionSpec("ACT-T26", ActionState.PAUSED, ActionEvent.CANCEL, ActionState.CANCELLED),
    TransitionSpec("ACT-T27", ActionState.FAILED, ActionEvent.RETRY, ActionState.READY),
    TransitionSpec(
        "ACT-T28", ActionState.FAILED, ActionEvent.COMPENSATE, ActionState.COMPENSATING
    ),
    TransitionSpec(
        "ACT-T29", ActionState.SUCCEEDED, ActionEvent.COMPENSATE, ActionState.COMPENSATING
    ),
    TransitionSpec(
        "ACT-T30", ActionState.COMPENSATING, ActionEvent.COMPLETE, ActionState.COMPENSATED
    ),
    TransitionSpec(
        "ACT-T31a", ActionState.COMPENSATING, ActionEvent.FAIL, ActionState.FAILED
    ),
    TransitionSpec("ACT-T31b", ActionState.READY, ActionEvent.ABSTAIN, ActionState.ABSTAINED),
)

TRANSITIONS = MappingProxyType(
    {(spec.source, spec.event): spec for spec in _SPECS}
)
TRANSITIONS_BY_ID = MappingProxyType({spec.transition_id: spec for spec in _SPECS})


def conceptual_transition_count() -> int:
    """T31 has two normative outcomes (31a and 31b), hence 31 decisions."""

    return 31


TERMINAL_STATES = frozenset(
    {
        ActionState.CANCELLED,
        ActionState.EXPIRED,
        ActionState.COMPENSATED,
        ActionState.REJECTED,
        ActionState.ABSTAINED,
    }
)


@dataclass(frozen=True, slots=True)
class ActionAuditEntry:
    transition_id: str
    source: ActionState
    event: ActionEvent
    target: ActionState
    occurred_at: datetime
    actor: str
    evidence: Mapping[str, Any]
    previous_hash: str
    entry_hash: str


@dataclass(frozen=True, slots=True)
class Action:
    action_id: str
    state: ActionState = ActionState.DRAFT
    version: int = 0
    not_before: datetime | None = None
    expires_at: datetime | None = None
    history: tuple[ActionAuditEntry, ...] = ()

    def __post_init__(self) -> None:
        if not self.action_id:
            raise ValueError("action_id must be non-empty")
        if self.version < 0:
            raise ValueError("action version cannot be negative")
        if self.not_before is not None:
            require_aware(self.not_before, field="not_before")
        if self.expires_at is not None:
            require_aware(self.expires_at, field="expires_at")
        if (
            self.not_before is not None
            and self.expires_at is not None
            and self.not_before >= self.expires_at
        ):
            raise TemporalGuardViolation("not_before must precede expires_at")


def _coerce_state(value: ActionState | str) -> ActionState:
    try:
        return value if isinstance(value, ActionState) else ActionState(value)
    except ValueError as exc:
        raise InvalidTransition(f"unknown action state: {value!r}") from exc


def _coerce_event(value: ActionEvent | str) -> ActionEvent:
    try:
        return value if isinstance(value, ActionEvent) else ActionEvent(value)
    except ValueError as exc:
        raise InvalidTransition(f"unknown action event: {value!r}") from exc


class ActionFSM:
    transitions = TRANSITIONS
    transitions_by_id = TRANSITIONS_BY_ID

    def allowed_events(self, state: ActionState | str) -> tuple[ActionEvent, ...]:
        current = _coerce_state(state)
        return tuple(
            sorted(
                (event for source, event in self.transitions if source is current),
                key=lambda event: event.value,
            )
        )

    @staticmethod
    def _check_window(action: Action, spec: TransitionSpec, instant: datetime) -> None:
        if spec.event is ActionEvent.EXPIRE:
            if action.expires_at is None or instant < action.expires_at:
                raise TemporalGuardViolation(
                    "EXPIRE is legal only at or after the action expiration"
                )
            return
        if not spec.enforces_action_window:
            return
        if action.not_before is not None and instant < action.not_before:
            raise TemporalGuardViolation("action is not yet active")
        if action.expires_at is not None and instant >= action.expires_at:
            raise TemporalGuardViolation("action capability window has expired")

    def transition(
        self,
        action: Action,
        event: ActionEvent | str,
        *,
        occurred_at: datetime,
        actor: str,
        evidence: Mapping[str, Any] | None = None,
        expected_version: int | None = None,
    ) -> Action:
        if not actor:
            raise ValueError("transition actor must be non-empty")
        instant = require_aware(occurred_at, field="occurred_at")
        if expected_version is not None and expected_version != action.version:
            raise ConcurrencyConflict(
                f"expected action version {expected_version}, found {action.version}"
            )
        if action.history and not self.verify_history(action):
            raise InvalidTransition("action audit history failed integrity verification")
        selected_event = _coerce_event(event)
        spec = self.transitions.get((action.state, selected_event))
        if spec is None:
            raise InvalidTransition(
                f"event {selected_event.value} is not legal from {action.state.value}"
            )
        if action.history and instant < action.history[-1].occurred_at:
            raise TemporalGuardViolation("action history cannot move backwards in time")
        self._check_window(action, spec, instant)

        stable_evidence = dict(evidence or {})
        previous_hash = action.history[-1].entry_hash if action.history else "0" * 64
        audit_payload = {
            "actionId": action.action_id,
            "transitionId": spec.transition_id,
            "source": spec.source.value,
            "event": spec.event.value,
            "target": spec.target.value,
            "occurredAt": instant.isoformat(),
            "actor": actor,
            "evidence": stable_evidence,
            "previousHash": previous_hash,
            "version": action.version + 1,
        }
        entry = ActionAuditEntry(
            transition_id=spec.transition_id,
            source=spec.source,
            event=spec.event,
            target=spec.target,
            occurred_at=instant,
            actor=actor,
            evidence=freeze_json(stable_evidence),
            previous_hash=previous_hash,
            entry_hash=canonical_sha256(audit_payload),
        )
        return replace(
            action,
            state=spec.target,
            version=action.version + 1,
            history=action.history + (entry,),
        )

    def transition_by_id(
        self,
        action: Action,
        transition_id: str,
        **kwargs: Any,
    ) -> Action:
        spec = self.transitions_by_id.get(transition_id)
        if spec is None:
            raise InvalidTransition(f"unknown transition id: {transition_id!r}")
        if action.state is not spec.source:
            raise InvalidTransition(
                f"{transition_id} requires state {spec.source.value}, found {action.state.value}"
            )
        return self.transition(action, spec.event, **kwargs)

    @staticmethod
    def verify_history(action: Action) -> bool:
        previous_hash = "0" * 64
        previous_state = ActionState.DRAFT
        for version, entry in enumerate(action.history, start=1):
            if entry.previous_hash != previous_hash or entry.source is not previous_state:
                return False
            payload = {
                "actionId": action.action_id,
                "transitionId": entry.transition_id,
                "source": entry.source.value,
                "event": entry.event.value,
                "target": entry.target.value,
                "occurredAt": entry.occurred_at.isoformat(),
                "actor": entry.actor,
                "evidence": entry.evidence,
                "previousHash": entry.previous_hash,
                "version": version,
            }
            if canonical_sha256(payload) != entry.entry_hash:
                return False
            previous_hash = entry.entry_hash
            previous_state = entry.target
        return action.version == len(action.history) and action.state is previous_state


FSM = ActionFSM
