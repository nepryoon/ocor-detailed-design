from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from ocor_runtime.c1.ports import (
    ArtifactGenerator,
    ArtifactManifestEntry,
    C1Diagnostic,
    C1Error,
    CanonicalIrBuilder,
    CanonicalIrRelease,
    CompilerRequest,
    DependencyLockEntry,
    DiagnosticCode,
    OacParser,
    SemanticValidator,
    SourceSyntax,
    SourceUnit,
    require_resolved_references,
    verify_deterministic_build,
)
from ocor_runtime.kernel.canonical import canonical_digest

DIGEST_A = "urn:sha256:" + "a" * 64
DIGEST_B = "urn:sha256:" + "b" * 64


def source_unit(content: bytes = b"package_id: urn:ocor:package:synthetic\n") -> SourceUnit:
    return SourceUnit.create(
        resource_id="urn:ocor:module:synthetic",
        version="1.0.0",
        syntax=SourceSyntax.YAML,
        content=content,
        source_path="modules/synthetic.yaml",
        imports=("urn:ocor:module:base",),
    )


def lock_entry() -> DependencyLockEntry:
    return DependencyLockEntry(
        resource_id="urn:ocor:module:base",
        version="1.0.0",
        digest=DIGEST_A,
    )


def compiler_request() -> CompilerRequest:
    return CompilerRequest(
        package_id="urn:ocor:package:synthetic",
        semantic_version="1.0.0",
        source_commit="0123456789abcdef0123456789abcdef01234567",
        compiler_version="ocor-c1/1.0.0",
        mapping_version="1.0.0",
        release_profile="POC",
        sources=(source_unit(),),
        dependency_lock=(lock_entry(),),
    )


def release(core: dict[str, object] | None = None) -> CanonicalIrRelease:
    return CanonicalIrRelease.create(
        core=core
        or {
            "format": "ocor.cir/1.0",
            "release": {"package_id": "urn:ocor:package:synthetic", "semantic_version": "1.0.0"},
            "modules": [{"module_id": "urn:ocor:module:synthetic", "version": "1.0.0"}],
        },
        artifacts=(
            ArtifactManifestEntry(
                artifact_id="urn:ocor:artifact:json-schema",
                media_type="application/schema+json",
                digest=DIGEST_B,
            ),
        ),
        signature_envelope_ref="urn:ocor:signature-envelope:synthetic",
    )


def test_source_unit_is_typed_content_addressed_and_immutable():
    unit = source_unit()
    assert unit.syntax is SourceSyntax.YAML
    assert unit.content_digest == canonical_digest({"bytes_hex": unit.content.hex()})
    with pytest.raises(FrozenInstanceError):
        unit.version = "2.0.0"  # type: ignore[misc]


def test_source_digest_changes_with_source_bytes():
    assert source_unit().content_digest != source_unit(b"package_id: changed\n").content_digest


@pytest.mark.parametrize("syntax", ["TURTLE", "SQL", "WOQL"])
def test_unknown_source_syntax_is_rejected_with_stable_code(syntax: str):
    with pytest.raises(C1Error) as exc_info:
        SourceUnit.create(
            resource_id="urn:ocor:module:synthetic",
            version="1.0.0",
            syntax=syntax,
            content=b"opaque",
            source_path="module.unknown",
        )
    assert exc_info.value.diagnostics[0].code is DiagnosticCode.UNKNOWN_SYNTAX


def test_empty_source_is_rejected():
    with pytest.raises(C1Error) as exc_info:
        source_unit(b"")
    assert exc_info.value.diagnostics[0].code is DiagnosticCode.SOURCE_INVALID


def test_compiler_request_is_exact_and_immutable():
    request = compiler_request()
    assert request.sources == (source_unit(),)
    assert request.dependency_lock == (lock_entry(),)
    with pytest.raises(FrozenInstanceError):
        request.package_id = "changed"  # type: ignore[misc]


def test_duplicate_source_identity_is_rejected():
    with pytest.raises(C1Error) as exc_info:
        CompilerRequest(
            package_id="urn:ocor:package:synthetic",
            semantic_version="1.0.0",
            source_commit="0123456789abcdef0123456789abcdef01234567",
            compiler_version="ocor-c1/1.0.0",
            mapping_version="1.0.0",
            release_profile="POC",
            sources=(source_unit(), source_unit()),
            dependency_lock=(lock_entry(),),
        )
    assert exc_info.value.diagnostics[0].code is DiagnosticCode.DUPLICATE_RESOURCE


def test_unlocked_import_is_rejected_before_parse():
    with pytest.raises(C1Error) as exc_info:
        CompilerRequest(
            package_id="urn:ocor:package:synthetic",
            semantic_version="1.0.0",
            source_commit="0123456789abcdef0123456789abcdef01234567",
            compiler_version="ocor-c1/1.0.0",
            mapping_version="1.0.0",
            release_profile="POC",
            sources=(source_unit(),),
            dependency_lock=(),
        )
    assert exc_info.value.diagnostics[0].code is DiagnosticCode.UNRESOLVED_REFERENCE


def test_invalid_lock_digest_is_rejected():
    with pytest.raises(C1Error) as exc_info:
        DependencyLockEntry("urn:ocor:module:base", "1.0.0", "sha256:bad")
    assert exc_info.value.diagnostics[0].code is DiagnosticCode.LOCK_INVALID


def test_reference_resolution_reports_sorted_unresolved_ids():
    with pytest.raises(C1Error) as exc_info:
        require_resolved_references(
            defined=("urn:ocor:type:a",),
            referenced=("urn:ocor:type:z", "urn:ocor:type:b"),
        )
    assert [item.path for item in exc_info.value.diagnostics] == [
        "urn:ocor:type:b",
        "urn:ocor:type:z",
    ]
    assert all(item.code is DiagnosticCode.UNRESOLVED_REFERENCE for item in exc_info.value.diagnostics)


def test_canonical_release_bytes_and_digest_are_stable_under_mapping_order():
    left = release({"format": "ocor.cir/1.0", "release": {"b": 2, "a": 1}})
    right = release({"release": {"a": 1, "b": 2}, "format": "ocor.cir/1.0"})
    assert left.canonical_bytes == right.canonical_bytes
    assert left.ir_digest == right.ir_digest


def test_release_core_and_artifact_manifest_are_deeply_immutable():
    item = release()
    with pytest.raises(TypeError):
        item.core["format"] = "changed"  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        item.artifacts[0].digest = DIGEST_A  # type: ignore[misc]


def test_release_rejects_duplicate_artifact_ids():
    artifact = ArtifactManifestEntry("urn:ocor:artifact:a", "application/json", DIGEST_A)
    with pytest.raises(C1Error) as exc_info:
        CanonicalIrRelease.create(
            core={"format": "ocor.cir/1.0"},
            artifacts=(artifact, artifact),
            signature_envelope_ref="urn:ocor:signature-envelope:synthetic",
        )
    assert exc_info.value.diagnostics[0].code is DiagnosticCode.DUPLICATE_RESOURCE


class StableBuilder:
    def build(self, request: CompilerRequest) -> CanonicalIrRelease:
        return release({"format": "ocor.cir/1.0", "package_id": request.package_id})


class AlternatingBuilder:
    def __init__(self) -> None:
        self.counter = 0

    def build(self, request: CompilerRequest) -> CanonicalIrRelease:
        self.counter += 1
        return release(
            {"format": "ocor.cir/1.0", "package_id": request.package_id, "run": self.counter}
        )


def test_determinism_guard_accepts_identical_builds():
    assert verify_deterministic_build(StableBuilder(), compiler_request()).ir_digest == StableBuilder().build(
        compiler_request()
    ).ir_digest


def test_determinism_guard_rejects_different_generation():
    with pytest.raises(C1Error) as exc_info:
        verify_deterministic_build(AlternatingBuilder(), compiler_request())
    assert exc_info.value.diagnostics[0].code is DiagnosticCode.NON_DETERMINISTIC_OUTPUT


def test_diagnostics_have_deterministic_order_and_safe_shape():
    error = C1Error(
        (
            C1Diagnostic(DiagnosticCode.UNRESOLVED_REFERENCE, "z", "unresolved"),
            C1Diagnostic(DiagnosticCode.UNKNOWN_SYNTAX, "a", "unknown"),
        )
    )
    assert [item.path for item in error.diagnostics] == ["a", "z"]
    assert error.to_result() == {
        "status": "RELEASE_REJECTED",
        "diagnostics": [
            {"code": "UNKNOWN_SYNTAX", "path": "a", "message": "unknown"},
            {"code": "UNRESOLVED_REFERENCE", "path": "z", "message": "unresolved"},
        ],
    }


def test_named_ports_are_runtime_checkable_protocols():
    assert isinstance(StableBuilder(), CanonicalIrBuilder)
    assert not isinstance(object(), OacParser)
    assert not isinstance(object(), SemanticValidator)
    assert not isinstance(object(), ArtifactGenerator)
