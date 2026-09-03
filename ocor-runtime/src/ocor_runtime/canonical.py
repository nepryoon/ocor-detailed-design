"""RFC 8785 (JCS) JSON canonicalization.

The implementation intentionally does not delegate to ``json.dumps`` for number
or object-key formatting.  JCS uses ECMAScript number serialization and UTF-16
code-unit ordering, both of which differ from Python's JSON defaults at relevant
boundary values.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from typing import Any

from .errors import CanonicalizationError, DigestProviderError

MAX_SAFE_INTEGER = 9_007_199_254_740_991


def _validate_scalar_string(value: str) -> None:
    for character in value:
        codepoint = ord(character)
        if 0xD800 <= codepoint <= 0xDFFF:
            raise CanonicalizationError("lone UTF-16 surrogate is not valid I-JSON")


def _serialize_string(value: str) -> str:
    _validate_scalar_string(value)
    escapes = {
        '"': r'\"',
        "\\": r"\\",
        "\b": r"\b",
        "\t": r"\t",
        "\n": r"\n",
        "\f": r"\f",
        "\r": r"\r",
    }
    encoded: list[str] = ['"']
    for character in value:
        escaped = escapes.get(character)
        if escaped is not None:
            encoded.append(escaped)
        elif ord(character) <= 0x1F:
            encoded.append(f"\\u{ord(character):04x}")
        else:
            encoded.append(character)
    encoded.append('"')
    return "".join(encoded)


def _utf16_sort_key(value: str) -> bytes:
    _validate_scalar_string(value)
    return value.encode("utf-16-be")


def _serialize_float(value: float) -> str:
    if not math.isfinite(value):
        raise CanonicalizationError("NaN and Infinity are not valid I-JSON numbers")
    if value == 0.0:
        return "0"

    sign = "-" if value < 0 else ""
    rendered = repr(abs(value)).lower()
    if "e" in rendered:
        mantissa, exponent_text = rendered.split("e", 1)
        exponent = int(exponent_text)
    else:
        mantissa, exponent = rendered, 0

    if "." in mantissa:
        integer_part, fraction_part = mantissa.split(".", 1)
        digits = integer_part + fraction_part
        decimal_position = len(integer_part) + exponent
    else:
        digits = mantissa
        decimal_position = len(mantissa) + exponent

    while len(digits) > 1 and digits.startswith("0"):
        digits = digits[1:]
        decimal_position -= 1
    while len(digits) > 1 and digits.endswith("0"):
        digits = digits[:-1]

    scientific_exponent = decimal_position - 1
    if scientific_exponent >= 21 or scientific_exponent <= -7:
        coefficient = digits[0]
        if len(digits) > 1:
            coefficient += "." + digits[1:]
        exponent_sign = "+" if scientific_exponent >= 0 else ""
        return f"{sign}{coefficient}e{exponent_sign}{scientific_exponent}"

    if decimal_position <= 0:
        body = "0." + ("0" * -decimal_position) + digits
    elif decimal_position >= len(digits):
        body = digits + ("0" * (decimal_position - len(digits)))
    else:
        body = digits[:decimal_position] + "." + digits[decimal_position:]
    return sign + body


def _serialize_integer(value: int) -> str:
    """Serialize integers only when their value survives the binary64 boundary."""

    if abs(value) <= MAX_SAFE_INTEGER:
        return str(value)
    try:
        binary64 = float(value)
    except OverflowError as exc:
        raise CanonicalizationError(
            "integer is not representable as an IEEE-754 binary64 value"
        ) from exc
    if not math.isfinite(binary64) or int(binary64) != value:
        raise CanonicalizationError(
            "integer is not exactly representable as an IEEE-754 binary64 value"
        )
    return _serialize_float(binary64)


def _serialize(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return _serialize_string(value)
    if isinstance(value, int):
        return _serialize_integer(value)
    if isinstance(value, float):
        return _serialize_float(value)
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise CanonicalizationError("JSON object keys must be strings")
        entries = []
        for key in sorted(value, key=_utf16_sort_key):
            entries.append(f"{_serialize_string(key)}:{_serialize(value[key])}")
        return "{" + ",".join(entries) + "}"
    if isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray, memoryview)
    ):
        return "[" + ",".join(_serialize(item) for item in value) + "]"
    raise CanonicalizationError(
        f"value of type {type(value).__name__!r} is not an I-JSON value"
    )


def canonicalize_json(value: Any) -> str:
    """Return the RFC 8785 canonical JSON text for a parsed JSON value."""

    return _serialize(value)


def canonicalize(value: Any) -> bytes:
    """Return RFC 8785 canonical JSON encoded as UTF-8 bytes."""

    return canonicalize_json(value).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    """Return a lowercase SHA-256 digest over canonical UTF-8 JSON."""

    try:
        return hashlib.sha256(canonicalize(value)).hexdigest()
    except OSError as exc:
        raise DigestProviderError("SHA-256 provider failure") from exc


def load_i_json(document: str | bytes | bytearray) -> Any:
    """Parse I-JSON while rejecting duplicate keys and non-finite constants."""

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise CanonicalizationError("duplicate object key")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise CanonicalizationError(f"non-finite JSON constant: {value}")

    def parse_integer(value: str) -> int | float:
        """Map JSON integers to the I-JSON binary64 domain without host-int drift."""

        try:
            binary64 = float(value)
        except (OverflowError, ValueError) as exc:
            raise CanonicalizationError("invalid I-JSON integer") from exc
        if not math.isfinite(binary64):
            raise CanonicalizationError(
                "integer is not representable as an IEEE-754 binary64 value"
            )
        if abs(binary64) <= MAX_SAFE_INTEGER:
            return int(value)
        return binary64

    try:
        parsed = json.loads(
            document,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_constant,
            parse_int=parse_integer,
        )
    except CanonicalizationError:
        raise
    except (UnicodeError, ValueError) as exc:
        raise CanonicalizationError("invalid I-JSON document") from exc
    canonicalize(parsed)
    return parsed
