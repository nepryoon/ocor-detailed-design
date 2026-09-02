"""PostgreSQL process-crash oracle for the C3 atomic commit invariant."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from enum import StrEnum
from typing import Any

import psycopg
from psycopg.rows import dict_row


class AtomicVisibilityError(RuntimeError):
    pass


class IdempotencyConflict(RuntimeError):
    pass


class CrashStage(StrEnum):
    BEFORE_TRANSACTION = "before-transaction"
    AFTER_TRANSACTION_BEGIN = "after-transaction-begin"
    AFTER_AGGREGATE_STAGE = "after-aggregate-stage"
    AFTER_OUTBOX_STAGE = "after-outbox-stage"
    AFTER_COMMIT_BEFORE_ACK = "after-commit-before-ack"

    @classmethod
    def precommit(cls) -> tuple[CrashStage, ...]:
        return (
            cls.BEFORE_TRANSACTION,
            cls.AFTER_TRANSACTION_BEGIN,
            cls.AFTER_AGGREGATE_STAGE,
            cls.AFTER_OUTBOX_STAGE,
        )


SCHEMA = """
CREATE TABLE IF NOT EXISTS spike_c3_aggregate (
    tenant_id TEXT NOT NULL,
    aggregate_type TEXT NOT NULL,
    aggregate_ref TEXT NOT NULL,
    revision BIGINT NOT NULL CHECK (revision > 0),
    state_digest TEXT NOT NULL,
    PRIMARY KEY (tenant_id, aggregate_type, aggregate_ref)
);
CREATE TABLE IF NOT EXISTS spike_c3_commit (
    commit_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    aggregate_type TEXT NOT NULL,
    aggregate_ref TEXT NOT NULL,
    from_revision BIGINT NOT NULL,
    to_revision BIGINT NOT NULL CHECK (to_revision = from_revision + 1),
    command_digest TEXT NOT NULL,
    state_digest TEXT NOT NULL,
    evidence_digest TEXT NOT NULL,
    governed_context_digest TEXT NOT NULL,
    UNIQUE (tenant_id, aggregate_type, aggregate_ref, to_revision)
);
CREATE TABLE IF NOT EXISTS spike_c3_idempotency (
    tenant_id TEXT NOT NULL,
    aggregate_type TEXT NOT NULL,
    aggregate_ref TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    command_digest TEXT NOT NULL,
    receipt JSONB NOT NULL,
    PRIMARY KEY (tenant_id, aggregate_type, aggregate_ref, idempotency_key)
);
CREATE TABLE IF NOT EXISTS spike_c3_outbox (
    event_id TEXT PRIMARY KEY,
    commit_id TEXT NOT NULL UNIQUE REFERENCES spike_c3_commit(commit_id),
    branch TEXT NOT NULL CHECK (branch = 'main'),
    payload_digest TEXT NOT NULL
);
"""

TABLES = (
    "spike_c3_aggregate",
    "spike_c3_commit",
    "spike_c3_idempotency",
    "spike_c3_outbox",
)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _digest(value: object) -> str:
    return "urn:sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _required(value: Mapping[str, Any], field: str) -> Any:
    if field not in value:
        raise ValueError(f"missing command field: {field}")
    return value[field]


class PostgreSQLAtomicCommitOracle:
    """Minimal retained adapter/fault harness for SPIKE-01 only."""

    def __init__(self, dsn: str) -> None:
        if not dsn:
            raise ValueError("a PostgreSQL DSN is required")
        self._dsn = dsn

    def connect(self) -> psycopg.Connection[Any]:
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.execute(SCHEMA)

    def reset(self) -> None:
        with self.connect() as connection:
            connection.execute(
                "TRUNCATE spike_c3_outbox, spike_c3_idempotency, "
                "spike_c3_commit, spike_c3_aggregate"
            )

    @staticmethod
    def _crash(selected: CrashStage | None, target: CrashStage) -> None:
        if selected is target:
            os._exit(86)

    def commit(
        self, command: Mapping[str, Any], *, crash_stage: CrashStage | None = None
    ) -> dict[str, Any]:
        stage = CrashStage(crash_stage) if crash_stage is not None else None
        self._crash(stage, CrashStage.BEFORE_TRANSACTION)
        context = _required(command, "governed_context")
        if not isinstance(context, Mapping):
            raise TypeError("governed_context must be an object")
        tenant_id = str(_required(context, "tenant_id"))
        aggregate_type = str(_required(command, "aggregate_type"))
        aggregate_ref = str(_required(command, "aggregate_ref"))
        expected_revision = int(_required(command, "expected_revision"))
        idempotency_key = str(_required(command, "idempotency_key"))
        if _required(command, "branch") != "main":
            raise ValueError("canonical commit branch must be main")
        command_digest = _digest(command)
        state_digest = _digest(_required(command, "canonical_delta"))
        evidence_digest = _digest(_required(command, "evidence_refs"))
        scope = (tenant_id, aggregate_type, aggregate_ref)

        connection = self.connect()
        try:
            with connection.transaction():
                self._crash(stage, CrashStage.AFTER_TRANSACTION_BEGIN)
                lock_key = "\x1f".join(scope)
                connection.execute(
                    "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (lock_key,)
                )
                replay = connection.execute(
                    """SELECT command_digest, receipt
                       FROM spike_c3_idempotency
                       WHERE tenant_id=%s AND aggregate_type=%s AND aggregate_ref=%s
                         AND idempotency_key=%s""",
                    (*scope, idempotency_key),
                ).fetchone()
                if replay is not None:
                    if replay["command_digest"] != command_digest:
                        raise IdempotencyConflict("idempotency scope was rebound")
                    return dict(replay["receipt"])

                current = connection.execute(
                    """SELECT revision FROM spike_c3_aggregate
                       WHERE tenant_id=%s AND aggregate_type=%s AND aggregate_ref=%s
                       FOR UPDATE""",
                    scope,
                ).fetchone()
                revision = int(current["revision"]) if current is not None else 0
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
                    {
                        "commit_id": commit_id,
                        "revision": to_revision,
                        "state_digest": state_digest,
                    }
                )
                receipt = {
                    "aggregate_ref": aggregate_ref,
                    "command_digest": command_digest,
                    "commit_id": commit_id,
                    "evidence_digest": evidence_digest,
                    "from_revision": revision,
                    "governed_context_digest": _required(
                        command, "governed_context_digest"
                    ),
                    "idempotency_key": idempotency_key,
                    "outbox_event_id": event_id,
                    "outbox_payload_digest": payload_digest,
                    "state_digest": state_digest,
                    "to_revision": to_revision,
                }
                connection.execute(
                    """INSERT INTO spike_c3_aggregate
                           (tenant_id, aggregate_type, aggregate_ref, revision, state_digest)
                       VALUES (%s, %s, %s, %s, %s)
                       ON CONFLICT (tenant_id, aggregate_type, aggregate_ref) DO UPDATE SET
                           revision=EXCLUDED.revision, state_digest=EXCLUDED.state_digest""",
                    (*scope, to_revision, state_digest),
                )
                self._crash(stage, CrashStage.AFTER_AGGREGATE_STAGE)
                connection.execute(
                    """INSERT INTO spike_c3_commit
                           (commit_id, tenant_id, aggregate_type, aggregate_ref,
                            from_revision, to_revision, command_digest, state_digest,
                            evidence_digest, governed_context_digest)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        commit_id,
                        *scope,
                        revision,
                        to_revision,
                        command_digest,
                        state_digest,
                        evidence_digest,
                        _required(command, "governed_context_digest"),
                    ),
                )
                connection.execute(
                    """INSERT INTO spike_c3_idempotency
                           (tenant_id, aggregate_type, aggregate_ref, idempotency_key,
                            command_digest, receipt)
                       VALUES (%s, %s, %s, %s, %s, %s::jsonb)""",
                    (
                        *scope,
                        idempotency_key,
                        command_digest,
                        _canonical_bytes(receipt).decode("utf-8"),
                    ),
                )
                connection.execute(
                    """INSERT INTO spike_c3_outbox
                           (event_id, commit_id, branch, payload_digest)
                       VALUES (%s, %s, 'main', %s)""",
                    (event_id, commit_id, payload_digest),
                )
                self._crash(stage, CrashStage.AFTER_OUTBOX_STAGE)
            self._crash(stage, CrashStage.AFTER_COMMIT_BEFORE_ACK)
            return receipt
        finally:
            connection.close()

    def counts(self) -> tuple[int, int, int, int]:
        with self.connect() as connection:
            return tuple(
                int(
                    connection.execute(
                        "SELECT COUNT(*) FROM " + table
                    ).fetchone()["count"]
                )
                for table in TABLES
            )

    def assert_atomic_visibility(self) -> tuple[int, int, int, int]:
        with self.connect() as connection:
            anomaly = connection.execute(
                """SELECT
                     (SELECT count(*) FROM spike_c3_aggregate a
                       WHERE NOT EXISTS (
                         SELECT 1 FROM spike_c3_commit c
                         WHERE (c.tenant_id,c.aggregate_type,c.aggregate_ref)=
                               (a.tenant_id,a.aggregate_type,a.aggregate_ref))) AS orphan_state,
                     (SELECT count(*) FROM spike_c3_commit c
                       LEFT JOIN spike_c3_outbox o ON o.commit_id=c.commit_id
                       LEFT JOIN spike_c3_idempotency i
                         ON (i.receipt->>'commit_id')=c.commit_id
                       WHERE o.commit_id IS NULL OR i.command_digest IS NULL) AS incomplete_commit,
                     (SELECT count(*) FROM spike_c3_idempotency i
                       LEFT JOIN spike_c3_commit c
                         ON c.commit_id=(i.receipt->>'commit_id')
                       WHERE c.commit_id IS NULL) AS phantom_receipt,
                     (SELECT count(*) FROM spike_c3_aggregate a
                       WHERE a.revision <> (
                         SELECT max(c.to_revision) FROM spike_c3_commit c
                         WHERE (c.tenant_id,c.aggregate_type,c.aggregate_ref)=
                               (a.tenant_id,a.aggregate_type,a.aggregate_ref))) AS revision_drift"""
            ).fetchone()
        assert anomaly is not None
        problems = {key: int(value) for key, value in anomaly.items() if int(value)}
        if problems:
            raise AtomicVisibilityError(f"partial durable visibility: {problems}")
        return self.counts()


AtomicCommitOracle = PostgreSQLAtomicCommitOracle
