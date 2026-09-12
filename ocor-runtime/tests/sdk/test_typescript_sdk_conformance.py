"""NFR-022: cross-SDK conformance between the Python and TypeScript SDKs.

DEC-212 Phase 2.3 requires demonstrating, on shared fixtures, identity of
canonical bytes, digests, error model, and idempotency semantics between the
Python SDK (ocor_runtime.canonical, the runtime's own reference
implementation, doubling as the Python SDK profile per DEC-075/FR-047) and
the generated TypeScript SDK (ocor-runtime/sdk/typescript). The MCP tool
descriptor's own idempotency semantics are that a client's idempotency-key
binding IS the canonical digest of the request payload -- so digest identity
across languages is not a separate concern from idempotency identity here,
it is the operative proof of it, and is asserted as such below rather than
as a fourth, redundant fixture set.

This suite drives the real compiled TypeScript implementation as a
subprocess (ocor-runtime/sdk/typescript/dist/cli/canonicalize.js), the same
pattern DEC-166/REM-0007 already established for using Node.js as the
cross-language oracle for the Python kernel's own RFC 8785 boundary values.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from ocor_runtime.canonical import CanonicalizationError, canonicalize_json, canonical_sha256

ROOT = Path(__file__).resolve().parents[3]
SDK_ROOT = ROOT / "ocor-runtime" / "sdk" / "typescript"
CLI_PATH = SDK_ROOT / "dist" / "cli" / "canonicalize.js"

NODE_AVAILABLE = shutil.which("node") is not None

# Fixtures chosen to exercise every boundary the Python port hand-derives
# and the TypeScript port gets for free from the ECMAScript engine: key
# ordering by UTF-16 code unit, control-character/unicode string escaping,
# the MAX_SAFE_INTEGER boundary, and the +-21/-7 scientific-notation
# exponent thresholds RFC 8785 mandates.
VALID_FIXTURES: list[Any] = [
    None,
    True,
    False,
    0,
    -0.0,
    1,
    -1,
    9_007_199_254_740_991,
    -9_007_199_254_740_991,
    3.14159,
    1e21,
    1e-7,
    1.5e-7,
    123.456e10,
    "",
    "plain",
    "line\nbreak\ttab\"quote\\backslash",
    "control",
    "unicode éèà 中文",
    [],
    {},
    {"b": 2, "a": 1, "z": 26, "A": 65},
    {"nested": {"array": [1, 2, {"deep": True}], "unicode_key_é": 1}},
    ["mixed", 1, None, True, {"k": [1, 2, 3]}],
]

INVALID_FIXTURE_CODES = [
    ("\ud800", "CANONICALIZATION_INVALID"),
    ("\udfff", "CANONICALIZATION_INVALID"),
]


def _typescript_available() -> bool:
    return NODE_AVAILABLE and CLI_PATH.is_file()


def _build_sdk_if_needed() -> None:
    if CLI_PATH.is_file():
        return
    if not (SDK_ROOT / "node_modules").is_dir():
        subprocess.run(["npm", "install", "--no-audit", "--no-fund"], cwd=SDK_ROOT, check=True)
    subprocess.run(["npx", "tsc", "--project", "tsconfig.json"], cwd=SDK_ROOT, check=True)


@pytest.fixture(scope="module", autouse=True)
def _ensure_typescript_sdk_built():
    if not NODE_AVAILABLE:
        pytest.skip("node not on PATH in this shell")
    _build_sdk_if_needed()
    if not CLI_PATH.is_file():
        pytest.skip("TypeScript SDK CLI did not build")


def _run_typescript_canonicalize(values: list[Any]) -> list[dict[str, Any]]:
    payload = "\n".join(json.dumps(value) for value in values) + "\n"
    result = subprocess.run(
        ["node", str(CLI_PATH)],
        input=payload,
        capture_output=True,
        text=True,
        check=True,
        cwd=SDK_ROOT,
    )
    lines = [line for line in result.stdout.splitlines() if line]
    assert len(lines) == len(values), f"expected {len(values)} result lines, got {len(lines)}: {result.stdout!r}"
    return [json.loads(line) for line in lines]


def test_canonical_byte_and_digest_identity_across_python_and_typescript():
    results = _run_typescript_canonicalize(VALID_FIXTURES)
    for value, result in zip(VALID_FIXTURES, results, strict=True):
        assert result["error_code"] is None, f"TypeScript rejected a valid fixture {value!r}: {result}"
        python_canonical = canonicalize_json(value)
        python_digest = canonical_sha256(value)
        assert result["canonical"] == python_canonical, (
            f"canonical text diverges for {value!r}: python={python_canonical!r} typescript={result['canonical']!r}"
        )
        assert result["digest"] == python_digest, (
            f"digest diverges for {value!r} despite identical canonical text: "
            f"python={python_digest} typescript={result['digest']}"
        )


def test_error_model_identity_across_python_and_typescript():
    fixtures = [value for value, _ in INVALID_FIXTURE_CODES]
    results = _run_typescript_canonicalize(fixtures)
    for (value, expected_code), result in zip(INVALID_FIXTURE_CODES, results, strict=True):
        assert result["error_code"] == expected_code, f"typescript error code for {value!r}: {result}"
        with pytest.raises(CanonicalizationError) as excinfo:
            canonicalize_json(value)
        assert excinfo.value.code == expected_code, f"python error code for {value!r}: {excinfo.value.code}"


def test_generated_contract_field_parity_between_python_and_typescript(tmp_path: Path):
    """The two SDKs' generated contracts come from the same generator run
    over the same pinned sources; assert they still expose the identical
    model/field inventory (name, optionality) rather than merely trusting
    that fact by construction."""

    import sys

    tools_dir = ROOT / "ocor-runtime" / "tools"
    sys.path.insert(0, str(tools_dir))
    try:
        import generate_contracts
    finally:
        sys.path.remove(str(tools_dir))

    manifest = generate_contracts.generate(ROOT / "reports" / "contracts", tmp_path)
    descriptor = json.loads((tmp_path / "contract-descriptor.json").read_text())
    typescript_text = (SDK_ROOT / "src" / "generated" / "ocor_contracts.ts").read_text()
    assert manifest["model_count"] == len(descriptor["models"])
    for model in descriptor["models"]:
        assert f"export interface {model['name']}" in typescript_text, (
            f"TypeScript SDK is missing or has drifted for model {model['name']}"
        )
        for field in model["fields"]:
            marker = f"{field['name']}{'?' if not field['required'] else ''}: {field['typescript_type']};"
            assert marker in typescript_text, (
                f"TypeScript SDK field mismatch for {model['name']}.{field['name']}: expected {marker!r}"
            )


def test_idempotency_binding_is_the_canonical_digest_in_both_sdks():
    """The MCP tool contract's idempotency semantics bind a request to its
    `idempotency_key` via the canonical digest of the governed request
    payload (kernel/canonical.py's `canonical_digest`, urn:sha256:-prefixed).
    Two structurally-identical requests (same fields, different key
    ordering) must bind to the same digest in both SDKs; two requests that
    differ in exactly one field must not."""

    base = {"aggregate_ref": "urn:ocor:mission-object:1", "expected_revision": 0, "canonical_delta": {"status": "A"}}
    reordered = {"canonical_delta": {"status": "A"}, "expected_revision": 0, "aggregate_ref": "urn:ocor:mission-object:1"}
    changed = {**base, "expected_revision": 1}

    python_base = canonical_sha256(base)
    python_reordered = canonical_sha256(reordered)
    python_changed = canonical_sha256(changed)
    assert python_base == python_reordered
    assert python_base != python_changed

    ts_results = _run_typescript_canonicalize([base, reordered, changed])
    assert ts_results[0]["digest"] == ts_results[1]["digest"] == python_base
    assert ts_results[2]["digest"] == python_changed
    assert ts_results[0]["digest"] != ts_results[2]["digest"]
