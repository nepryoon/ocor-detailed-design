from __future__ import annotations

import pytest

# isort: split
from ocor_runtime.canonical import canonical_sha256
from ocor_runtime.errors import DigestProviderError
from ocor_runtime.kernel import canonical as kernel
from ocor_runtime.kernel.governed_context import (
    GovernedContext,
    GovernedContextCodec,
    GovernedContextError,
    VerifiedGovernedContextBinding,
)

DIGEST_A = "urn:sha256:" + "a" * 64
DIGEST_B = "urn:sha256:" + "b" * 64
DIGEST_C = "urn:sha256:" + "c" * 64


def context() -> GovernedContext:
    return GovernedContext.from_mapping(
        {
            "tenant_id": "urn:ocor:tenant:synthetic",
            "organization_id": "urn:ocor:org:synthetic",
            "domain_id": "urn:ocor:domain:logistics",
            "compartments": ["urn:ocor:compartment:alpha"],
            "classification_marking_ref": DIGEST_A,
            "purpose": "canonical-remediation-test",
            "effective_principal_id": "spiffe://ocor.test/workload/query-gateway",
            "actor_chain": ["urn:ocor:actor:gateway"],
            "ontology_release_digest": DIGEST_B,
            "policy_bundle_digest": DIGEST_C,
            "correlation_id": "018f2f95-01b2-7cc3-8d4e-123456789abc",
        }
    )


def test_real_governed_context_json_boundary_uses_canonical_kernel():
    expected = context()
    binding = VerifiedGovernedContextBinding(
        binding_ref="urn:ocor:binding:canonical-remediation", expected=expected
    )
    payload = GovernedContextCodec.to_json(expected)
    restored = GovernedContextCodec.from_json(payload, binding, expected.digest())
    assert restored == expected
    assert payload == expected.canonical_bytes()


def test_boundary_fault_injection_rejects_corrupted_digest():
    expected = context()
    binding = VerifiedGovernedContextBinding(
        binding_ref="urn:ocor:binding:canonical-remediation", expected=expected
    )
    corrupted = "urn:sha256:" + "0" * 64
    with pytest.raises(GovernedContextError, match="digest mismatch") as failure:
        GovernedContextCodec.from_json(expected.canonical_bytes(), binding, corrupted)
    assert failure.value.code == "GOVERNED_CONTEXT_MISMATCH"


def test_hash_provider_failure_is_typed_bounded_and_cannot_produce_a_false_digest(
    monkeypatch: pytest.MonkeyPatch,
):
    def fail_hash(_payload: bytes) -> object:
        raise OSError("x" * 10_000)

    monkeypatch.setattr(kernel.hashlib, "sha256", fail_hash)
    for operation in (context().digest, lambda: canonical_sha256({})):
        with pytest.raises(DigestProviderError) as failure:
            operation()
        assert failure.value.code == "DIGEST_PROVIDER_FAILURE"
        assert str(failure.value) == "SHA-256 provider failure"
        assert isinstance(failure.value.__cause__, OSError)
