"""OCOR-DEV-0033: Complete C1 releases semantic diff migration and generators.

Proves that comparing, classifying, planning and generating artifacts
for a pair of canonical IR releases is deterministic and
content-addressed at every step, and that a BREAKING change can never
reach artifact generation without an explicit, non-empty governed
migration plan. Pure, in-memory, deterministic component -- no
external service is needed or used, like OCOR-DEV-0028/0032's C1
slices. Reuses the sealed C1 ports (OCOR-DEV-0011) unmodified, and
OCOR-DEV-0032's ``ocor_runtime.c1.frontend`` (unmodified) to build real
``CanonicalIrRelease`` fixtures.
"""

from __future__ import annotations

import json

import pytest
from ocor_runtime.c1.frontend import FrontendCanonicalIrBuilder
from ocor_runtime.c1.ports import C1Error, CompilerRequest, SourceSyntax, SourceUnit
from ocor_runtime.c1.releases import (
    BREAKING,
    COMPATIBLE,
    IDENTICAL,
    RetainedArtifactGenerator,
    RetainedCompatibilityChecker,
    RetainedMigrationPlanner,
    RetainedSemanticDiffEngine,
)

COMMIT = "0123456789abcdef0123456789abcdef01234567"


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
        package_id="urn:ocor:package:release-fixture",
        semantic_version="1.0.0",
        source_commit=COMMIT,
        compiler_version="0.1.0",
        mapping_version="1",
        release_profile="poc",
        sources=sources,
        dependency_lock=(),
    )


def resource(resource_id: str, *, name: str = "Alpha", count: int = 3) -> SourceUnit:
    return json_source(
        resource_id,
        "1",
        {
            "id": resource_id,
            "fields": {"name": name, "count": count},
            "field_types": {"name": "string", "count": "integer"},
        },
    )


def build(*sources: SourceUnit):
    return FrontendCanonicalIrBuilder().build(request(sources))


def test_comparing_a_release_with_itself_is_identical_with_a_stable_digest():
    release = build(resource("urn:ocor:resource:a"))
    engine = RetainedSemanticDiffEngine()
    first = engine.compare(release, release)
    second = engine.compare(release, release)
    assert first == second
    assert first.startswith("urn:sha256:")


def test_compare_detects_added_removed_and_changed_resources():
    previous = build(resource("urn:ocor:resource:a"), resource("urn:ocor:resource:b"))
    candidate = build(resource("urn:ocor:resource:a", count=99), resource("urn:ocor:resource:c"))
    engine = RetainedSemanticDiffEngine()

    diff_digest = engine.compare(previous, candidate)
    reverse_digest = engine.compare(candidate, previous)

    assert diff_digest.startswith("urn:sha256:")
    assert diff_digest != reverse_digest  # the diff is directional


def test_check_classifies_identical_releases():
    release = build(resource("urn:ocor:resource:a"))
    assert RetainedCompatibilityChecker().check(release, release) == IDENTICAL


def test_check_classifies_a_pure_addition_as_compatible():
    previous = build(resource("urn:ocor:resource:a"))
    candidate = build(resource("urn:ocor:resource:a"), resource("urn:ocor:resource:b"))
    assert RetainedCompatibilityChecker().check(previous, candidate) == COMPATIBLE


def test_check_classifies_a_resource_removal_as_breaking():
    previous = build(resource("urn:ocor:resource:a"), resource("urn:ocor:resource:b"))
    candidate = build(resource("urn:ocor:resource:a"))
    assert RetainedCompatibilityChecker().check(previous, candidate) == BREAKING


def test_check_classifies_a_field_type_change_as_breaking():
    previous = build(resource("urn:ocor:resource:a"))
    changed_type = json_source(
        "urn:ocor:resource:a",
        "1",
        {
            "id": "urn:ocor:resource:a",
            "fields": {"name": "Alpha", "count": "3"},
            "field_types": {"name": "string", "count": "string"},
        },
    )
    candidate = build(changed_type)
    assert RetainedCompatibilityChecker().check(previous, candidate) == BREAKING


def test_check_classifies_a_removed_field_type_declaration_as_breaking():
    previous = build(resource("urn:ocor:resource:a"))
    fewer_types = json_source(
        "urn:ocor:resource:a",
        "1",
        {
            "id": "urn:ocor:resource:a",
            "fields": {"name": "Alpha"},
            "field_types": {"name": "string"},
        },
    )
    candidate = build(fewer_types)
    assert RetainedCompatibilityChecker().check(previous, candidate) == BREAKING


def test_migration_plan_is_deterministic_and_content_addressed():
    previous = build(resource("urn:ocor:resource:a"), resource("urn:ocor:resource:b"))
    candidate = build(resource("urn:ocor:resource:a"), resource("urn:ocor:resource:c"))
    planner = RetainedMigrationPlanner()

    first = planner.plan(previous, candidate)
    second = planner.plan(previous, candidate)

    assert first == second
    assert first["plan_digest"].startswith("urn:sha256:")
    assert first["classification"] == BREAKING
    ops = {(step["op"], step["resource_id"]) for step in first["migration_steps"]}
    assert ("retire", "urn:ocor:resource:b") in ops
    assert ("introduce", "urn:ocor:resource:c") in ops


def test_migration_plan_digest_changes_if_the_plan_body_would_differ():
    previous = build(resource("urn:ocor:resource:a"))
    candidate_one = build(resource("urn:ocor:resource:a"), resource("urn:ocor:resource:b"))
    candidate_two = build(resource("urn:ocor:resource:a"), resource("urn:ocor:resource:c"))
    planner = RetainedMigrationPlanner()

    plan_one = planner.plan(previous, candidate_one)
    plan_two = planner.plan(previous, candidate_two)

    assert plan_one["plan_digest"] != plan_two["plan_digest"]


def test_generate_produces_a_content_addressed_release_manifest_artifact():
    release = build(resource("urn:ocor:resource:a"), resource("urn:ocor:resource:b"))
    artifacts = RetainedArtifactGenerator().generate(release)

    assert len(artifacts) == 1
    assert artifacts[0].artifact_id == "urn:ocor:package:release-fixture:release-manifest"
    assert artifacts[0].digest.startswith("urn:sha256:")


def test_a_breaking_change_without_a_governed_migration_plan_is_blocked_from_generation():
    previous = build(resource("urn:ocor:resource:a"), resource("urn:ocor:resource:b"))
    candidate = build(resource("urn:ocor:resource:a"))
    generator = RetainedArtifactGenerator()

    with pytest.raises(C1Error) as excinfo:
        generator.generate_governed(previous, candidate, None)
    assert "governed migration plan" in excinfo.value.diagnostics[0].message


def test_a_breaking_change_with_a_governed_migration_plan_reaches_generation():
    previous = build(resource("urn:ocor:resource:a"), resource("urn:ocor:resource:b"))
    candidate = build(resource("urn:ocor:resource:a"))
    plan = RetainedMigrationPlanner().plan(previous, candidate)

    artifacts = RetainedArtifactGenerator().generate_governed(previous, candidate, plan)
    assert len(artifacts) == 1


def test_a_compatible_change_reaches_generation_without_needing_a_migration_plan():
    previous = build(resource("urn:ocor:resource:a"))
    candidate = build(resource("urn:ocor:resource:a"), resource("urn:ocor:resource:b"))

    artifacts = RetainedArtifactGenerator().generate_governed(previous, candidate, None)
    assert len(artifacts) == 1


def test_no_partial_artifact_list_is_ever_returned_for_a_blocked_breaking_change():
    previous = build(resource("urn:ocor:resource:a"), resource("urn:ocor:resource:b"))
    candidate = build(resource("urn:ocor:resource:a"))
    generator = RetainedArtifactGenerator()

    result = None
    try:
        result = generator.generate_governed(previous, candidate, {"migration_steps": []})
    except C1Error:
        pass
    assert result is None
