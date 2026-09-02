#!/usr/bin/env python3
"""Deterministically validate approved contracts and materialize SDK boundaries."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import grpc_tools
import yaml
from google.protobuf import descriptor_pb2
from jsonschema import Draft202012Validator
from openapi_spec_validator import validate as validate_openapi

GENERATOR_VERSION = "1.0.0"
PINNED_SOURCE_HASHES = {
    "capability-lease.schema.json": "d16951ad374f33138541370d55d0cd474ae0672ae3fa0a134d0a10ae030ddf0e",
    "governed-context.schema.json": "04671e932f7378c34b07fc01881755c7c5af66787ef2f6a3ca2da5bd86c22a88",
    "governed-memory-item.schema.json": "8d0167be6467a8cfb4e41e4c7cc1e8f207b578456238a7da41f7a4da091e47b5",
    "ocor-governed-memory.openapi.yaml": "526caa147715aaffc6d4003889db1111e50d6cd17cd9fc61dbfad28f58343d9b",
    "ocor-named-query-gateway.openapi.yaml": "652403f5aab29312452f9814a0fe87f74b6a142c361de415c4d79b3b8406e03e",
    "ocor_registry.proto": "7de0aa5f592a013f2f067866ce6dbb27c1ecbffefcc14eb3a0e0d959bfc24694",
}
# Filled only with hashes produced from the pinned source set and this generator version.
PINNED_GENERATED_HASHES = {
    "contract-descriptor.json": "611226a9e0427882e57b5d8f89d726563688154a89d1dd3ba691546d1925e413",
    "ocor_contracts.py": "6cf97b6f026d49b36c1114232240be3c6b1c53e728afc37abc3aac239ca9b418",
    "ocor_contracts.ts": "0f8a104d8b8f2bc776abdb905f7f6910acdd50781380bde330a58a9fb2b6b0b0",
}
ARTIFACT_NAMES = ("contract-descriptor.json", "ocor_contracts.py", "ocor_contracts.ts")
FORBIDDEN_BACKEND = re.compile(
    r"(?:TypeDB|TerminusDB|SPARQL|TypeQL|WOQL|backend[_ -]?(?:id|table|column|schema))",
    re.IGNORECASE,
)


class ContractGenerationError(ValueError):
    """A source contract or generated artifact is non-reproducible or unsafe."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _atomic_write(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        handle.write(value)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractGenerationError(f"JSON Schema parse failed for {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractGenerationError(f"JSON Schema root is not an object: {path.name}")
    return value


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ContractGenerationError(f"OpenAPI parse failed for {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractGenerationError(f"OpenAPI root is not an object: {path.name}")
    return value


def _verify_sources(source: Path) -> None:
    actual_names = {path.name for path in source.iterdir() if path.is_file()}
    if actual_names != set(PINNED_SOURCE_HASHES):
        raise ContractGenerationError("source contract inventory differs from the approved pin set")
    for name, expected in PINNED_SOURCE_HASHES.items():
        actual = _sha256(source / name)
        if actual != expected:
            raise ContractGenerationError(
                f"source digest mismatch for {name}: expected {expected}, observed {actual}"
            )


def _scan_backend_neutrality(source: Path) -> None:
    for path in sorted(source.iterdir()):
        if not path.is_file():
            continue
        match = FORBIDDEN_BACKEND.search(path.read_text(encoding="utf-8"))
        if match:
            raise ContractGenerationError(
                f"backend identifier is forbidden in {path.name}: {match.group(0)}"
            )


def _ref_locations(value: object, target: str, path: tuple[object, ...] = ()) -> list[tuple[object, ...]]:
    locations: list[tuple[object, ...]] = []
    if isinstance(value, Mapping):
        if value.get("$ref") == target:
            locations.append(path)
        for key, child in value.items():
            locations.extend(_ref_locations(child, target, (*path, key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            locations.extend(_ref_locations(child, target, (*path, index)))
    return locations


def _closed_public_records(document: Mapping[str, Any], source_name: str) -> None:
    schemas = document.get("components", {}).get("schemas", {})
    if not isinstance(schemas, Mapping):
        raise ContractGenerationError(f"OpenAPI components.schemas missing in {source_name}")
    for name, schema in schemas.items():
        if not isinstance(schema, Mapping):
            continue
        object_like = schema.get("type") == "object" or "properties" in schema or "allOf" in schema
        if not object_like or schema.get("$ref"):
            continue
        closed = schema.get("additionalProperties") is False or schema.get("unevaluatedProperties") is False
        if closed:
            continue
        target = f"#/components/schemas/{name}"
        locations = _ref_locations(document.get("paths", {}), target)
        locations.extend(_ref_locations(schemas, target))
        # An unclosed composition base is safe only inside allOf of closed concrete records.
        all_of_only = bool(locations) and all("allOf" in location for location in locations)
        if all_of_only:
            consumers = [
                candidate
                for candidate in schemas.values()
                if isinstance(candidate, Mapping)
                and any(
                    isinstance(item, Mapping) and item.get("$ref") == target
                    for item in candidate.get("allOf", [])
                )
            ]
            if consumers and all(item.get("unevaluatedProperties") is False for item in consumers):
                continue
        raise ContractGenerationError(f"open public record {source_name}#/components/schemas/{name}")


def _compile_proto(source: Path) -> descriptor_pb2.FileDescriptorSet:
    proto = source / "ocor_registry.proto"
    include = Path(grpc_tools.__file__).resolve().parent / "_proto"
    with tempfile.TemporaryDirectory(prefix="ocor-contract-proto-") as directory:
        descriptor = Path(directory) / "contracts.pb"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "grpc_tools.protoc",
                f"-I{source}",
                f"-I{include}",
                f"--descriptor_set_out={descriptor}",
                "--include_imports",
                str(proto),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            raise ContractGenerationError(f"Proto3 compilation failed: {result.stderr.strip()}")
        file_set = descriptor_pb2.FileDescriptorSet()
        file_set.ParseFromString(descriptor.read_bytes())
        return file_set


def validate_contracts(source: Path, *, enforce_pins: bool = True) -> dict[str, object]:
    source = source.resolve()
    if enforce_pins:
        _verify_sources(source)
    _scan_backend_neutrality(source)
    json_documents: dict[str, dict[str, Any]] = {}
    for path in sorted(source.glob("*.schema.json")):
        document = _load_json(path)
        try:
            Draft202012Validator.check_schema(document)
        except Exception as exc:
            raise ContractGenerationError(f"JSON Schema validation failed for {path.name}: {exc}") from exc
        if document.get("type") == "object" and document.get("additionalProperties") is not False:
            raise ContractGenerationError(f"open public record {path.name}#")
        json_documents[path.name] = document
    openapi_documents: dict[str, dict[str, Any]] = {}
    for path in sorted(source.glob("*.openapi.yaml")):
        document = _load_yaml(path)
        try:
            validate_openapi(document, base_uri=path.resolve().as_uri())
        except Exception as exc:
            raise ContractGenerationError(f"OpenAPI validation failed for {path.name}: {exc}") from exc
        _closed_public_records(document, path.name)
        openapi_documents[path.name] = document
    proto_descriptor = _compile_proto(source)
    return {
        "json": json_documents,
        "openapi": openapi_documents,
        "proto": proto_descriptor,
    }


def _safe_name(value: str) -> str:
    parts = re.findall(r"[A-Za-z0-9]+", value)
    result = "".join(part[:1].upper() + part[1:] for part in parts)
    if not result or result[0].isdigit():
        result = "Contract" + result
    return result


def _schema_type(schema: Mapping[str, Any], language: str) -> str:
    if "$ref" in schema:
        name = str(schema["$ref"]).rsplit("/", 1)[-1]
        return _safe_name(name)
    kind = schema.get("type")
    if kind == "string":
        return "str" if language == "python" else "string"
    if kind == "integer":
        return "int" if language == "python" else "number"
    if kind == "number":
        return "float" if language == "python" else "number"
    if kind == "boolean":
        return "bool" if language == "python" else "boolean"
    if kind == "array":
        child = _schema_type(schema.get("items", {}), language)
        return f"list[{child}]" if language == "python" else f"ReadonlyArray<{child}>"
    return "object"


def _schema_model(name: str, schema: Mapping[str, Any], source: str) -> dict[str, object]:
    required = set(schema.get("required", []))
    properties = schema.get("properties", {})
    fields = []
    if isinstance(properties, Mapping):
        for field_name, field_schema in sorted(properties.items()):
            fields.append(
                {
                    "name": field_name,
                    "python_type": _schema_type(field_schema, "python"),
                    "typescript_type": _schema_type(field_schema, "typescript"),
                    "required": field_name in required,
                }
            )
    return {"name": _safe_name(name), "source": source, "fields": fields}


def _models(validated: Mapping[str, object]) -> list[dict[str, object]]:
    models: list[dict[str, object]] = []
    for source, document in validated["json"].items():  # type: ignore[union-attr]
        title = document.get("title") or Path(source).stem
        models.append(_schema_model(str(title), document, source))
    for source, document in validated["openapi"].items():  # type: ignore[union-attr]
        prefix = "Memory" if "memory" in source else "Gateway"
        for name, schema in sorted(document.get("components", {}).get("schemas", {}).items()):
            if isinstance(schema, Mapping) and (schema.get("type") == "object" or "properties" in schema):
                models.append(_schema_model(prefix + name, schema, source))
    descriptor: descriptor_pb2.FileDescriptorSet = validated["proto"]  # type: ignore[assignment]
    type_names = descriptor_pb2.FieldDescriptorProto.Type
    for file_descriptor in descriptor.file:
        if file_descriptor.name != "ocor_registry.proto":
            continue
        for message in file_descriptor.message_type:
            fields = []
            for field in sorted(message.field, key=lambda item: item.number):
                scalar = type_names.Name(field.type).removeprefix("TYPE_").lower()
                python_type = {"string": "str", "bool": "bool"}.get(scalar, "int" if scalar.startswith(("int", "uint")) else "object")
                typescript_type = "string" if scalar == "string" else "boolean" if scalar == "bool" else "number" if scalar.startswith(("int", "uint", "float", "double")) else "object"
                if field.label == descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED:
                    python_type = f"list[{python_type}]"
                    typescript_type = f"ReadonlyArray<{typescript_type}>"
                fields.append(
                    {
                        "name": field.name,
                        "python_type": python_type,
                        "typescript_type": typescript_type,
                        "required": not field.proto3_optional,
                    }
                )
            models.append(
                {"name": _safe_name("Registry" + message.name), "source": file_descriptor.name, "fields": fields}
            )
    names = [str(model["name"]) for model in models]
    if len(names) != len(set(names)):
        raise ContractGenerationError("generated model names collide")
    return sorted(models, key=lambda model: str(model["name"]))


def _render(models: list[dict[str, object]]) -> dict[str, bytes]:
    descriptor = {
        "generator_version": GENERATOR_VERSION,
        "models": models,
        "source_sha256": PINNED_SOURCE_HASHES,
    }
    descriptor_bytes = (json.dumps(descriptor, indent=2, sort_keys=True) + "\n").encode()
    python_lines = [
        '"""Generated by OCOR contract generator 1.0.0; do not edit."""',
        "",
        "from __future__ import annotations",
        "",
        "from typing import NotRequired, TypedDict",
        "",
    ]
    typescript_lines = ["// Generated by OCOR contract generator 1.0.0; do not edit.", ""]
    for model in models:
        python_lines.append(f"class {model['name']}(TypedDict):")
        fields = model["fields"]
        if not fields:
            python_lines.append("    pass")
        for field in fields:
            type_name = field["python_type"]
            if not field["required"]:
                type_name = f"NotRequired[{type_name}]"
            python_lines.append(f"    {field['name']}: {type_name}")
        python_lines.append("")
        typescript_lines.append(f"export interface {model['name']} {{")
        for field in fields:
            optional = "" if field["required"] else "?"
            typescript_lines.append(f"  readonly {field['name']}{optional}: {field['typescript_type']};")
        typescript_lines.extend(["}", ""])
    return {
        "contract-descriptor.json": descriptor_bytes,
        "ocor_contracts.py": ("\n".join(python_lines).rstrip() + "\n").encode(),
        "ocor_contracts.ts": ("\n".join(typescript_lines).rstrip() + "\n").encode(),
    }


def generate(source: Path, output: Path) -> dict[str, object]:
    validated = validate_contracts(source)
    models = _models(validated)
    artifacts = _render(models)
    hashes = {name: _sha256_bytes(content) for name, content in sorted(artifacts.items())}
    if PINNED_GENERATED_HASHES and hashes != PINNED_GENERATED_HASHES:
        raise ContractGenerationError(
            f"generated hashes differ from pins: expected {PINNED_GENERATED_HASHES}, observed {hashes}"
        )
    for name, content in artifacts.items():
        _atomic_write(output / name, content)
    manifest: dict[str, object] = {
        "schema_version": "1.0",
        "generator_version": GENERATOR_VERSION,
        "source_sha256": PINNED_SOURCE_HASHES,
        "artifact_sha256": hashes,
        "model_count": len(models),
        "validation": {
            "json_schema": "PASS",
            "openapi_3_1": "PASS",
            "proto3": "PASS",
            "closed_public_records": "PASS",
            "backend_neutrality": "PASS",
        },
    }
    _atomic_write(output / "MANIFEST.json", (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode())
    return manifest


def check_generated(source: Path, output: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="ocor-contract-check-") as directory:
        expected_dir = Path(directory)
        manifest = generate(source, expected_dir)
        expected_names = {*ARTIFACT_NAMES, "MANIFEST.json"}
        actual_names = {path.name for path in output.iterdir() if path.is_file()}
        if actual_names != expected_names:
            raise ContractGenerationError("generated drift: artifact inventory differs")
        for name in sorted(expected_names):
            if (output / name).read_bytes() != (expected_dir / name).read_bytes():
                raise ContractGenerationError(f"generated drift: {name} differs")
        return manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("generate", "check"))
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        manifest = generate(args.source, args.output) if args.operation == "generate" else check_generated(args.source, args.output)
        print(f"PASS: {args.operation} {manifest['model_count']} pinned contract models")
        return 0
    except (ContractGenerationError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
