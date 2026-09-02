"""Typed named-query, consistency and watermark ports for C2."""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any, ClassVar, Protocol, runtime_checkable

from ..kernel.canonical import (
    IdentifierError,
    validate_correlation_id,
    verify_canonical_digest,
)
from ..kernel.governed_context import GovernedContext, GovernedContextError

DIGEST = re.compile(r"urn:sha256:[0-9a-f]{64}")
NAMED_CONTRACT = re.compile(r"urn:ocor:contract:named-query:[A-Za-z0-9._~-]+")
FORBIDDEN_QUERY_FIELDS = frozenset({"query", "query_text", "sparql", "sql", "typeql", "woql"})


class C2Error(ValueError):
    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {message}")


def _required(field: str, value: object) -> str:
    if not isinstance(value, str) or not value:
        raise C2Error("QUERY_CONTRACT_INVALID", f"{field} is required")
    return value


def _digest(field: str, value: object) -> str:
    result = _required(field, value)
    if DIGEST.fullmatch(result) is None:
        raise C2Error("QUERY_CONTRACT_INVALID", f"{field} must be a SHA-256 URN")
    return result


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(child) for key, child in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(child) for child in value)
    return copy.deepcopy(value)


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [_thaw(child) for child in value]
    return copy.deepcopy(value)


class ConsistencyMode(StrEnum):
    BEST_AVAILABLE = "BEST_AVAILABLE"
    AT_LEAST_COMMIT = "AT_LEAST_COMMIT"
    EXACT_AT_COMMIT = "EXACT_AT_COMMIT"


@dataclass(frozen=True, slots=True)
class ServedContext:
    branch: str
    ontology_release_digest: str
    canonical_commit: str
    projection_watermark: str
    staleness_ms: int
    governed_context_digest: str
    policy_bundle_digest: str

    def __post_init__(self) -> None:
        for field in ("branch", "canonical_commit", "projection_watermark"):
            _required(field, getattr(self, field))
        for field in (
            "ontology_release_digest",
            "governed_context_digest",
            "policy_bundle_digest",
        ):
            _digest(field, getattr(self, field))
        if isinstance(self.staleness_ms, bool) or not isinstance(self.staleness_ms, int) or self.staleness_ms < 0:
            raise C2Error("QUERY_CONTRACT_INVALID", "staleness_ms must be non-negative")


@dataclass(frozen=True, slots=True)
class ConsistencyRequirement:
    mode: ConsistencyMode
    required_commit: str | None = None
    wait_timeout_ms: int = 0

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "mode", ConsistencyMode(self.mode))
        except ValueError as exc:
            raise C2Error("CONSISTENCY_INVALID", f"unknown consistency mode: {self.mode}") from exc
        if isinstance(self.wait_timeout_ms, bool) or not isinstance(self.wait_timeout_ms, int) or not 0 <= self.wait_timeout_ms <= 30000:
            raise C2Error("CONSISTENCY_INVALID", "wait_timeout_ms is outside 0..30000")
        requires_commit = self.mode in {
            ConsistencyMode.AT_LEAST_COMMIT,
            ConsistencyMode.EXACT_AT_COMMIT,
        }
        if requires_commit and (not isinstance(self.required_commit, str) or not self.required_commit):
            raise C2Error("CONSISTENCY_INVALID", "required_commit is mandatory for strong consistency")
        if not requires_commit and self.required_commit is not None:
            raise C2Error("CONSISTENCY_INVALID", "BEST_AVAILABLE cannot declare required_commit")

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> ConsistencyRequirement:
        allowed = {"mode", "required_commit", "wait_timeout_ms"}
        if set(value) - allowed:
            raise C2Error("CONSISTENCY_INVALID", "additional consistency property")
        try:
            return cls(
                mode=value["mode"],  # type: ignore[arg-type]
                required_commit=value.get("required_commit"),  # type: ignore[arg-type]
                wait_timeout_ms=value.get("wait_timeout_ms", 0),  # type: ignore[arg-type]
            )
        except KeyError as exc:
            raise C2Error("CONSISTENCY_INVALID", "mode is required") from exc

    def to_mapping(self) -> dict[str, object]:
        result: dict[str, object] = {"mode": self.mode.value, "wait_timeout_ms": self.wait_timeout_ms}
        if self.required_commit is not None:
            result["required_commit"] = self.required_commit
        return result

    def verify_served(self, served: ServedContext) -> ServedContext:
        if self.mode is ConsistencyMode.BEST_AVAILABLE:
            return served
        if served.projection_watermark != self.required_commit:
            reason = (
                "CONSISTENCY_DOWNGRADE"
                if self.mode is ConsistencyMode.EXACT_AT_COMMIT
                else "PROJECTION_NOT_READY"
            )
            raise C2Error(reason, "served watermark does not satisfy the requested commit")
        if self.mode is ConsistencyMode.EXACT_AT_COMMIT and served.canonical_commit != self.required_commit:
            raise C2Error("CONSISTENCY_DOWNGRADE", "served commit is not exact")
        return served


@dataclass(frozen=True, slots=True)
class NamedQueryRequest:
    request_id: str
    contract_id: str
    contract_version: str
    contract_digest: str
    parameters: Mapping[str, Any]
    governed_context: GovernedContext
    governed_context_digest: str
    consistency: ConsistencyRequirement

    fields: ClassVar[tuple[str, ...]] = (
        "request_id",
        "contract_id",
        "contract_version",
        "contract_digest",
        "parameters",
        "governed_context",
        "governed_context_digest",
        "consistency",
    )

    def __post_init__(self) -> None:
        try:
            validate_correlation_id(self.request_id)
        except IdentifierError as exc:
            raise C2Error("QUERY_CONTRACT_INVALID", f"request_id is invalid: {exc}") from exc
        if NAMED_CONTRACT.fullmatch(self.contract_id) is None:
            raise C2Error("ARBITRARY_QUERY_FORBIDDEN", "only allow-listed named query contract IDs are accepted")
        _required("contract_version", self.contract_version)
        _digest("contract_digest", self.contract_digest)
        _digest("governed_context_digest", self.governed_context_digest)
        if not self.governed_context.purpose:
            raise C2Error("PURPOSE_MISSING", "purpose is required before routing")
        try:
            verify_canonical_digest(
                self.governed_context.to_mapping(), self.governed_context_digest
            )
        except Exception as exc:
            raise C2Error("GOVERNED_CONTEXT_MISMATCH", "GCS digest mismatch") from exc
        if not isinstance(self.parameters, Mapping):
            raise C2Error("QUERY_CONTRACT_INVALID", "parameters must be an object")
        forbidden = FORBIDDEN_QUERY_FIELDS & {str(key).lower() for key in self.parameters}
        if forbidden:
            raise C2Error("ARBITRARY_QUERY_FORBIDDEN", "parameters contain arbitrary query text")
        object.__setattr__(self, "parameters", _freeze(self.parameters))

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> NamedQueryRequest:
        present = set(value)
        additional = present - set(cls.fields)
        missing = set(cls.fields) - present
        if additional:
            reason = "ARBITRARY_QUERY_FORBIDDEN" if {str(item).lower() for item in additional} & FORBIDDEN_QUERY_FIELDS else "QUERY_CONTRACT_INVALID"
            raise C2Error(reason, f"additional query fields: {sorted(additional)}")
        if missing:
            raise C2Error("QUERY_CONTRACT_INVALID", f"missing query fields: {sorted(missing)}")
        context_value = value["governed_context"]
        if not isinstance(context_value, Mapping):
            raise C2Error("QUERY_CONTRACT_INVALID", "governed_context must be an object")
        try:
            context = GovernedContext.from_mapping(context_value)
        except GovernedContextError as exc:
            reason = "PURPOSE_MISSING" if "purpose" in str(exc) else "GOVERNED_CONTEXT_MISMATCH"
            raise C2Error(reason, str(exc)) from exc
        consistency_value = value["consistency"]
        if not isinstance(consistency_value, Mapping):
            raise C2Error("CONSISTENCY_INVALID", "consistency must be an object")
        return cls(
            request_id=value["request_id"],  # type: ignore[arg-type]
            contract_id=value["contract_id"],  # type: ignore[arg-type]
            contract_version=value["contract_version"],  # type: ignore[arg-type]
            contract_digest=value["contract_digest"],  # type: ignore[arg-type]
            parameters=value["parameters"],  # type: ignore[arg-type]
            governed_context=context,
            governed_context_digest=value["governed_context_digest"],  # type: ignore[arg-type]
            consistency=ConsistencyRequirement.from_mapping(consistency_value),
        )

    @property
    def isolation_key(self) -> tuple[object, ...]:
        return self.governed_context.isolation_key()

    def to_mapping(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "contract_digest": self.contract_digest,
            "parameters": _thaw(self.parameters),
            "governed_context": self.governed_context.to_mapping(),
            "governed_context_digest": self.governed_context_digest,
            "consistency": self.consistency.to_mapping(),
        }

    def verify_served(self, served: ServedContext) -> ServedContext:
        context = self.governed_context
        if (
            served.governed_context_digest != self.governed_context_digest
            or served.policy_bundle_digest != context.policy_bundle_digest
            or served.ontology_release_digest != context.ontology_release_digest
        ):
            raise C2Error("STALE_CONTEXT", "served context drifted from request bindings")
        return self.consistency.verify_served(served)


@dataclass(frozen=True, slots=True)
class NamedQueryResponse:
    request_id: str
    result_ref: str
    result_digest: str
    served: ServedContext

    def __post_init__(self) -> None:
        validate_correlation_id(self.request_id)
        _required("result_ref", self.result_ref)
        _digest("result_digest", self.result_digest)


@dataclass(frozen=True, slots=True)
class Watermark:
    projection_id: str
    branch: str
    ontology_release_digest: str
    canonical_commit: str
    observed_at: datetime

    def __post_init__(self) -> None:
        for field in ("projection_id", "branch", "canonical_commit"):
            _required(field, getattr(self, field))
        _digest("ontology_release_digest", self.ontology_release_digest)
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise C2Error("QUERY_CONTRACT_INVALID", "observed_at must be timezone-aware")


@runtime_checkable
class NamedQueryPort(Protocol):
    def execute(self, request: NamedQueryRequest) -> NamedQueryResponse: ...


@runtime_checkable
class ProjectionReadPort(Protocol):
    def read(self, request: NamedQueryRequest) -> NamedQueryResponse: ...


@runtime_checkable
class PolicyDecisionPort(Protocol):
    def decide(self, request: NamedQueryRequest) -> str: ...


@runtime_checkable
class AuthorityResolutionPort(Protocol):
    def resolve(self, request: NamedQueryRequest) -> str: ...


@runtime_checkable
class EvidenceReadPort(Protocol):
    def get(self, evidence_ref: str, request: NamedQueryRequest) -> Mapping[str, object]: ...


@runtime_checkable
class WatermarkPort(Protocol):
    def current(self, projection_id: str, branch: str) -> Watermark: ...
