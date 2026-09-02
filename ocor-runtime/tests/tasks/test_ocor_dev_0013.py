from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime

import pytest
from ocor_runtime.c3.ports import (
    C3Error,
    CanonicalReadPort,
    CanonicalSnapshot,
    ClaimSourceBinding,
    CommitReceipt,
    GovernedCanonicalCommitCommand,
    GovernedCommitPort,
    IdempotencyBinding,
    OutboxEnvelope,
    OutboxRelayPort,
    RecoveryPort,
    RevisionPort,
)
from ocor_runtime.kernel.canonical import canonical_digest
from ocor_runtime.kernel.governed_context import GovernedContext

DIGEST_A = "urn:sha256:" + "a" * 64
DIGEST_B = "urn:sha256:" + "b" * 64
DIGEST_C = "urn:sha256:" + "c" * 64
DIGEST_D = "urn:sha256:" + "d" * 64
NOW = datetime(2026, 9, 2, 4, 10, tzinfo=UTC)


@pytest.fixture
def context() -> GovernedContext:
    return GovernedContext.from_mapping(
        {
            "tenant_id": "urn:ocor:tenant:synthetic",
            "organization_id": "urn:ocor:org:synthetic",
            "domain_id": "urn:ocor:domain:logistics",
            "compartments": ["urn:ocor:compartment:alpha"],
            "classification_marking_ref": DIGEST_A,
            "purpose": "governed-canonical-commit",
            "effective_principal_id": "spiffe://ocor.test/workload/action-engine",
            "actor_chain": ["urn:ocor:actor:analyst", "urn:ocor:actor:c6"],
            "ontology_release_digest": DIGEST_B,
            "policy_bundle_digest": DIGEST_C,
            "correlation_id": "018f2f95-01b2-7cc3-8d4e-123456789abc",
        }
    )


@pytest.fixture
def command(context: GovernedContext) -> GovernedCanonicalCommitCommand:
    return GovernedCanonicalCommitCommand.from_mapping(
        {
            "command_id": "urn:ocor:command:synthetic:1",
            "action_instance_id": "urn:ocor:action:synthetic:1",
            "aggregate_type": "MissionObject",
            "aggregate_ref": "urn:ocor:mission-object:synthetic:1",
            "expected_revision": 7,
            "canonical_delta": {"status": "ASSESSED", "confidence": 0.8},
            "decision_ref": "urn:ocor:decision:synthetic:1",
            "authority_ref": "urn:ocor:authority:synthetic:1",
            "evidence_refs": ["urn:ocor:evidence:synthetic:1"],
            "claim_source_bindings": [
                {
                    "claim_ref": "urn:ocor:claim:synthetic:1",
                    "source_ref": "urn:ocor:source:synthetic:1",
                    "evidence_ref": "urn:ocor:evidence:synthetic:1",
                }
            ],
            "precondition_bindings": ["urn:ocor:precondition:revision-7"],
            "invariant_bindings": ["urn:ocor:invariant:single-writer"],
            "idempotency_key": "synthetic-commit-key-0001",
            "governed_context": context.to_mapping(),
            "governed_context_digest": context.digest(),
            "gate_package_digest": DIGEST_D,
            "branch": "main",
        }
    )


@pytest.fixture
def receipt(command: GovernedCanonicalCommitCommand) -> CommitReceipt:
    state = {"status": "ASSESSED"}
    payload = {"commit_id": "urn:ocor:commit:synthetic:8"}
    return CommitReceipt.from_command(
        command,
        commit_id="urn:ocor:commit:synthetic:8",
        state_digest=canonical_digest(state),
        outbox_event_id="urn:ocor:event:synthetic:8",
        outbox_payload_digest=canonical_digest(payload),
        committed_at=NOW,
    )


def test_command_is_closed_content_addressed_and_deeply_immutable(
    command: GovernedCanonicalCommitCommand,
):
    value = command.to_mapping()
    assert value["governed_context_digest"] == command.governed_context.digest()
    assert command.command_digest.startswith("urn:sha256:")
    with pytest.raises(TypeError):
        command.canonical_delta["status"] = "TAMPERED"  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        command.branch = "scenario"  # type: ignore[misc]


@pytest.mark.parametrize(
    "field",
    [
        "command_id",
        "action_instance_id",
        "aggregate_type",
        "aggregate_ref",
        "expected_revision",
        "canonical_delta",
        "decision_ref",
        "authority_ref",
        "evidence_refs",
        "claim_source_bindings",
        "precondition_bindings",
        "invariant_bindings",
        "idempotency_key",
        "governed_context",
        "governed_context_digest",
        "gate_package_digest",
        "branch",
    ],
)
def test_command_missing_any_binding_is_rejected(
    command: GovernedCanonicalCommitCommand, field: str
):
    value = command.to_mapping()
    del value[field]
    with pytest.raises(C3Error) as exc_info:
        GovernedCanonicalCommitCommand.from_mapping(value)
    assert exc_info.value.reason_code == "COMMIT_CONTRACT_INVALID"


def test_additional_command_field_is_rejected(command: GovernedCanonicalCommitCommand):
    value = command.to_mapping()
    value["writer_override"] = "bypass"
    with pytest.raises(C3Error) as exc_info:
        GovernedCanonicalCommitCommand.from_mapping(value)
    assert exc_info.value.reason_code == "COMMIT_CONTRACT_INVALID"


def test_only_main_can_produce_canonical_outbox(command: GovernedCanonicalCommitCommand):
    value = command.to_mapping()
    value["branch"] = "scenario/what-if"
    with pytest.raises(C3Error) as exc_info:
        GovernedCanonicalCommitCommand.from_mapping(value)
    assert exc_info.value.reason_code == "SINGLE_WRITER_VIOLATION"


def test_revision_and_gcs_mismatch_fail_with_stable_codes(
    command: GovernedCanonicalCommitCommand,
):
    with pytest.raises(C3Error) as revision_error:
        GovernedCanonicalCommitCommand.from_mapping(
            {**command.to_mapping(), "expected_revision": -1}
        )
    assert revision_error.value.reason_code == "REVISION_CONFLICT"

    with pytest.raises(C3Error) as context_error:
        GovernedCanonicalCommitCommand.from_mapping(
            {**command.to_mapping(), "governed_context_digest": DIGEST_A}
        )
    assert context_error.value.reason_code == "GOVERNED_CONTEXT_MISMATCH"


def test_receipt_binds_revision_state_idempotency_evidence_gcs_and_outbox(
    command: GovernedCanonicalCommitCommand, receipt: CommitReceipt
):
    assert receipt.from_revision == 7
    assert receipt.to_revision == 8
    assert receipt.state_digest == canonical_digest({"status": "ASSESSED"})
    assert receipt.idempotency_key == command.idempotency_key
    assert receipt.evidence_refs == command.evidence_refs
    assert receipt.governed_context_digest == command.governed_context_digest
    assert receipt.outbox_event_id == "urn:ocor:event:synthetic:8"
    assert receipt.outbox_payload_digest == canonical_digest(
        {"commit_id": "urn:ocor:commit:synthetic:8"}
    )
    assert receipt.verify(command) is receipt


@pytest.mark.parametrize(
    "change",
    [
        {"to_revision": 9},
        {"state_digest": ""},
        {"idempotency_key": "different-key-000000"},
        {"evidence_refs": ("urn:ocor:evidence:other",)},
        {"governed_context_digest": DIGEST_C},
        {"outbox_event_id": ""},
    ],
)
def test_receipt_missing_or_drifting_binding_is_rejected(
    command: GovernedCanonicalCommitCommand,
    receipt: CommitReceipt,
    change: dict[str, object],
):
    with pytest.raises(C3Error):
        replace(receipt, **change).verify(command)


def test_idempotency_replay_returns_original_receipt_only_for_same_content(
    command: GovernedCanonicalCommitCommand, receipt: CommitReceipt
):
    binding = IdempotencyBinding.from_commit(command, receipt)
    replay = GovernedCanonicalCommitCommand.from_mapping(command.to_mapping())
    assert binding.resolve(replay) is receipt


def test_idempotency_key_reuse_with_different_content_is_rejected(
    command: GovernedCanonicalCommitCommand, receipt: CommitReceipt
):
    binding = IdempotencyBinding.from_commit(command, receipt)
    changed = GovernedCanonicalCommitCommand.from_mapping(
        {**command.to_mapping(), "canonical_delta": {"status": "REJECTED"}}
    )
    with pytest.raises(C3Error) as exc_info:
        binding.resolve(changed)
    assert exc_info.value.reason_code == "IDEMPOTENCY_CONFLICT"


def test_idempotency_scope_includes_tenant_type_and_ref(
    command: GovernedCanonicalCommitCommand, receipt: CommitReceipt
):
    binding = IdempotencyBinding.from_commit(command, receipt)
    assert binding.scope == (
        command.governed_context.tenant_id,
        command.aggregate_type,
        command.aggregate_ref,
        command.idempotency_key,
    )


def test_snapshot_and_outbox_envelope_are_immutable_and_integrity_bound(
    command: GovernedCanonicalCommitCommand, receipt: CommitReceipt
):
    snapshot = CanonicalSnapshot.from_receipt(receipt, {"status": "ASSESSED"})
    envelope = OutboxEnvelope.from_receipt(receipt, {"commit_id": receipt.commit_id})
    assert snapshot.state_digest == canonical_digest({"status": "ASSESSED"})
    assert envelope.branch == "main"
    assert envelope.commit_id == receipt.commit_id
    with pytest.raises(TypeError):
        envelope.payload["commit_id"] = "tampered"  # type: ignore[index]
    with pytest.raises(C3Error):
        replace(snapshot, revision=-1)
    with pytest.raises(C3Error):
        replace(envelope, branch="scenario")


class CommitHandler:
    def commit(self, command: GovernedCanonicalCommitCommand) -> CommitReceipt:
        raise NotImplementedError


def test_all_c3_ports_are_runtime_checkable():
    assert isinstance(CommitHandler(), GovernedCommitPort)
    assert not isinstance(object(), CanonicalReadPort)
    assert not isinstance(object(), OutboxRelayPort)
    assert not isinstance(object(), RevisionPort)
    assert not isinstance(object(), RecoveryPort)


def test_claim_source_binding_requires_all_three_refs():
    with pytest.raises(C3Error) as exc_info:
        ClaimSourceBinding("urn:ocor:claim:1", "", "urn:ocor:evidence:1")
    assert exc_info.value.reason_code == "COMMIT_CONTRACT_INVALID"
