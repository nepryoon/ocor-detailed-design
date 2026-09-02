from __future__ import annotations

import hashlib
import shutil
import struct
import subprocess
from datetime import UTC, datetime, timedelta, timezone

import pytest

# isort: split
from ocor_runtime.errors import CanonicalizationError
from ocor_runtime.kernel.canonical import (
    IdentifierError,
    TimestampError,
    TraceIdentifiers,
    canonical_bytes,
    canonical_digest,
    canonical_set,
    format_utc_timestamp,
    parse_i_json,
    parse_utc_timestamp,
    validate_causation_id,
    validate_correlation_id,
    verify_canonical_digest,
)


def test_rfc_8785_number_and_string_vectors_produce_stable_bytes():
    value = {
        "numbers": [333333333.33333329, 1e30, 4.50, 2e-3, 1e-27],
        "string": "€$\u000f\nA'B\"\\\"/",
        "literals": [None, True, False],
    }
    assert canonical_bytes(value) == (
        b'{"literals":[null,true,false],"numbers":[333333333.3333333,1e+30,4.5,0.002,1e-27],'
        b'"string":"\xe2\x82\xac$\\u000f\\nA\'B\\\"\\\\\\\"/"}'
    )


@pytest.mark.parametrize(
    ("binary64_hex", "expected"),
    [
        ("0000000000000000", "0"),
        ("8000000000000000", "0"),
        ("0000000000000001", "5e-324"),
        ("8000000000000001", "-5e-324"),
        ("7fefffffffffffff", "1.7976931348623157e+308"),
        ("ffefffffffffffff", "-1.7976931348623157e+308"),
        ("4340000000000000", "9007199254740992"),
        ("c340000000000000", "-9007199254740992"),
        ("4430000000000000", "295147905179352830000"),
        ("44b52d02c7e14af5", "9.999999999999997e+22"),
        ("44b52d02c7e14af6", "1e+23"),
        ("44b52d02c7e14af7", "1.0000000000000001e+23"),
        ("444b1ae4d6e2ef4c", "999999999999999500000"),
        ("444b1ae4d6e2ef4d", "999999999999999600000"),
        ("444b1ae4d6e2ef4e", "999999999999999700000"),
        ("444b1ae4d6e2ef4f", "999999999999999900000"),
        ("444b1ae4d6e2ef50", "1e+21"),
        ("3eb0c6f7a0b5ed8c", "9.999999999999997e-7"),
        ("3eb0c6f7a0b5ed8d", "0.000001"),
        ("3e7ad7f29abcaf48", "1e-7"),
    ],
)
def test_rfc_8785_appendix_b_binary64_vectors(binary64_hex: str, expected: str):
    value = struct.unpack(">d", bytes.fromhex(binary64_hex))[0]
    assert canonical_bytes(value) == expected.encode()
    assert canonical_bytes(parse_i_json(expected)) == expected.encode()


def test_exact_two_to_the_53_integer_has_independent_golden_digest():
    value = 9_007_199_254_740_992
    assert canonical_bytes(value) == b"9007199254740992"
    assert parse_i_json("9007199254740992") == value
    assert canonical_digest(value) == (
        "urn:sha256:c681da39d7273a6a24c15c9cac3a75526ff2ecf8ba4ee60346a0c70c8163bdb2"
    )


@pytest.mark.parametrize(
    "document",
    [
        "9007199254740992",
        "9007199254740993",
        "-9007199254740992",
        "295147905179352830000",
        "999999999999999900000",
        "1e23",
        "1e-7",
        "0.000001",
    ],
)
def test_number_serialization_matches_node_ecmascript_boundary(document: str):
    node = shutil.which("node")
    assert node is not None, "Node.js is mandatory for the cross-language JCS oracle"
    version = subprocess.run(
        [node, "--version"], check=False, capture_output=True, text=True, timeout=10
    )
    assert version.returncode == 0 and version.stdout.strip() == "v20.20.2"
    result = subprocess.run(
        [
            node,
            "-e",
            "process.stdout.write(JSON.stringify(JSON.parse(process.argv[1])))",
            "--",
            document,
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert canonical_bytes(parse_i_json(document)).decode() == result.stdout


def test_utf16_property_order_matches_rfc_8785():
    value = {"\r": 1, "1": 2, "\u0080": 3, "ö": 4, "€": 5, "😀": 6, "דּ": 7}
    assert canonical_bytes(value).decode() == (
        '{"\\r":1,"1":2,"\u0080":3,"ö":4,"€":5,"😀":6,"דּ":7}'
    )


def test_digest_is_lowercase_urn_and_recalculation_fails_closed():
    value = {"z": 0, "a": [3, 2, 1]}
    expected = "urn:sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()
    assert canonical_digest(value) == expected
    assert verify_canonical_digest(value, expected) == expected
    with pytest.raises(CanonicalizationError, match="digest mismatch"):
        verify_canonical_digest(value, "urn:sha256:" + "0" * 64)


def test_semantic_set_is_canonically_sorted_and_rejects_duplicates():
    assert canonical_set(["z", "a", "😀"]) == ("a", "z", "😀")
    with pytest.raises(CanonicalizationError, match="duplicate"):
        canonical_set([{"a": 1}, {"a": 1}])


def test_utc_wire_boundaries_are_strict_and_normalized():
    boundary = parse_utc_timestamp("2026-09-02T00:00:00.123400Z")
    assert boundary == datetime(2026, 9, 2, 0, 0, 0, 123400, tzinfo=UTC)
    assert format_utc_timestamp(boundary) == "2026-09-02T00:00:00.1234Z"
    shifted = datetime(2026, 9, 2, 2, 0, tzinfo=timezone(timedelta(hours=2)))
    assert format_utc_timestamp(shifted) == "2026-09-02T00:00:00Z"


@pytest.mark.parametrize(
    "value",
    [
        "2026-09-02T00:00:00",
        "2026-09-02T00:00:00+00:00",
        "2026-09-02t00:00:00z",
        "2026-09-02T00:00:60Z",
        "2026-09-02T00:00:00.1234567Z",
    ],
)
def test_noncanonical_or_unrepresentable_wire_time_is_rejected(value: str):
    with pytest.raises(TimestampError):
        parse_utc_timestamp(value)
    with pytest.raises(TimestampError, match="naive"):
        format_utc_timestamp(datetime(2026, 9, 2))  # noqa: DTZ001 -- negative case


def test_correlation_and_causation_ids_are_canonical_rfc4122_uuids():
    correlation = "018f1f76-7e0a-7cc8-98c8-acde48001122"
    causation = "550e8400-e29b-41d4-a716-446655440000"
    assert validate_correlation_id(correlation) == correlation
    assert validate_causation_id(causation) == causation
    trace = TraceIdentifiers(correlation_id=correlation, causation_id=causation)
    assert trace.as_dict() == {"correlation_id": correlation, "causation_id": causation}


@pytest.mark.parametrize(
    "value",
    [
        "",
        "550E8400-E29B-41D4-A716-446655440000",
        "{550e8400-e29b-41d4-a716-446655440000}",
        "00000000-0000-0000-0000-000000000000",
        "not-a-uuid",
    ],
)
def test_malformed_identifiers_are_rejected(value: str):
    with pytest.raises(IdentifierError):
        validate_correlation_id(value)


@pytest.mark.parametrize(
    "document",
    [
        '{"a":1,"a":2}',
        '{"value":NaN}',
        '{"value":1e10000}',
        '"\ud800"',
    ],
)
def test_duplicate_keys_and_non_i_json_values_are_rejected(document: str):
    with pytest.raises(CanonicalizationError):
        parse_i_json(document)


def test_kernel_errors_expose_stable_bounded_reason_codes():
    with pytest.raises(IdentifierError) as identifier:
        validate_correlation_id("not-a-uuid")
    with pytest.raises(TimestampError) as timestamp:
        parse_utc_timestamp("2026-09-02T00:00:00+00:00")
    assert identifier.value.code == "IDENTIFIER_INVALID"
    assert timestamp.value.code == "TIMESTAMP_INVALID"


def test_canonical_and_digest_errors_are_typed_and_bounded():
    with pytest.raises(CanonicalizationError) as huge:
        canonical_bytes(10**5000)
    with pytest.raises(CanonicalizationError) as parsed:
        parse_i_json("1" * 5000)
    with pytest.raises(CanonicalizationError) as digest:
        verify_canonical_digest({}, "not-a-digest")
    assert huge.value.code == "CANONICALIZATION_INVALID"
    assert parsed.value.code == "CANONICALIZATION_INVALID"
    assert digest.value.code == "DIGEST_INVALID"
    assert max(len(str(item.value)) for item in (huge, parsed, digest)) < 100
