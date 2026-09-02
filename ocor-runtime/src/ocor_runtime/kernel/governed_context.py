"""Closed, binding-verified Governed Context Set boundary codec."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, ClassVar

from ..errors import CanonicalizationError
from .canonical import (
    canonical_bytes,
    canonical_digest,
    canonical_set,
    parse_i_json,
    verify_canonical_digest,
)

GCS_FIELDS = (
    "tenant_id",
    "organization_id",
    "domain_id",
    "compartments",
    "classification_marking_ref",
    "purpose",
    "effective_principal_id",
    "actor_chain",
    "ontology_release_digest",
    "policy_bundle_digest",
    "correlation_id",
)
GCS_FIELD_SET = frozenset(GCS_FIELDS)
DIGEST = re.compile(r"urn:sha256:[0-9a-f]{64}")
PROTO_DECLARED_FIELDS = (
    "tenant_id",
    "organization_id",
    "domain_id",
    "compartments",
    "classification_marking_ref",
    "purpose",
    "ontology_release_digest",
    "policy_bundle_digest",
    "correlation_id",
)


class GovernedContextError(ValueError):
    """Stable fail-closed error for an invalid or unbound GCS."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _required_string(field: str, value: object) -> str:
    if not isinstance(value, str) or not value:
        raise GovernedContextError(
            "GOVERNED_CONTEXT_INVALID",
            f"{field} must be a non-empty string without coercion",
        )
    return value


def _required_digest(field: str, value: object) -> str:
    result = _required_string(field, value)
    if DIGEST.fullmatch(result) is None:
        raise GovernedContextError(
            "GOVERNED_CONTEXT_INVALID",
            f"{field} must be a canonical SHA-256 URN",
        )
    return result


def _required_array(field: str, value: object, *, semantic_set: bool) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise GovernedContextError(
            "GOVERNED_CONTEXT_INVALID", f"{field} must be a non-empty array"
        )
    items = tuple(_required_string(field, item) for item in value)
    if not items:
        raise GovernedContextError(
            "GOVERNED_CONTEXT_INVALID", f"{field} must be a non-empty array"
        )
    if len(set(items)) != len(items):
        raise GovernedContextError(
            "GOVERNED_CONTEXT_INVALID", f"{field} contains a duplicate value"
        )
    if not semantic_set:
        return items
    try:
        return canonical_set(items)
    except CanonicalizationError as exc:  # defensive: duplicate check is explicit above
        raise GovernedContextError("GOVERNED_CONTEXT_INVALID", str(exc)) from exc


def _required_mapping_array(
    field: str, value: object, *, semantic_set: bool
) -> tuple[str, ...]:
    """Validate a JSON-schema array at a mapping boundary without coercion."""

    if not isinstance(value, list):
        raise GovernedContextError(
            "GOVERNED_CONTEXT_INVALID", f"{field} must be a non-empty array"
        )
    return _required_array(field, value, semantic_set=semantic_set)


@dataclass(frozen=True, slots=True)
class GovernedContext:
    """The exact normative eleven-field GovernedContext v1.2 record."""

    tenant_id: str
    organization_id: str
    domain_id: str
    compartments: tuple[str, ...]
    classification_marking_ref: str
    purpose: str
    effective_principal_id: str
    actor_chain: tuple[str, ...]
    ontology_release_digest: str
    policy_bundle_digest: str
    correlation_id: str

    fields: ClassVar[tuple[str, ...]] = GCS_FIELDS

    def __post_init__(self) -> None:
        for field in (
            "tenant_id",
            "organization_id",
            "domain_id",
            "purpose",
            "effective_principal_id",
        ):
            _required_string(field, getattr(self, field))
        object.__setattr__(
            self,
            "compartments",
            _required_array("compartments", self.compartments, semantic_set=True),
        )
        object.__setattr__(
            self,
            "actor_chain",
            _required_array("actor_chain", self.actor_chain, semantic_set=False),
        )
        for field in (
            "classification_marking_ref",
            "ontology_release_digest",
            "policy_bundle_digest",
        ):
            _required_digest(field, getattr(self, field))
        _required_string("correlation_id", self.correlation_id)

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> GovernedContext:
        """Validate a closed record without applying a trust binding."""

        if not isinstance(value, Mapping):
            raise GovernedContextError(
                "GOVERNED_CONTEXT_INVALID", "GovernedContext must be an object"
            )
        present = frozenset(value)
        missing = sorted(GCS_FIELD_SET - present)
        additional = sorted(present - GCS_FIELD_SET)
        if missing:
            raise GovernedContextError(
                "GOVERNED_CONTEXT_INCOMPLETE",
                f"missing GovernedContext fields: {', '.join(missing)}",
            )
        if additional:
            raise GovernedContextError(
                "GOVERNED_CONTEXT_ADDITIONAL_PROPERTY",
                f"additional GovernedContext fields: {', '.join(additional)}",
            )
        return cls(
            tenant_id=value["tenant_id"],  # type: ignore[arg-type]
            organization_id=value["organization_id"],  # type: ignore[arg-type]
            domain_id=value["domain_id"],  # type: ignore[arg-type]
            compartments=_required_mapping_array(
                "compartments", value["compartments"], semantic_set=True
            ),
            classification_marking_ref=value["classification_marking_ref"],  # type: ignore[arg-type]
            purpose=value["purpose"],  # type: ignore[arg-type]
            effective_principal_id=value["effective_principal_id"],  # type: ignore[arg-type]
            actor_chain=_required_mapping_array(
                "actor_chain", value["actor_chain"], semantic_set=False
            ),
            ontology_release_digest=value["ontology_release_digest"],  # type: ignore[arg-type]
            policy_bundle_digest=value["policy_bundle_digest"],  # type: ignore[arg-type]
            correlation_id=value["correlation_id"],  # type: ignore[arg-type]
        )

    def to_mapping(self) -> dict[str, object]:
        """Return the exact boundary names in normative order."""

        return {
            "tenant_id": self.tenant_id,
            "organization_id": self.organization_id,
            "domain_id": self.domain_id,
            "compartments": list(self.compartments),
            "classification_marking_ref": self.classification_marking_ref,
            "purpose": self.purpose,
            "effective_principal_id": self.effective_principal_id,
            "actor_chain": list(self.actor_chain),
            "ontology_release_digest": self.ontology_release_digest,
            "policy_bundle_digest": self.policy_bundle_digest,
            "correlation_id": self.correlation_id,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_bytes(self.to_mapping())

    def digest(self) -> str:
        return canonical_digest(self.to_mapping())

    def isolation_key(self) -> tuple[object, ...]:
        """Return the exact normative cache/index partition key."""

        return (
            self.tenant_id,
            self.organization_id,
            self.domain_id,
            self.compartments,
            self.purpose,
            self.classification_marking_ref,
            self.ontology_release_digest,
            self.policy_bundle_digest,
        )


@dataclass(frozen=True, slots=True)
class VerifiedGovernedContextBinding:
    """Trusted admission result supplied by an authenticated binding provider."""

    binding_ref: str
    expected: GovernedContext

    def __post_init__(self) -> None:
        _required_string("binding_ref", self.binding_ref)
        if not isinstance(self.expected, GovernedContext):
            raise GovernedContextError(
                "GOVERNED_CONTEXT_INVALID", "binding must contain a validated context"
            )


class GovernedContextCodec:
    """Verify the same GCS and digest at JSON, OpenAPI and Proto boundaries."""

    @staticmethod
    def _require_binding(binding: object) -> VerifiedGovernedContextBinding:
        if not isinstance(binding, VerifiedGovernedContextBinding):
            raise GovernedContextError(
                "GOVERNED_CONTEXT_MISMATCH", "a verified binding is required"
            )
        return binding

    @staticmethod
    def _admit(
        candidate: GovernedContext,
        binding: VerifiedGovernedContextBinding,
        claimed_digest: str,
    ) -> GovernedContext:
        binding = GovernedContextCodec._require_binding(binding)
        if candidate != binding.expected:
            differing = [
                field
                for field in GCS_FIELDS
                if getattr(candidate, field) != getattr(binding.expected, field)
            ]
            raise GovernedContextError(
                "GOVERNED_CONTEXT_MISMATCH",
                f"binding mismatch for: {', '.join(differing)}",
            )
        try:
            verify_canonical_digest(candidate.to_mapping(), claimed_digest)
        except CanonicalizationError as exc:
            raise GovernedContextError(
                "GOVERNED_CONTEXT_MISMATCH", f"governed context digest mismatch: {exc}"
            ) from exc
        return candidate

    @staticmethod
    def to_json(context: GovernedContext) -> bytes:
        return context.canonical_bytes()

    @classmethod
    def from_json(
        cls,
        payload: str | bytes | bytearray,
        binding: VerifiedGovernedContextBinding,
        claimed_digest: str,
    ) -> GovernedContext:
        try:
            parsed = parse_i_json(payload)
        except (CanonicalizationError, UnicodeError, ValueError) as exc:
            raise GovernedContextError(
                "GOVERNED_CONTEXT_INVALID", f"invalid JSON or duplicate key: {exc}"
            ) from exc
        if not isinstance(parsed, Mapping):
            raise GovernedContextError(
                "GOVERNED_CONTEXT_INVALID", "GovernedContext JSON must be an object"
            )
        return cls._admit(
            GovernedContext.from_mapping(parsed), binding, claimed_digest
        )

    @staticmethod
    def to_openapi(context: GovernedContext) -> dict[str, object]:
        return context.to_mapping()

    @classmethod
    def from_openapi(
        cls,
        value: Mapping[str, object],
        binding: VerifiedGovernedContextBinding,
        claimed_digest: str,
    ) -> GovernedContext:
        return cls._admit(
            GovernedContext.from_mapping(value), binding, claimed_digest
        )

    @staticmethod
    def to_proto(context: GovernedContext, message: Any) -> Any:
        """Populate the approved InvocationContext transport projection."""

        for field in PROTO_DECLARED_FIELDS:
            value = getattr(context, field)
            if field == "compartments":
                target = getattr(message, field)
                del target[:]
                target.extend(value)
            else:
                setattr(message, field, value)
        message.governed_context_digest = context.digest()
        return message

    @classmethod
    def from_proto(
        cls, message: Any, binding: VerifiedGovernedContextBinding
    ) -> GovernedContext:
        """Rebuild omitted identity fields only from the verified binding."""

        binding = cls._require_binding(binding)
        values = binding.expected.to_mapping()
        try:
            for field in PROTO_DECLARED_FIELDS:
                raw = getattr(message, field)
                values[field] = list(raw) if field == "compartments" else raw
            claimed_digest = message.governed_context_digest
        except AttributeError as exc:
            raise GovernedContextError(
                "GOVERNED_CONTEXT_INCOMPLETE",
                f"missing Proto GovernedContext projection: {exc}",
            ) from exc
        return cls._admit(
            GovernedContext.from_mapping(values), binding, claimed_digest
        )
