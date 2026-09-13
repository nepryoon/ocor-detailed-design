"""Real-concurrency locking, isolation and reconciliation oracle for the
selected C3 backend (PostgreSQL).

This module deliberately reuses the atomic-commit contract already sealed
in ``spikes.c3_atomicity.oracle`` (OCOR-DEV-0015) rather than
re-implementing commit semantics: OCOR-DEV-0016 asks whether the *same
selected backend* also meets locking, isolation and reconciliation oracles
under real concurrency, not whether a different implementation could. This
module only adds the concurrent-race harness and the independent,
out-of-band probes needed to observe locking and isolation properties
directly against the real running database, rather than merely inferring
them from a single writer's outcome.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Mapping
from typing import Any

import psycopg

from spikes.c3_atomicity.oracle import PostgreSQLAtomicCommitOracle

RaceOutcome = tuple[dict[str, Any] | None, BaseException | None]


def race_distinct_commands(
    oracle: PostgreSQLAtomicCommitOracle,
    command_a: Mapping[str, Any],
    command_b: Mapping[str, Any],
) -> tuple[RaceOutcome, RaceOutcome]:
    """Commit two DISTINCT commands for the same aggregate and the same
    ``expected_revision``, released to run at the same instant via a
    barrier, each on its own real PostgreSQL connection (``oracle.commit``
    opens and closes its own connection per call, so concurrent threads
    never share a connection). Returns ``(outcome_a, outcome_b)``, where
    each outcome is ``(receipt, None)`` on success or ``(None, error)``.
    """
    barrier = threading.Barrier(2)
    outcomes: dict[str, RaceOutcome] = {}

    def attempt(key: str, command: Mapping[str, Any]) -> None:
        barrier.wait(timeout=5)
        try:
            outcomes[key] = (oracle.commit(command), None)
        except BaseException as error:  # noqa: BLE001 -- classified by the caller
            outcomes[key] = (None, error)

    threads = [
        threading.Thread(target=attempt, args=("a", command_a)),
        threading.Thread(target=attempt, args=("b", command_b)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    return outcomes["a"], outcomes["b"]


def lock_key_for(scope: tuple[str, str, str]) -> str:
    """The same advisory-lock key derivation used by the sealed oracle's
    ``commit`` (``\\x1f``-joined scope), so an independent probe contends
    for the identical lock, not a look-alike."""
    return "\x1f".join(scope)


def observe_lock_contention(dsn: str, lock_key: str, *, deadline_seconds: float) -> bool:
    """Poll ``pg_try_advisory_xact_lock`` for ``lock_key`` from an
    independent connection until either it is observed held by another
    session, or ``deadline_seconds`` elapses. Returns ``True`` the first
    time contention is observed. Intended to run concurrently with a real
    race so the caller can assert genuine mutual exclusion was witnessed on
    the wire, not merely inferred from the race's outcome.
    """
    deadline = time.monotonic() + deadline_seconds
    with psycopg.connect(dsn, autocommit=True) as connection:
        while time.monotonic() < deadline:
            with connection.transaction():
                row = connection.execute(
                    "SELECT pg_try_advisory_xact_lock(hashtextextended(%s, 0))",
                    (lock_key,),
                ).fetchone()
            assert row is not None
            if not row[0]:
                return True
            time.sleep(0.0002)
    return False


def sample_revision_during(
    dsn: str,
    scope: tuple[str, str, str],
    barrier: threading.Barrier,
    samples: list[int | None],
    *,
    duration_seconds: float,
) -> None:
    """Continuously read the committed revision for ``scope`` from an
    independent connection while a concurrent writer transaction is in
    flight, appending every observed value to ``samples``. Used to prove
    no dirty read is ever observed (a real isolation property of the
    selected backend under READ COMMITTED, its default), rather than
    assumed by construction.
    """
    with psycopg.connect(dsn, autocommit=True) as connection:
        barrier.wait(timeout=5)
        deadline = time.monotonic() + duration_seconds
        while time.monotonic() < deadline:
            row = connection.execute(
                """SELECT revision FROM spike_c3_aggregate
                   WHERE tenant_id=%s AND aggregate_type=%s AND aggregate_ref=%s""",
                scope,
            ).fetchone()
            samples.append(int(row[0]) if row is not None else None)
