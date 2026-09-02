from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import ModuleType

import grpc_tools
import pytest
import yaml
from jsonschema import Draft202012Validator

from ocor_runtime.kernel.canonical import IdentifierError, validate_correlation_id
from ocor_runtime.kernel.governed_context import (
    GCS_FIELDS,
    GovernedContext,
    GovernedContextCodec,
    GovernedContextError,
    VerifiedGovernedContextBinding,
)

DIGEST_A = "urn:sha256:" + "a" * 64
DIGEST_B = "urn:sha256:" + "b" * 64
DIGEST_C = "urn:sha256:" + "c" * 64
CORRELATION_ID = "018f2f95-01b2-7cc3-8d4e-123456789abc"


def context_values() -> dict[str, object]:
    return {
        "tenant_id": "urn:ocor:tenant:synthetic",
        "organization_id": "urn:ocor:org:synthetic",
        "domain_id": "urn:ocor:domain:logistics",
        "compartments": ["urn:ocor:compartment:zulu", "urn:ocor:compartment:alpha"],
        "classification_marking_ref": DIGEST_A,
        "purpose": "synthetic-mission-evaluation",
        "effective_principal_id": "spiffe://ocor.test/workload/query-gateway",
        "actor_chain": ["urn:ocor:actor:alice", "urn:ocor:actor:gateway"],
        "ontology_release_digest": DIGEST_B,
        "policy_bundle_digest": DIGEST_C,
        "correlation_id": CORRELATION_ID,
    }


@pytest.fixture
def context() -> GovernedContext:
    return GovernedContext.from_mapping(context_values())


@pytest.fixture
def binding(context: GovernedContext) -> VerifiedGovernedContextBinding:
    return VerifiedGovernedContextBinding(
        binding_ref="urn:ocor:binding:synthetic-query", expected=context
    )


@pytest.fixture(scope="module")
def registry_proto(tmp_path_factory: pytest.TempPathFactory) -> ModuleType:
    output = tmp_path_factory.mktemp("ocor-registry-proto")
    root = Path(__file__).resolve().parents[2]
    contracts = root / "docs/governance_dossier/contracts"
    include = Path(grpc_tools.__file__).resolve().parent / "_proto"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "grpc_tools.protoc",
            f"-I{contracts}",
            f"-I{include}",
            f"--python_out={output}",
            str(contracts / "ocor_registry.proto"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    module_path = output / "ocor_registry_pb2.py"
    spec = importlib.util.spec_from_file_location("ocor_registry_pb2", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_closed_eleven_field_record_canonicalizes_only_set_fields(context: GovernedContext):
    assert GCS_FIELDS == tuple(context_values())
    assert context.compartments == (
        "urn:ocor:compartment:alpha",
        "urn:ocor:compartment:zulu",
    )
    assert context.actor_chain == (
        "urn:ocor:actor:alice",
        "urn:ocor:actor:gateway",
    )
    assert list(context.to_mapping()) == list(GCS_FIELDS)
    assert context.canonical_bytes() == json.dumps(
        context.to_mapping(), ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode()
    assert context.digest().startswith("urn:sha256:")


def test_equivalent_compartment_sets_have_identical_bytes_and_digest():
    left = GovernedContext.from_mapping(context_values())
    right_values = context_values()
    right_values["compartments"] = list(reversed(right_values["compartments"]))
    right = GovernedContext.from_mapping(right_values)
    assert left.canonical_bytes() == right.canonical_bytes()
    assert left.digest() == right.digest()


@pytest.mark.parametrize("field", GCS_FIELDS)
def test_missing_field_fails_closed(field: str):
    values = context_values()
    del values[field]
    with pytest.raises(GovernedContextError, match="missing") as exc_info:
        GovernedContext.from_mapping(values)
    assert exc_info.value.code == "GOVERNED_CONTEXT_INCOMPLETE"


@pytest.mark.parametrize("extra", ["principal_id", "causation_id", "trace_id"])
def test_extra_or_alias_field_fails_closed(extra: str):
    values = context_values()
    values[extra] = "attacker-controlled"
    with pytest.raises(GovernedContextError, match="additional") as exc_info:
        GovernedContext.from_mapping(values)
    assert exc_info.value.code == "GOVERNED_CONTEXT_ADDITIONAL_PROPERTY"


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("tenant_id", 7),
        ("purpose", ""),
        ("compartments", "urn:ocor:compartment:not-an-array"),
        ("actor_chain", []),
        ("classification_marking_ref", "sha256:" + "a" * 64),
        ("ontology_release_digest", "urn:sha256:" + "A" * 64),
        ("policy_bundle_digest", "urn:sha256:short"),
    ],
)
def test_non_canonical_or_coerced_values_fail(field: str, bad_value: object):
    values = context_values()
    values[field] = bad_value
    with pytest.raises(GovernedContextError):
        GovernedContext.from_mapping(values)


def test_mapping_accepts_schema_valid_non_uuid_correlation_without_weakening_uuid_api():
    values = context_values()
    values["correlation_id"] = "request-from-approved-schema"
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "docs/governance_dossier/contracts/governed-context.schema.json"
    )
    validator = Draft202012Validator(json.loads(schema_path.read_text()))

    assert validator.is_valid(values)
    assert (
        GovernedContext.from_mapping(values).correlation_id == values["correlation_id"]
    )
    with pytest.raises(IdentifierError, match="canonical UUID"):
        validate_correlation_id(values["correlation_id"])  # type: ignore[arg-type]


@pytest.mark.parametrize("field", ["compartments", "actor_chain"])
def test_mapping_rejects_tuple_where_approved_schema_rejects_non_array(field: str):
    values = context_values()
    values[field] = tuple(values[field])  # type: ignore[arg-type]
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "docs/governance_dossier/contracts/governed-context.schema.json"
    )
    validator = Draft202012Validator(json.loads(schema_path.read_text()))

    assert not validator.is_valid(values)
    with pytest.raises(
        GovernedContextError, match=f"{field} must be a non-empty array"
    ):
        GovernedContext.from_mapping(values)


@pytest.mark.parametrize("field", ["compartments", "actor_chain"])
def test_duplicate_array_values_fail(field: str):
    values = context_values()
    values[field] = [values[field][0], values[field][0]]  # type: ignore[index]
    with pytest.raises(GovernedContextError, match="duplicate"):
        GovernedContext.from_mapping(values)


def test_json_boundary_round_trip_verifies_binding_and_digest(
    context: GovernedContext, binding: VerifiedGovernedContextBinding
):
    payload = GovernedContextCodec.to_json(context)
    restored = GovernedContextCodec.from_json(payload, binding, context.digest())
    assert restored == context
    assert restored.canonical_bytes() == payload


def test_json_boundary_rejects_duplicate_keys(
    context: GovernedContext, binding: VerifiedGovernedContextBinding
):
    payload = context.canonical_bytes().decode()
    duplicate = payload.replace(
        '"tenant_id":"urn:ocor:tenant:synthetic"',
        '"tenant_id":"urn:ocor:tenant:synthetic","tenant_id":"attacker"',
    )
    with pytest.raises(GovernedContextError, match="duplicate"):
        GovernedContextCodec.from_json(duplicate, binding, context.digest())


def test_openapi_boundary_round_trip_is_identical(
    context: GovernedContext, binding: VerifiedGovernedContextBinding
):
    wire = GovernedContextCodec.to_openapi(context)
    restored = GovernedContextCodec.from_openapi(wire, binding, context.digest())
    assert restored == context
    assert restored.digest() == context.digest()


def test_openapi_component_uses_and_accepts_the_approved_closed_schema(
    context: GovernedContext,
):
    runtime_root = Path(__file__).resolve().parents[2]
    contracts = runtime_root / "docs/governance_dossier/contracts"
    schema = json.loads((contracts / "governed-context.schema.json").read_text())
    api = yaml.safe_load((contracts / "ocor-governed-memory.openapi.yaml").read_text())
    assert api["components"]["schemas"]["GovernedContext"] == {
        "$ref": "./governed-context.schema.json"
    }
    Draft202012Validator(schema).validate(context.to_mapping())


@pytest.mark.parametrize(
    "stale_field",
    [
        "tenant_id",
        "compartments",
        "effective_principal_id",
        "actor_chain",
        "ontology_release_digest",
        "policy_bundle_digest",
    ],
)
def test_verified_binding_mismatch_fails_before_use(
    context: GovernedContext,
    binding: VerifiedGovernedContextBinding,
    stale_field: str,
):
    wire = context.to_mapping()
    if isinstance(wire[stale_field], list):
        wire[stale_field] = ["urn:ocor:stale"]
    elif stale_field in {"ontology_release_digest", "policy_bundle_digest"}:
        wire[stale_field] = DIGEST_A
    else:
        wire[stale_field] = "stale"
    with pytest.raises(GovernedContextError, match="binding mismatch") as exc_info:
        GovernedContextCodec.from_openapi(wire, binding, context.digest())
    assert exc_info.value.code == "GOVERNED_CONTEXT_MISMATCH"


def test_claimed_digest_mismatch_fails_closed(
    context: GovernedContext, binding: VerifiedGovernedContextBinding
):
    with pytest.raises(GovernedContextError, match="digest mismatch"):
        GovernedContextCodec.from_openapi(context.to_mapping(), binding, DIGEST_A)


def test_real_proto_invocation_context_round_trip_uses_verified_identity_binding(
    context: GovernedContext,
    binding: VerifiedGovernedContextBinding,
    registry_proto: ModuleType,
):
    message = registry_proto.InvocationContext()
    GovernedContextCodec.to_proto(context, message)
    serialized = message.SerializeToString(deterministic=True)
    reparsed = registry_proto.InvocationContext.FromString(serialized)
    restored = GovernedContextCodec.from_proto(reparsed, binding)
    assert restored == context
    assert restored.canonical_bytes() == context.canonical_bytes()
    assert not hasattr(reparsed, "effective_principal_id")
    assert not hasattr(reparsed, "actor_chain")


@pytest.mark.parametrize("field", ["ontology_release_digest", "policy_bundle_digest"])
def test_real_proto_stale_pin_fails_before_dispatch(
    context: GovernedContext,
    binding: VerifiedGovernedContextBinding,
    registry_proto: ModuleType,
    field: str,
):
    message = registry_proto.InvocationContext()
    GovernedContextCodec.to_proto(context, message)
    setattr(message, field, DIGEST_A)
    with pytest.raises(GovernedContextError, match="binding mismatch"):
        GovernedContextCodec.from_proto(message, binding)


def test_real_proto_tampered_digest_fails_before_dispatch(
    context: GovernedContext,
    binding: VerifiedGovernedContextBinding,
    registry_proto: ModuleType,
):
    message = registry_proto.InvocationContext()
    GovernedContextCodec.to_proto(context, message)
    message.governed_context_digest = DIGEST_A
    with pytest.raises(GovernedContextError, match="digest mismatch"):
        GovernedContextCodec.from_proto(message, binding)


@pytest.mark.parametrize("unverified_binding", [None, object()])
def test_proto_rejects_unverified_binding_before_dereference(
    registry_proto: ModuleType, unverified_binding: object
):
    message = registry_proto.InvocationContext()

    with pytest.raises(
        GovernedContextError, match="a verified binding is required"
    ) as exc_info:
        GovernedContextCodec.from_proto(
            message,
            unverified_binding,  # type: ignore[arg-type]
        )
    assert exc_info.value.code == "GOVERNED_CONTEXT_MISMATCH"


def test_context_and_verified_binding_are_immutable(
    context: GovernedContext, binding: VerifiedGovernedContextBinding
):
    with pytest.raises(FrozenInstanceError):
        context.purpose = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        binding.binding_ref = "changed"  # type: ignore[misc]


def test_isolation_key_contains_the_exact_normative_partition(context: GovernedContext):
    assert context.isolation_key() == (
        context.tenant_id,
        context.organization_id,
        context.domain_id,
        context.compartments,
        context.purpose,
        context.classification_marking_ref,
        context.ontology_release_digest,
        context.policy_bundle_digest,
    )
