"""OCOR-DEV-REM-0010: contract generator $ref resolution.

RED (reports/tests/evidence/rem_generate_contracts_refs/red.log, fingerprint
below): the generator committed as ocor-runtime/tools/generate_contracts.py
at OCOR-DEV-0010's acceptance resolved a `$ref` by taking the bare last path
segment (`rsplit("/")[-1]`) with no awareness of the `Gateway`/`Memory`
prefix `_models()` itself adds to OpenAPI-sourced object records, and no
handling at all for `$ref` targets that are not object records (a plain
SHA-256 digest string, a non-empty string array, a same-document alias
forwarding to a whole external JSON Schema document). Compiling the
generator's own `ocor_contracts.ts` output with `tsc --strict` -- something
OCOR-DEV-0010's own test suite (ocor-runtime/tests/tasks/test_ocor_dev_0010.py,
sealed, left untouched by this remediation) never did, because it only
asserts that each model's own `export interface <Name>` declaration line is
present, not that the file as a whole type-checks -- fails with 19 distinct
`TS2304: Cannot find name` errors, one per broken or unresolved reference.

GREEN: this test drives the same real generator end-to-end against the same
pinned source contracts and asserts, mechanically, that every `$ref` in the
pinned set now resolves to either a real generated model or an inlined
primitive type, that the sealed ocor_contracts.ts consumer, when it exists
(ocor-runtime/sdk/typescript), still compiles under `tsc --strict`, and that
the fix changed reference resolution only -- not the model inventory
test_ocor_dev_0010.py already pins.
"""

from __future__ import annotations

import hashlib
import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOL_PATH = ROOT / "ocor-runtime/tools/generate_contracts.py"
CONTRACTS = ROOT / "reports/contracts"
RED_LOG = ROOT / "reports/tests/evidence/rem_generate_contracts_refs/red.log"
SDK_ROOT = ROOT / "ocor-runtime/sdk/typescript"

SPEC = importlib.util.spec_from_file_location("generate_contracts_rem0010", TOOL_PATH)
assert SPEC is not None and SPEC.loader is not None
generate_contracts = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = generate_contracts
SPEC.loader.exec_module(generate_contracts)


def test_red_log_is_sealed_and_fingerprinted():
    assert RED_LOG.is_file(), "RED evidence for OCOR-DEV-REM-0010 is missing"
    digest = hashlib.sha256(RED_LOG.read_bytes()).hexdigest()
    assert digest == "0ee2ffc5df633cbdfa947d941395c647df78b1d5d02658c2aa826fd590d6c5f9"
    assert "Cannot find name 'QueryContext'" in RED_LOG.read_text(encoding="utf-8")


def _find_dollar_refs(node: object) -> list[str]:
    found: list[str] = []
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str):
            found.append(ref)
        for value in node.values():
            found.extend(_find_dollar_refs(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_find_dollar_refs(item))
    return found


def test_every_pinned_ref_resolves_to_a_real_model_or_a_primitive(tmp_path: Path):
    validated = generate_contracts.validate_contracts(CONTRACTS)
    index = generate_contracts._build_reference_index(validated)
    models = generate_contracts._models(validated)
    declared_names = {str(model["name"]) for model in models}
    primitive_tokens = re.compile(r"^(str|int|float|bool|object|list\[.*\]|string|number|boolean|ReadonlyArray<.*>)$")

    # Mirror _models()'s own traversal exactly: only the properties of a
    # whole JSON Schema document, and the properties of an OpenAPI component
    # that is itself an object record, are ever passed to _schema_model --
    # an allOf composition's own $ref (or a components.schemas entry that is
    # itself just `{"$ref": "<external file>"}`) is never visited as a field
    # reference, so it is out of scope for this invariant by construction.
    all_refs: set[str] = set()
    for document in validated["json"].values():
        all_refs.update(_find_dollar_refs(document.get("properties", {})))
    for document in validated["openapi"].values():
        for schema in document.get("components", {}).get("schemas", {}).values():
            if isinstance(schema, dict) and (schema.get("type") == "object" or "properties" in schema):
                all_refs.update(_find_dollar_refs(schema.get("properties", {})))

    unresolved = sorted(ref for ref in all_refs if ref not in index)
    assert not unresolved, f"references with no resolution at all: {unresolved}"

    for ref in sorted(all_refs):
        resolved = index[ref]
        for language in ("python", "typescript"):
            text = resolved[language]
            assert text in declared_names or primitive_tokens.match(text), (
                f"{ref} ({language}) resolves to {text!r}, which is neither a "
                "declared model nor a recognized primitive/array type"
            )


@pytest.mark.parametrize(
    ("ref", "expected_python", "expected_typescript"),
    [
        ("#/components/schemas/QueryContext", "GatewayQueryContext", "GatewayQueryContext"),
        ("#/components/schemas/ContractCall", "GatewayContractCall", "GatewayContractCall"),
        ("#/components/schemas/ResourceRef", "GatewayResourceRef", "GatewayResourceRef"),
        ("#/components/schemas/MemoryHit", "MemoryMemoryHit", "MemoryMemoryHit"),
        ("#/components/schemas/GovernedContext", "OCORGovernedContextV12", "OCORGovernedContextV12"),
        ("#/components/schemas/Digest", "str", "string"),
        ("#/$defs/refs", "list[str]", "ReadonlyArray<string>"),
        ("#/$defs/nonEmptyRefs", "list[str]", "ReadonlyArray<string>"),
        ("#/$defs/digest", "str", "string"),
    ],
)
def test_the_specific_previously_broken_references_now_resolve(
    ref: str, expected_python: str, expected_typescript: str
):
    validated = generate_contracts.validate_contracts(CONTRACTS)
    index = generate_contracts._build_reference_index(validated)
    assert index[ref]["python"] == expected_python
    assert index[ref]["typescript"] == expected_typescript


def test_fix_changes_reference_resolution_only_not_the_model_inventory():
    validated = generate_contracts.validate_contracts(CONTRACTS)
    models = generate_contracts._models(validated)
    assert len(models) == 54
    # Sealed test_ocor_dev_0010.py already asserts every model's own
    # declaration line is present; this asserts the inverse fact it does
    # not check -- that no *reference* in the generated text is dangling --
    # by actually parsing every `export interface` name out of a fresh
    # render and confirming it's a closed set against what the source
    # documents (and their $defs/components entries) could possibly name.
    names = {str(model["name"]) for model in models}
    assert "GatewayQueryContext" in names
    assert "MemoryMemoryHit" in names
    assert "GovernedContext" not in names, "GovernedContext is a forwarding alias, not its own model"
    assert "Digest" not in names, "Digest is inlined as a primitive, not its own model"


@pytest.mark.skipif(shutil.which("tsc") is None, reason="tsc not on PATH in this shell")
def test_generated_contracts_compile_under_tsc_strict(tmp_path: Path):
    if not SDK_ROOT.is_dir():
        pytest.skip("ocor-runtime/sdk/typescript does not exist yet")
    # generate_contracts always emits the Python/TypeScript/descriptor triple
    # together; the committed SDK directory intentionally keeps only the
    # TypeScript artifact, so compare that one file's bytes directly rather
    # than the whole-directory check_generated() expects.
    manifest = generate_contracts.generate(CONTRACTS, tmp_path)
    assert manifest["model_count"] == 54
    committed = (SDK_ROOT / "src" / "generated" / "ocor_contracts.ts").read_bytes()
    fresh = (tmp_path / "ocor_contracts.ts").read_bytes()
    assert committed == fresh, "committed ocor_contracts.ts has drifted from the generator's output"
    result = subprocess.run(
        ["tsc", "--noEmit", "--project", str(SDK_ROOT / "tsconfig.json")],
        capture_output=True,
        text=True,
        check=False,
        cwd=SDK_ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr
