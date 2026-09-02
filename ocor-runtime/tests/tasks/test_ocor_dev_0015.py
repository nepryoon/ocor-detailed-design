from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from ocor_runtime.c3.ports import GovernedCanonicalCommitCommand
from ocor_runtime.kernel.governed_context import GovernedContext

from spikes.c3_atomicity.oracle import (
    AtomicCommitOracle,
    AtomicVisibilityError,
    CrashStage,
    IdempotencyConflict,
)

DIGEST_A = "urn:sha256:" + "a" * 64
DIGEST_B = "urn:sha256:" + "b" * 64
DIGEST_C = "urn:sha256:" + "c" * 64
DIGEST_D = "urn:sha256:" + "d" * 64
WORKER = Path("spikes/c3_atomicity/crash_worker.py").resolve()


@pytest.fixture
def command() -> dict[str, object]:
    context = GovernedContext.from_mapping(
        {
            "tenant_id": "urn:ocor:tenant:synthetic",
            "organization_id": "urn:ocor:org:synthetic",
            "domain_id": "urn:ocor:domain:logistics",
            "compartments": ["urn:ocor:compartment:alpha"],
            "classification_marking_ref": DIGEST_A,
            "purpose": "atomicity-spike",
            "effective_principal_id": "spiffe://ocor.test/workload/c6",
            "actor_chain": ["urn:ocor:actor:synthetic", "urn:ocor:actor:c6"],
            "ontology_release_digest": DIGEST_B,
            "policy_bundle_digest": DIGEST_C,
            "correlation_id": "018f2f95-01b2-7cc3-8d4e-123456789abc",
        }
    )
    return GovernedCanonicalCommitCommand.from_mapping(
        {
            "command_id": "urn:ocor:command:atomicity:1",
            "action_instance_id": "urn:ocor:action:atomicity:1",
            "aggregate_type": "MissionObject",
            "aggregate_ref": "urn:ocor:mission-object:atomicity:1",
            "expected_revision": 0,
            "canonical_delta": {"status": "ASSESSED"},
            "decision_ref": "urn:ocor:decision:atomicity:1",
            "authority_ref": "urn:ocor:authority:atomicity:1",
            "evidence_refs": ["urn:ocor:evidence:atomicity:1"],
            "claim_source_bindings": [
                {
                    "claim_ref": "urn:ocor:claim:atomicity:1",
                    "source_ref": "urn:ocor:source:atomicity:1",
                    "evidence_ref": "urn:ocor:evidence:atomicity:1",
                }
            ],
            "precondition_bindings": ["urn:ocor:precondition:revision-0"],
            "invariant_bindings": ["urn:ocor:invariant:atomic-outbox"],
            "idempotency_key": "atomicity-spike-key-0001",
            "governed_context": context.to_mapping(),
            "governed_context_digest": context.digest(),
            "gate_package_digest": DIGEST_D,
            "branch": "main",
        }
    ).to_mapping()


def crash(database: Path, command: dict[str, object], stage: CrashStage) -> int:
    result = subprocess.run(
        [sys.executable, str(WORKER), str(database), stage.value],
        input=json.dumps(command),
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert result.stderr == ""
    return result.returncode


@pytest.mark.parametrize("stage", CrashStage.precommit())
def test_abrupt_precommit_crash_recovers_with_zero_partial_visibility(
    tmp_path: Path, command: dict[str, object], stage: CrashStage
):
    database = tmp_path / f"{stage.value}.sqlite"
    oracle = AtomicCommitOracle(database)
    oracle.initialize()
    assert crash(database, command, stage) == 86
    assert oracle.assert_atomic_visibility() == (0, 0, 0, 0)


def test_postcommit_preack_crash_has_all_four_durable_records_and_exact_retry(
    tmp_path: Path, command: dict[str, object]
):
    database = tmp_path / "postcommit.sqlite"
    oracle = AtomicCommitOracle(database)
    oracle.initialize()
    assert crash(database, command, CrashStage.AFTER_COMMIT_BEFORE_ACK) == 86
    assert oracle.assert_atomic_visibility() == (1, 1, 1, 1)
    with oracle.connect() as connection:
        stored = connection.execute(
            "SELECT receipt_json FROM canonical_idempotency"
        ).fetchone()[0]
    assert oracle.commit(command) == json.loads(stored)
    assert oracle.assert_atomic_visibility() == (1, 1, 1, 1)


def test_identical_retry_returns_byte_identical_original_receipt(
    tmp_path: Path, command: dict[str, object]
):
    oracle = AtomicCommitOracle(tmp_path / "retry.sqlite")
    oracle.initialize()
    first = oracle.commit(command)
    second = oracle.commit(command)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert oracle.assert_atomic_visibility() == (1, 1, 1, 1)


def test_key_reuse_with_changed_content_is_rejected_without_partial_write(
    tmp_path: Path, command: dict[str, object]
):
    oracle = AtomicCommitOracle(tmp_path / "conflict.sqlite")
    oracle.initialize()
    original = oracle.commit(command)
    changed = {**command, "canonical_delta": {"status": "REJECTED"}}
    with pytest.raises(IdempotencyConflict):
        oracle.commit(changed)
    assert oracle.commit(command) == original
    assert oracle.assert_atomic_visibility() == (1, 1, 1, 1)


def test_partial_visibility_falsifies_oracle_instead_of_passing(
    tmp_path: Path,
):
    oracle = AtomicCommitOracle(tmp_path / "partial.sqlite")
    oracle.initialize()
    with oracle.connect() as connection:
        connection.execute(
            """INSERT INTO canonical_aggregate
                   (tenant_id, aggregate_type, aggregate_ref, revision, state_digest)
               VALUES ('tenant', 'type', 'ref', 1, ?)""",
            (DIGEST_A,),
        )
    with pytest.raises(AtomicVisibilityError, match="partial durable visibility"):
        oracle.assert_atomic_visibility()


def test_scenario_branch_cannot_create_relayable_outbox(
    tmp_path: Path, command: dict[str, object]
):
    oracle = AtomicCommitOracle(tmp_path / "scenario.sqlite")
    oracle.initialize()
    with pytest.raises(ValueError, match="branch must be main"):
        oracle.commit({**command, "branch": "scenario/test"})
    assert oracle.assert_atomic_visibility() == (0, 0, 0, 0)
