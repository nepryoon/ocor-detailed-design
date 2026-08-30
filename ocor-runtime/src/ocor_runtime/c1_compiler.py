"""C1 — deterministic semantic document compiler."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError, ValidationError
from referencing import Registry, Resource

from .canonical import canonical_sha256, canonicalize
from .errors import SchemaValidationError


@dataclass(frozen=True, slots=True)
class CompiledArtifact:
    """Immutable output of semantic compilation."""

    artifact_id: str
    semantic_digest: str
    envelope_digest: str
    canonical_payload: bytes
    document: Mapping[str, Any]
    schema_id: str | None = None


def semantic_view(document: Mapping[str, Any]) -> Any:
    """Select identity-bearing data while excluding operational markings.

    An envelope with a ``payload`` field identifies the kind, schema version and
    payload.  Markings and mutable envelope metadata are deliberately excluded.
    Bare documents exclude only their top-level marking annotations.
    """

    if "payload" in document:
        view: dict[str, Any] = {"payload": copy.deepcopy(document["payload"])}
        for key in ("kind", "schemaVersion"):
            if key in document:
                view[key] = copy.deepcopy(document[key])
        return view
    return {
        key: copy.deepcopy(value)
        for key, value in document.items()
        if key not in {"markings", "$markings", "operationalMetadata"}
    }


class SemanticCompiler:
    """Validate, canonicalize and content-address a semantic envelope."""

    def __init__(
        self,
        schema: Mapping[str, Any] | None = None,
        *,
        registry: Registry | None = None,
    ) -> None:
        self._schema = copy.deepcopy(schema) if schema is not None else None
        self._validator: Draft202012Validator | None = None
        if self._schema is not None:
            try:
                Draft202012Validator.check_schema(self._schema)
            except SchemaError as exc:
                raise SchemaValidationError(f"invalid compiler schema: {exc.message}") from exc
            self._validator = Draft202012Validator(
                self._schema,
                registry=registry or Registry(),
                format_checker=FormatChecker(),
            )

    @classmethod
    def from_schema_file(cls, path: str | Path) -> "SemanticCompiler":
        import json

        schema_path = Path(path)
        schemas: list[Mapping[str, Any]] = []
        for candidate in sorted(schema_path.parent.glob("*.schema.json")):
            with candidate.open("r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            if "$id" in loaded:
                schemas.append(loaded)
        selected = next(
            (item for item in schemas if item.get("$id", "").endswith(schema_path.name)),
            None,
        )
        if selected is None:
            with schema_path.open("r", encoding="utf-8") as handle:
                selected = json.load(handle)
            schemas.append(selected)
        registry = Registry().with_resources(
            (item["$id"], Resource.from_contents(item)) for item in schemas
        )
        return cls(selected, registry=registry)

    def validate(self, document: Mapping[str, Any]) -> None:
        if not isinstance(document, Mapping):
            raise SchemaValidationError("semantic document must be a JSON object")
        if self._validator is None:
            return
        errors = sorted(
            self._validator.iter_errors(document),
            key=lambda item: tuple(str(component) for component in item.path),
        )
        if errors:
            error: ValidationError = errors[0]
            location = "/".join(str(item) for item in error.absolute_path) or "$"
            raise SchemaValidationError(f"{location}: {error.message}") from error

    def compile(self, document: Mapping[str, Any]) -> CompiledArtifact:
        self.validate(document)
        stable_document = copy.deepcopy(dict(document))
        identity_payload = semantic_view(stable_document)
        semantic_digest = canonical_sha256(identity_payload)
        envelope_digest = canonical_sha256(stable_document)
        schema_id = self._schema.get("$id") if self._schema else None
        return CompiledArtifact(
            artifact_id=f"urn:ocor:sha256:{semantic_digest}",
            semantic_digest=semantic_digest,
            envelope_digest=envelope_digest,
            canonical_payload=canonicalize(identity_payload),
            document=_freeze(stable_document),
            schema_id=schema_id,
        )


Compiler = SemanticCompiler


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return copy.deepcopy(value)
