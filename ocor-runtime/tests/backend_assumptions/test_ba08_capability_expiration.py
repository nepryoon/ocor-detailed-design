from __future__ import annotations

from datetime import timedelta

import pytest

from ocor_runtime.c6_capabilities import CapabilityAuthority
from ocor_runtime.errors import AuthorizationError

pytestmark = pytest.mark.backend_assumption


def _lease(authority, fixed_now, **kwargs):
    return authority.issue(
        subject="agent-1",
        capabilities=["action:read", "action:write"],
        resources=["urn:ocor:action/*"],
        issued_at=fixed_now,
        not_before=fixed_now + timedelta(seconds=1),
        expires_at=fixed_now + timedelta(seconds=11),
        **kwargs,
    )


def test_ba08_lease_window_is_start_inclusive_and_end_exclusive(fixed_now):
    authority = CapabilityAuthority()
    lease = _lease(authority, fixed_now)
    with pytest.raises(AuthorizationError):
        authority.authorize(
            lease,
            "action:read",
            "urn:ocor:action/1",
            at=lease.not_before - timedelta(microseconds=1),
            subject="agent-1",
        )
    assert authority.authorize(
        lease,
        "action:read",
        "urn:ocor:action/1",
        at=lease.not_before,
        subject="agent-1",
    )
    with pytest.raises(AuthorizationError):
        authority.authorize(
            lease,
            "action:read",
            "urn:ocor:action/1",
            at=lease.expires_at,
            subject="agent-1",
        )


def test_ba08_revocation_and_scope_fail_closed(fixed_now):
    authority = CapabilityAuthority()
    lease = _lease(authority, fixed_now)
    active = lease.not_before + timedelta(seconds=1)
    with pytest.raises(AuthorizationError):
        authority.authorize(
            lease, "action:delete", "urn:ocor:action/1", at=active
        )
    with pytest.raises(AuthorizationError):
        authority.authorize(
            lease, "action:read", "urn:ocor:evidence/1", at=active
        )
    authority.revoke(lease.lease_id, at=active)
    with pytest.raises(AuthorizationError):
        authority.authorize(
            lease, "action:read", "urn:ocor:action/1", at=active
        )


def test_ba08_delegation_cannot_escalate_capability_or_time(fixed_now):
    authority = CapabilityAuthority()
    parent = _lease(authority, fixed_now)
    with pytest.raises(AuthorizationError):
        authority.issue(
            subject="child",
            capabilities=["action:delete"],
            resources=["urn:ocor:action/1"],
            issued_at=fixed_now,
            not_before=parent.not_before,
            expires_at=parent.expires_at,
            parent=parent,
        )


def test_ba08_usage_limited_lease_expires_by_consumption(fixed_now):
    authority = CapabilityAuthority()
    lease = _lease(authority, fixed_now, max_uses=1)
    active = lease.not_before
    authority.authorize(
        lease,
        "action:write",
        "urn:ocor:action/1",
        at=active,
        consume=True,
    )
    with pytest.raises(AuthorizationError):
        authority.authorize(
            lease,
            "action:write",
            "urn:ocor:action/1",
            at=active,
            consume=True,
        )

