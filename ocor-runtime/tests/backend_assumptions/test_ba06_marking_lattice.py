from __future__ import annotations

import pytest

from ocor_runtime.c4_marking import (
    MarkingEngine,
    MarkingSchemeDefinition,
    MarkingSet,
)
from ocor_runtime.errors import MarkingError

pytestmark = pytest.mark.backend_assumption


def test_ba06_total_order_join_is_commutative_associative_idempotent_and_monotonic():
    scheme = MarkingSchemeDefinition(
        "classification", ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "SECRET"]
    )
    assert scheme.join("PUBLIC", "SECRET") == "SECRET"
    assert scheme.join("SECRET", "PUBLIC") == "SECRET"
    assert scheme.join("INTERNAL", "INTERNAL") == "INTERNAL"
    assert scheme.join(scheme.join("PUBLIC", "INTERNAL"), "SECRET") == scheme.join(
        "PUBLIC", scheme.join("INTERNAL", "SECRET")
    )
    result = scheme.join("INTERNAL", "CONFIDENTIAL")
    assert scheme.leq("INTERNAL", result)
    assert scheme.leq("CONFIDENTIAL", result)


def test_ba06_partial_order_uses_the_unique_least_upper_bound():
    scheme = MarkingSchemeDefinition(
        "compartments",
        labels=["NONE", "ALPHA", "BRAVO", "ALPHA_BRAVO"],
        relations=[
            ("NONE", "ALPHA"),
            ("NONE", "BRAVO"),
            ("ALPHA", "ALPHA_BRAVO"),
            ("BRAVO", "ALPHA_BRAVO"),
        ],
    )
    assert scheme.join("ALPHA", "BRAVO") == "ALPHA_BRAVO"
    assert scheme.meet("ALPHA", "BRAVO") == "NONE"


def test_ba06_marking_set_join_never_downgrades_any_input():
    engine = MarkingEngine(
        [MarkingSchemeDefinition("classification", ["PUBLIC", "INTERNAL", "SECRET"])]
    )
    combined = engine.join(
        MarkingSet({"classification": "INTERNAL"}),
        MarkingSet({"classification": "SECRET"}),
    )
    assert combined["classification"] == "SECRET"


def test_ba06_non_lattice_definition_is_rejected():
    with pytest.raises(MarkingError):
        MarkingSchemeDefinition(
            "broken", labels=["A", "B"], relations=[]
        )


def test_ba06_duplicate_scheme_identifiers_are_rejected():
    scheme = MarkingSchemeDefinition("classification", ["PUBLIC", "SECRET"])
    with pytest.raises(MarkingError):
        MarkingEngine([scheme, scheme])
