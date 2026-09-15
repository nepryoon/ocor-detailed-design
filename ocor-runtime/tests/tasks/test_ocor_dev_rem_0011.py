"""OCOR-DEV-REM-0011 — C1 frontend fail-closed handling of execution_owner.

Review finding RVW-04: ``FrontendTypeAndSemanticValidator`` computed
``{owners} if isinstance(owners, str) else set(owners)``. A malformed
``execution_owner`` (a non-string, non-list value) raised ``TypeError`` and
crashed the compiler instead of producing a deterministic ``C1Error``
diagnostic; a list containing non-string owners, or a mapping, was silently
accepted. The compiler contract is that malformed models never crash and never
reach generation — they must be rejected with a bounded, coded diagnostic.
"""

from __future__ import annotations

import json

import pytest
from ocor_runtime.c1.frontend import FrontendCanonicalIrBuilder
from ocor_runtime.c1.ports import C1Error, CompilerRequest, DiagnosticCode, SourceSyntax, SourceUnit

_COMMIT = "0123456789abcdef0123456789abcdef01234567"


def _source(resource_id: str, body: dict[str, object]) -> SourceUnit:
    return SourceUnit.create(
        resource_id=resource_id,
        version="1",
        syntax=SourceSyntax.JSON,
        content=json.dumps(body).encode("utf-8"),
        source_path=f"{resource_id}.json",
    )


def _request(source: SourceUnit) -> CompilerRequest:
    return CompilerRequest(
        package_id="urn:ocor:package:rem-0011",
        semantic_version="1.0.0",
        source_commit=_COMMIT,
        compiler_version="0.1.0",
        mapping_version="1",
        release_profile="poc",
        sources=(source,),
        dependency_lock=(),
    )


def _body(resource_id: str, owner: object) -> dict[str, object]:
    return {
        "id": resource_id,
        "fields": {"name": "Alpha"},
        "field_types": {"name": "string"},
        "execution_owner": owner,
    }


@pytest.mark.parametrize("owner", [42, 3.14, True, {"urn:ocor:owner:a": 1}, [123], ["urn:ocor:owner:a", 7]])
def test_malformed_execution_owner_is_a_coded_diagnostic_not_a_crash(owner: object) -> None:
    rid = "urn:ocor:resource:rem0011"
    with pytest.raises(C1Error) as excinfo:
        FrontendCanonicalIrBuilder().build(_request(_source(rid, _body(rid, owner))))
    assert excinfo.value.diagnostics[0].code is DiagnosticCode.TYPE_ERROR


def test_valid_string_and_list_owners_still_behave() -> None:
    rid = "urn:ocor:resource:ok"
    release = FrontendCanonicalIrBuilder().build(_request(_source(rid, _body(rid, "urn:ocor:owner:a"))))
    assert release.core["resources"][rid]["execution_owner"] == "urn:ocor:owner:a"

    with pytest.raises(C1Error) as excinfo:
        FrontendCanonicalIrBuilder().build(
            _request(_source(rid, _body(rid, ["urn:ocor:owner:a", "urn:ocor:owner:b"])))
        )
    assert excinfo.value.diagnostics[0].code is DiagnosticCode.MULTIPLE_EXECUTION_OWNERS
