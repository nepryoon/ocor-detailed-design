"""Typed fail-closed boundary contracts for C3 canonical state and outbox."""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any, ClassVar, Protocol, runtime_checkable

from ..kernel.canonical import canonical_digest, format_utc_timestamp
from ..kernel.governed_context import GovernedContext, GovernedContextError

DIGEST = re.compile(r"urn:sha256:[0-9a-f]{64}")


class C3Error(ValueError):
    """Stable, bounded C3 contract failure."""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {message}")


def _required(field: str, value: object) -> str:
    if not isinstance(value, str) or not value:
        raise C3Error("COMMIT_CONTRACT_INVALID", f"{field} is required")
    return value


def _digest(field: str, value: object) -> str:
    result = _required(field, value)
    if DIGEST.fullmatch(result) is None:
        raise C3Error("COMMIT_CONTRACT_INVALID", f"{field} must be a SHA-256 URN")
    return result


def _refs(field: str, values: object) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
        raise C3Error("COMMIT_CONTRACT_INVALID", f"{field} must be an array")
    result = tuple(values)
    if not result or any(not isinstance(item, str) or not item for item in result):
        raise C3Error("COMMIT_CONTRACT_INVALID", f"{field} must contain non-empty refs")
    if len(result) != len(set(result)):
        raise C3Error("COMMIT_CONTRACT_INVALID", f"{field} contains duplicate refs")
    return tuple(sorted(result))


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise C3Error("COMMIT_CONTRACT_INVALID", "canonical_delta keys must be strings")
        return MappingProxyType({key: _freeze(child) for key, child in value.items()})
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(_freeze(child) for child in value)
    return copy.deepcopy(value)


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [_thaw(child) for child in value]
    return copy.deepcopy(value)


@dataclass(frozen=True, slots=True, order=True)
class ClaimSourceBinding:
    claim_ref: str
    source_ref: str
    evidence_ref: str

    fields: ClassVar[frozenset[str]] = frozenset(
        {"claim_ref", "source_ref", "evidence_ref"}
    )

    def __post_init__(self) -> None:
        for field in self.fields:
            _required(field, getattr(self, field))

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> ClaimSourceBinding:
        if set(value) != cls.fields:
            raise C3Error(
                "COMMIT_CONTRACT_INVALID", "claim/source binding must be an exact record"
            )
        return cls(
            claim_ref=value["claim_ref"],  # type: ignore[arg-type]
            source_ref=value["source_ref"],  # type: ignore[arg-type]
            evidence_ref=value["evidence_ref"],  # type: ignore[arg-type]
        )

    def to_mapping(self) -> dict[str, str]:
        return {
            "claim_ref": self.claim_ref,
            "source_ref": self.source_ref,
            "evidence_ref": self.evidence_ref,
        }


@dataclass(frozen=True, slots=True)
class GovernedCanonicalCommitCommand:
    command_id: str
    action_instance_id: str
    aggregate_type: str
    aggregate_ref: str
    expected_revision: int
    canonical_delta: Mapping[str, Any]
    decision_ref: str
    authority_ref: str
    evidence_refs: tuple[str, ...]
    claim_source_bindings: tuple[ClaimSourceBinding, ...]
    precondition_bindings: tuple[str, ...]
    invariant_bindings: tuple[str, ...]
    idempotency_key: str
    governed_context: GovernedContext
    governed_context_digest: str
    gate_package_digest: str
    branch: str

    fields: ClassVar[tuple[str, ...]] = (
        "command_id",
        "action_instance_id",
        "aggregate_type",
        "aggregate_ref",
        "expected_revision",
        "canonical_delta",
        "decision_ref",
        "authority_ref",
        "evidence_refs",
        "claim_source_bindings",
        "precondition_bindings",
        "invariant_bindings",
        "idempotency_key",
        "governed_context",
        "governed_context_digest",
        "gate_package_digest",
        "branch",
    )

    def __post_init__(self) -> None:
        for field in (
            "command_id",
            "action_instance_id",
            "aggregate_type",
            "aggregate_ref",
            "decision_ref",
            "authority_ref",
        ):
            _required(field, getattr(self, field))
        if (
            isinstance(self.expected_revision, bool)
            or not isinstance(self.expected_revision, int)
            or self.expected_revision < 0
        ):
            raise C3Error("REVISION_CONFLICT", "expected_revision must be non-negative")
        if not isinstance(self.canonical_delta, Mapping) or not self.canonical_delta:
            raise C3Error("COMMIT_CONTRACT_INVALID", "canonical_delta must be a non-empty object")
        object.__setattr__(self, "canonical_delta", _freeze(self.canonical_delta))
        object.__setattr__(self, "evidence_refs", _refs("evidence_refs", self.evidence_refs))
        if not self.claim_source_bindings:
            raise C3Error("COMMIT_CONTRACT_INVALID", "claim_source_bindings is required")
        bindings = tuple(sorted(self.claim_source_bindings))
        if len(bindings) != len(set(bindings)):
            raise C3Error("COMMIT_CONTRACT_INVALID", "duplicate claim/source binding")
        object.__setattr__(self, "claim_source_bindings", bindings)
        object.__setattr__(
            self,
            "precondition_bindings",
            _refs("precondition_bindings", self.precondition_bindings),
        )
        object.__setattr__(
            self,
            "invariant_bindings",
            _refs("invariant_bindings", self.invariant_bindings),
        )
        if len(_required("idempotency_key", self.idempotency_key)) < 16:
            raise C3Error(
                "COMMIT_CONTRACT_INVALID", "idempotency_key must contain at least 16 characters"
            )
        _digest("governed_context_digest", self.governed_context_digest)
        if self.governed_context.digest() != self.governed_context_digest:
            raise C3Error("GOVERNED_CONTEXT_MISMATCH", "GCS digest does not match the record")
        _digest("gate_package_digest", self.gate_package_digest)
        if self.branch != "main":
            raise C3Error(
                "SINGLE_WRITER_VIOLATION", "canonical commits and relayable outbox use main only"
            )

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> GovernedCanonicalCommitCommand:
        present = set(value)
        expected = set(cls.fields)
        if present != expected:
            raise C3Error(
                "COMMIT_CONTRACT_INVALID",
                f"command fields differ: missing={sorted(expected - present)}, additional={sorted(present - expected)}",
            )
        context_value = value["governed_context"]
        if not isinstance(context_value, Mapping):
            raise C3Error("COMMIT_CONTRACT_INVALID", "governed_context must be an object")
        try:
            context = GovernedContext.from_mapping(context_value)
        except GovernedContextError as exc:
            raise C3Error("GOVERNED_CONTEXT_MISMATCH", str(exc)) from exc
        delta = value["canonical_delta"]
        if not isinstance(delta, Mapping):
            raise C3Error("COMMIT_CONTRACT_INVALID", "canonical_delta must be an object")
        raw_bindings = value["claim_source_bindings"]
        if (
            isinstance(raw_bindings, (str, bytes, bytearray))
            or not isinstance(raw_bindings, Sequence)
            or any(not isinstance(item, Mapping) for item in raw_bindings)
        ):
            raise C3Error("COMMIT_CONTRACT_INVALID", "claim_source_bindings must be an array")
        return cls(
            command_id=value["command_id"],  # type: ignore[arg-type]
            action_instance_id=value["action_instance_id"],  # type: ignore[arg-type]
            aggregate_type=value["aggregate_type"],  # type: ignore[arg-type]
            aggregate_ref=value["aggregate_ref"],  # type: ignore[arg-type]
            expected_revision=value["expected_revision"],  # type: ignore[arg-type]
            canonical_delta=delta,
            decision_ref=value["decision_ref"],  # type: ignore[arg-type]
            authority_ref=value["authority_ref"],  # type: ignore[arg-type]
            evidence_refs=value["evidence_refs"],  # type: ignore[arg-type]
            claim_source_bindings=tuple(
                ClaimSourceBinding.from_mapping(item) for item in raw_bindings
            ),
            precondition_bindings=value["precondition_bindings"],  # type: ignore[arg-type]
            invariant_bindings=value["invariant_bindings"],  # type: ignore[arg-type]
            idempotency_key=value["idempotency_key"],  # type: ignore[arg-type]
            governed_context=context,
            governed_context_digest=value["governed_context_digest"],  # type: ignore[arg-type]
            gate_package_digest=value["gate_package_digest"],  # type: ignore[arg-type]
            branch=value["branch"],  # type: ignore[arg-type]
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "command_id": self.command_id,
            "action_instance_id": self.action_instance_id,
            "aggregate_type": self.aggregate_type,
            "aggregate_ref": self.aggregate_ref,
            "expected_revision": self.expected_revision,
            "canonical_delta": _thaw(self.canonical_delta),
            "decision_ref": self.decision_ref,
            "authority_ref": self.authority_ref,
            "evidence_refs": list(self.evidence_refs),
            "claim_source_bindings": [item.to_mapping() for item in self.claim_source_bindings],
            "precondition_bindings": list(self.precondition_bindings),
            "invariant_bindings": list(self.invariant_bindings),
            "idempotency_key": self.idempotency_key,
            "governed_context": self.governed_context.to_mapping(),
            "governed_context_digest": self.governed_context_digest,
            "gate_package_digest": self.gate_package_digest,
            "branch": self.branch,
        }

    @property
    def command_digest(self) -> str:
        return canonical_digest(self.to_mapping())

    @property
    def idempotency_scope(self) -> tuple[str, str, str, str]:
        return (
            self.governed_context.tenant_id,
            self.aggregate_type,
            self.aggregate_ref,
            self.idempotency_key,
        )


@dataclass(frozen=True, slots=True)
class CommitReceipt:
    command_id: str
    command_digest: str
    commit_id: str
    tenant_id: str
    aggregate_type: str
    aggregate_ref: str
    from_revision: int
    to_revision: int
    state_digest: str
    idempotency_key: str
    decision_ref: str
    authority_ref: str
    evidence_refs: tuple[str, ...]
    governed_context_digest: str
    gate_package_digest: str
    outbox_event_id: str
    outbox_payload_digest: str
    branch: str
    committed_at: datetime
    replayed: bool = False

    def __post_init__(self) -> None:
        for field in (
            "command_id",
            "commit_id",
            "tenant_id",
            "aggregate_type",
            "aggregate_ref",
            "idempotency_key",
            "decision_ref",
            "authority_ref",
            "outbox_event_id",
        ):
            _required(field, getattr(self, field))
        for field in (
            "command_digest",
            "state_digest",
            "governed_context_digest",
            "gate_package_digest",
            "outbox_payload_digest",
        ):
            _digest(field, getattr(self, field))
        if self.from_revision < 0 or self.to_revision != self.from_revision + 1:
            raise C3Error("REVISION_CONFLICT", "receipt revision interval must advance by one")
        object.__setattr__(self, "evidence_refs", _refs("evidence_refs", self.evidence_refs))
        if self.branch != "main":
            raise C3Error("SINGLE_WRITER_VIOLATION", "receipt branch must be main")
        if (
            not isinstance(self.committed_at, datetime)
            or self.committed_at.tzinfo is None
            or self.committed_at.utcoffset() is None
        ):
            raise C3Error("COMMIT_CONTRACT_INVALID", "committed_at must be timezone-aware")
        if not isinstance(self.replayed, bool):
            raise C3Error("COMMIT_CONTRACT_INVALID", "replayed must be boolean")

    @classmethod
    def from_command(
        cls,
        command: GovernedCanonicalCommitCommand,
        *,
        commit_id: str,
        state_digest: str,
        outbox_event_id: str,
        outbox_payload_digest: str,
        committed_at: datetime,
        replayed: bool = False,
    ) -> CommitReceipt:
        return cls(
            command_id=command.command_id,
            command_digest=command.command_digest,
            commit_id=commit_id,
            tenant_id=command.governed_context.tenant_id,
            aggregate_type=command.aggregate_type,
            aggregate_ref=command.aggregate_ref,
            from_revision=command.expected_revision,
            to_revision=command.expected_revision + 1,
            state_digest=state_digest,
            idempotency_key=command.idempotency_key,
            decision_ref=command.decision_ref,
            authority_ref=command.authority_ref,
            evidence_refs=command.evidence_refs,
            governed_context_digest=command.governed_context_digest,
            gate_package_digest=command.gate_package_digest,
            outbox_event_id=outbox_event_id,
            outbox_payload_digest=outbox_payload_digest,
            branch=command.branch,
            committed_at=committed_at,
            replayed=replayed,
        )

    def verify(self, command: GovernedCanonicalCommitCommand) -> CommitReceipt:
        expected = {
            "command_id": command.command_id,
            "command_digest": command.command_digest,
            "tenant_id": command.governed_context.tenant_id,
            "aggregate_type": command.aggregate_type,
            "aggregate_ref": command.aggregate_ref,
            "from_revision": command.expected_revision,
            "to_revision": command.expected_revision + 1,
            "idempotency_key": command.idempotency_key,
            "decision_ref": command.decision_ref,
            "authority_ref": command.authority_ref,
            "evidence_refs": command.evidence_refs,
            "governed_context_digest": command.governed_context_digest,
            "gate_package_digest": command.gate_package_digest,
            "branch": command.branch,
        }
        drifted = [field for field, value in expected.items() if getattr(self, field) != value]
        if drifted:
            reason = (
                "REVISION_CONFLICT"
                if {"from_revision", "to_revision"} & set(drifted)
                else "COMMIT_RECEIPT_MISMATCH"
            )
            raise C3Error(reason, f"receipt bindings drifted: {sorted(drifted)}")
        return self


@dataclass(frozen=True, slots=True)
class IdempotencyBinding:
    scope: tuple[str, str, str, str]
    command_digest: str
    receipt: CommitReceipt

    def __post_init__(self) -> None:
        if len(self.scope) != 4 or any(not item for item in self.scope):
            raise C3Error("COMMIT_CONTRACT_INVALID", "idempotency scope is invalid")
        _digest("command_digest", self.command_digest)

    @classmethod
    def from_commit(
        cls, command: GovernedCanonicalCommitCommand, receipt: CommitReceipt
    ) -> IdempotencyBinding:
        receipt.verify(command)
        return cls(command.idempotency_scope, command.command_digest, receipt)

    def resolve(self, command: GovernedCanonicalCommitCommand) -> CommitReceipt:
        if self.scope != command.idempotency_scope or self.command_digest != command.command_digest:
            raise C3Error(
                "IDEMPOTENCY_CONFLICT",
                "idempotency key or scope was rebound to different command content",
            )
        return self.receipt


@dataclass(frozen=True, slots=True)
class CanonicalSnapshot:
    tenant_id: str
    aggregate_type: str
    aggregate_ref: str
    revision: int
    state: Mapping[str, Any]
    state_digest: str
    commit_id: str

    def __post_init__(self) -> None:
        for field in ("tenant_id", "aggregate_type", "aggregate_ref", "commit_id"):
            _required(field, getattr(self, field))
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 0:
            raise C3Error("REVISION_CONFLICT", "snapshot revision must be non-negative")
        if not isinstance(self.state, Mapping):
            raise C3Error("COMMIT_CONTRACT_INVALID", "snapshot state must be an object")
        frozen = _freeze(self.state)
        _digest("state_digest", self.state_digest)
        if canonical_digest(frozen) != self.state_digest:
            raise C3Error("COMMIT_RECEIPT_MISMATCH", "snapshot state digest mismatch")
        object.__setattr__(self, "state", frozen)

    @classmethod
    def from_receipt(
        cls, receipt: CommitReceipt, state: Mapping[str, Any]
    ) -> CanonicalSnapshot:
        frozen = _freeze(state)
        if canonical_digest(frozen) != receipt.state_digest:
            raise C3Error("COMMIT_RECEIPT_MISMATCH", "snapshot state digest mismatch")
        return cls(
            receipt.tenant_id,
            receipt.aggregate_type,
            receipt.aggregate_ref,
            receipt.to_revision,
            frozen,
            receipt.state_digest,
            receipt.commit_id,
        )


@dataclass(frozen=True, slots=True)
class OutboxEnvelope:
    event_id: str
    commit_id: str
    aggregate_ref: str
    aggregate_revision: int
    payload: Mapping[str, Any]
    payload_digest: str
    branch: str
    occurred_at: datetime

    def __post_init__(self) -> None:
        for field in ("event_id", "commit_id", "aggregate_ref"):
            _required(field, getattr(self, field))
        if (
            isinstance(self.aggregate_revision, bool)
            or not isinstance(self.aggregate_revision, int)
            or self.aggregate_revision <= 0
        ):
            raise C3Error("REVISION_CONFLICT", "outbox revision must be positive")
        if not isinstance(self.payload, Mapping):
            raise C3Error("COMMIT_CONTRACT_INVALID", "outbox payload must be an object")
        frozen = _freeze(self.payload)
        _digest("payload_digest", self.payload_digest)
        if canonical_digest(frozen) != self.payload_digest:
            raise C3Error("COMMIT_RECEIPT_MISMATCH", "outbox payload digest mismatch")
        object.__setattr__(self, "payload", frozen)
        if self.branch != "main":
            raise C3Error("SINGLE_WRITER_VIOLATION", "relayable outbox branch must be main")
        if (
            not isinstance(self.occurred_at, datetime)
            or self.occurred_at.tzinfo is None
            or self.occurred_at.utcoffset() is None
        ):
            raise C3Error("COMMIT_CONTRACT_INVALID", "occurred_at must be timezone-aware")

    @classmethod
    def from_receipt(
        cls, receipt: CommitReceipt, payload: Mapping[str, Any]
    ) -> OutboxEnvelope:
        frozen = _freeze(payload)
        if canonical_digest(frozen) != receipt.outbox_payload_digest:
            raise C3Error("COMMIT_RECEIPT_MISMATCH", "outbox payload digest mismatch")
        return cls(
            receipt.outbox_event_id,
            receipt.commit_id,
            receipt.aggregate_ref,
            receipt.to_revision,
            frozen,
            receipt.outbox_payload_digest,
            receipt.branch,
            receipt.committed_at,
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "commit_id": self.commit_id,
            "aggregate_ref": self.aggregate_ref,
            "aggregate_revision": self.aggregate_revision,
            "payload": _thaw(self.payload),
            "payload_digest": self.payload_digest,
            "branch": self.branch,
            "occurred_at": format_utc_timestamp(self.occurred_at),
        }


@runtime_checkable
class GovernedCommitPort(Protocol):
    def commit(self, command: GovernedCanonicalCommitCommand) -> CommitReceipt: ...


@runtime_checkable
class CanonicalReadPort(Protocol):
    def read(
        self, tenant_id: str, aggregate_type: str, aggregate_ref: str
    ) -> CanonicalSnapshot | None: ...


@runtime_checkable
class OutboxRelayPort(Protocol):
    def claim_batch(self, *, limit: int) -> tuple[OutboxEnvelope, ...]: ...

    def acknowledge(self, event_id: str, *, acknowledged_at: datetime) -> None: ...


@runtime_checkable
class RevisionPort(Protocol):
    def current_revision(
        self, tenant_id: str, aggregate_type: str, aggregate_ref: str
    ) -> int: ...


@runtime_checkable
class RecoveryPort(Protocol):
    def reconcile(self, *, limit: int) -> int: ...
