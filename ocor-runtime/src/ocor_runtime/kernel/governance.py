"""Fail-closed Authority, capability lease, evidence and provenance kernel."""

from __future__ import annotations

import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import IntEnum, StrEnum
from typing import ClassVar

from .canonical import (
    IdentifierError,
    canonical_digest,
    format_utc_timestamp,
    parse_utc_timestamp,
    validate_causation_id,
    validate_correlation_id,
)
from .governed_context import GovernedContext

DIGEST_PREFIX = "urn:sha256:"
# Used only when a malformed record is rejected before it supplies a correlation ID.
CORRELATION_ZERO = "00000000-0000-4000-8000-000000000001"


class FailureClass(StrEnum):
    TRANSIENT = "TRANSIENT"
    PERMANENT = "PERMANENT"
    POLICY_DENIED = "POLICY_DENIED"
    POISON = "POISON"


class RiskClass(IntEnum):
    R0_INFORMATIONAL = 0
    R1_LOW = 1
    R2_CONTROLLED = 2
    R3_HIGH_IMPACT = 3


class GovernanceFault(RuntimeError):
    """Typed boundary failure with bounded, non-secret problem output."""

    def __init__(
        self,
        reason_code: str,
        failure_class: FailureClass,
        correlation_id: str,
        title: str,
        *,
        causation_id: str | None = None,
    ) -> None:
        if not reason_code or not title or len(title) > 256:
            raise ValueError("reason_code and a bounded title are required")
        validate_correlation_id(correlation_id)
        if causation_id is not None:
            validate_causation_id(causation_id)
        self.reason_code = reason_code
        self.failure_class = FailureClass(failure_class)
        self.correlation_id = correlation_id
        self.causation_id = causation_id
        self.title = title
        super().__init__(f"{reason_code}: {title}")

    @property
    def retryable(self) -> bool:
        return self.failure_class is FailureClass.TRANSIENT

    def to_problem(self) -> dict[str, object]:
        return {
            "reason_code": self.reason_code,
            "failure_class": self.failure_class.value,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "retryable": self.retryable,
            "title": self.title,
        }


def _fault(
    reason: str,
    correlation_id: str,
    title: str,
    failure_class: FailureClass = FailureClass.POLICY_DENIED,
) -> GovernanceFault:
    return GovernanceFault(reason, failure_class, correlation_id, title)


def _string(field: str, value: object, correlation_id: str = CORRELATION_ZERO) -> str:
    if not isinstance(value, str) or not value:
        raise _fault("GOVERNANCE_RECORD_INVALID", correlation_id, f"{field} is required")
    return value


def _digest(field: str, value: object, correlation_id: str = CORRELATION_ZERO) -> str:
    result = _string(field, value, correlation_id)
    if len(result) != 75 or not result.startswith(DIGEST_PREFIX):
        raise _fault(
            "GOVERNANCE_RECORD_INVALID", correlation_id, f"{field} is not a SHA-256 URN"
        )
    suffix = result.removeprefix(DIGEST_PREFIX)
    if any(character not in "0123456789abcdef" for character in suffix):
        raise _fault(
            "GOVERNANCE_RECORD_INVALID", correlation_id, f"{field} is not a SHA-256 URN"
        )
    return result


def _aware(field: str, value: datetime, correlation_id: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise _fault("GOVERNANCE_RECORD_INVALID", correlation_id, f"{field} must be aware UTC")
    return value


def _refs(field: str, value: Sequence[str], correlation_id: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes, bytearray)):
        raise _fault("PROVENANCE_INCOMPLETE", correlation_id, f"{field} must be an array")
    items = tuple(value)
    if not items or any(not isinstance(item, str) or not item for item in items):
        raise _fault("PROVENANCE_INCOMPLETE", correlation_id, f"{field} is incomplete")
    if len(items) != len(set(items)):
        raise _fault("PROVENANCE_INCOMPLETE", correlation_id, f"{field} has duplicates")
    return items


@dataclass(frozen=True, slots=True)
class Authority:
    authority_id: str
    effective_principal_id: str
    capability_ids: tuple[str, ...]
    resource_scopes: tuple[str, ...]
    tenant_id: str
    domains: tuple[str, ...]
    compartments: tuple[str, ...]
    permitted_purposes: tuple[str, ...]
    risk_ceiling: RiskClass
    not_before: datetime
    expires_at: datetime
    delegation_ref: str
    policy_bundle_digest: str
    signature_ref: str

    def __post_init__(self) -> None:
        correlation = CORRELATION_ZERO
        for field in (
            "authority_id",
            "effective_principal_id",
            "tenant_id",
            "signature_ref",
        ):
            _string(field, getattr(self, field), correlation)
        for field in (
            "capability_ids",
            "resource_scopes",
            "domains",
            "compartments",
            "permitted_purposes",
        ):
            object.__setattr__(self, field, _refs(field, getattr(self, field), correlation))
        _digest("delegation_ref", self.delegation_ref, correlation)
        _digest("policy_bundle_digest", self.policy_bundle_digest, correlation)
        object.__setattr__(self, "risk_ceiling", RiskClass(self.risk_ceiling))
        _aware("not_before", self.not_before, correlation)
        _aware("expires_at", self.expires_at, correlation)
        if self.not_before >= self.expires_at:
            raise _fault(
                "GOVERNANCE_RECORD_INVALID",
                correlation,
                "Authority validity window is empty",
            )


@dataclass(frozen=True, slots=True)
class AuthorityRequest:
    capability_id: str
    resource_scope: str
    risk_class: RiskClass
    governed_context: GovernedContext
    at: datetime

    def __post_init__(self) -> None:
        correlation = self.governed_context.correlation_id
        _string("capability_id", self.capability_id, correlation)
        _string("resource_scope", self.resource_scope, correlation)
        object.__setattr__(self, "risk_class", RiskClass(self.risk_class))
        _aware("at", self.at, correlation)


@dataclass(frozen=True, slots=True)
class AuthorityDecision:
    authority_id: str
    governed_context_digest: str
    purpose: str
    valid_until: datetime


def validate_authority(
    authority: Authority,
    request: AuthorityRequest,
    *,
    signature_verified: bool,
    revoked: bool,
) -> AuthorityDecision:
    """Apply the effective Authority intersection without wildcard widening."""

    correlation = request.governed_context.correlation_id
    if not signature_verified or not authority.signature_ref:
        raise _fault("AUTHORITY_UNSIGNED", correlation, "Authority signature is not verified")
    if revoked:
        raise _fault("AUTHORITY_REVOKED", correlation, "Authority is revoked")
    if request.at < authority.not_before:
        raise _fault("AUTHORITY_NOT_YET_VALID", correlation, "Authority is not yet valid")
    if request.at >= authority.expires_at:
        raise _fault("AUTHORITY_EXPIRED", correlation, "Authority is expired")
    context = request.governed_context
    in_scope = (
        context.effective_principal_id == authority.effective_principal_id
        and request.capability_id in authority.capability_ids
        and request.resource_scope in authority.resource_scopes
        and context.tenant_id == authority.tenant_id
        and context.domain_id in authority.domains
        and set(context.compartments).issubset(authority.compartments)
        and context.purpose in authority.permitted_purposes
        and request.risk_class <= authority.risk_ceiling
        and context.policy_bundle_digest == authority.policy_bundle_digest
    )
    if not in_scope:
        raise _fault(
            "AUTHORITY_SCOPE_MISMATCH",
            correlation,
            "Authority does not contain the requested scope, purpose, risk, or binding",
        )
    return AuthorityDecision(
        authority_id=authority.authority_id,
        governed_context_digest=context.digest(),
        purpose=context.purpose,
        valid_until=authority.expires_at,
    )


@dataclass(frozen=True, slots=True)
class CapabilityLease:
    lease_id: str
    capability_id: str
    effective_principal_id: str
    delegation_ref: str
    action_instance_id: str
    governed_context_digest: str
    gate_package_digest: str
    stop_epoch: int
    fencing_token: int
    issued_at: datetime
    expires_at: datetime

    fields: ClassVar[tuple[str, ...]] = (
        "lease_id",
        "capability_id",
        "effective_principal_id",
        "delegation_ref",
        "action_instance_id",
        "governed_context_digest",
        "gate_package_digest",
        "stop_epoch",
        "fencing_token",
        "issued_at",
        "expires_at",
    )

    def __post_init__(self) -> None:
        for field in (
            "lease_id",
            "capability_id",
            "effective_principal_id",
            "action_instance_id",
        ):
            _string(field, getattr(self, field))
        for field in (
            "delegation_ref",
            "governed_context_digest",
            "gate_package_digest",
        ):
            _digest(field, getattr(self, field))
        if (
            isinstance(self.stop_epoch, bool)
            or not isinstance(self.stop_epoch, int)
            or self.stop_epoch < 0
        ):
            raise _fault("LEASE_INVALID", CORRELATION_ZERO, "stop_epoch is invalid")
        if (
            isinstance(self.fencing_token, bool)
            or not isinstance(self.fencing_token, int)
            or self.fencing_token < 1
        ):
            raise _fault("LEASE_INVALID", CORRELATION_ZERO, "fencing_token is invalid")
        _aware("issued_at", self.issued_at, CORRELATION_ZERO)
        _aware("expires_at", self.expires_at, CORRELATION_ZERO)
        duration = self.expires_at - self.issued_at
        if duration <= timedelta(0):
            raise _fault("LEASE_INVALID", CORRELATION_ZERO, "lease validity window is empty")
        if duration > timedelta(seconds=5):
            raise _fault("LEASE_INVALID", CORRELATION_ZERO, "lease TTL exceeds five seconds")

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> CapabilityLease:
        present = frozenset(value)
        required = frozenset(cls.fields)
        missing = sorted(required - present)
        additional = sorted(present - required)
        if missing:
            raise _fault(
                "LEASE_INVALID",
                CORRELATION_ZERO,
                f"missing lease fields: {', '.join(missing)}",
            )
        if additional:
            raise _fault(
                "LEASE_INVALID",
                CORRELATION_ZERO,
                f"additional lease fields: {', '.join(additional)}",
            )
        try:
            issued_at = parse_utc_timestamp(value["issued_at"])  # type: ignore[arg-type]
            expires_at = parse_utc_timestamp(value["expires_at"])  # type: ignore[arg-type]
            return cls(
                lease_id=value["lease_id"],  # type: ignore[arg-type]
                capability_id=value["capability_id"],  # type: ignore[arg-type]
                effective_principal_id=value["effective_principal_id"],  # type: ignore[arg-type]
                delegation_ref=value["delegation_ref"],  # type: ignore[arg-type]
                action_instance_id=value["action_instance_id"],  # type: ignore[arg-type]
                governed_context_digest=value["governed_context_digest"],  # type: ignore[arg-type]
                gate_package_digest=value["gate_package_digest"],  # type: ignore[arg-type]
                stop_epoch=value["stop_epoch"],  # type: ignore[arg-type]
                fencing_token=value["fencing_token"],  # type: ignore[arg-type]
                issued_at=issued_at,
                expires_at=expires_at,
            )
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, GovernanceFault):
                raise
            raise _fault("LEASE_INVALID", CORRELATION_ZERO, f"invalid lease: {exc}") from exc

    def to_mapping(self) -> dict[str, object]:
        return {
            "lease_id": self.lease_id,
            "capability_id": self.capability_id,
            "effective_principal_id": self.effective_principal_id,
            "delegation_ref": self.delegation_ref,
            "action_instance_id": self.action_instance_id,
            "governed_context_digest": self.governed_context_digest,
            "gate_package_digest": self.gate_package_digest,
            "stop_epoch": self.stop_epoch,
            "fencing_token": self.fencing_token,
            "issued_at": format_utc_timestamp(self.issued_at),
            "expires_at": format_utc_timestamp(self.expires_at),
        }


@dataclass(frozen=True, slots=True)
class LeaseExpectation:
    capability_id: str
    effective_principal_id: str
    delegation_ref: str
    action_instance_id: str
    governed_context_digest: str
    gate_package_digest: str
    stop_epoch: int
    fencing_token: int
    emission_attempt: int
    at: datetime

    def __post_init__(self) -> None:
        for field in ("capability_id", "effective_principal_id", "action_instance_id"):
            _string(field, getattr(self, field))
        for field in ("delegation_ref", "governed_context_digest", "gate_package_digest"):
            _digest(field, getattr(self, field))
        if self.stop_epoch < 0 or self.fencing_token < 1 or self.emission_attempt < 1:
            raise _fault("LEASE_INVALID", CORRELATION_ZERO, "lease expectation counters invalid")
        _aware("at", self.at, CORRELATION_ZERO)


@dataclass(frozen=True, slots=True)
class LeaseConsumptionReceipt:
    consumption_key: tuple[str, str, int]
    governed_context_digest: str
    consumed_at: datetime


class LeaseConsumptionLedger:
    """Local atomic one-shot lease consumption boundary."""

    def __init__(self) -> None:
        self._consumed: set[tuple[str, str, int]] = set()
        self._lock = threading.RLock()

    def consume(
        self,
        lease: CapabilityLease,
        expected: LeaseExpectation,
        *,
        signature_verified: bool,
        revoked: bool,
    ) -> LeaseConsumptionReceipt:
        correlation = CORRELATION_ZERO
        with self._lock:
            if not signature_verified:
                raise _fault("LEASE_INVALID", correlation, "lease signature is not verified")
            if revoked:
                raise _fault("LEASE_REVOKED", correlation, "lease is revoked")
            if expected.at < lease.issued_at or expected.at >= lease.expires_at:
                raise _fault("LEASE_EXPIRED", correlation, "lease is outside its time window")
            bindings = (
                "capability_id",
                "effective_principal_id",
                "delegation_ref",
                "action_instance_id",
                "governed_context_digest",
                "gate_package_digest",
            )
            if any(getattr(lease, field) != getattr(expected, field) for field in bindings):
                raise _fault(
                    "LEASE_CONTEXT_MISMATCH",
                    correlation,
                    "lease principal, scope, action, GCS, delegation, or gate binding differs",
                )
            if lease.stop_epoch != expected.stop_epoch:
                raise _fault("STOP_EPOCH_MISMATCH", correlation, "lease stop epoch differs")
            if lease.fencing_token != expected.fencing_token:
                raise _fault("FENCING_TOKEN_STALE", correlation, "lease fencing token is stale")
            key = (lease.lease_id, lease.action_instance_id, expected.emission_attempt)
            if key in self._consumed:
                raise _fault("LEASE_ALREADY_CONSUMED", correlation, "lease attempt was consumed")
            self._consumed.add(key)
            return LeaseConsumptionReceipt(key, lease.governed_context_digest, expected.at)


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    evidence_id: str
    content_digest: str
    source_ref: str
    acquired_at: datetime
    acquirer_principal_id: str
    method_ref: str
    chain_of_custody: tuple[str, ...]
    marking_ref: str
    retention_until: datetime

    def __post_init__(self) -> None:
        for field in ("evidence_id", "source_ref", "acquirer_principal_id", "method_ref"):
            _string(field, getattr(self, field))
        _digest("content_digest", self.content_digest)
        _digest("marking_ref", self.marking_ref)
        object.__setattr__(
            self,
            "chain_of_custody",
            _refs("chain_of_custody", self.chain_of_custody, CORRELATION_ZERO),
        )
        _aware("acquired_at", self.acquired_at, CORRELATION_ZERO)
        _aware("retention_until", self.retention_until, CORRELATION_ZERO)
        if self.retention_until <= self.acquired_at:
            raise _fault(
                "EVIDENCE_INVALID", CORRELATION_ZERO, "evidence retention has expired"
            )

    def to_mapping(self) -> dict[str, object]:
        return {
            "evidence_id": self.evidence_id,
            "content_digest": self.content_digest,
            "source_ref": self.source_ref,
            "acquired_at": format_utc_timestamp(self.acquired_at),
            "acquirer_principal_id": self.acquirer_principal_id,
            "method_ref": self.method_ref,
            "chain_of_custody": list(self.chain_of_custody),
            "marking_ref": self.marking_ref,
            "retention_until": format_utc_timestamp(self.retention_until),
        }

    def digest(self) -> str:
        return canonical_digest(self.to_mapping())


@dataclass(frozen=True, slots=True)
class ProvenanceRecord:
    provenance_id: str
    evidence_refs: tuple[str, ...]
    source_refs: tuple[str, ...]
    activity_refs: tuple[str, ...]
    actor_refs: tuple[str, ...]
    governed_context_digest: str
    correlation_id: str
    causation_id: str
    created_at: datetime

    def __post_init__(self) -> None:
        correlation = self.correlation_id if isinstance(self.correlation_id, str) else CORRELATION_ZERO
        try:
            validate_correlation_id(self.correlation_id)
            validate_causation_id(self.causation_id)
        except IdentifierError as exc:
            raise _fault(
                "PROVENANCE_INCOMPLETE", CORRELATION_ZERO, f"causal binding invalid: {exc}"
            ) from exc
        _string("provenance_id", self.provenance_id, correlation)
        for field in ("evidence_refs", "source_refs", "activity_refs", "actor_refs"):
            object.__setattr__(self, field, _refs(field, getattr(self, field), correlation))
        try:
            _digest("governed_context_digest", self.governed_context_digest, correlation)
            _aware("created_at", self.created_at, correlation)
        except GovernanceFault as exc:
            raise _fault("PROVENANCE_INCOMPLETE", correlation, exc.title) from exc

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> ProvenanceRecord:
        try:
            return cls(
                provenance_id=value["provenance_id"],  # type: ignore[arg-type]
                evidence_refs=tuple(value["evidence_refs"]),  # type: ignore[arg-type]
                source_refs=tuple(value["source_refs"]),  # type: ignore[arg-type]
                activity_refs=tuple(value["activity_refs"]),  # type: ignore[arg-type]
                actor_refs=tuple(value["actor_refs"]),  # type: ignore[arg-type]
                governed_context_digest=value["governed_context_digest"],  # type: ignore[arg-type]
                correlation_id=value["correlation_id"],  # type: ignore[arg-type]
                causation_id=value["causation_id"],  # type: ignore[arg-type]
                created_at=parse_utc_timestamp(value["created_at"]),  # type: ignore[arg-type]
            )
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, GovernanceFault):
                raise
            raise _fault(
                "PROVENANCE_INCOMPLETE", CORRELATION_ZERO, f"invalid provenance: {exc}"
            ) from exc

    def to_mapping(self) -> dict[str, object]:
        return {
            "provenance_id": self.provenance_id,
            "evidence_refs": list(self.evidence_refs),
            "source_refs": list(self.source_refs),
            "activity_refs": list(self.activity_refs),
            "actor_refs": list(self.actor_refs),
            "governed_context_digest": self.governed_context_digest,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "created_at": format_utc_timestamp(self.created_at),
        }

    def digest(self) -> str:
        return canonical_digest(self.to_mapping())
