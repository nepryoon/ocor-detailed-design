"""Process-crash oracle for the C3 revision/state/idempotency/outbox invariant.

SQLite is used as a real file-backed transactional reference, not as the selected
C3 backend. OCOR-DEV-0016 separately qualifies the selected backend under real
concurrency. Abrupt worker exit exercises journal recovery rather than an in-memory
mock or exception-only rollback.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from typing import Any


class AtomicVisibilityError(RuntimeError):
    pass


class IdempotencyConflict(RuntimeError):
    pass


class CrashStage(StrEnum):
    BEFORE_TRANSACTION = "before-transaction"
    AFTER_BEGIN = "after-begin"
    AFTER_STATE = "after-state"
    AFTER_COMMIT_RECORD = "after-commit-record"
    AFTER_IDEMPOTENCY = "after-idempotency"
    AFTER_OUTBOX = "after-outbox"
    AFTER_COMMIT_BEFORE_ACK = "after-commit-before-ack"

    @classmethod
    def precommit(cls) -> tuple[CrashStage, ...]:
        return (
            cls.BEFORE_TRANSACTION,
            cls.AFTER_BEGIN,
            cls.AFTER_STATE,
            cls.AFTER_COMMIT_RECORD,
            cls.AFTER_IDEMPOTENCY,
            cls.AFTER_OUTBOX,
        )


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=FULL;
CREATE TABLE IF NOT EXISTS canonical_aggregate (
    tenant_id TEXT NOT NULL,
    aggregate_type TEXT NOT NULL,
    aggregate_ref TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision > 0),
    state_digest TEXT NOT NULL,
    PRIMARY KEY (tenant_id, aggregate_type, aggregate_ref)
);
CREATE TABLE IF NOT EXISTS canonical_commit (
    commit_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    aggregate_type TEXT NOT NULL,
    aggregate_ref TEXT NOT NULL,
    from_revision INTEGER NOT NULL,
    to_revision INTEGER NOT NULL,
    command_digest TEXT NOT NULL,
    state_digest TEXT NOT NULL,
    evidence_digest TEXT NOT NULL,
    governed_context_digest TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS canonical_idempotency (
    tenant_id TEXT NOT NULL,
    aggregate_type TEXT NOT NULL,
    aggregate_ref TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    command_digest TEXT NOT NULL,
    receipt_json TEXT NOT NULL,
    PRIMARY KEY (tenant_id, aggregate_type, aggregate_ref, idempotency_key)
);
CREATE TABLE IF NOT EXISTS canonical_outbox (
    event_id TEXT PRIMARY KEY,
    commit_id TEXT NOT NULL UNIQUE REFERENCES canonical_commit(commit_id),
    branch TEXT NOT NULL CHECK (branch = 'main'),
    payload_digest TEXT NOT NULL
);
"""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _digest(value: object) -> str:
    return "urn:sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _required(command: Mapping[str, Any], field: str) -> Any:
    if field not in command:
        raise ValueError(f"missing command field: {field}")
    return command[field]


class AtomicCommitOracle:
    def __init__(self, database: str | Path) -> None:
        self.database = Path(database)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=5, isolation_level=None)
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    @staticmethod
    def _crash(selected: CrashStage | None, target: CrashStage) -> None:
        if selected is target:
            os._exit(86)

    def commit(
        self, command: Mapping[str, Any], *, crash_stage: CrashStage | None = None
    ) -> dict[str, Any]:
        stage = CrashStage(crash_stage) if crash_stage is not None else None
        self._crash(stage, CrashStage.BEFORE_TRANSACTION)
        tenant_id = _required(_required(command, "governed_context"), "tenant_id")
        aggregate_type = _required(command, "aggregate_type")
        aggregate_ref = _required(command, "aggregate_ref")
        expected_revision = _required(command, "expected_revision")
        idempotency_key = _required(command, "idempotency_key")
        if _required(command, "branch") != "main":
            raise ValueError("canonical commit branch must be main")
        command_digest = _digest(command)
        state_digest = _digest(_required(command, "canonical_delta"))
        evidence_digest = _digest(_required(command, "evidence_refs"))
        scope = (tenant_id, aggregate_type, aggregate_ref, idempotency_key)

        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._crash(stage, CrashStage.AFTER_BEGIN)
            replay = connection.execute(
                """SELECT command_digest, receipt_json FROM canonical_idempotency
                   WHERE tenant_id=? AND aggregate_type=? AND aggregate_ref=?
                     AND idempotency_key=?""",
                scope,
            ).fetchone()
            if replay is not None:
                if replay[0] != command_digest:
                    raise IdempotencyConflict("idempotency scope was rebound")
                connection.rollback()
                return json.loads(replay[1])

            current = connection.execute(
                """SELECT revision FROM canonical_aggregate
                   WHERE tenant_id=? AND aggregate_type=? AND aggregate_ref=?""",
                scope[:3],
            ).fetchone()
            revision = int(current[0]) if current is not None else 0
            if expected_revision != revision:
                raise AtomicVisibilityError(
                    f"revision conflict: expected {expected_revision}, found {revision}"
                )
            to_revision = revision + 1
            commit_id = "urn:ocor:commit:sha256:" + hashlib.sha256(
                f"{command_digest}:{to_revision}".encode()
            ).hexdigest()
            event_id = "urn:ocor:event:sha256:" + hashlib.sha256(
                f"{commit_id}:outbox".encode()
            ).hexdigest()
            payload_digest = _digest(
                {"commit_id": commit_id, "revision": to_revision, "state_digest": state_digest}
            )
            receipt = {
                "aggregate_ref": aggregate_ref,
                "command_digest": command_digest,
                "commit_id": commit_id,
                "evidence_digest": evidence_digest,
                "from_revision": revision,
                "governed_context_digest": _required(command, "governed_context_digest"),
                "idempotency_key": idempotency_key,
                "outbox_event_id": event_id,
                "outbox_payload_digest": payload_digest,
                "state_digest": state_digest,
                "to_revision": to_revision,
            }
            connection.execute(
                """INSERT INTO canonical_aggregate
                       (tenant_id, aggregate_type, aggregate_ref, revision, state_digest)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT (tenant_id, aggregate_type, aggregate_ref) DO UPDATE SET
                       revision=excluded.revision, state_digest=excluded.state_digest""",
                (*scope[:3], to_revision, state_digest),
            )
            self._crash(stage, CrashStage.AFTER_STATE)
            connection.execute(
                """INSERT INTO canonical_commit
                       (commit_id, tenant_id, aggregate_type, aggregate_ref,
                        from_revision, to_revision, command_digest, state_digest,
                        evidence_digest, governed_context_digest)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    commit_id,
                    *scope[:3],
                    revision,
                    to_revision,
                    command_digest,
                    state_digest,
                    evidence_digest,
                    _required(command, "governed_context_digest"),
                ),
            )
            self._crash(stage, CrashStage.AFTER_COMMIT_RECORD)
            connection.execute(
                """INSERT INTO canonical_idempotency
                       (tenant_id, aggregate_type, aggregate_ref, idempotency_key,
                        command_digest, receipt_json)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (*scope, command_digest, _canonical_bytes(receipt).decode()),
            )
            self._crash(stage, CrashStage.AFTER_IDEMPOTENCY)
            connection.execute(
                """INSERT INTO canonical_outbox
                       (event_id, commit_id, branch, payload_digest)
                   VALUES (?, ?, 'main', ?)""",
                (event_id, commit_id, payload_digest),
            )
            self._crash(stage, CrashStage.AFTER_OUTBOX)
            connection.commit()
            self._crash(stage, CrashStage.AFTER_COMMIT_BEFORE_ACK)
            return receipt
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def counts(self) -> tuple[int, int, int, int]:
        with self.connect() as connection:
            tables = (
                "canonical_aggregate",
                "canonical_commit",
                "canonical_idempotency",
                "canonical_outbox",
            )
            return tuple(
                int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                for table in tables
            )

    def assert_atomic_visibility(self) -> tuple[int, int, int, int]:
        counts = self.counts()
        if len(set(counts)) != 1:
            raise AtomicVisibilityError(f"partial durable visibility: {counts}")
        return counts
