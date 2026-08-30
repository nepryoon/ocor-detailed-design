from __future__ import annotations

from datetime import timedelta

import pytest

from ocor_runtime.c5_actions import Action, ActionEvent, ActionFSM, ActionState
from ocor_runtime.errors import TemporalGuardViolation

pytestmark = pytest.mark.backend_assumption


def test_ba05_action_window_is_start_inclusive_and_end_exclusive(fixed_now):
    fsm = ActionFSM()
    action = Action(
        "action-1",
        state=ActionState.READY,
        not_before=fixed_now,
        expires_at=fixed_now + timedelta(minutes=5),
    )
    with pytest.raises(TemporalGuardViolation):
        fsm.transition(
            action,
            ActionEvent.START,
            occurred_at=fixed_now - timedelta(microseconds=1),
            actor="worker",
        )
    started = fsm.transition(
        action,
        ActionEvent.START,
        occurred_at=fixed_now,
        actor="worker",
    )
    assert started.state is ActionState.RUNNING

    at_expiry = Action(
        "action-2",
        state=ActionState.READY,
        not_before=fixed_now,
        expires_at=fixed_now + timedelta(minutes=5),
    )
    with pytest.raises(TemporalGuardViolation):
        fsm.transition(
            at_expiry,
            ActionEvent.START,
            occurred_at=at_expiry.expires_at,
            actor="worker",
        )


def test_ba05_expire_event_is_legal_only_at_or_after_deadline(fixed_now):
    fsm = ActionFSM()
    action = Action(
        "action-1",
        state=ActionState.SCHEDULED,
        not_before=fixed_now,
        expires_at=fixed_now + timedelta(minutes=5),
    )
    with pytest.raises(TemporalGuardViolation):
        fsm.transition(
            action,
            ActionEvent.EXPIRE,
            occurred_at=fixed_now,
            actor="scheduler",
        )
    expired = fsm.transition(
        action,
        ActionEvent.EXPIRE,
        occurred_at=action.expires_at,
        actor="scheduler",
    )
    assert expired.state is ActionState.EXPIRED


def test_ba05_audit_clock_cannot_move_backwards(fixed_now):
    fsm = ActionFSM()
    proposed = fsm.transition(
        Action("action-1"),
        ActionEvent.SUBMIT,
        occurred_at=fixed_now,
        actor="author",
    )
    with pytest.raises(TemporalGuardViolation):
        fsm.transition(
            proposed,
            ActionEvent.VALIDATE,
            occurred_at=fixed_now - timedelta(seconds=1),
            actor="validator",
        )


def test_ba05_naive_datetimes_fail_closed(fixed_now):
    with pytest.raises(TemporalGuardViolation):
        Action(
            "action-1",
            not_before=fixed_now.replace(tzinfo=None),
            expires_at=fixed_now + timedelta(minutes=1),
        )

