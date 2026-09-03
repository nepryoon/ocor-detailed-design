from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

# isort: split
from ocor_runtime.kernel.governance import (
    Authority,
    AuthorityRequest,
    CapabilityLease,
    EvidenceRecord,
    FailureClass,
    GovernanceFault,
    InMemoryLeaseState,
    InMemoryTrustedClock,
    LeaseConsumptionLedger,
    LeaseExpectation,
    LeaseStateDecision,
    LeaseStateOutcome,
    ProvenanceRecord,
    RiskClass,
    VerifiedAuthorityBinding,
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
        causation_id=CAUSATION_ID,
    )


@pytest.fixture
def authority_binding(context: GovernedContext) -> VerifiedAuthorityBinding:
    return VerifiedAuthorityBinding(
        binding_ref="urn:ocor:binding:synthetic:1",
        delegation_ref="urn:sha256:" + "d" * 64,
        expected_context=context,
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
        correlation_id=CORRELATION_ID,
        causation_id=CAUSATION_ID,
    )


@pytest.fixture
def clock() -> InMemoryTrustedClock:
    return InMemoryTrustedClock(NOW)


@pytest.fixture
def lease_state(lease: CapabilityLease) -> InMemoryLeaseState:
    return InMemoryLeaseState(
        stop_epoch=lease.stop_epoch,
        fencing_tokens={lease.action_instance_id: lease.fencing_token},
    )


@pytest.fixture
def ledger(
    clock: InMemoryTrustedClock, lease_state: InMemoryLeaseState
) -> LeaseConsumptionLedger:
    return LeaseConsumptionLedger(clock=clock, state=lease_state)


def test_valid_authority_preserves_scope_purpose_ttl_and_binding(
    authority: Authority,
    authority_request: AuthorityRequest,
    authority_binding: VerifiedAuthorityBinding,
):
    decision = validate_authority(
        authority,
        authority_request,
        signature_verified=True,
        revoked=False,
        verified_binding=authority_binding,
    )
    assert decision.authority_id == authority.authority_id
    assert decision.governed_context_digest == authority_request.governed_context.digest()
    assert decision.valid_until == authority.expires_at
    assert decision.purpose == authority_request.governed_context.purpose


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"effective_principal_id": "spiffe://attacker"}, "AUTHORITY_BINDING_MISMATCH"),
        ({"capability_id": "urn:ocor:capability:admin"}, "AUTHORITY_SCOPE_MISMATCH"),
        ({"resource_scope": "urn:ocor:resource:simulator:beta"}, "AUTHORITY_SCOPE_MISMATCH"),
        ({"risk_class": RiskClass.R3_HIGH_IMPACT}, "AUTHORITY_SCOPE_MISMATCH"),
    ],
)
def test_authority_cannot_be_widened(
    authority: Authority,
    authority_request: AuthorityRequest,
    authority_binding: VerifiedAuthorityBinding,
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
        validate_authority(
            authority,
            request,
            signature_verified=True,
            revoked=False,
            verified_binding=authority_binding,
        )
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
    authority_binding: VerifiedAuthorityBinding,
    change: dict[str, object],
    reason: str,
):
    with pytest.raises(GovernanceFault) as exc_info:
        validate_authority(
            authority,
            replace(authority_request, **change),
            signature_verified=True,
            revoked=False,
            verified_binding=authority_binding,
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
    authority_binding: VerifiedAuthorityBinding,
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
            verified_binding=authority_binding,
        )
    assert exc_info.value.reason_code == reason


def test_policy_purpose_and_compartment_are_part_of_authority_scope(
    authority: Authority,
    authority_request: AuthorityRequest,
    authority_binding: VerifiedAuthorityBinding,
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
            validate_authority(
                authority,
                request,
                signature_verified=True,
                revoked=False,
                verified_binding=authority_binding,
            )
        assert exc_info.value.reason_code == "AUTHORITY_BINDING_MISMATCH"


def test_authority_requires_verified_delegation_context_binding(
    authority: Authority,
    authority_request: AuthorityRequest,
    authority_binding: VerifiedAuthorityBinding,
):
    for candidate_authority, candidate_request, candidate_binding in (
        (authority, authority_request, None),
        (replace(authority, delegation_ref=DIGEST_B), authority_request, authority_binding),
        (
            authority,
            replace(
                authority_request,
                governed_context=replace(
                    authority_request.governed_context,
                    actor_chain=("urn:ocor:actor:mallory",),
                ),
            ),
            authority_binding,
        ),
    ):
        with pytest.raises(GovernanceFault) as exc_info:
            validate_authority(
                candidate_authority,
                candidate_request,
                signature_verified=True,
                revoked=False,
                verified_binding=candidate_binding,
            )
        assert exc_info.value.reason_code == "AUTHORITY_BINDING_MISMATCH"
        assert exc_info.value.causation_id == CAUSATION_ID


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
    lease: CapabilityLease,
    lease_expectation: LeaseExpectation,
    ledger: LeaseConsumptionLedger,
):
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
    ledger: LeaseConsumptionLedger,
    signature_verified: bool,
    revoked: bool,
    reason: str,
):
    with pytest.raises(GovernanceFault) as exc_info:
        ledger.consume(
            lease,
            lease_expectation,
            signature_verified=signature_verified,
            revoked=revoked,
        )
    assert exc_info.value.reason_code == reason


def test_expired_lease_fails_closed(
    lease: CapabilityLease,
    lease_expectation: LeaseExpectation,
    ledger: LeaseConsumptionLedger,
    clock: InMemoryTrustedClock,
):
    clock.advance(timedelta(seconds=3))
    with pytest.raises(GovernanceFault) as exc_info:
        ledger.consume(
            lease,
            replace(lease_expectation, at=NOW),
            signature_verified=True,
            revoked=False,
        )
    assert exc_info.value.reason_code == "LEASE_EXPIRED"


def test_expiry_is_rechecked_inside_atomic_consumption_boundary(
    lease: CapabilityLease,
    lease_expectation: LeaseExpectation,
    clock: InMemoryTrustedClock,
):
    class AdvanceAtAtomicBoundary(InMemoryLeaseState):
        def consume_if_current(self, **kwargs):  # type: ignore[no-untyped-def]
            clock.advance(timedelta(seconds=3))
            return super().consume_if_current(**kwargs)

    state = AdvanceAtAtomicBoundary(
        stop_epoch=lease.stop_epoch,
        fencing_tokens={lease.action_instance_id: lease.fencing_token},
    )
    ledger = LeaseConsumptionLedger(clock=clock, state=state)

    with pytest.raises(GovernanceFault) as exc_info:
        ledger.consume(
            lease,
            lease_expectation,
            signature_verified=True,
            revoked=False,
        )

    assert exc_info.value.reason_code == "LEASE_EXPIRED"
    assert state.consumption(lease.lease_id) is None


def test_atomic_boundary_fails_closed_when_clock_is_unavailable(
    lease: CapabilityLease,
    lease_expectation: LeaseExpectation,
    lease_state: InMemoryLeaseState,
):
    class UnavailableClock:
        @staticmethod
        def now() -> datetime:
            raise RuntimeError("sensitive provider diagnostic")

    ledger = LeaseConsumptionLedger(clock=UnavailableClock(), state=lease_state)

    with pytest.raises(GovernanceFault) as exc_info:
        ledger.consume(
            lease,
            lease_expectation,
            signature_verified=True,
            revoked=False,
        )

    assert exc_info.value.reason_code == "CONTROL_PLANE_UNAVAILABLE"
    assert "sensitive provider diagnostic" not in str(exc_info.value)
    assert lease_state.consumption(lease.lease_id) is None


@pytest.mark.parametrize(
    "evaluated_at",
    [
        NOW.replace(tzinfo=None),
        NOW - timedelta(seconds=3),
        NOW + timedelta(seconds=4),
    ],
)
def test_malformed_authoritative_consumption_time_fails_closed(
    lease: CapabilityLease,
    lease_expectation: LeaseExpectation,
    clock: InMemoryTrustedClock,
    evaluated_at: datetime,
):
    class ContradictoryState:
        @staticmethod
        def consume_if_current(**_kwargs) -> LeaseStateDecision:  # type: ignore[no-untyped-def]
            return LeaseStateDecision(LeaseStateOutcome.CONSUMED, evaluated_at)

    ledger = LeaseConsumptionLedger(clock=clock, state=ContradictoryState())

    with pytest.raises(GovernanceFault) as exc_info:
        ledger.consume(
            lease,
            lease_expectation,
            signature_verified=True,
            revoked=False,
        )

    assert exc_info.value.reason_code == "CONTROL_PLANE_UNAVAILABLE"
    assert exc_info.value.failure_class is FailureClass.PERMANENT


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
    lease: CapabilityLease,
    lease_expectation: LeaseExpectation,
    ledger: LeaseConsumptionLedger,
    field: str,
):
    value = DIGEST_B if field.endswith("digest") or field == "delegation_ref" else "stale"
    with pytest.raises(GovernanceFault) as exc_info:
        ledger.consume(
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
    ledger: LeaseConsumptionLedger,
    change: dict[str, object],
    reason: str,
):
    with pytest.raises(GovernanceFault) as exc_info:
        ledger.consume(
            lease,
            replace(lease_expectation, **change),
            signature_verified=True,
            revoked=False,
        )
    assert exc_info.value.reason_code == reason


@pytest.mark.parametrize(
    ("advance", "reason"),
    [
        ("stop", "STOP_EPOCH_MISMATCH"),
        ("fence", "FENCING_TOKEN_STALE"),
        ("revoke", "LEASE_REVOKED"),
    ],
)
def test_lease_uses_authoritative_state_not_caller_matching_values(
    lease: CapabilityLease,
    lease_expectation: LeaseExpectation,
    ledger: LeaseConsumptionLedger,
    lease_state: InMemoryLeaseState,
    advance: str,
    reason: str,
):
    if advance == "stop":
        lease_state.set_stop_epoch(lease.stop_epoch + 1)
    elif advance == "fence":
        lease_state.set_fencing_token(
            lease.action_instance_id, lease.fencing_token + 1
        )
    else:
        lease_state.revoke(lease.lease_id)
    with pytest.raises(GovernanceFault) as exc_info:
        ledger.consume(
            lease,
            lease_expectation,
            signature_verified=True,
            revoked=False,
        )
    assert exc_info.value.reason_code == reason


def test_caller_time_is_observability_only_and_cannot_override_trusted_clock(
    lease: CapabilityLease,
    lease_expectation: LeaseExpectation,
    ledger: LeaseConsumptionLedger,
):
    receipt = ledger.consume(
        lease,
        replace(lease_expectation, at=lease.expires_at + timedelta(days=1)),
        signature_verified=True,
        revoked=False,
    )
    assert receipt.consumed_at == NOW


def test_changed_emission_attempt_cannot_reuse_lease(
    lease: CapabilityLease,
    lease_expectation: LeaseExpectation,
    ledger: LeaseConsumptionLedger,
):
    ledger.consume(
        lease,
        lease_expectation,
        signature_verified=True,
        revoked=False,
    )
    with pytest.raises(GovernanceFault) as exc_info:
        ledger.consume(
            lease,
            replace(lease_expectation, emission_attempt=2),
            signature_verified=True,
            revoked=False,
        )
    assert exc_info.value.reason_code == "LEASE_ALREADY_CONSUMED"


def test_concurrent_lease_consumption_has_exactly_one_winner(
    lease: CapabilityLease,
    lease_expectation: LeaseExpectation,
    ledger: LeaseConsumptionLedger,
):
    workers = 12
    barrier = threading.Barrier(workers)

    def consume(attempt: int) -> str:
        barrier.wait()
        try:
            ledger.consume(
                lease,
                replace(lease_expectation, emission_attempt=attempt),
                signature_verified=True,
                revoked=False,
            )
        except GovernanceFault as exc:
            return exc.reason_code
        return "CONSUMED"

    with ThreadPoolExecutor(max_workers=workers) as executor:
        outcomes = list(executor.map(consume, range(1, workers + 1)))
    assert outcomes.count("CONSUMED") == 1
    assert outcomes.count("LEASE_ALREADY_CONSUMED") == workers - 1


def test_lease_fails_closed_without_authoritative_ports(
    lease: CapabilityLease, lease_expectation: LeaseExpectation
):
    with pytest.raises(GovernanceFault) as exc_info:
        LeaseConsumptionLedger().consume(
            lease,
            lease_expectation,
            signature_verified=True,
            revoked=False,
        )
    assert exc_info.value.reason_code == "CONTROL_PLANE_UNAVAILABLE"
    assert exc_info.value.failure_class is FailureClass.PERMANENT


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


def test_provenance_mapping_is_closed_and_does_not_coerce_strings(
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
    values = provenance.to_mapping()
    values["unexpected"] = "not admitted"
    with pytest.raises(GovernanceFault, match="additional"):
        ProvenanceRecord.from_mapping(values)

    for field in ("evidence_refs", "source_refs", "activity_refs", "actor_refs"):
        values = provenance.to_mapping()
        values[field] = "urn:ocor:not-an-array"
        with pytest.raises(GovernanceFault, match="must be an array"):
            ProvenanceRecord.from_mapping(values)


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
        "PROJECTION_NOT_READY",
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
    poison = GovernanceFault(
        "POISON_EVENT",
        FailureClass.POISON,
        CORRELATION_ID,
        "poison event quarantined",
    )
    assert transient.retryable is True
    assert permanent.retryable is False
    assert poison.retryable is False
    assert permanent.to_problem() == {
        "reason_code": "LEASE_CONTEXT_MISMATCH",
        "failure_class": "POLICY_DENIED",
        "correlation_id": CORRELATION_ID,
        "causation_id": CAUSATION_ID,
        "retryable": False,
        "title": "lease rejected",
    }


@pytest.mark.parametrize(
    ("reason", "failure_class"),
    [
        ("UNDECLARED_REASON", FailureClass.PERMANENT),
        ("LEASE_CONTEXT_MISMATCH", FailureClass.TRANSIENT),
        ("CONTROL_PLANE_UNAVAILABLE", FailureClass.TRANSIENT),
    ],
)
def test_fault_taxonomy_rejects_undeclared_or_unsafe_combinations(
    reason: str, failure_class: FailureClass
):
    with pytest.raises(ValueError):
        GovernanceFault(
            reason,
            failure_class,
            CORRELATION_ID,
            "unsafe combination",
        )


def test_fault_observability_is_bounded_and_preserves_causal_ids():
    fault = GovernanceFault(
        "LEASE_CONTEXT_MISMATCH",
        FailureClass.POLICY_DENIED,
        CORRELATION_ID,
        "lease rejected",
        causation_id=CAUSATION_ID,
    )
    assert fault.to_problem()["correlation_id"] == CORRELATION_ID
    assert fault.to_problem()["causation_id"] == CAUSATION_ID
    with pytest.raises(ValueError):
        GovernanceFault(
            "LEASE_CONTEXT_MISMATCH",
            FailureClass.POLICY_DENIED,
            CORRELATION_ID,
            "x" * 257,
        )
