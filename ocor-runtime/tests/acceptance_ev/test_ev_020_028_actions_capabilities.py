from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

import pytest

from ocor_runtime.c5_actions import (
    TRANSITIONS_BY_ID,
    Action,
    ActionEvent,
    ActionFSM,
    ActionState,
    conceptual_transition_count,
)
from ocor_runtime.c6_capabilities import CapabilityAuthority
from ocor_runtime.errors import (
    AuthorizationError,
    InvalidTransition,
    TemporalGuardViolation,
)

pytestmark = pytest.mark.acceptance


def test_ev_020_all_act_t01_through_act_t31b_transitions_are_executable_contracts(fixed_now):
    expected = {f"ACT-T{number:02d}" for number in range(1, 31)} | {
        "ACT-T31a",
        "ACT-T31b",
    }
    assert set(TRANSITIONS_BY_ID) == expected
    assert len(TRANSITIONS_BY_ID) == 32
    assert conceptual_transition_count() == 31
    assert len({(item.source, item.event) for item in TRANSITIONS_BY_ID.values()}) == 32
    fsm = ActionFSM()
    for transition_id, spec in TRANSITIONS_BY_ID.items():
        action = Action(
            f"probe-{transition_id}",
            state=spec.source,
            not_before=fixed_now - timedelta(seconds=1),
            expires_at=fixed_now + timedelta(seconds=1),
        )
        occurred_at = (
            action.expires_at if spec.event is ActionEvent.EXPIRE else fixed_now
        )
        transitioned = fsm.transition_by_id(
            action,
            transition_id,
            occurred_at=occurred_at,
            actor="transition-probe",
        )
        assert transitioned.state is spec.target
        assert transitioned.history[-1].transition_id == transition_id


def test_ev_021_happy_path_transition_history_is_complete_and_tamper_evident(fixed_now):
    fsm = ActionFSM()
    action = Action(
        "action-1",
        not_before=fixed_now,
        expires_at=fixed_now + timedelta(minutes=10),
    )
    sequence = [
        (ActionEvent.SUBMIT, fixed_now - timedelta(seconds=3)),
        (ActionEvent.VALIDATE, fixed_now - timedelta(seconds=2)),
        (ActionEvent.AUTHORIZE, fixed_now - timedelta(seconds=1)),
        (ActionEvent.DISPATCH, fixed_now),
        (ActionEvent.START, fixed_now + timedelta(seconds=1)),
        (ActionEvent.SUCCEED, fixed_now + timedelta(seconds=2)),
    ]
    for event, occurred_at in sequence:
        action = fsm.transition(
            action,
            event,
            occurred_at=occurred_at,
            actor="acceptance-runner",
            expected_version=action.version,
        )
    assert action.state is ActionState.SUCCEEDED
    assert action.version == len(sequence)
    assert fsm.verify_history(action)


def test_ev_022_undefined_transition_is_rejected_without_mutating_action(fixed_now):
    fsm = ActionFSM()
    action = Action("action-1")
    with pytest.raises(InvalidTransition):
        fsm.transition(
            action,
            ActionEvent.START,
            occurred_at=fixed_now,
            actor="worker",
        )
    assert action.state is ActionState.DRAFT
    assert action.version == 0
    assert action.history == ()


def test_ev_023_temporal_execution_guards_use_inclusive_start_exclusive_end(fixed_now):
    fsm = ActionFSM()
    action = Action(
        "action-1",
        state=ActionState.READY,
        not_before=fixed_now,
        expires_at=fixed_now + timedelta(seconds=5),
    )
    with pytest.raises(TemporalGuardViolation):
        fsm.transition(
            action,
            ActionEvent.START,
            occurred_at=fixed_now - timedelta(microseconds=1),
            actor="worker",
        )
    assert fsm.transition(
        action, ActionEvent.START, occurred_at=fixed_now, actor="worker"
    ).state is ActionState.RUNNING
    with pytest.raises(TemporalGuardViolation):
        fsm.transition(
            action,
            ActionEvent.START,
            occurred_at=action.expires_at,
            actor="worker",
        )


def test_ev_024_audit_hash_chain_detects_evidence_tampering(fixed_now):
    fsm = ActionFSM()
    action = fsm.transition(
        Action("action-1"),
        ActionEvent.SUBMIT,
        occurred_at=fixed_now,
        actor="author",
        evidence={"ticket": "T-1"},
    )
    assert fsm.verify_history(action)
    forged_entry = replace(action.history[0], evidence={"ticket": "T-2"})
    forged = replace(action, history=(forged_entry,))
    assert not fsm.verify_history(forged)
    with pytest.raises(InvalidTransition):
        fsm.transition(
            forged,
            ActionEvent.VALIDATE,
            occurred_at=fixed_now,
            actor="attacker",
        )


def test_ev_025_compensation_and_identify_abstention_are_explicit_fsm_outcomes(fixed_now):
    fsm = ActionFSM()
    succeeded = Action(
        "action-1",
        not_before=fixed_now,
        expires_at=fixed_now + timedelta(minutes=1),
    )
    for event in (
        ActionEvent.SUBMIT,
        ActionEvent.VALIDATE,
        ActionEvent.AUTHORIZE,
        ActionEvent.DISPATCH,
        ActionEvent.START,
        ActionEvent.SUCCEED,
    ):
        succeeded = fsm.transition(
            succeeded, event, occurred_at=fixed_now, actor="operator"
        )
    compensating = fsm.transition(
        succeeded,
        ActionEvent.COMPENSATE,
        occurred_at=fixed_now,
        actor="operator",
    )
    compensated = fsm.transition(
        compensating,
        ActionEvent.COMPLETE,
        occurred_at=fixed_now,
        actor="operator",
    )
    assert compensated.state is ActionState.COMPENSATED
    ready = Action(
        "action-2",
        not_before=fixed_now,
        expires_at=fixed_now + timedelta(minutes=1),
    )
    for event in (
        ActionEvent.SUBMIT,
        ActionEvent.VALIDATE,
        ActionEvent.AUTHORIZE,
        ActionEvent.DISPATCH,
    ):
        ready = fsm.transition(ready, event, occurred_at=fixed_now, actor="agent")
    abstained = fsm.transition(
        ready,
        ActionEvent.ABSTAIN,
        occurred_at=fixed_now,
        actor="agent",
        evidence={"reason": "ambiguous identity"},
    )
    assert abstained.state is ActionState.ABSTAINED
    assert abstained.history[-1].transition_id == "ACT-T31b"


def test_ev_026_capability_lease_expiration_is_enforced_at_exact_boundary(fixed_now):
    authority = CapabilityAuthority()
    lease = authority.issue(
        subject="agent",
        capabilities=["action:read"],
        resources=["urn:ocor:action/1"],
        issued_at=fixed_now,
        expires_at=fixed_now + timedelta(seconds=5),
    )
    assert authority.authorize(
        lease, "action:read", "urn:ocor:action/1", at=fixed_now, subject="agent"
    )
    with pytest.raises(AuthorizationError):
        authority.authorize(
            lease,
            "action:read",
            "urn:ocor:action/1",
            at=lease.expires_at,
            subject="agent",
        )


def test_ev_027_capability_subject_operation_and_resource_scopes_do_not_leak(fixed_now):
    authority = CapabilityAuthority()
    lease = authority.issue(
        subject="agent",
        capabilities=["action:read"],
        resources=["urn:ocor:action/*"],
        issued_at=fixed_now,
        ttl=timedelta(minutes=1),
    )
    invalid_requests = [
        ("other", "action:read", "urn:ocor:action/1"),
        ("agent", "action:write", "urn:ocor:action/1"),
        ("agent", "action:read", "urn:ocor:evidence/1"),
    ]
    for subject, capability, resource in invalid_requests:
        with pytest.raises(AuthorizationError):
            authority.authorize(
                lease,
                capability,
                resource,
                at=fixed_now,
                subject=subject,
            )


def test_ev_028_delegation_revocation_and_usage_limits_cannot_be_bypassed(fixed_now):
    authority = CapabilityAuthority()
    parent = authority.issue(
        subject="parent",
        capabilities=["action:*"],
        resources=["urn:ocor:action/*"],
        issued_at=fixed_now,
        ttl=timedelta(minutes=5),
    )
    child = authority.issue(
        subject="child",
        capabilities=["action:read"],
        resources=["urn:ocor:action/1"],
        issued_at=fixed_now,
        expires_at=fixed_now + timedelta(minutes=1),
        parent=parent,
        max_uses=1,
    )
    authority.authorize(
        child,
        "action:read",
        "urn:ocor:action/1",
        at=fixed_now,
        subject="child",
        consume=True,
    )
    with pytest.raises(AuthorizationError):
        authority.authorize(
            child,
            "action:read",
            "urn:ocor:action/1",
            at=fixed_now,
            subject="child",
            consume=True,
        )
    authority.revoke(parent.lease_id, at=fixed_now)
    with pytest.raises(AuthorizationError):
        authority.authorize(
            child,
            "action:read",
            "urn:ocor:action/1",
            at=fixed_now,
            subject="child",
        )
    with pytest.raises(AuthorizationError):
        authority.issue(
            subject="escalated",
            capabilities=["admin"],
            resources=["*"],
            issued_at=fixed_now,
            expires_at=fixed_now + timedelta(minutes=1),
            parent=parent,
        )
