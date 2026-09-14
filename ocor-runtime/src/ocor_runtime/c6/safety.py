"""C6 -- compensation reconciliation, break-glass and emergency stop.

The smallest contract-compliant slice of LLD v1.1 sections 4.2/4.3 and
6's normative safety obligations, layered on the sealed 44-transition
table (OCOR-DEV-0042, ``ocor_runtime.c6.fsm``, reused unmodified) and
the sealed Human Gate dual-control coordinator (OCOR-DEV-0043,
``ocor_runtime.c6.human_gate``, reused unmodified only conceptually --
break-glass's own two-distinct-human requirement mirrors, but does not
import, Human Gate's separation-of-duties dedup, since break-glass has
no notion of distinct required roles). Reuses the sealed
``ocor_runtime.c2_identity.IdentityRegistry`` (unmodified) to refuse an
unresolved break-glass approver.

Three real safety mechanisms, each producing immutable evidence:

* ``EmergencyStopController`` -- the approved ``NORMAL -> STOPPING ->
  STOPPED -> RESET_PENDING -> NORMAL`` machine (LLD 4.3). Accepting a
  stop atomically increments a monotonic ``stop_epoch`` under a real
  lock; ``guard_dispatch`` fails closed unless the system is
  ``NORMAL`` *and* the presented fencing epoch is exactly the current
  one -- a command fenced to any other epoch, older or from a prior
  stop/reset cycle, can never dispatch, so a reset never silently
  re-enables a lease issued before it. Reset requires dual control
  (two distinct, resolved human approvers).
* ``BreakGlassController`` -- a bounded, dual-human-approved
  exceptional grant (LLD 4.2): requires a typed reason, an incident
  reference, a minimal scope, exactly two distinct resolved human
  approvers, and a TTL bounded by ``MAX_BREAK_GLASS_TTL``.
  ``authorize`` is a pure function of (grant, capability, at) re-run
  on every use -- an expired grant, one already revoked, one
  requesting a capability on the fixed ``FORBIDDEN_BREAK_GLASS_CAPABILITIES``
  denylist (create a Decision, reduce marking, disable
  provenance/audit, ignore emergency stop, change the release pin,
  authorize R3 without quorum, or access outside compartment), or one
  used while an emergency stop is active, is refused every time, never
  only at grant time. Every successful use requires a non-empty review
  reference, making the LLD's "review obbligatoria" structural.
* ``OutcomeReconciler`` -- LLD ``ACT-T18a``/``T18b``/``T20a``-``c``/
  ``T21``-``T21e``/``T24``/``T25``'s ambiguous-outcome and compensation
  reconciliation path: an ambiguous timeout suspends retry and opens
  reconciliation; real ``Evidence`` resolves it to confirmed/failed
  (or compensated/compensation-failed); no evidence before the
  reconciliation deadline escalates to ``INDETERMINATE`` and opens
  adjudication, never inferring an outcome. ``require_may_auto_retry``
  is the task's own core negative claim made executable: an ambiguous
  outcome whose effect is not proven idempotent can never be
  auto-retried, no matter how long it has been ambiguous.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from ..c2_identity import IdentityRegistry
from ..c3_store import require_aware
from ..errors import OCORError

MAX_BREAK_GLASS_TTL = timedelta(minutes=15)

FORBIDDEN_BREAK_GLASS_CAPABILITIES = frozenset(
    {
        "create_decision",
        "reduce_marking",
        "disable_provenance",
        "disable_audit",
        "ignore_emergency_stop",
        "change_release_pin",
        "authorize_r3_without_quorum",
        "access_outside_compartment",
    }
)


class SafetyError(OCORError):
    """A safety mechanism refused an operation. ``reason_code``
    identifies why, mirroring the reason-code pattern already
    established by every other retained C1-C8 component this
    session."""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {message}")


class StopStatus(str, Enum):
    NORMAL = "NORMAL"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    RESET_PENDING = "RESET_PENDING"


@dataclass(frozen=True, slots=True)
class StopEvent:
    epoch: int
    status: StopStatus
    reason: str
    at: datetime


class EmergencyStopController:
    """The approved emergency-stop FSM with a real lock around its
    epoch and status, so a concurrent activation and dispatch attempt
    can never race past each other."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._status = StopStatus.NORMAL
        self._epoch = 0
        self._history: list[StopEvent] = []

    @property
    def status(self) -> StopStatus:
        with self._lock:
            return self._status

    @property
    def epoch(self) -> int:
        with self._lock:
            return self._epoch

    @property
    def history(self) -> tuple[StopEvent, ...]:
        with self._lock:
            return tuple(self._history)

    def activate(self, *, reason: str, at: datetime) -> StopEvent:
        instant = require_aware(at, field="at")
        if not reason:
            raise ValueError("an emergency stop requires a reason")
        with self._lock:
            if self._status is not StopStatus.NORMAL:
                raise SafetyError("INVALID_STOP_TRANSITION", f"cannot activate stop from {self._status.value}")
            self._epoch += 1
            self._status = StopStatus.STOPPING
            event = StopEvent(epoch=self._epoch, status=self._status, reason=reason, at=instant)
            self._history.append(event)
            return event

    def finish_draining(self, *, at: datetime) -> StopEvent:
        instant = require_aware(at, field="at")
        with self._lock:
            if self._status is not StopStatus.STOPPING:
                raise SafetyError("INVALID_STOP_TRANSITION", f"cannot finish draining from {self._status.value}")
            self._status = StopStatus.STOPPED
            event = StopEvent(epoch=self._epoch, status=self._status, reason="drain complete", at=instant)
            self._history.append(event)
            return event

    def request_reset(self, *, approvers: tuple[str, str], identities: IdentityRegistry, at: datetime) -> StopEvent:
        instant = require_aware(at, field="at")
        distinct = set(approvers)
        if len(distinct) != 2:
            raise SafetyError("RESET_REQUIRES_DUAL_CONTROL", "reset requires exactly two distinct human approvers")
        for principal in distinct:
            if identities.get(principal) is None:
                raise SafetyError("RESET_REQUIRES_DUAL_CONTROL", f"unresolved approver: {principal!r}")
        with self._lock:
            if self._status is not StopStatus.STOPPED:
                raise SafetyError("INVALID_STOP_TRANSITION", f"cannot request reset from {self._status.value}")
            self._status = StopStatus.RESET_PENDING
            event = StopEvent(epoch=self._epoch, status=self._status, reason="reset requested", at=instant)
            self._history.append(event)
            return event

    def confirm_reset(self, *, at: datetime) -> StopEvent:
        instant = require_aware(at, field="at")
        with self._lock:
            if self._status is not StopStatus.RESET_PENDING:
                raise SafetyError("INVALID_STOP_TRANSITION", f"cannot confirm reset from {self._status.value}")
            # A brand-new epoch: never re-enables a lease or command
            # fenced to the pre-stop epoch, even now that the system
            # is NORMAL again.
            self._epoch += 1
            self._status = StopStatus.NORMAL
            event = StopEvent(epoch=self._epoch, status=self._status, reason="reset confirmed, new epoch issued", at=instant)
            self._history.append(event)
            return event

    def guard_dispatch(self, *, fenced_epoch: int) -> None:
        with self._lock:
            if self._status is not StopStatus.NORMAL:
                raise SafetyError("SYSTEM_NOT_NORMAL", f"emergency stop is {self._status.value}, dispatch is blocked")
            if fenced_epoch != self._epoch:
                raise SafetyError("STOP_EPOCH_STALE", f"command fenced to epoch {fenced_epoch}, current epoch is {self._epoch}")


@dataclass(frozen=True, slots=True)
class BreakGlassGrant:
    grant_id: str
    reason: str
    incident_ref: str
    scope: str
    approvers: tuple[str, str]
    granted_at: datetime
    ttl: timedelta

    def __post_init__(self) -> None:
        require_aware(self.granted_at, field="granted_at")
        if not self.grant_id:
            raise ValueError("a BreakGlassGrant requires a grant_id")
        if not self.reason:
            raise ValueError("a BreakGlassGrant requires a typed reason")
        if not self.incident_ref:
            raise ValueError("a BreakGlassGrant requires an incident_ref")
        if not self.scope:
            raise ValueError("a BreakGlassGrant requires a minimal scope")
        if len(set(self.approvers)) != 2:
            raise ValueError("a BreakGlassGrant requires exactly two distinct human approvers")
        if self.ttl <= timedelta(0) or self.ttl > MAX_BREAK_GLASS_TTL:
            raise ValueError(f"break-glass ttl must be positive and at most {MAX_BREAK_GLASS_TTL}")

    @property
    def expires_at(self) -> datetime:
        return self.granted_at + self.ttl


@dataclass(frozen=True, slots=True)
class BreakGlassUse:
    """Immutable evidence of one authorized use -- the mandatory
    review reference is captured on the record itself, never
    optional."""

    grant_id: str
    capability: str
    review_ref: str
    used_at: datetime


class BreakGlassController:
    def __init__(self, *, identities: IdentityRegistry, stop: EmergencyStopController) -> None:
        self._identities = identities
        self._stop = stop
        self._revoked_grant_ids: set[str] = set()

    def grant(
        self,
        *,
        grant_id: str,
        reason: str,
        incident_ref: str,
        scope: str,
        approvers: tuple[str, str],
        at: datetime,
        ttl: timedelta,
    ) -> BreakGlassGrant:
        instant = require_aware(at, field="at")
        distinct = sorted(set(approvers))
        if len(distinct) != 2:
            raise SafetyError("BREAK_GLASS_REQUIRES_TWO_DISTINCT_HUMANS", "break-glass requires exactly two distinct human approvers")
        for principal in distinct:
            if self._identities.get(principal) is None:
                raise SafetyError("BREAK_GLASS_REQUIRES_TWO_DISTINCT_HUMANS", f"unresolved approver: {principal!r}")
        first, second = distinct
        return BreakGlassGrant(
            grant_id=grant_id,
            reason=reason,
            incident_ref=incident_ref,
            scope=scope,
            approvers=(first, second),
            granted_at=instant,
            ttl=ttl,
        )

    def revoke(self, grant: BreakGlassGrant) -> None:
        self._revoked_grant_ids.add(grant.grant_id)

    def authorize(self, grant: BreakGlassGrant, *, capability: str, review_ref: str, at: datetime) -> BreakGlassUse:
        instant = require_aware(at, field="at")
        if grant.grant_id in self._revoked_grant_ids:
            raise SafetyError("BREAK_GLASS_EXPIRED", f"grant {grant.grant_id!r} was revoked")
        if instant >= grant.expires_at:
            raise SafetyError("BREAK_GLASS_EXPIRED", f"grant {grant.grant_id!r} expired at {grant.expires_at.isoformat()}")
        if capability in FORBIDDEN_BREAK_GLASS_CAPABILITIES:
            raise SafetyError("BREAK_GLASS_FORBIDDEN_CAPABILITY", f"break-glass can never authorize {capability!r}")
        if self._stop.status is not StopStatus.NORMAL:
            raise SafetyError("BREAK_GLASS_STOP_ACTIVE", "break-glass can never override an active emergency stop")
        if not review_ref:
            raise SafetyError("BREAK_GLASS_REVIEW_REQUIRED", "every break-glass use requires a mandatory review reference")
        return BreakGlassUse(grant_id=grant.grant_id, capability=capability, review_ref=review_ref, used_at=instant)


class OutcomeStatus(str, Enum):
    CONFIRMED = "EXECUTION_CONFIRMED"
    FAILED = "EXECUTION_FAILED"
    UNKNOWN = "EXECUTION_UNKNOWN"
    INDETERMINATE = "EXECUTION_INDETERMINATE"
    COMPENSATED = "COMPENSATED"
    COMPENSATION_FAILED = "COMPENSATION_FAILED"
    COMPENSATION_UNKNOWN = "COMPENSATION_UNKNOWN"
    COMPENSATION_INDETERMINATE = "COMPENSATION_INDETERMINATE"


_AMBIGUOUS_STATUSES = frozenset(
    {
        OutcomeStatus.UNKNOWN,
        OutcomeStatus.COMPENSATION_UNKNOWN,
        OutcomeStatus.INDETERMINATE,
        OutcomeStatus.COMPENSATION_INDETERMINATE,
    }
)
_RESOLVABLE_STATUSES = frozenset({OutcomeStatus.UNKNOWN, OutcomeStatus.COMPENSATION_UNKNOWN})


@dataclass(frozen=True, slots=True)
class ReconciliationRecord:
    command_id: str
    status: OutcomeStatus
    idempotent_effect_proven: bool
    recorded_at: datetime
    note: str


class OutcomeReconciler:
    def __init__(self) -> None:
        self._records: dict[str, ReconciliationRecord] = {}

    @property
    def records(self) -> tuple[ReconciliationRecord, ...]:
        return tuple(self._records.values())

    def status(self, command_id: str) -> OutcomeStatus:
        return self._require_record(command_id).status

    def _require_record(self, command_id: str) -> ReconciliationRecord:
        record = self._records.get(command_id)
        if record is None:
            raise SafetyError("UNKNOWN_COMMAND", f"no reconciliation record for {command_id!r}")
        return record

    def mark_ambiguous(
        self, command_id: str, *, idempotent_effect_proven: bool, at: datetime, note: str = "ambiguous timeout"
    ) -> ReconciliationRecord:
        instant = require_aware(at, field="at")
        record = ReconciliationRecord(
            command_id=command_id, status=OutcomeStatus.UNKNOWN, idempotent_effect_proven=idempotent_effect_proven, recorded_at=instant, note=note
        )
        self._records[command_id] = record
        return record

    def mark_compensation_ambiguous(
        self,
        command_id: str,
        *,
        idempotent_effect_proven: bool,
        at: datetime,
        note: str = "compensation ambiguous timeout",
    ) -> ReconciliationRecord:
        instant = require_aware(at, field="at")
        record = ReconciliationRecord(
            command_id=command_id,
            status=OutcomeStatus.COMPENSATION_UNKNOWN,
            idempotent_effect_proven=idempotent_effect_proven,
            recorded_at=instant,
            note=note,
        )
        self._records[command_id] = record
        return record

    def resolve_with_evidence(self, command_id: str, *, effect_confirmed: bool, at: datetime) -> ReconciliationRecord:
        instant = require_aware(at, field="at")
        previous = self._require_record(command_id)
        if previous.status not in _RESOLVABLE_STATUSES:
            raise SafetyError("INVALID_RECONCILIATION_TRANSITION", f"cannot resolve from {previous.status.value}")
        if previous.status is OutcomeStatus.UNKNOWN:
            new_status = OutcomeStatus.CONFIRMED if effect_confirmed else OutcomeStatus.FAILED
        else:
            new_status = OutcomeStatus.COMPENSATED if effect_confirmed else OutcomeStatus.COMPENSATION_FAILED
        record = ReconciliationRecord(
            command_id=command_id,
            status=new_status,
            idempotent_effect_proven=previous.idempotent_effect_proven,
            recorded_at=instant,
            note="resolved by Evidence",
        )
        self._records[command_id] = record
        return record

    def escalate_if_deadline_passed(self, command_id: str, *, at: datetime, deadline: datetime) -> ReconciliationRecord:
        instant = require_aware(at, field="at")
        require_aware(deadline, field="deadline")
        previous = self._require_record(command_id)
        if previous.status not in _RESOLVABLE_STATUSES:
            raise SafetyError("INVALID_RECONCILIATION_TRANSITION", f"cannot escalate from {previous.status.value}")
        if instant < deadline:
            return previous
        new_status = OutcomeStatus.INDETERMINATE if previous.status is OutcomeStatus.UNKNOWN else OutcomeStatus.COMPENSATION_INDETERMINATE
        record = ReconciliationRecord(
            command_id=command_id,
            status=new_status,
            idempotent_effect_proven=previous.idempotent_effect_proven,
            recorded_at=instant,
            note="reconciliation deadline passed; adjudication opened",
        )
        self._records[command_id] = record
        return record

    def require_may_auto_retry(self, command_id: str) -> None:
        record = self._records.get(command_id)
        if record is None:
            return
        if record.status in _AMBIGUOUS_STATUSES and not record.idempotent_effect_proven:
            raise SafetyError(
                "AUTO_RETRY_BLOCKED_AMBIGUOUS_NON_IDEMPOTENT",
                f"{command_id!r} has an ambiguous, non-idempotent-proven outcome and cannot be auto-retried",
            )
