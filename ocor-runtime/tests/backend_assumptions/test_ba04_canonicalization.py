from __future__ import annotations

import pytest
from ocor_runtime.canonical import canonical_sha256, canonicalize_json, load_i_json
from ocor_runtime.errors import CanonicalizationError

pytestmark = pytest.mark.backend_assumption


def test_ba04_rfc8785_known_number_and_string_vector():
    value = {
        "numbers": [333333333.33333329, 1e30, 4.50, 2e-3, 1e-27, -0.0],
        "string": "€$\u000f\nA'B\"\\\"/",
        "literals": [None, True, False],
    }
    assert canonicalize_json(value) == (
        '{"literals":[null,true,false],'
        '"numbers":[333333333.3333333,1e+30,4.5,0.002,1e-27,0],'
        '"string":"€$\\u000f\\nA\'B\\\"\\\\\\\"/"}'
    )


def test_ba04_key_order_does_not_change_digest_and_utf16_order_is_used():
    left = {"\ufffd": 1, "😀": 2, "a": 3}
    right = {"a": 3, "😀": 2, "\ufffd": 1}
    assert canonical_sha256(left) == canonical_sha256(right)
    assert canonicalize_json(left).startswith('{"a":3,"😀":2,"�":1')


@pytest.mark.parametrize("value", [float("nan"), float("inf"), 2**53 + 1])
def test_ba04_non_interoperable_numbers_are_rejected(value):
    with pytest.raises(CanonicalizationError):
        canonicalize_json(value)


def test_ba04_exact_binary64_integer_boundary_is_canonical():
    assert canonicalize_json(2**53) == "9007199254740992"


def test_ba04_duplicate_json_members_are_rejected():
    with pytest.raises(CanonicalizationError):
        load_i_json('{"a":1,"a":2}')
