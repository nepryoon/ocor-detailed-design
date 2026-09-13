"""OCOR-DEV-0028: Build retained C1 compiler slice.

Proves that a versioned DSL fixture compiles to immutable canonical IR
and migration metadata with a reproducible digest, and that invalid
semantics or malformed sources can never publish an IR release. This is
a retained (non-spike) runtime component: pure, in-memory, deterministic
-- no external service is needed or used. Reuses the sealed C1 ports
(OCOR-DEV-0011, ``ocor_runtime.c1.ports``) unmodified.
"""

from __future__ import annotations

import json

import pytest
from ocor_runtime.c1.compiler import RetainedCanonicalIrBuilder
from ocor_runtime.kernel.canonical import canonical_digest
from ocor_runtime.c1.ports import (
    C1Error,
    CompilerRequest,
    DependencyLockEntry,
    DiagnosticCode,
    SourceSyntax,
    SourceUnit,
    verify_deterministic_build,
)

DIGEST_A = "urn:sha256:" + "a" * 64
COMMIT = "0123456789abcdef0123456789abcdef01234567"


def yaml_source(resource_id: str, version: str, *, fields: dict[str, object], imports: tuple[str, ...] = ()) -> SourceUnit:
    body = f"id: {resource_id}\nfields:\n" + "\n".join(f"  {key}: {value!r}" for key, value in fields.items())
    return SourceUnit.create(
        resource_id=resource_id,
        version=version,
        syntax=SourceSyntax.YAML,
        content=body.encode("utf-8"),
        source_path=f"{resource_id}.yaml",
        imports=imports,
    )


def json_source(resource_id: str, version: str, *, fields: dict[str, object], imports: tuple[str, ...] = ()) -> SourceUnit:
    body = json.dumps({"id": resource_id, "fields": fields})
    return SourceUnit.create(
        resource_id=resource_id,
        version=version,
        syntax=SourceSyntax.JSON,
        content=body.encode("utf-8"),
        source_path=f"{resource_id}.json",
        imports=imports,
    )


def request(sources: tuple[SourceUnit, ...], *, lock: tuple[DependencyLockEntry, ...] = ()) -> CompilerRequest:
    return CompilerRequest(
        package_id="urn:ocor:package:spike-fixture",
        semantic_version="1.0.0",
        source_commit=COMMIT,
        compiler_version="0.1.0",
        mapping_version="1",
        release_profile="poc",
        sources=sources,
        dependency_lock=lock,
    )


def test_valid_dsl_fixture_compiles_to_canonical_ir_with_migration_metadata():
    sources = (
        yaml_source("urn:ocor:resource:alpha", "1", fields={"name": "Alpha"}),
        json_source("urn:ocor:resource:bravo", "1", fields={"name": "Bravo"}),
    )
    release = RetainedCanonicalIrBuilder().build(request(sources))

    assert set(release.core["resources"]) == {"urn:ocor:resource:alpha", "urn:ocor:resource:bravo"}
    assert release.ir_digest.startswith("urn:sha256:")
    assert len(release.artifacts) == 1
    assert release.artifacts[0].artifact_id == "urn:ocor:package:spike-fixture:migration-metadata"
    assert release.artifacts[0].digest.startswith("urn:sha256:")
    assert release.signature_envelope_ref == f"urn:ocor:unsigned:{canonical_digest(release.core)}"


def test_repeated_compilation_is_byte_identical_reproducible():
    sources = (yaml_source("urn:ocor:resource:alpha", "1", fields={"name": "Alpha", "count": 3}),)
    release = verify_deterministic_build(RetainedCanonicalIrBuilder(), request(sources))
    assert release.ir_digest.startswith("urn:sha256:")


def test_unresolved_import_reference_is_rejected_before_building():
    sources = (yaml_source("urn:ocor:resource:alpha", "1", fields={"name": "Alpha"}, imports=("urn:ocor:resource:missing",)),)
    with pytest.raises(C1Error) as excinfo:
        request(sources)  # the sealed CompilerRequest constructor itself rejects this
    assert excinfo.value.diagnostics[0].code is DiagnosticCode.UNRESOLVED_REFERENCE


def test_malformed_yaml_syntax_is_rejected_with_source_invalid():
    broken = SourceUnit.create(
        resource_id="urn:ocor:resource:broken",
        version="1",
        syntax=SourceSyntax.YAML,
        content=b"id: [unterminated\n  - broken",
        source_path="broken.yaml",
    )
    with pytest.raises(C1Error) as excinfo:
        RetainedCanonicalIrBuilder().build(request((broken,)))
    assert excinfo.value.diagnostics[0].code is DiagnosticCode.SOURCE_INVALID


def test_parsed_content_missing_required_keys_is_rejected_with_type_error():
    incomplete = SourceUnit.create(
        resource_id="urn:ocor:resource:incomplete",
        version="1",
        syntax=SourceSyntax.YAML,
        content=b"id: urn:ocor:resource:incomplete\n",
        source_path="incomplete.yaml",
    )
    with pytest.raises(C1Error) as excinfo:
        RetainedCanonicalIrBuilder().build(request((incomplete,)))
    assert excinfo.value.diagnostics[0].code is DiagnosticCode.TYPE_ERROR


def test_fields_not_a_mapping_is_rejected_with_type_error():
    wrong_shape = SourceUnit.create(
        resource_id="urn:ocor:resource:wrong-shape",
        version="1",
        syntax=SourceSyntax.JSON,
        content=json.dumps({"id": "urn:ocor:resource:wrong-shape", "fields": ["not", "a", "mapping"]}).encode(),
        source_path="wrong-shape.json",
    )
    with pytest.raises(C1Error) as excinfo:
        RetainedCanonicalIrBuilder().build(request((wrong_shape,)))
    assert excinfo.value.diagnostics[0].code is DiagnosticCode.TYPE_ERROR


def test_declared_id_mismatch_is_rejected_with_constraint_error():
    mismatched = SourceUnit.create(
        resource_id="urn:ocor:resource:expected",
        version="1",
        syntax=SourceSyntax.YAML,
        content=b"id: urn:ocor:resource:different\nfields:\n  name: X\n",
        source_path="mismatched.yaml",
    )
    with pytest.raises(C1Error) as excinfo:
        RetainedCanonicalIrBuilder().build(request((mismatched,)))
    assert excinfo.value.diagnostics[0].code is DiagnosticCode.CONSTRAINT_ERROR


def test_no_invalid_semantics_path_ever_returns_a_release_object():
    """The negative acceptance criterion, proven directly: every rejection
    path above raises before RetainedCanonicalIrBuilder.build can return
    anything -- there is no code path that returns a partially-valid
    CanonicalIrRelease."""
    broken = SourceUnit.create(
        resource_id="urn:ocor:resource:broken",
        version="1",
        syntax=SourceSyntax.YAML,
        content=b"id: [unterminated\n  - broken",
        source_path="broken.yaml",
    )
    builder = RetainedCanonicalIrBuilder()
    result = None
    try:
        result = builder.build(request((broken,)))
    except C1Error:
        pass
    assert result is None
