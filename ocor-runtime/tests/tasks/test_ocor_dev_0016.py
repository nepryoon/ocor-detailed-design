"""OCOR-DEV-0016: SPIKE selected C3 backend behaviour.

Proves that the *selected* C3 backend (PostgreSQL, as already implemented
and sealed by OCOR-DEV-0015's atomic-commit oracle) also meets locking,
isolation, failure and reconciliation oracles under real concurrency, not
only under a single writer. Every oracle here drives a real, running
PostgreSQL instance -- no mocks, no fakes -- through
``spikes.c3_atomicity.oracle.PostgreSQLAtomicCommitOracle`` (reused
unmodified) plus the independent concurrent-race harness and out-of-band
probes added in ``spikes.c3_backend.concurrency_oracle``.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest
from ocor_runtime.kernel.governed_context import GovernedContext
from ocor_runtime.c3.ports import GovernedCanonicalCommitCommand

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from spikes.c3_atomicity.oracle import (  # noqa: E402 -- must follow sys.path.insert above
    AtomicCommitOracle,
    AtomicVisibilityError,
    CrashStage,
)
from spikes.c3_backend.concurrency_oracle import (  # noqa: E402 -- must follow sys.path.insert above
    lock_key_for,
    observe_lock_contention,
    race_distinct_commands,
    sample_revision_during,
)

WORKER = REPOSITORY_ROOT / "spikes/c3_atomicity/crash_worker.py"
DIGEST_A = "urn:sha256:" + "a" * 64
DIGEST_B = "urn:sha256:" + "b" * 64
DIGEST_C = "urn:sha256:" + "c" * 64
DIGEST_D = "urn:sha256:" + "d" * 64
AGGREGATE_REF = "urn:ocor:mission-object:backend-concurrency:1"
SCOPE = ("urn:ocor:tenant:synthetic", "MissionObject", AGGREGATE_REF)


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


def make_command(
    *, command_id: str, idempotency_key: str, expected_revision: int, canonical_delta: dict[str, object]
) -> dict[str, object]:
    context = GovernedContext.from_mapping(
        {
            "tenant_id": "urn:ocor:tenant:synthetic",
            "organization_id": "urn:ocor:org:synthetic",
            "domain_id": "urn:ocor:domain:logistics",
            "compartments": ["urn:ocor:compartment:alpha"],
            "classification_marking_ref": DIGEST_A,
            "purpose": "backend-concurrency-spike",
            "effective_principal_id": "spiffe://ocor.test/workload/c6",
            "actor_chain": ["urn:ocor:actor:synthetic", "urn:ocor:actor:c6"],
            "ontology_release_digest": DIGEST_B,
            "policy_bundle_digest": DIGEST_C,
            "correlation_id": "018f2f95-01b2-7cc3-8d4e-123456789abc",
        }
    )
    return GovernedCanonicalCommitCommand.from_mapping(
        {
            "command_id": command_id,
            "action_instance_id": command_id.replace("command", "action"),
            "aggregate_type": "MissionObject",
            "aggregate_ref": AGGREGATE_REF,
            "expected_revision": expected_revision,
            "canonical_delta": canonical_delta,
            "decision_ref": "urn:ocor:decision:backend-concurrency:1",
            "authority_ref": "urn:ocor:authority:backend-concurrency:1",
            "evidence_refs": ["urn:ocor:evidence:backend-concurrency:1"],
            "claim_source_bindings": [
                {
                    "claim_ref": "urn:ocor:claim:backend-concurrency:1",
                    "source_ref": "urn:ocor:source:backend-concurrency:1",
                    "evidence_ref": "urn:ocor:evidence:backend-concurrency:1",
                }
            ],
            "precondition_bindings": [f"urn:ocor:precondition:revision-{expected_revision}"],
            "invariant_bindings": ["urn:ocor:invariant:atomic-outbox"],
            "idempotency_key": idempotency_key,
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


def test_two_distinct_commands_racing_the_same_revision_never_both_succeed(
    oracle: AtomicCommitOracle, postgres_dsn: str
):
    command_a = make_command(
        command_id="urn:ocor:command:backend-concurrency:a",
        idempotency_key="backend-concurrency-key-a",
        expected_revision=0,
        canonical_delta={"status": "ASSESSED_BY_A"},
    )
    command_b = make_command(
        command_id="urn:ocor:command:backend-concurrency:b",
        idempotency_key="backend-concurrency-key-b",
        expected_revision=0,
        canonical_delta={"status": "ASSESSED_BY_B"},
    )
    (receipt_a, error_a), (receipt_b, error_b) = race_distinct_commands(oracle, command_a, command_b)

    successes = [r for r in (receipt_a, receipt_b) if r is not None]
    failures = [e for e in (error_a, error_b) if e is not None]
    assert len(successes) == 1, "exactly one distinct writer must win the race, never zero or both"
    assert len(failures) == 1
    assert isinstance(failures[0], AtomicVisibilityError)
    assert "revision conflict" in str(failures[0])
    assert successes[0]["to_revision"] == 1
    assert oracle.assert_atomic_visibility() == (1, 1, 1, 1)


def test_lock_contention_is_observed_on_the_wire_during_the_race(
    oracle: AtomicCommitOracle, postgres_dsn: str
):
    command_a = make_command(
        command_id="urn:ocor:command:backend-concurrency:lock-a",
        idempotency_key="backend-concurrency-lock-key-a",
        expected_revision=0,
        canonical_delta={"status": "LOCK_PROBE_A"},
    )
    command_b = make_command(
        command_id="urn:ocor:command:backend-concurrency:lock-b",
        idempotency_key="backend-concurrency-lock-key-b",
        expected_revision=0,
        canonical_delta={"status": "LOCK_PROBE_B"},
    )
    observed: list[bool] = []

    def observer() -> None:
        observed.append(
            observe_lock_contention(postgres_dsn, lock_key_for(SCOPE), deadline_seconds=5.0)
        )

    observer_thread = threading.Thread(target=observer)
    observer_thread.start()
    race_distinct_commands(oracle, command_a, command_b)
    observer_thread.join(timeout=10)

    assert observed and observed[0] is True, (
        "an independent connection never observed the real advisory lock held by another "
        "session; the race outcome alone does not prove genuine mutual exclusion"
    )
    assert oracle.assert_atomic_visibility() == (1, 1, 1, 1)


def test_concurrent_reader_never_observes_an_invalid_revision_during_a_race(
    oracle: AtomicCommitOracle, postgres_dsn: str
):
    command_a = make_command(
        command_id="urn:ocor:command:backend-concurrency:iso-a",
        idempotency_key="backend-concurrency-iso-key-a",
        expected_revision=0,
        canonical_delta={"status": "ISOLATION_PROBE_A"},
    )
    command_b = make_command(
        command_id="urn:ocor:command:backend-concurrency:iso-b",
        idempotency_key="backend-concurrency-iso-key-b",
        expected_revision=0,
        canonical_delta={"status": "ISOLATION_PROBE_B"},
    )
    barrier = threading.Barrier(2)
    samples: list[int | None] = []
    reader_thread = threading.Thread(
        target=sample_revision_during,
        args=(postgres_dsn, SCOPE, barrier, samples),
        kwargs={"duration_seconds": 2.0},
    )
    reader_thread.start()

    def race_after_barrier() -> None:
        barrier.wait(timeout=5)
        race_distinct_commands(oracle, command_a, command_b)

    race_thread = threading.Thread(target=race_after_barrier)
    race_thread.start()
    race_thread.join(timeout=10)
    reader_thread.join(timeout=10)

    assert samples, "the concurrent reader never sampled anything; the probe is unsound"
    assert set(samples) <= {None, 0, 1}, (
        f"a concurrent reader observed a revision outside the valid {{None, 0, 1}} boundary "
        f"values during the race, which would mean a dirty read leaked an uncommitted or "
        f"torn write from another session: {sorted(v for v in set(samples) if v not in (None, 0, 1))}"
    )
    assert oracle.assert_atomic_visibility() == (1, 1, 1, 1)


def test_real_concurrent_crash_during_a_live_race_leaves_zero_partial_visibility(
    oracle: AtomicCommitOracle, postgres_dsn: str
):
    crashing_command = make_command(
        command_id="urn:ocor:command:backend-concurrency:crash",
        idempotency_key="backend-concurrency-crash-key",
        expected_revision=0,
        canonical_delta={"status": "CRASHING_WRITER"},
    )
    survivor_command = make_command(
        command_id="urn:ocor:command:backend-concurrency:survivor",
        idempotency_key="backend-concurrency-survivor-key",
        expected_revision=0,
        canonical_delta={"status": "SURVIVING_WRITER"},
    )
    outcomes: dict[str, object] = {}

    def run_crash() -> None:
        outcomes["crash_returncode"] = crash(crashing_command, CrashStage.AFTER_AGGREGATE_STAGE)

    crash_thread = threading.Thread(target=run_crash)
    crash_thread.start()

    # Deterministic synchronization instead of a timing guess: block the main
    # thread on the same real advisory lock used by commit() until an
    # independent probe observes it held by the crashing subprocess. Only
    # then release the survivor, so its own lock acquisition provably
    # overlaps the crashing writer's still-open, uncommitted transaction
    # rather than racing it from a cold start (where either side could win
    # the lock first, which would only re-exercise the distinct-writer race
    # already covered above).
    contended = observe_lock_contention(postgres_dsn, lock_key_for(SCOPE), deadline_seconds=5.0)
    assert contended, (
        "never observed the crashing subprocess hold the advisory lock; the synchronization "
        "primitive itself is unsound, so the crash could not be proven concurrent"
    )

    def run_survivor() -> None:
        try:
            outcomes["survivor_receipt"] = oracle.commit(survivor_command)
        except BaseException as error:  # noqa: BLE001 -- classified below
            outcomes["survivor_error"] = error

    survivor_thread = threading.Thread(target=run_survivor)
    survivor_thread.start()
    crash_thread.join(timeout=10)
    survivor_thread.join(timeout=10)

    assert outcomes.get("crash_returncode") == 86, "the crash worker did not crash as instructed"
    receipt = outcomes.get("survivor_receipt")
    assert receipt is not None, (
        f"the concurrent survivor never committed successfully: {outcomes.get('survivor_error')!r}"
    )
    assert receipt["to_revision"] == 1
    assert oracle.assert_atomic_visibility() == (1, 1, 1, 1), (
        "a real concurrent process crash left partial visibility behind even though the "
        "surviving writer committed successfully"
    )

    continuation = make_command(
        command_id="urn:ocor:command:backend-concurrency:continuation",
        idempotency_key="backend-concurrency-continuation-key",
        expected_revision=1,
        canonical_delta={"status": "RECONCILED_CONTINUATION"},
    )
    continued = oracle.commit(continuation)
    assert continued["from_revision"] == 1
    assert continued["to_revision"] == 2
    assert oracle.assert_atomic_visibility() == (1, 2, 2, 2), (
        "the reconciled ledger did not accept further correct progress after the "
        "concurrent crash"
    )


def test_phantom_receipt_anomaly_falsifies_the_reconciliation_oracle(
    oracle: AtomicCommitOracle,
):
    with oracle.connect() as connection:
        connection.execute(
            """INSERT INTO spike_c3_idempotency
                   (tenant_id, aggregate_type, aggregate_ref, idempotency_key,
                    command_digest, receipt)
               VALUES (%s, %s, %s, %s, %s, %s::jsonb)""",
            (
                *SCOPE,
                "phantom-key",
                DIGEST_A,
                json.dumps({"commit_id": "urn:ocor:commit:sha256:" + "0" * 64}),
            ),
        )
    with pytest.raises(AtomicVisibilityError, match="phantom_receipt"):
        oracle.assert_atomic_visibility()
