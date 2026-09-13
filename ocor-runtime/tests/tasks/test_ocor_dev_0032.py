"""OCOR-DEV-0032: Complete C1 parser type-checker and semantic validation.

Proves that a comprehensive negative corpus (missing type declarations,
unsupported declared types, type mismatches, ambiguous execution
ownership, unresolved semantic references, cyclic references, and
malformed syntax) each produces a stable, correctly-coded diagnostic,
and that a valid corpus compiles deterministically -- so ambiguous,
cyclic or invalid models can never reach generation. Pure, in-memory,
deterministic component -- no external service is needed or used, like
OCOR-DEV-0028's C1 compiler slice. Reuses the sealed C1 ports
(OCOR-DEV-0011, ``ocor_runtime.c1.ports``) unmodified; OCOR-DEV-0028's
own sealed compiler is untouched.
"""

from __future__ import annotations

import json

import pytest
from ocor_runtime.c1.frontend import FrontendCanonicalIrBuilder
from ocor_runtime.c1.ports import (
    C1Error,
    CompilerRequest,
    DiagnosticCode,
    SourceSyntax,
    SourceUnit,
    verify_deterministic_build,
)

COMMIT = "0123456789abcdef0123456789abcdef01234567"


def yaml_source(resource_id: str, version: str, body: str, *, imports: tuple[str, ...] = ()) -> SourceUnit:
    return SourceUnit.create(
        resource_id=resource_id,
        version=version,
        syntax=SourceSyntax.YAML,
        content=body.encode("utf-8"),
        source_path=f"{resource_id}.yaml",
        imports=imports,
    )


def json_source(resource_id: str, version: str, body: dict[str, object]) -> SourceUnit:
    return SourceUnit.create(
        resource_id=resource_id,
        version=version,
        syntax=SourceSyntax.JSON,
        content=json.dumps(body).encode("utf-8"),
        source_path=f"{resource_id}.json",
    )


def request(sources: tuple[SourceUnit, ...]) -> CompilerRequest:
    return CompilerRequest(
        package_id="urn:ocor:package:frontend-fixture",
        semantic_version="1.0.0",
        source_commit=COMMIT,
        compiler_version="0.1.0",
        mapping_version="1",
        release_profile="poc",
        sources=sources,
        dependency_lock=(),
    )


def valid_resource(resource_id: str, *, name: str = "Alpha", count: int = 3, references: list[str] | None = None) -> SourceUnit:
    body = {
        "id": resource_id,
        "fields": {"name": name, "count": count},
        "field_types": {"name": "string", "count": "integer"},
    }
    if references is not None:
        body["references"] = references
    return json_source(resource_id, "1", body)


def test_valid_corpus_compiles_deterministically_with_field_types_and_references():
    upstream = valid_resource("urn:ocor:resource:upstream")
    downstream = valid_resource("urn:ocor:resource:downstream", references=["urn:ocor:resource:upstream"])
    release = verify_deterministic_build(FrontendCanonicalIrBuilder(), request((upstream, downstream)))

    resources = release.core["resources"]
    assert resources["urn:ocor:resource:upstream"]["field_types"] == {"name": "string", "count": "integer"}
    # release.core is recursively frozen (lists become tuples) by the
    # sealed CanonicalIrRelease.create().
    assert resources["urn:ocor:resource:downstream"]["references"] == ("urn:ocor:resource:upstream",)
    assert release.ir_digest.startswith("urn:sha256:")


def test_missing_field_types_key_is_rejected_with_type_error():
    broken = json_source(
        "urn:ocor:resource:broken",
        "1",
        {"id": "urn:ocor:resource:broken", "fields": {"name": "Alpha"}},
    )
    with pytest.raises(C1Error) as excinfo:
        FrontendCanonicalIrBuilder().build(request((broken,)))
    assert excinfo.value.diagnostics[0].code is DiagnosticCode.TYPE_ERROR


def test_field_without_a_declared_type_is_rejected_with_type_error():
    broken = json_source(
        "urn:ocor:resource:broken",
        "1",
        {
            "id": "urn:ocor:resource:broken",
            "fields": {"name": "Alpha", "count": 3},
            "field_types": {"name": "string"},
        },
    )
    with pytest.raises(C1Error) as excinfo:
        FrontendCanonicalIrBuilder().build(request((broken,)))
    assert excinfo.value.diagnostics[0].code is DiagnosticCode.TYPE_ERROR


def test_unsupported_declared_type_is_rejected_with_unsupported_capability():
    broken = json_source(
        "urn:ocor:resource:broken",
        "1",
        {
            "id": "urn:ocor:resource:broken",
            "fields": {"name": "Alpha"},
            "field_types": {"name": "regex"},
        },
    )
    with pytest.raises(C1Error) as excinfo:
        FrontendCanonicalIrBuilder().build(request((broken,)))
    assert excinfo.value.diagnostics[0].code is DiagnosticCode.UNSUPPORTED_CAPABILITY


def test_field_value_not_matching_its_declared_type_is_rejected_with_type_error():
    broken = json_source(
        "urn:ocor:resource:broken",
        "1",
        {
            "id": "urn:ocor:resource:broken",
            "fields": {"count": "not-a-number"},
            "field_types": {"count": "integer"},
        },
    )
    with pytest.raises(C1Error) as excinfo:
        FrontendCanonicalIrBuilder().build(request((broken,)))
    assert excinfo.value.diagnostics[0].code is DiagnosticCode.TYPE_ERROR


def test_a_boolean_value_never_satisfies_the_integer_type():
    """bool is a subclass of int in Python -- the grammar must not let a
    boolean silently pass as a declared integer."""
    broken = json_source(
        "urn:ocor:resource:broken",
        "1",
        {
            "id": "urn:ocor:resource:broken",
            "fields": {"count": True},
            "field_types": {"count": "integer"},
        },
    )
    with pytest.raises(C1Error) as excinfo:
        FrontendCanonicalIrBuilder().build(request((broken,)))
    assert excinfo.value.diagnostics[0].code is DiagnosticCode.TYPE_ERROR


def test_multiple_distinct_execution_owners_is_rejected_as_ambiguous():
    broken = json_source(
        "urn:ocor:resource:broken",
        "1",
        {
            "id": "urn:ocor:resource:broken",
            "fields": {"name": "Alpha"},
            "field_types": {"name": "string"},
            "execution_owner": ["urn:ocor:owner:a", "urn:ocor:owner:b"],
        },
    )
    with pytest.raises(C1Error) as excinfo:
        FrontendCanonicalIrBuilder().build(request((broken,)))
    assert excinfo.value.diagnostics[0].code is DiagnosticCode.MULTIPLE_EXECUTION_OWNERS


def test_a_single_execution_owner_repeated_is_not_ambiguous():
    ok = json_source(
        "urn:ocor:resource:ok",
        "1",
        {
            "id": "urn:ocor:resource:ok",
            "fields": {"name": "Alpha"},
            "field_types": {"name": "string"},
            "execution_owner": ["urn:ocor:owner:a", "urn:ocor:owner:a"],
        },
    )
    release = FrontendCanonicalIrBuilder().build(request((ok,)))
    assert release.core["resources"]["urn:ocor:resource:ok"]["execution_owner"] == ("urn:ocor:owner:a", "urn:ocor:owner:a")


def test_an_unresolved_semantic_reference_is_rejected():
    lonely = valid_resource("urn:ocor:resource:lonely", references=["urn:ocor:resource:missing"])
    with pytest.raises(C1Error) as excinfo:
        FrontendCanonicalIrBuilder().build(request((lonely,)))
    assert excinfo.value.diagnostics[0].code is DiagnosticCode.UNRESOLVED_REFERENCE


def test_a_direct_two_resource_reference_cycle_is_rejected():
    a = valid_resource("urn:ocor:resource:a", references=["urn:ocor:resource:b"])
    b = valid_resource("urn:ocor:resource:b", references=["urn:ocor:resource:a"])
    with pytest.raises(C1Error) as excinfo:
        FrontendCanonicalIrBuilder().build(request((a, b)))
    assert excinfo.value.diagnostics[0].code is DiagnosticCode.CONSTRAINT_ERROR
    assert "cyclic reference" in excinfo.value.diagnostics[0].message


def test_a_longer_three_resource_reference_cycle_is_rejected():
    a = valid_resource("urn:ocor:resource:a", references=["urn:ocor:resource:b"])
    b = valid_resource("urn:ocor:resource:b", references=["urn:ocor:resource:c"])
    c = valid_resource("urn:ocor:resource:c", references=["urn:ocor:resource:a"])
    with pytest.raises(C1Error) as excinfo:
        FrontendCanonicalIrBuilder().build(request((a, b, c)))
    assert excinfo.value.diagnostics[0].code is DiagnosticCode.CONSTRAINT_ERROR


def test_a_non_cyclic_diamond_reference_graph_compiles_successfully():
    root = valid_resource("urn:ocor:resource:root")
    left = valid_resource("urn:ocor:resource:left", references=["urn:ocor:resource:root"])
    right = valid_resource("urn:ocor:resource:right", references=["urn:ocor:resource:root"])
    top = valid_resource(
        "urn:ocor:resource:top", references=["urn:ocor:resource:left", "urn:ocor:resource:right"]
    )
    release = FrontendCanonicalIrBuilder().build(request((root, left, right, top)))
    assert set(release.core["resources"]) == {
        "urn:ocor:resource:root",
        "urn:ocor:resource:left",
        "urn:ocor:resource:right",
        "urn:ocor:resource:top",
    }


def test_malformed_yaml_syntax_is_rejected_with_source_invalid():
    broken = yaml_source("urn:ocor:resource:broken", "1", "id: [unterminated\n  - broken")
    with pytest.raises(C1Error) as excinfo:
        FrontendCanonicalIrBuilder().build(request((broken,)))
    assert excinfo.value.diagnostics[0].code is DiagnosticCode.SOURCE_INVALID


def test_declared_id_mismatch_is_rejected_with_constraint_error():
    mismatched = yaml_source(
        "urn:ocor:resource:expected",
        "1",
        "id: urn:ocor:resource:different\nfields:\n  name: X\nfield_types:\n  name: string\n",
    )
    with pytest.raises(C1Error) as excinfo:
        FrontendCanonicalIrBuilder().build(request((mismatched,)))
    assert excinfo.value.diagnostics[0].code is DiagnosticCode.CONSTRAINT_ERROR


def test_no_rejection_path_ever_returns_a_partial_release():
    a = valid_resource("urn:ocor:resource:a", references=["urn:ocor:resource:b"])
    b = valid_resource("urn:ocor:resource:b", references=["urn:ocor:resource:a"])
    builder = FrontendCanonicalIrBuilder()
    result = None
    try:
        result = builder.build(request((a, b)))
    except C1Error:
        pass
    assert result is None
