from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from ocor_runtime.kernel.governance import (
    Authority,
    AuthorityRequest,
    CapabilityLease,
    EvidenceRecord,
    FailureClass,
    GovernanceFault,
    LeaseConsumptionLedger,
    LeaseExpectation,
    ProvenanceRecord,
    RiskClass,
    validate_authority,
)
from ocor_runtime.kernel.governed_context import GovernedContext

NOW = datetime(2026, 9, 2, 3, 30, tzinfo=UTC)
DIGEST_A = "urn:sha256:" + "a" * 64
DIGEST_B = "urn:sha256:" + "b" * 64
DIGEST_C = "urn:sha256:" + "c" * 64
CORRELATION_ID = "018f2f95-01b2-7cc3-8d4e-123456789abc"
CAUSATION_ID = "018f2f95-01b2-7cc3-8d4e-123456789abd"


@pytest.fixture
def context() -> GovernedContext:
    return GovernedContext.from_mapping(
        {
            "tenant_id": "urn:ocor:tenant:synthetic",
            "organization_id": "urn:ocor:org:synthetic",
            "domain_id": "urn:ocor:domain:logistics",
            "compartments": ["urn:ocor:compartment:alpha"],
            "classification_marking_ref": DIGEST_A,
            "purpose": "synthetic-mission-evaluation",
            "effective_principal_id": "spiffe://ocor.test/workload/action-engine",
            "actor_chain": ["urn:ocor:actor:alice", "urn:ocor:actor:action-engine"],
            "ontology_release_digest": DIGEST_B,
            "policy_bundle_digest": DIGEST_C,
            "correlation_id": CORRELATION_ID,
        }
    )


@pytest.fixture
def authority(context: GovernedContext) -> Authority:
    return Authority(
        authority_id="urn:ocor:authority:synthetic-action",
        effective_principal_id=context.effective_principal_id,
        capability_ids=("urn:ocor:capability:dispatch",),
        resource_scopes=("urn:ocor:resource:simulator:alpha",),
        tenant_id=context.tenant_id,
        domains=(context.domain_id,),
        compartments=context.compartments,
        permitted_purposes=(context.purpose,),
        risk_ceiling=RiskClass.R2_CONTROLLED,
        not_before=NOW - timedelta(minutes=1),
        expires_at=NOW + timedelta(minutes=4),
        delegation_ref="urn:sha256:" + "d" * 64,
        policy_bundle_digest=context.policy_bundle_digest,
        signature_ref="urn:ocor:signature:authority:1",
    )


@pytest.fixture
def authority_request(context: GovernedContext) -> AuthorityRequest:
    return AuthorityRequest(
        capability_id="urn:ocor:capability:dispatch",
        resource_scope="urn:ocor:resource:simulator:alpha",
        risk_class=RiskClass.R2_CONTROLLED,
        governed_context=context,
        at=NOW,
    )


@pytest.fixture
def lease(context: GovernedContext) -> CapabilityLease:
    return CapabilityLease.from_mapping(
        {
            "lease_id": "urn:ocor:lease:dispatch:1",
            "capability_id": "urn:ocor:capability:dispatch",
            "effective_principal_id": context.effective_principal_id,
            "delegation_ref": "urn:sha256:" + "d" * 64,
            "action_instance_id": "urn:ocor:action:synthetic:1",
            "governed_context_digest": context.digest(),
            "gate_package_digest": DIGEST_A,
            "stop_epoch": 7,
            "fencing_token": 12,
            "issued_at": "2026-09-02T03:29:58Z",
            "expires_at": "2026-09-02T03:30:03Z",
        }
    )


@pytest.fixture
def lease_expectation(context: GovernedContext) -> LeaseExpectation:
    return LeaseExpectation(
        capability_id="urn:ocor:capability:dispatch",
        effective_principal_id=context.effective_principal_id,
        delegation_ref="urn:sha256:" + "d" * 64,
        action_instance_id="urn:ocor:action:synthetic:1",
        governed_context_digest=context.digest(),
        gate_package_digest=DIGEST_A,
        stop_epoch=7,
        fencing_token=12,
        emission_attempt=1,
        at=NOW,
    )


def test_valid_authority_preserves_scope_purpose_ttl_and_binding(
    authority: Authority, authority_request: AuthorityRequest
):
    decision = validate_authority(
        authority, authority_request, signature_verified=True, revoked=False
    )
    assert decision.authority_id == authority.authority_id
    assert decision.governed_context_digest == authority_request.governed_context.digest()
    assert decision.valid_until == authority.expires_at
    assert decision.purpose == authority_request.governed_context.purpose


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"effective_principal_id": "spiffe://attacker"}, "AUTHORITY_SCOPE_MISMATCH"),
        ({"capability_id": "urn:ocor:capability:admin"}, "AUTHORITY_SCOPE_MISMATCH"),
        ({"resource_scope": "urn:ocor:resource:simulator:beta"}, "AUTHORITY_SCOPE_MISMATCH"),
        ({"risk_class": RiskClass.R3_HIGH_IMPACT}, "AUTHORITY_SCOPE_MISMATCH"),
    ],
)
def test_authority_cannot_be_widened(
    authority: Authority,
    authority_request: AuthorityRequest,
    change: dict[str, object],
    reason: str,
):
    if "effective_principal_id" in change:
        context = replace(
            authority_request.governed_context,
            effective_principal_id=change["effective_principal_id"],
        )
        request = replace(authority_request, governed_context=context)
    else:
        request = replace(authority_request, **change)
    with pytest.raises(GovernanceFault) as exc_info:
        validate_authority(authority, request, signature_verified=True, revoked=False)
    assert exc_info.value.reason_code == reason


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"at": NOW - timedelta(minutes=2)}, "AUTHORITY_NOT_YET_VALID"),
        ({"at": NOW + timedelta(minutes=5)}, "AUTHORITY_EXPIRED"),
    ],
)
def test_authority_time_window_fails_closed(
    authority: Authority,
    authority_request: AuthorityRequest,
    change: dict[str, object],
    reason: str,
):
    with pytest.raises(GovernanceFault) as exc_info:
        validate_authority(
            authority,
            replace(authority_request, **change),
            signature_verified=True,
            revoked=False,
        )
    assert exc_info.value.reason_code == reason


@pytest.mark.parametrize(
    ("signature_verified", "revoked", "reason"),
    [
        (False, False, "AUTHORITY_UNSIGNED"),
        (True, True, "AUTHORITY_REVOKED"),
    ],
)
def test_unsigned_or_revoked_authority_fails_closed(
    authority: Authority,
    authority_request: AuthorityRequest,
    signature_verified: bool,
    revoked: bool,
    reason: str,
):
    with pytest.raises(GovernanceFault) as exc_info:
        validate_authority(
            authority,
            authority_request,
            signature_verified=signature_verified,
            revoked=revoked,
        )
    assert exc_info.value.reason_code == reason


def test_policy_purpose_and_compartment_are_part_of_authority_scope(
    authority: Authority, authority_request: AuthorityRequest
):
    for context_change in (
        {"purpose": "unapproved-purpose"},
        {"policy_bundle_digest": DIGEST_A},
        {"compartments": ("urn:ocor:compartment:beta",)},
    ):
        request = replace(
            authority_request,
            governed_context=replace(authority_request.governed_context, **context_change),
        )
        with pytest.raises(GovernanceFault) as exc_info:
            validate_authority(authority, request, signature_verified=True, revoked=False)
        assert exc_info.value.reason_code == "AUTHORITY_SCOPE_MISMATCH"


def test_capability_lease_matches_the_approved_closed_schema(lease: CapabilityLease):
    runtime_root = Path(__file__).resolve().parents[2]
    schema = json.loads(
        (
            runtime_root
            / "docs/governance_dossier/contracts/capability-lease.schema.json"
        ).read_text()
    )
    Draft202012Validator(schema).validate(lease.to_mapping())
    assert tuple(lease.to_mapping()) == CapabilityLease.fields
    assert lease.expires_at - lease.issued_at == timedelta(seconds=5)


@pytest.mark.parametrize("field", CapabilityLease.fields)
def test_capability_lease_rejects_missing_fields(lease: CapabilityLease, field: str):
    values = lease.to_mapping()
    del values[field]
    with pytest.raises(GovernanceFault) as exc_info:
        CapabilityLease.from_mapping(values)
    assert exc_info.value.reason_code == "LEASE_INVALID"


def test_capability_lease_rejects_additional_fields(lease: CapabilityLease):
    values = lease.to_mapping()
    values["resource_reservation"] = True
    with pytest.raises(GovernanceFault, match="additional"):
        CapabilityLease.from_mapping(values)


def test_capability_lease_ttl_cannot_exceed_five_seconds(lease: CapabilityLease):
    values = lease.to_mapping()
    values["expires_at"] = "2026-09-02T03:30:04Z"
    with pytest.raises(GovernanceFault, match="five seconds"):
        CapabilityLease.from_mapping(values)


def test_valid_lease_is_consumed_once_atomically(
    lease: CapabilityLease, lease_expectation: LeaseExpectation
):
    ledger = LeaseConsumptionLedger()
    receipt = ledger.consume(
        lease,
        lease_expectation,
        signature_verified=True,
        revoked=False,
    )
    assert receipt.consumption_key == (lease.lease_id, lease.action_instance_id, 1)
    assert receipt.governed_context_digest == lease.governed_context_digest
    with pytest.raises(GovernanceFault) as exc_info:
        ledger.consume(
            lease,
            lease_expectation,
            signature_verified=True,
            revoked=False,
        )
    assert exc_info.value.reason_code == "LEASE_ALREADY_CONSUMED"


@pytest.mark.parametrize(
    ("signature_verified", "revoked", "reason"),
    [(False, False, "LEASE_INVALID"), (True, True, "LEASE_REVOKED")],
)
def test_unsigned_or_revoked_lease_fails_closed(
    lease: CapabilityLease,
    lease_expectation: LeaseExpectation,
    signature_verified: bool,
    revoked: bool,
    reason: str,
):
    with pytest.raises(GovernanceFault) as exc_info:
        LeaseConsumptionLedger().consume(
            lease,
            lease_expectation,
            signature_verified=signature_verified,
            revoked=revoked,
        )
    assert exc_info.value.reason_code == reason


def test_expired_lease_fails_closed(
    lease: CapabilityLease, lease_expectation: LeaseExpectation
):
    with pytest.raises(GovernanceFault) as exc_info:
        LeaseConsumptionLedger().consume(
            lease,
            replace(lease_expectation, at=lease.expires_at),
            signature_verified=True,
            revoked=False,
        )
    assert exc_info.value.reason_code == "LEASE_EXPIRED"


@pytest.mark.parametrize(
    "field",
    [
        "capability_id",
        "effective_principal_id",
        "delegation_ref",
        "action_instance_id",
        "governed_context_digest",
        "gate_package_digest",
    ],
)
def test_lease_binding_mismatch_has_stable_reason(
    lease: CapabilityLease, lease_expectation: LeaseExpectation, field: str
):
    value = DIGEST_B if field.endswith("digest") or field == "delegation_ref" else "stale"
    with pytest.raises(GovernanceFault) as exc_info:
        LeaseConsumptionLedger().consume(
            lease,
            replace(lease_expectation, **{field: value}),
            signature_verified=True,
            revoked=False,
        )
    assert exc_info.value.reason_code == "LEASE_CONTEXT_MISMATCH"


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"stop_epoch": 8}, "STOP_EPOCH_MISMATCH"),
        ({"fencing_token": 13}, "FENCING_TOKEN_STALE"),
    ],
)
def test_lease_epoch_and_fencing_fail_with_specific_reasons(
    lease: CapabilityLease,
    lease_expectation: LeaseExpectation,
    change: dict[str, object],
    reason: str,
):
    with pytest.raises(GovernanceFault) as exc_info:
        LeaseConsumptionLedger().consume(
            lease,
            replace(lease_expectation, **change),
            signature_verified=True,
            revoked=False,
        )
    assert exc_info.value.reason_code == reason


@pytest.fixture
def evidence(context: GovernedContext) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id="urn:ocor:evidence:synthetic:1",
        content_digest=DIGEST_A,
        source_ref="urn:ocor:source:synthetic-sensor",
        acquired_at=NOW,
        acquirer_principal_id=context.effective_principal_id,
        method_ref="urn:ocor:method:simulated-observation:v1",
        chain_of_custody=("urn:ocor:custody:ingress", "urn:ocor:custody:validator"),
        marking_ref=context.classification_marking_ref,
        retention_until=NOW + timedelta(days=30),
    )


def test_evidence_is_content_addressed_immutable_and_retained(evidence: EvidenceRecord):
    assert evidence.digest().startswith("urn:sha256:")
    assert evidence.retention_until > evidence.acquired_at
    with pytest.raises(FrozenInstanceError):
        evidence.source_ref = "changed"  # type: ignore[misc]
    assert replace(evidence, source_ref="urn:ocor:source:other").digest() != evidence.digest()


def test_evidence_requires_chain_of_custody_and_valid_retention(evidence: EvidenceRecord):
    with pytest.raises(GovernanceFault) as chain_error:
        replace(evidence, chain_of_custody=())
    assert chain_error.value.reason_code == "PROVENANCE_INCOMPLETE"
    with pytest.raises(GovernanceFault) as retention_error:
        replace(evidence, retention_until=evidence.acquired_at)
    assert retention_error.value.reason_code == "EVIDENCE_INVALID"


def test_provenance_preserves_evidence_and_causal_bindings(
    evidence: EvidenceRecord, context: GovernedContext
):
    provenance = ProvenanceRecord(
        provenance_id="urn:ocor:provenance:synthetic:1",
        evidence_refs=(evidence.evidence_id,),
        source_refs=(evidence.source_ref,),
        activity_refs=("urn:ocor:activity:acquisition:1",),
        actor_refs=(context.effective_principal_id,),
        governed_context_digest=context.digest(),
        correlation_id=CORRELATION_ID,
        causation_id=CAUSATION_ID,
        created_at=NOW,
    )
    restored = ProvenanceRecord.from_mapping(provenance.to_mapping())
    assert restored == provenance
    assert restored.correlation_id == CORRELATION_ID
    assert restored.causation_id == CAUSATION_ID
    assert restored.evidence_refs == (evidence.evidence_id,)


@pytest.mark.parametrize(
    "change",
    [
        {"evidence_refs": ()},
        {"source_refs": ()},
        {"activity_refs": ()},
        {"actor_refs": ()},
        {"correlation_id": "bad"},
        {"causation_id": "bad"},
    ],
)
def test_incomplete_or_malformed_provenance_fails_closed(
    evidence: EvidenceRecord, context: GovernedContext, change: dict[str, object]
):
    values = {
        "provenance_id": "urn:ocor:provenance:synthetic:1",
        "evidence_refs": (evidence.evidence_id,),
        "source_refs": (evidence.source_ref,),
        "activity_refs": ("urn:ocor:activity:acquisition:1",),
        "actor_refs": (context.effective_principal_id,),
        "governed_context_digest": context.digest(),
        "correlation_id": CORRELATION_ID,
        "causation_id": CAUSATION_ID,
        "created_at": NOW,
    }
    values.update(change)
    with pytest.raises(GovernanceFault) as exc_info:
        ProvenanceRecord(**values)
    assert exc_info.value.reason_code == "PROVENANCE_INCOMPLETE"


def test_typed_error_taxonomy_is_stable_and_retry_safe():
    transient = GovernanceFault(
        "CONTROL_PLANE_UNAVAILABLE",
        FailureClass.TRANSIENT,
        CORRELATION_ID,
        "control plane unavailable",
    )
    permanent = GovernanceFault(
        "LEASE_CONTEXT_MISMATCH",
        FailureClass.POLICY_DENIED,
        CORRELATION_ID,
        "lease rejected",
        causation_id=CAUSATION_ID,
    )
    assert transient.retryable is True
    assert permanent.retryable is False
    assert permanent.to_problem() == {
        "reason_code": "LEASE_CONTEXT_MISMATCH",
        "failure_class": "POLICY_DENIED",
        "correlation_id": CORRELATION_ID,
        "causation_id": CAUSATION_ID,
        "retryable": False,
        "title": "lease rejected",
    }
