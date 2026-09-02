"""Canonical bytes, identifiers, digests and UTC boundary primitives."""

from __future__ import annotations

import hashlib
import hmac
import re
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import pairwise
from typing import Any, TypeVar

from ..canonical import canonicalize, load_i_json
from ..errors import CanonicalizationError, OCORError

T = TypeVar("T")
DIGEST = re.compile(r"urn:sha256:[0-9a-f]{64}")
UTC_TIMESTAMP = re.compile(
    r"(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})T"
    r"(?P<time>[0-9]{2}:[0-9]{2}:[0-9]{2})"
    r"(?P<fraction>\.[0-9]{1,6})?Z"
)


class KernelBoundaryError(OCORError, ValueError):
    """A typed kernel-boundary failure with a stable bounded reason code."""

    code = "KERNEL_BOUNDARY_INVALID"


class IdentifierError(KernelBoundaryError):
    """An identifier is absent, non-canonical or outside RFC 4122."""

    code = "IDENTIFIER_INVALID"


class TimestampError(KernelBoundaryError):
    """A timestamp cannot be represented at an OCOR UTC boundary."""

    code = "TIMESTAMP_INVALID"


class DigestError(CanonicalizationError):
    """A canonical digest is malformed or does not bind the supplied value."""

    code = "DIGEST_INVALID"


def canonical_bytes(value: Any) -> bytes:
    """Return RFC 8785 UTF-8 bytes for an I-JSON value."""

    return canonicalize(value)


def parse_i_json(document: str | bytes | bytearray) -> Any:
    """Parse I-JSON, rejecting duplicate keys and ambiguous numeric values."""

    return load_i_json(document)


def canonical_digest(value: Any) -> str:
    """Return the normative lowercase SHA-256 URN for canonical bytes."""

    return "urn:sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def verify_canonical_digest(value: Any, claimed_digest: str) -> str:
    """Recalculate a digest and fail closed on malformed or mismatched claims."""

    if not isinstance(claimed_digest, str) or DIGEST.fullmatch(claimed_digest) is None:
        raise DigestError("claimed digest is not a canonical SHA-256 URN")
    calculated = canonical_digest(value)
    if not hmac.compare_digest(calculated, claimed_digest):
        raise DigestError("canonical digest mismatch")
    return calculated


def canonical_set(values: Iterable[T]) -> tuple[T, ...]:
    """Sort set-like JSON values by canonical bytes and reject duplicates."""

    keyed = [(canonical_bytes(value), value) for value in values]
    keyed.sort(key=lambda item: item[0])
    for previous, current in pairwise(keyed):
        if previous[0] == current[0]:
            raise CanonicalizationError("duplicate canonical value in semantic set")
    return tuple(value for _, value in keyed)


def parse_utc_timestamp(value: str) -> datetime:
    """Parse the canonical RFC 3339 UTC wire form without coercing offsets."""

    if not isinstance(value, str) or UTC_TIMESTAMP.fullmatch(value) is None:
        raise TimestampError("timestamp must be canonical RFC 3339 UTC with Z suffix")
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise TimestampError("invalid UTC timestamp") from exc
    if parsed.utcoffset() != UTC.utcoffset(parsed):
        raise TimestampError("timestamp is not UTC")
    return parsed


def format_utc_timestamp(value: datetime) -> str:
    """Normalize an aware datetime to the shortest microsecond UTC wire form."""

    if not isinstance(value, datetime):
        raise TimestampError("timestamp value must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise TimestampError("naive datetime is forbidden at a UTC boundary")
    utc_value = value.astimezone(UTC)
    rendered = utc_value.strftime("%Y-%m-%dT%H:%M:%S")
    if utc_value.microsecond:
        rendered += f".{utc_value.microsecond:06d}".rstrip("0")
    return rendered + "Z"


def _validate_identifier(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise IdentifierError(f"{field} must be a non-empty canonical UUID")
    try:
        parsed = uuid.UUID(value)
    except (AttributeError, ValueError) as exc:
        raise IdentifierError(f"{field} must be a canonical UUID") from exc
    if str(parsed) != value:
        raise IdentifierError(f"{field} must use lowercase hyphenated canonical form")
    if parsed.int == 0 or parsed.variant != uuid.RFC_4122:
        raise IdentifierError(f"{field} must be a non-nil RFC 4122 UUID")
    return value


def validate_correlation_id(value: str) -> str:
    """Validate a correlation identifier without aliasing or normalization."""

    return _validate_identifier(value, "correlation_id")


def validate_causation_id(value: str) -> str:
    """Validate a causation identifier without aliasing or normalization."""

    return _validate_identifier(value, "causation_id")


@dataclass(frozen=True, slots=True)
class TraceIdentifiers:
    """Closed correlation/causation pair carried across an OCOR boundary."""

    correlation_id: str
    causation_id: str | None = None

    def __post_init__(self) -> None:
        validate_correlation_id(self.correlation_id)
        if self.causation_id is not None:
            validate_causation_id(self.causation_id)

    def as_dict(self) -> dict[str, str | None]:
        return {
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
        }
