from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOL_PATH = ROOT / "tools/generate_contracts.py"
SPEC = importlib.util.spec_from_file_location("generate_contracts", TOOL_PATH)
assert SPEC is not None and SPEC.loader is not None
generate_contracts = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = generate_contracts
SPEC.loader.exec_module(generate_contracts)

ContractGenerationError = generate_contracts.ContractGenerationError
PINNED_GENERATED_HASHES = generate_contracts.PINNED_GENERATED_HASHES
PINNED_SOURCE_HASHES = generate_contracts.PINNED_SOURCE_HASHES
check_generated = generate_contracts.check_generated
generate = generate_contracts.generate
validate_contracts = generate_contracts.validate_contracts


@pytest.fixture
def contracts() -> Path:
    return ROOT / "docs/governance_dossier/contracts"


def copy_contracts(source: Path, destination: Path) -> Path:
    copied = destination / "contracts"
    shutil.copytree(source, copied)
    return copied


def test_pinned_sources_cover_every_approved_contract(contracts: Path):
    assert set(PINNED_SOURCE_HASHES) == {path.name for path in contracts.iterdir() if path.is_file()}
    assert all(len(value) == 64 for value in PINNED_SOURCE_HASHES.values())


def test_real_openapi_proto_and_json_schema_generate_reproducibly(
    contracts: Path, tmp_path: Path
):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_manifest = generate(contracts, first)
    second_manifest = generate(contracts, second)
    assert first_manifest == second_manifest
    assert first_manifest["generator_version"] == "1.0.0"
    assert first_manifest["source_sha256"] == PINNED_SOURCE_HASHES
    assert first_manifest["artifact_sha256"] == PINNED_GENERATED_HASHES
    assert first_manifest["validation"] == {
        "json_schema": "PASS",
        "openapi_3_1": "PASS",
        "proto3": "PASS",
        "closed_public_records": "PASS",
        "backend_neutrality": "PASS",
    }
    for name, digest in PINNED_GENERATED_HASHES.items():
        assert (first / name).read_bytes() == (second / name).read_bytes()
        assert len(digest) == 64


def test_generated_python_and_typescript_expose_same_model_inventory(
    contracts: Path, tmp_path: Path
):
    output = tmp_path / "generated"
    manifest = generate(contracts, output)
    descriptor = json.loads((output / "contract-descriptor.json").read_text())
    python_text = (output / "ocor_contracts.py").read_text()
    typescript_text = (output / "ocor_contracts.ts").read_text()
    assert manifest["model_count"] == len(descriptor["models"])
    for model in descriptor["models"]:
        assert f"class {model['name']}(TypedDict" in python_text
        assert f"export interface {model['name']}" in typescript_text


def test_check_generated_detects_drift(contracts: Path, tmp_path: Path):
    output = tmp_path / "generated"
    generate(contracts, output)
    target = output / "ocor_contracts.py"
    target.write_text(target.read_text() + "# drift\n")
    with pytest.raises(ContractGenerationError, match="generated drift"):
        check_generated(contracts, output)


def test_source_drift_fails_before_generation(contracts: Path, tmp_path: Path):
    source = copy_contracts(contracts, tmp_path)
    target = source / "governed-context.schema.json"
    target.write_text(target.read_text().replace("GovernedContext v1.2", "drift"))
    with pytest.raises(ContractGenerationError, match="source digest mismatch"):
        generate(source, tmp_path / "output")


def test_open_public_request_record_is_rejected(contracts: Path, tmp_path: Path):
    source = copy_contracts(contracts, tmp_path)
    target = source / "ocor-named-query-gateway.openapi.yaml"
    target.write_text(target.read_text().replace("      additionalProperties: false\n", "", 1))
    with pytest.raises(ContractGenerationError, match="open public record"):
        validate_contracts(source, enforce_pins=False)


@pytest.mark.parametrize(
    "forbidden",
    ["TypeDB", "TerminusDB", "SPARQL", "TypeQL", "WOQL", "backend_table_id"],
)
def test_backend_identifiers_are_rejected(
    contracts: Path, tmp_path: Path, forbidden: str
):
    source = copy_contracts(contracts, tmp_path)
    target = source / "governed-context.schema.json"
    document = json.loads(target.read_text())
    document["description"] = f"leaks {forbidden}"
    target.write_text(json.dumps(document))
    with pytest.raises(ContractGenerationError, match="backend identifier"):
        validate_contracts(source, enforce_pins=False)


def test_unknown_openapi_reference_is_rejected(contracts: Path, tmp_path: Path):
    source = copy_contracts(contracts, tmp_path)
    target = source / "ocor-governed-memory.openapi.yaml"
    target.write_text(
        target.read_text().replace(
            "./governed-context.schema.json", "./missing-context.schema.json", 1
        )
    )
    with pytest.raises(ContractGenerationError, match="OpenAPI"):
        validate_contracts(source, enforce_pins=False)


def test_invalid_proto_is_rejected(contracts: Path, tmp_path: Path):
    source = copy_contracts(contracts, tmp_path)
    target = source / "ocor_registry.proto"
    target.write_text(target.read_text().replace('syntax = "proto3";', 'syntax = "bad";'))
    with pytest.raises(ContractGenerationError, match="Proto"):
        validate_contracts(source, enforce_pins=False)


def test_cli_check_succeeds_only_for_exact_generated_tree(contracts: Path, tmp_path: Path):
    output = tmp_path / "generated"
    generated = subprocess.run(
        [sys.executable, str(TOOL_PATH), "generate", "--source", str(contracts), "--output", str(output)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert generated.returncode == 0, generated.stderr
    checked = subprocess.run(
        [sys.executable, str(TOOL_PATH), "check", "--source", str(contracts), "--output", str(output)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert checked.returncode == 0, checked.stderr
    assert "PASS" in checked.stdout
