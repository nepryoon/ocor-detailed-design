from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta, timezone

import pytest
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
        '{"value":9007199254740992}',
        '"\ud800"',
    ],
)
def test_duplicate_keys_and_non_i_json_values_are_rejected(document: str):
    with pytest.raises(CanonicalizationError):
        parse_i_json(document)
