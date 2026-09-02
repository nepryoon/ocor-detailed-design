from __future__ import annotations

from pathlib import Path

import pytest

# isort: split
from ocor_runtime.c1_compiler import SemanticCompiler
from ocor_runtime.c2_identity import (
    IdentityRecord,
    IdentityRegistry,
    ResolutionStatus,
)
from ocor_runtime.canonical import canonical_sha256, canonicalize_json, load_i_json
from ocor_runtime.errors import (
    CanonicalizationError,
    IdentityConflictError,
    SchemaValidationError,
)

pytestmark = pytest.mark.acceptance
SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"


def test_ev_001_rfc8785_object_order_is_deterministic():
    first = {"z": 0, "a": {"b": 2, "a": 1}}
    second = {"a": {"a": 1, "b": 2}, "z": 0}
    assert canonicalize_json(first) == '{"a":{"a":1,"b":2},"z":0}'
    assert canonical_sha256(first) == canonical_sha256(second)


def test_ev_002_rfc8785_ecmascript_number_boundaries_and_escaping():
    assert canonicalize_json([1e20, 1e21, 1e-6, 1e-7, -0.0]) == (
        "[100000000000000000000,1e+21,0.000001,1e-7,0]"
    )
    assert canonicalize_json("\b\t\n\f\r\u0000\\\"") == (
        '"\\b\\t\\n\\f\\r\\u0000\\\\\\\""'
    )


def test_ev_003_non_i_json_values_fail_closed():
    for value in (float("nan"), float("-inf"), 9_007_199_254_740_993, {1: "x"}):
        with pytest.raises(CanonicalizationError):
            canonicalize_json(value)
    assert canonicalize_json(9_007_199_254_740_992) == "9007199254740992"
    assert canonicalize_json(load_i_json("9007199254740993")) == "9007199254740992"
    with pytest.raises(CanonicalizationError):
        canonicalize_json("\ud800")


def test_ev_004_compiler_is_content_addressed_and_output_is_immutable():
    source = {
        "schemaVersion": "1.2",
        "kind": "Identity",
        "payload": {"name": "Alice", "roles": ["reviewer"]},
    }
    artifact = SemanticCompiler().compile(source)
    source["payload"]["name"] = "Mallory"
    assert artifact.artifact_id == f"urn:ocor:sha256:{artifact.semantic_digest}"
    assert artifact.canonical_payload == (
        b'{"kind":"Identity","payload":{"name":"Alice","roles":["reviewer"]},'
        b'"schemaVersion":"1.2"}'
    )
    with pytest.raises(TypeError):
        artifact.document["payload"]["name"] = "Mallory"


def test_ev_005_compiler_enforces_normative_schema_and_external_references():
    compiler = SemanticCompiler.from_schema_file(SCHEMAS / "semantic-envelope.schema.json")
    valid = {
        "schemaVersion": "1.2",
        "kind": "Identity",
        "objectId": "identity-1",
        "payload": {"canonicalId": "urn:ocor:identity:alice"},
    }
    assert compiler.compile(valid).schema_id.endswith("semantic-envelope.schema.json")
    invalid = {**valid, "payload": {"canonicalId": "not-a-canonical-id"}}
    with pytest.raises(SchemaValidationError):
        compiler.compile(invalid)


def test_ev_006_canonical_identity_is_resolved_exactly():
    registry = IdentityRegistry()
    registry.register(IdentityRecord("urn:ocor:identity:alice"))
    outcome = registry.resolve("urn:ocor:identity:alice")
    assert outcome.status is ResolutionStatus.IDENTIFIED
    assert outcome.canonical_id == "urn:ocor:identity:alice"
    assert outcome.confidence == 1.0


def test_ev_007_unique_normalized_alias_resolves_to_canonical_identity():
    registry = IdentityRegistry()
    registry.register(
        IdentityRecord(
            "urn:ocor:identity:alice",
            aliases=frozenset({" Alice@Example.Invalid "}),
        )
    )
    assert registry.resolve("alice@example.invalid").canonical_id == (
        "urn:ocor:identity:alice"
    )


def test_ev_008_unknown_identity_produces_explicit_abstention():
    outcome = IdentityRegistry().resolve("unobserved@example.invalid")
    assert outcome.status is ResolutionStatus.ABSTAIN
    assert outcome.canonical_id is None
    assert "no authoritative" in outcome.reason


def test_ev_009_ambiguous_identity_produces_abstention_not_a_guess():
    registry = IdentityRegistry()
    registry.register(
        IdentityRecord("urn:ocor:identity:alice", aliases=frozenset({"shared"}))
    )
    registry.register(
        IdentityRecord("urn:ocor:identity:alicia", aliases=frozenset({"shared"}))
    )
    outcome = registry.resolve("SHARED")
    assert outcome.status is ResolutionStatus.ABSTAIN
    assert outcome.canonical_id is None
    assert outcome.candidates == (
        "urn:ocor:identity:alice",
        "urn:ocor:identity:alicia",
    )


def test_ev_010_identity_evidence_requires_threshold_and_margin_and_records_are_immutable():
    registry = IdentityRegistry()
    alice = IdentityRecord(
        "urn:ocor:identity:alice",
        aliases=frozenset({"shared"}),
        attributes={"country": "IT"},
    )
    registry.register(alice)
    registry.register(
        IdentityRecord("urn:ocor:identity:alicia", aliases=frozenset({"shared"}))
    )
    weak = registry.resolve(
        "shared",
        evidence={
            "urn:ocor:identity:alice": 0.79,
            "urn:ocor:identity:alicia": 0.10,
        },
    )
    assert weak.status is ResolutionStatus.ABSTAIN
    strong = registry.resolve(
        "shared",
        evidence={
            "urn:ocor:identity:alice": 0.95,
            "urn:ocor:identity:alicia": 0.20,
        },
    )
    assert strong.canonical_id == "urn:ocor:identity:alice"
    with pytest.raises(IdentityConflictError):
        registry.register(
            IdentityRecord(
                "urn:ocor:identity:alice", attributes={"country": "US"}
            )
        )
