from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from ocor_runtime.c3.ports import GovernedCanonicalCommitCommand
from ocor_runtime.kernel.governed_context import GovernedContext

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

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
WORKER = REPOSITORY_ROOT / "spikes/c3_atomicity/crash_worker.py"


@pytest.fixture(scope="session")
def postgres_dsn() -> str:
    dsn = os.environ.get("OCOR_LIVE_POSTGRES_DSN")
    if not dsn:
        pytest.fail("OCOR_LIVE_POSTGRES_DSN is mandatory qualifying evidence")
    return dsn


@pytest.fixture
def oracle(postgres_dsn: str) -> AtomicCommitOracle:
    value = AtomicCommitOracle(postgres_dsn)
    value.initialize()
    value.reset()
    return value


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


def crash(command: dict[str, object], stage: CrashStage) -> int:
    result = subprocess.run(
        [sys.executable, str(WORKER), stage.value],
        input=json.dumps(command),
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert result.stderr == ""
    return result.returncode


@pytest.mark.parametrize("stage", CrashStage.precommit())
def test_real_postgresql_precommit_process_crash_has_zero_partial_visibility(
    oracle: AtomicCommitOracle, command: dict[str, object], stage: CrashStage
):
    assert crash(command, stage) == 86
    assert oracle.assert_atomic_visibility() == (0, 0, 0, 0)


def test_real_postgresql_postcommit_preack_crash_has_complete_exact_retry(
    oracle: AtomicCommitOracle, command: dict[str, object]
):
    assert crash(command, CrashStage.AFTER_COMMIT_BEFORE_ACK) == 86
    assert oracle.assert_atomic_visibility() == (1, 1, 1, 1)
    with oracle.connect() as connection:
        stored = connection.execute(
            "SELECT receipt FROM spike_c3_idempotency"
        ).fetchone()["receipt"]
    assert oracle.commit(command) == stored
    assert oracle.assert_atomic_visibility() == (1, 1, 1, 1)


def test_two_concurrent_identical_retries_return_one_identical_receipt(
    oracle: AtomicCommitOracle, command: dict[str, object]
):
    barrier = threading.Barrier(3)

    def attempt() -> dict[str, object]:
        barrier.wait(timeout=5)
        return oracle.commit(command)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(attempt), pool.submit(attempt)]
        barrier.wait(timeout=5)
        receipts = [future.result(timeout=10) for future in futures]
    assert receipts[0] == receipts[1]
    assert oracle.assert_atomic_visibility() == (1, 1, 1, 1)


def test_key_reuse_with_changed_content_is_rejected_without_partial_write(
    oracle: AtomicCommitOracle, command: dict[str, object]
):
    original = oracle.commit(command)
    changed = {**command, "canonical_delta": {"status": "REJECTED"}}
    with pytest.raises(IdempotencyConflict):
        oracle.commit(changed)
    assert oracle.commit(command) == original
    assert oracle.assert_atomic_visibility() == (1, 1, 1, 1)


def test_atomic_oracle_accepts_multiple_revisions_without_global_count_equality(
    oracle: AtomicCommitOracle, command: dict[str, object]
):
    first = oracle.commit(command)
    second_command = {
        **command,
        "command_id": "urn:ocor:command:atomicity:2",
        "expected_revision": 1,
        "canonical_delta": {"status": "CONFIRMED"},
        "idempotency_key": "atomicity-spike-key-0002",
    }
    second = oracle.commit(second_command)
    assert first["to_revision"] == 1
    assert second["from_revision"] == 1
    assert second["to_revision"] == 2
    assert oracle.assert_atomic_visibility() == (1, 2, 2, 2)


def test_partial_visibility_falsifies_oracle_instead_of_passing(
    oracle: AtomicCommitOracle,
):
    with oracle.connect() as connection:
        connection.execute(
            """INSERT INTO spike_c3_aggregate
                   (tenant_id, aggregate_type, aggregate_ref, revision, state_digest)
               VALUES ('tenant', 'type', 'ref', 1, %s)""",
            (DIGEST_A,),
        )
    with pytest.raises(AtomicVisibilityError, match="partial durable visibility"):
        oracle.assert_atomic_visibility()


def test_scenario_branch_cannot_create_relayable_outbox(
    oracle: AtomicCommitOracle, command: dict[str, object]
):
    with pytest.raises(ValueError, match="branch must be main"):
        oracle.commit({**command, "branch": "scenario/test"})
    assert oracle.assert_atomic_visibility() == (0, 0, 0, 0)
