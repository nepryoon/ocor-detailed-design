from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta

import pytest
from ocor_runtime.kernel.governed_context import GovernedContext
from ocor_runtime.security.ports import (
    AuthenticatedPrincipal,
    ControlName,
    ControlStatus,
    IdentityProviderPort,
    IdentityRequest,
    PolicyDecision,
    PolicyDecisionPort,
    PolicyEffect,
    PolicyRequest,
    SecretLease,
    SecretProviderPort,
    SecretRequest,
    SecurityControlError,
    StopEpochPort,
    StopEpochSnapshot,
    WorkloadIdentity,
    WorkloadIdentityPort,
)

DIGEST_A = "urn:sha256:" + "a" * 64
DIGEST_B = "urn:sha256:" + "b" * 64
DIGEST_C = "urn:sha256:" + "c" * 64
NOW = datetime(2026, 9, 2, 4, 20, tzinfo=UTC)


@pytest.fixture
def context() -> GovernedContext:
    return GovernedContext.from_mapping(
        {
            "tenant_id": "urn:ocor:tenant:synthetic",
            "organization_id": "urn:ocor:org:synthetic",
            "domain_id": "urn:ocor:domain:logistics",
            "compartments": ["urn:ocor:compartment:alpha"],
            "classification_marking_ref": DIGEST_A,
            "purpose": "governed-read",
            "effective_principal_id": "urn:ocor:principal:analyst-1",
            "actor_chain": ["urn:ocor:principal:analyst-1"],
            "ontology_release_digest": DIGEST_B,
            "policy_bundle_digest": DIGEST_C,
            "correlation_id": "018f2f95-01b2-7cc3-8d4e-123456789abc",
        }
    )


def available(control: ControlName, source_digest: str = DIGEST_A) -> ControlStatus:
    return ControlStatus.available(control, observed_at=NOW, source_digest=source_digest)


@pytest.mark.parametrize("control", list(ControlName))
def test_each_control_has_explicit_available_and_unavailable_semantics(control: ControlName):
    assert available(control).require_available() is None
    unavailable = ControlStatus.unavailable(
        control,
        reason_code=f"{control.value}_TIMEOUT",
        observed_at=NOW,
        source_digest=DIGEST_A,
    )
    with pytest.raises(SecurityControlError) as exc_info:
        unavailable.require_available()
    assert exc_info.value.reason_code == f"{control.value}_UNAVAILABLE"


def test_unavailable_status_requires_bounded_reason():
    with pytest.raises(SecurityControlError) as exc_info:
        ControlStatus(ControlName.POLICY, False, None, NOW, DIGEST_A)
    assert exc_info.value.reason_code == "CONTROL_STATUS_INVALID"


def test_identity_request_never_carries_raw_credentials():
    request = IdentityRequest(
        credential_ref="urn:ocor:credential-ref:synthetic:1",
        expected_audience="urn:ocor:audience:gateway",
        correlation_id="018f2f95-01b2-7cc3-8d4e-123456789abc",
    )
    assert set(request.to_mapping()) == {
        "credential_ref",
        "expected_audience",
        "correlation_id",
    }
    assert "token" not in repr(request).lower()


@pytest.mark.parametrize("principal_id", ["", "anonymous", "ANONYMOUS", "guest"])
def test_anonymous_or_shared_fallback_identity_is_rejected(principal_id: str):
    with pytest.raises(SecurityControlError) as exc_info:
        AuthenticatedPrincipal(
            principal_id=principal_id,
            session_id="urn:ocor:session:synthetic:1",
            actor_chain=("urn:ocor:principal:synthetic:1",),
            assurance_level="AAL2",
            authenticated_at=NOW,
            expires_at=NOW + timedelta(minutes=5),
            status=available(ControlName.IDENTITY),
        )
    assert exc_info.value.reason_code == "ANONYMOUS_IDENTITY_FORBIDDEN"


def test_unavailable_identity_cannot_construct_authenticated_principal():
    status = ControlStatus.unavailable(
        ControlName.IDENTITY,
        reason_code="IDP_TIMEOUT",
        observed_at=NOW,
        source_digest=DIGEST_A,
    )
    with pytest.raises(SecurityControlError) as exc_info:
        AuthenticatedPrincipal(
            "urn:ocor:principal:synthetic:1",
            "urn:ocor:session:synthetic:1",
            ("urn:ocor:principal:synthetic:1",),
            "AAL2",
            NOW,
            NOW + timedelta(minutes=5),
            status,
        )
    assert exc_info.value.reason_code == "IDENTITY_UNAVAILABLE"


@pytest.fixture
def principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        "urn:ocor:principal:analyst-1",
        "urn:ocor:session:synthetic:1",
        ("urn:ocor:principal:analyst-1",),
        "AAL2",
        NOW,
        NOW + timedelta(minutes=5),
        available(ControlName.IDENTITY),
    )


@pytest.fixture
def policy_request(
    principal: AuthenticatedPrincipal, context: GovernedContext
) -> PolicyRequest:
    return PolicyRequest(
        principal=principal,
        action="ocor.query.named",
        resource="urn:ocor:resource:synthetic:1",
        governed_context=context,
        governed_context_digest=context.digest(),
        at=NOW,
    )


def test_policy_permit_is_explicit_and_bound_to_identity_purpose_policy_and_gcs(
    policy_request: PolicyRequest,
):
    decision = PolicyDecision.from_request(
        policy_request,
        effect=PolicyEffect.PERMIT,
        decision_id="urn:ocor:policy-decision:synthetic:1",
        valid_until=NOW + timedelta(seconds=30),
        status=available(ControlName.POLICY, DIGEST_C),
    )
    assert decision.verify(policy_request, at=NOW) is decision
    assert decision.principal_id == policy_request.principal.principal_id
    assert decision.purpose == policy_request.governed_context.purpose
    assert decision.policy_bundle_digest == DIGEST_C
    assert decision.governed_context_digest == policy_request.governed_context_digest


def test_unavailable_policy_cannot_degrade_to_permit(policy_request: PolicyRequest):
    unavailable = ControlStatus.unavailable(
        ControlName.POLICY,
        reason_code="OPA_TIMEOUT",
        observed_at=NOW,
        source_digest=DIGEST_A,
    )
    with pytest.raises(SecurityControlError) as exc_info:
        PolicyDecision.from_request(
            policy_request,
            effect=PolicyEffect.PERMIT,
            decision_id="urn:ocor:policy-decision:synthetic:1",
            valid_until=NOW + timedelta(seconds=30),
            status=unavailable,
        )
    assert exc_info.value.reason_code == "POLICY_UNAVAILABLE"


def test_policy_deny_and_constraint_dispositions_are_not_coerced_to_permit(
    policy_request: PolicyRequest,
):
    for effect in (
        PolicyEffect.DENY,
        PolicyEffect.PERMIT_WITH_CONSTRAINTS,
        PolicyEffect.REQUIRE_APPROVAL,
        PolicyEffect.OBLIGATE,
    ):
        decision = PolicyDecision.from_request(
            policy_request,
            effect=effect,
            decision_id=f"urn:ocor:policy-decision:{effect.value.lower()}",
            valid_until=NOW + timedelta(seconds=30),
            status=available(ControlName.POLICY, DIGEST_C),
            obligations=("urn:ocor:obligation:synthetic",),
        )
        assert decision.effect is effect
        assert decision.effect is not PolicyEffect.PERMIT


def test_policy_drift_or_expiry_fails_closed(
    policy_request: PolicyRequest,
):
    decision = PolicyDecision.from_request(
        policy_request,
        effect=PolicyEffect.PERMIT,
        decision_id="urn:ocor:policy-decision:synthetic:1",
        valid_until=NOW + timedelta(seconds=30),
        status=available(ControlName.POLICY, DIGEST_C),
    )
    with pytest.raises(SecurityControlError) as expired:
        decision.verify(policy_request, at=decision.valid_until)
    assert expired.value.reason_code == "POLICY_DECISION_EXPIRED"
    changed = replace(policy_request, action="ocor.commit")
    with pytest.raises(SecurityControlError) as drifted:
        decision.verify(changed, at=NOW)
    assert drifted.value.reason_code == "POLICY_BINDING_MISMATCH"


def test_workload_identity_requires_attested_unexpired_spiffe_svid():
    identity = WorkloadIdentity(
        spiffe_id="spiffe://ocor.rome/poc/tenant-a/runtime/c2/instance-1",
        svid_ref="urn:ocor:svid:synthetic:1",
        trust_bundle_digest=DIGEST_A,
        attested=True,
        not_before=NOW - timedelta(seconds=1),
        expires_at=NOW + timedelta(minutes=1),
        status=available(ControlName.WORKLOAD_IDENTITY),
    )
    assert identity.require_valid(at=NOW) is identity
    for changed, reason in (
        ({"spiffe_id": "urn:ocor:not-spiffe"}, "WORKLOAD_IDENTITY_INVALID"),
        ({"attested": False}, "WORKLOAD_IDENTITY_UNATTESTED"),
    ):
        with pytest.raises(SecurityControlError) as exc_info:
            replace(identity, **changed)
        assert exc_info.value.reason_code == reason
    with pytest.raises(SecurityControlError) as expired:
        identity.require_valid(at=identity.expires_at)
    assert expired.value.reason_code == "WORKLOAD_IDENTITY_EXPIRED"


def test_secret_contract_exposes_only_reference_and_binds_request(
    principal: AuthenticatedPrincipal, context: GovernedContext
):
    request = SecretRequest(
        secret_ref="urn:ocor:secret-ref:synthetic:database",
        principal_id=principal.principal_id,
        purpose=context.purpose,
        governed_context_digest=context.digest(),
        requested_at=NOW,
    )
    lease = SecretLease.from_request(
        request,
        handle_ref="urn:ocor:secret-handle:synthetic:1",
        version="7",
        expires_at=NOW + timedelta(seconds=30),
        status=available(ControlName.SECRETS),
    )
    assert lease.verify(request, at=NOW) is lease
    representation = repr(lease).lower()
    assert "password" not in representation
    assert not hasattr(lease, "value")
    assert not hasattr(lease, "material")


def test_unavailable_secret_provider_has_no_embedded_fallback(
    principal: AuthenticatedPrincipal, context: GovernedContext
):
    request = SecretRequest(
        "urn:ocor:secret-ref:synthetic:database",
        principal.principal_id,
        context.purpose,
        context.digest(),
        NOW,
    )
    status = ControlStatus.unavailable(
        ControlName.SECRETS,
        reason_code="SECRET_REFERENCE_NOT_RESOLVED",
        observed_at=NOW,
        source_digest=DIGEST_A,
    )
    with pytest.raises(SecurityControlError) as exc_info:
        SecretLease.from_request(
            request,
            handle_ref="embedded-password",
            version="fallback",
            expires_at=NOW + timedelta(seconds=30),
            status=status,
        )
    assert exc_info.value.reason_code == "SECRETS_UNAVAILABLE"


def test_stop_epoch_blocks_active_stop_stale_epoch_and_unavailable_control():
    normal = StopEpochSnapshot(
        epoch=8,
        stopped=False,
        observed_at=NOW,
        status=available(ControlName.STOP_EPOCH),
    )
    assert normal.assert_dispatch_allowed(expected_epoch=8) is normal
    with pytest.raises(SecurityControlError) as stale:
        normal.assert_dispatch_allowed(expected_epoch=7)
    assert stale.value.reason_code == "STOP_EPOCH_MISMATCH"
    with pytest.raises(SecurityControlError) as stopped:
        replace(normal, stopped=True).assert_dispatch_allowed(expected_epoch=8)
    assert stopped.value.reason_code == "EMERGENCY_STOP_ACTIVE"
    unavailable = ControlStatus.unavailable(
        ControlName.STOP_EPOCH,
        reason_code="STOP_STORE_TIMEOUT",
        observed_at=NOW,
        source_digest=DIGEST_A,
    )
    with pytest.raises(SecurityControlError) as missing:
        replace(normal, status=unavailable)
    assert missing.value.reason_code == "STOP_EPOCH_UNAVAILABLE"


class IdentityHandler:
    def authenticate(self, request: IdentityRequest) -> AuthenticatedPrincipal:
        raise NotImplementedError


def test_all_security_ports_are_runtime_checkable():
    assert isinstance(IdentityHandler(), IdentityProviderPort)
    assert not isinstance(object(), PolicyDecisionPort)
    assert not isinstance(object(), WorkloadIdentityPort)
    assert not isinstance(object(), SecretProviderPort)
    assert not isinstance(object(), StopEpochPort)


def test_security_records_are_immutable(principal: AuthenticatedPrincipal):
    with pytest.raises(FrozenInstanceError):
        principal.assurance_level = "AAL0"  # type: ignore[misc]
