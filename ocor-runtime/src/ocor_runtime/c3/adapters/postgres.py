"""Direct PostgreSQL client adapter for the retained C3 canonical commit
slice.

Every ``psycopg`` reference is confined to this module (AFF-002/AFF-006,
``OCOR_LANGUAGE_POLICY.md`` row 8: direct backend clients are restricted
to an ``adapters/`` subtree). This adapter exposes only plain,
psycopg-free Python types (dataclasses, dicts, primitives) to its caller
(``ocor_runtime.c3.service``), which never imports ``psycopg`` itself.

The real-concurrency locking/atomicity technique (an advisory-lock-guarded
transaction) matches what the sealed spikes already proved for real
(``spikes.c3_atomicity.oracle``, OCOR-DEV-0015; ``spikes.c3_backend``,
OCOR-DEV-0016), reimplemented here against the sealed C3 ports' own field
names rather than the spikes' ad-hoc schema.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json

from ...kernel.canonical import canonical_digest

SCHEMA = """
CREATE TABLE IF NOT EXISTS c3_aggregate (
    tenant_id TEXT NOT NULL,
    aggregate_type TEXT NOT NULL,
    aggregate_ref TEXT NOT NULL,
    revision BIGINT NOT NULL CHECK (revision >= 0),
    state JSONB NOT NULL,
    state_digest TEXT NOT NULL,
    commit_id TEXT NOT NULL,
    PRIMARY KEY (tenant_id, aggregate_type, aggregate_ref)
);
CREATE TABLE IF NOT EXISTS c3_commit (
    commit_id TEXT PRIMARY KEY,
    command_id TEXT NOT NULL,
    command_digest TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    aggregate_type TEXT NOT NULL,
    aggregate_ref TEXT NOT NULL,
    from_revision BIGINT NOT NULL,
    to_revision BIGINT NOT NULL CHECK (to_revision = from_revision + 1),
    state_digest TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    decision_ref TEXT NOT NULL,
    authority_ref TEXT NOT NULL,
    evidence_refs JSONB NOT NULL,
    governed_context_digest TEXT NOT NULL,
    gate_package_digest TEXT NOT NULL,
    outbox_event_id TEXT NOT NULL,
    outbox_payload_digest TEXT NOT NULL,
    branch TEXT NOT NULL CHECK (branch = 'main'),
    committed_at TIMESTAMPTZ NOT NULL,
    UNIQUE (tenant_id, aggregate_type, aggregate_ref, to_revision)
);
CREATE TABLE IF NOT EXISTS c3_idempotency (
    tenant_id TEXT NOT NULL,
    aggregate_type TEXT NOT NULL,
    aggregate_ref TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    command_digest TEXT NOT NULL,
    commit_id TEXT NOT NULL REFERENCES c3_commit(commit_id),
    PRIMARY KEY (tenant_id, aggregate_type, aggregate_ref, idempotency_key)
);
CREATE TABLE IF NOT EXISTS c3_outbox (
    event_id TEXT PRIMARY KEY,
    commit_id TEXT NOT NULL UNIQUE REFERENCES c3_commit(commit_id),
    aggregate_ref TEXT NOT NULL,
    aggregate_revision BIGINT NOT NULL,
    payload JSONB NOT NULL,
    payload_digest TEXT NOT NULL,
    branch TEXT NOT NULL CHECK (branch = 'main'),
    occurred_at TIMESTAMPTZ NOT NULL,
    acknowledged_at TIMESTAMPTZ
);
"""

TABLES = ("c3_outbox", "c3_idempotency", "c3_commit", "c3_aggregate")


class CrashStage(StrEnum):
    AFTER_AGGREGATE_UPSERT = "AFTER_AGGREGATE_UPSERT"
    AFTER_COMMIT_INSERT = "AFTER_COMMIT_INSERT"
    AFTER_IDEMPOTENCY_INSERT = "AFTER_IDEMPOTENCY_INSERT"
    AFTER_OUTBOX_INSERT = "AFTER_OUTBOX_INSERT"
    AFTER_COMMIT_BEFORE_ACK = "AFTER_COMMIT_BEFORE_ACK"


class PostgresAdapterError(RuntimeError):
    """Stable, bounded adapter failure; the caller translates
    ``reason_code`` into the sealed ``C3Error``."""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {message}")


@dataclass(frozen=True, slots=True)
class CommitOutcome:
    commit_id: str
    from_revision: int
    to_revision: int
    state_digest: str
    outbox_event_id: str
    outbox_payload_digest: str
    committed_at: datetime
    replayed: bool


@dataclass(frozen=True, slots=True)
class SnapshotRow:
    revision: int
    state: dict[str, Any]
    state_digest: str
    commit_id: str


@dataclass(frozen=True, slots=True)
class OutboxRow:
    event_id: str
    commit_id: str
    aggregate_ref: str
    aggregate_revision: int
    payload: dict[str, Any]
    payload_digest: str
    branch: str
    occurred_at: datetime


def _merge_delta(current: Mapping[str, Any], delta: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(current)
    merged.update(delta)
    return merged


class PostgresC3Adapter:
    """The only module in this component that imports ``psycopg``."""

    def __init__(self, dsn: str) -> None:
        if not dsn:
            raise ValueError("a PostgreSQL DSN is required")
        self._dsn = dsn

    def initialize(self) -> None:
        with psycopg.connect(self._dsn) as connection:
            connection.execute(SCHEMA)

    def reset(self) -> None:
        with psycopg.connect(self._dsn) as connection:
            connection.execute("TRUNCATE " + ", ".join(TABLES))

    @staticmethod
    def _crash(selected: CrashStage | None, target: CrashStage) -> None:
        if selected is target:
            os._exit(86)

    def commit_transaction(
        self,
        *,
        tenant_id: str,
        aggregate_type: str,
        aggregate_ref: str,
        idempotency_key: str,
        command_id: str,
        command_digest: str,
        expected_revision: int,
        canonical_delta: Mapping[str, Any],
        decision_ref: str,
        authority_ref: str,
        evidence_refs: Sequence[str],
        governed_context_digest: str,
        gate_package_digest: str,
        branch: str,
        crash_after: CrashStage | None = None,
    ) -> CommitOutcome:
        connection = psycopg.connect(self._dsn, row_factory=dict_row)
        try:
            with connection.transaction():
                lock_key = "\x1f".join((tenant_id, aggregate_type, aggregate_ref))
                connection.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (lock_key,))

                existing = connection.execute(
                    """SELECT c.* FROM c3_idempotency i JOIN c3_commit c ON c.commit_id = i.commit_id
                       WHERE i.tenant_id=%s AND i.aggregate_type=%s AND i.aggregate_ref=%s
                         AND i.idempotency_key=%s""",
                    (tenant_id, aggregate_type, aggregate_ref, idempotency_key),
                ).fetchone()
                if existing is not None:
                    if existing["command_digest"] != command_digest:
                        raise PostgresAdapterError(
                            "IDEMPOTENCY_CONFLICT",
                            "idempotency key or scope was rebound to different command content",
                        )
                    return CommitOutcome(
                        commit_id=existing["commit_id"],
                        from_revision=int(existing["from_revision"]),
                        to_revision=int(existing["to_revision"]),
                        state_digest=existing["state_digest"],
                        outbox_event_id=existing["outbox_event_id"],
                        outbox_payload_digest=existing["outbox_payload_digest"],
                        committed_at=existing["committed_at"],
                        replayed=True,
                    )

                current = connection.execute(
                    """SELECT revision, state FROM c3_aggregate
                       WHERE tenant_id=%s AND aggregate_type=%s AND aggregate_ref=%s
                       FOR UPDATE""",
                    (tenant_id, aggregate_type, aggregate_ref),
                ).fetchone()
                revision = int(current["revision"]) if current is not None else 0
                if expected_revision != revision:
                    raise PostgresAdapterError(
                        "REVISION_CONFLICT", f"expected revision {expected_revision}, found {revision}"
                    )
                state = dict(current["state"]) if current is not None else {}
                new_state = _merge_delta(state, canonical_delta)
                new_state_digest = canonical_digest(new_state)
                to_revision = revision + 1

                commit_id = "urn:ocor:commit:sha256:" + hashlib.sha256(
                    f"{command_digest}:{to_revision}".encode()
                ).hexdigest()
                outbox_event_id = "urn:ocor:event:sha256:" + hashlib.sha256(
                    f"{commit_id}:outbox".encode()
                ).hexdigest()
                outbox_payload = {
                    "commit_id": commit_id,
                    "aggregate_ref": aggregate_ref,
                    "to_revision": to_revision,
                    "state_digest": new_state_digest,
                }
                outbox_payload_digest = canonical_digest(outbox_payload)
                committed_at = datetime.now(UTC)

                connection.execute(
                    """INSERT INTO c3_aggregate
                           (tenant_id, aggregate_type, aggregate_ref, revision, state, state_digest, commit_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (tenant_id, aggregate_type, aggregate_ref) DO UPDATE SET
                           revision=EXCLUDED.revision, state=EXCLUDED.state,
                           state_digest=EXCLUDED.state_digest, commit_id=EXCLUDED.commit_id""",
                    (
                        tenant_id,
                        aggregate_type,
                        aggregate_ref,
                        to_revision,
                        Json(new_state),
                        new_state_digest,
                        commit_id,
                    ),
                )
                self._crash(crash_after, CrashStage.AFTER_AGGREGATE_UPSERT)

                connection.execute(
                    """INSERT INTO c3_commit
                           (commit_id, command_id, command_digest, tenant_id, aggregate_type, aggregate_ref,
                            from_revision, to_revision, state_digest, idempotency_key, decision_ref,
                            authority_ref, evidence_refs, governed_context_digest, gate_package_digest,
                            outbox_event_id, outbox_payload_digest, branch, committed_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        commit_id,
                        command_id,
                        command_digest,
                        tenant_id,
                        aggregate_type,
                        aggregate_ref,
                        revision,
                        to_revision,
                        new_state_digest,
                        idempotency_key,
                        decision_ref,
                        authority_ref,
                        Json(list(evidence_refs)),
                        governed_context_digest,
                        gate_package_digest,
                        outbox_event_id,
                        outbox_payload_digest,
                        branch,
                        committed_at,
                    ),
                )
                self._crash(crash_after, CrashStage.AFTER_COMMIT_INSERT)

                connection.execute(
                    """INSERT INTO c3_idempotency
                           (tenant_id, aggregate_type, aggregate_ref, idempotency_key, command_digest, commit_id)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (tenant_id, aggregate_type, aggregate_ref, idempotency_key, command_digest, commit_id),
                )
                self._crash(crash_after, CrashStage.AFTER_IDEMPOTENCY_INSERT)

                connection.execute(
                    """INSERT INTO c3_outbox
                           (event_id, commit_id, aggregate_ref, aggregate_revision, payload, payload_digest,
                            branch, occurred_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        outbox_event_id,
                        commit_id,
                        aggregate_ref,
                        to_revision,
                        Json(outbox_payload),
                        outbox_payload_digest,
                        branch,
                        committed_at,
                    ),
                )
                self._crash(crash_after, CrashStage.AFTER_OUTBOX_INSERT)
            self._crash(crash_after, CrashStage.AFTER_COMMIT_BEFORE_ACK)
            return CommitOutcome(
                commit_id=commit_id,
                from_revision=revision,
                to_revision=to_revision,
                state_digest=new_state_digest,
                outbox_event_id=outbox_event_id,
                outbox_payload_digest=outbox_payload_digest,
                committed_at=committed_at,
                replayed=False,
            )
        finally:
            connection.close()

    def read_snapshot(self, tenant_id: str, aggregate_type: str, aggregate_ref: str) -> SnapshotRow | None:
        with psycopg.connect(self._dsn, row_factory=dict_row) as connection:
            row = connection.execute(
                """SELECT revision, state, state_digest, commit_id FROM c3_aggregate
                   WHERE tenant_id=%s AND aggregate_type=%s AND aggregate_ref=%s""",
                (tenant_id, aggregate_type, aggregate_ref),
            ).fetchone()
        if row is None:
            return None
        return SnapshotRow(
            revision=int(row["revision"]),
            state=dict(row["state"]),
            state_digest=row["state_digest"],
            commit_id=row["commit_id"],
        )

    def current_revision(self, tenant_id: str, aggregate_type: str, aggregate_ref: str) -> int:
        with psycopg.connect(self._dsn, row_factory=dict_row) as connection:
            row = connection.execute(
                """SELECT revision FROM c3_aggregate
                   WHERE tenant_id=%s AND aggregate_type=%s AND aggregate_ref=%s""",
                (tenant_id, aggregate_type, aggregate_ref),
            ).fetchone()
        return int(row["revision"]) if row is not None else 0

    def claim_outbox_batch(self, *, limit: int) -> tuple[OutboxRow, ...]:
        with psycopg.connect(self._dsn, row_factory=dict_row) as connection:
            rows = connection.execute(
                """SELECT event_id, commit_id, aggregate_ref, aggregate_revision, payload, payload_digest,
                          branch, occurred_at
                   FROM c3_outbox WHERE acknowledged_at IS NULL ORDER BY occurred_at LIMIT %s""",
                (limit,),
            ).fetchall()
        return tuple(
            OutboxRow(
                event_id=row["event_id"],
                commit_id=row["commit_id"],
                aggregate_ref=row["aggregate_ref"],
                aggregate_revision=int(row["aggregate_revision"]),
                payload=dict(row["payload"]),
                payload_digest=row["payload_digest"],
                branch=row["branch"],
                occurred_at=row["occurred_at"],
            )
            for row in rows
        )

    def acknowledge_outbox(self, event_id: str, *, acknowledged_at: datetime) -> None:
        with psycopg.connect(self._dsn) as connection:
            connection.execute(
                "UPDATE c3_outbox SET acknowledged_at=%s WHERE event_id=%s", (acknowledged_at, event_id)
            )

    def reconcile(self, *, limit: int) -> int:
        """Real defense-in-depth repair pass: every commit row must have a
        matching idempotency row and a matching outbox row. Under normal
        operation this is always true by transactional atomicity -- a
        crash mid-commit rolls the whole transaction back, leaving nothing
        partial to reconcile. This exists to recover from a genuine crash
        fixture (a simulated corruption: a derived row deleted after the
        fact) by re-deriving the missing row from the commit row's own
        denormalized fields, never by fabricating new commit content."""
        repaired = 0
        with psycopg.connect(self._dsn, row_factory=dict_row) as connection:
            orphaned_idempotency = connection.execute(
                """SELECT c.* FROM c3_commit c
                   LEFT JOIN c3_idempotency i ON i.commit_id = c.commit_id
                   WHERE i.commit_id IS NULL LIMIT %s""",
                (limit,),
            ).fetchall()
            for row in orphaned_idempotency:
                connection.execute(
                    """INSERT INTO c3_idempotency
                           (tenant_id, aggregate_type, aggregate_ref, idempotency_key, command_digest, commit_id)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       ON CONFLICT DO NOTHING""",
                    (
                        row["tenant_id"],
                        row["aggregate_type"],
                        row["aggregate_ref"],
                        row["idempotency_key"],
                        row["command_digest"],
                        row["commit_id"],
                    ),
                )
                repaired += 1

            orphaned_outbox = connection.execute(
                """SELECT c.* FROM c3_commit c
                   LEFT JOIN c3_outbox o ON o.commit_id = c.commit_id
                   WHERE o.commit_id IS NULL LIMIT %s""",
                (limit,),
            ).fetchall()
            for row in orphaned_outbox:
                payload = {
                    "commit_id": row["commit_id"],
                    "aggregate_ref": row["aggregate_ref"],
                    "to_revision": int(row["to_revision"]),
                    "state_digest": row["state_digest"],
                }
                connection.execute(
                    """INSERT INTO c3_outbox
                           (event_id, commit_id, aggregate_ref, aggregate_revision, payload, payload_digest,
                            branch, occurred_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT DO NOTHING""",
                    (
                        row["outbox_event_id"],
                        row["commit_id"],
                        row["aggregate_ref"],
                        int(row["to_revision"]),
                        Json(payload),
                        row["outbox_payload_digest"],
                        row["branch"],
                        row["committed_at"],
                    ),
                )
                repaired += 1
        return repaired
