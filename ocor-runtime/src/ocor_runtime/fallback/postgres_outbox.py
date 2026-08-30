"""PostgreSQL transactional-outbox fallback ratified for BA-01.

This adapter is deliberately DB-API shaped so the runtime does not require a
specific PostgreSQL client.  Aggregate state, outbox state and reconciliation
intent are committed by one database transaction.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Protocol

from ..canonical import canonical_sha256
from ..errors import ConcurrencyConflict


POSTGRESQL_DDL = """
CREATE TABLE IF NOT EXISTS ocor_aggregates (
    aggregate_id TEXT PRIMARY KEY,
    version BIGINT NOT NULL CHECK (version > 0),
    document JSONB NOT NULL,
    semantic_digest CHAR(64) NOT NULL,
    writer_id TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    last_transaction_id UUID NOT NULL
);

CREATE TABLE IF NOT EXISTS ocor_outbox (
    event_id UUID PRIMARY KEY,
    transaction_id UUID NOT NULL,
    aggregate_id TEXT NOT NULL,
    aggregate_version BIGINT NOT NULL CHECK (aggregate_version > 0),
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    payload_digest CHAR(64) NOT NULL,
    request_digest CHAR(64) NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    occurred_at TIMESTAMPTZ NOT NULL,
    emitted_at TIMESTAMPTZ,
    UNIQUE (aggregate_id, aggregate_version),
    FOREIGN KEY (aggregate_id) REFERENCES ocor_aggregates(aggregate_id)
        DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE IF NOT EXISTS ocor_reconciliation_queue (
    transaction_id UUID PRIMARY KEY,
    aggregate_id TEXT NOT NULL,
    aggregate_version BIGINT NOT NULL,
    expected_event_id UUID NOT NULL,
    reconciled_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ocor_outbox_pending_idx
    ON ocor_outbox (occurred_at, event_id)
    WHERE emitted_at IS NULL;
""".strip()


class Cursor(Protocol):
    rowcount: int

    def execute(self, operation: str, parameters: tuple[Any, ...] = ()) -> Any: ...

    def fetchone(self) -> Any: ...

    def fetchall(self) -> list[Any]: ...

    def close(self) -> None: ...


class Connection(Protocol):
    def cursor(self) -> Cursor: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


@dataclass(frozen=True, slots=True)
class PostgreSQLWriteReceipt:
    transaction_id: str
    event_id: str
    aggregate_id: str
    aggregate_version: int
    replayed: bool = False


class PostgreSQLTransactionalOutbox:
    """Fallback C3 adapter using one PostgreSQL transaction per mutation."""

    supports_atomic_multi_document_writes = True

    def __init__(self, connection_factory: Callable[[], Connection]) -> None:
        self._connection_factory = connection_factory

    def initialize(self) -> None:
        connection = self._connection_factory()
        cursor = connection.cursor()
        try:
            cursor.execute(POSTGRESQL_DDL)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()

    def write(
        self,
        aggregate_id: str,
        document: dict[str, Any],
        *,
        expected_version: int,
        writer_id: str,
        event_type: str,
        payload: dict[str, Any],
        idempotency_key: str,
        occurred_at: datetime,
    ) -> PostgreSQLWriteReceipt:
        connection = self._connection_factory()
        cursor = connection.cursor()
        request_digest = canonical_sha256(
            {
                "aggregateId": aggregate_id,
                "document": document,
                "eventType": event_type,
                "payload": payload,
            }
        )
        try:
            cursor.execute(
                "SELECT event_id, transaction_id, aggregate_id, aggregate_version, "
                "request_digest "
                "FROM ocor_outbox WHERE idempotency_key = %s",
                (idempotency_key,),
            )
            replay = cursor.fetchone()
            if replay:
                if str(replay[4]) != request_digest:
                    raise ConcurrencyConflict(
                        "idempotency key was reused for a different write request"
                    )
                connection.commit()
                return PostgreSQLWriteReceipt(
                    transaction_id=str(replay[1]),
                    event_id=str(replay[0]),
                    aggregate_id=str(replay[2]),
                    aggregate_version=int(replay[3]),
                    replayed=True,
                )

            cursor.execute(
                "SELECT version FROM ocor_aggregates WHERE aggregate_id = %s FOR UPDATE",
                (aggregate_id,),
            )
            row = cursor.fetchone()
            current_version = int(row[0]) if row else 0
            if current_version != expected_version:
                raise ConcurrencyConflict(
                    f"expected aggregate version {expected_version}, found {current_version}"
                )

            version = current_version + 1
            transaction_id = uuid.uuid4()
            event_id = uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"ocor:{aggregate_id}:{idempotency_key}:{canonical_sha256(document)}",
            )
            document_json = json.dumps(document, separators=(",", ":"), ensure_ascii=False)
            payload_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
            cursor.execute(
                """INSERT INTO ocor_aggregates
                   (aggregate_id, version, document, semantic_digest, writer_id,
                    updated_at, last_transaction_id)
                   VALUES (%s, %s, %s::jsonb, %s, %s, %s, %s)
                   ON CONFLICT (aggregate_id) DO UPDATE SET
                     version = EXCLUDED.version,
                     document = EXCLUDED.document,
                     semantic_digest = EXCLUDED.semantic_digest,
                     writer_id = EXCLUDED.writer_id,
                     updated_at = EXCLUDED.updated_at,
                     last_transaction_id = EXCLUDED.last_transaction_id
                   WHERE ocor_aggregates.version = %s""",
                (
                    aggregate_id,
                    version,
                    document_json,
                    canonical_sha256(document),
                    writer_id,
                    occurred_at,
                    transaction_id,
                    expected_version,
                ),
            )
            cursor.execute(
                """INSERT INTO ocor_outbox
                   (event_id, transaction_id, aggregate_id, aggregate_version,
                    event_type, payload, payload_digest, request_digest,
                    idempotency_key, occurred_at)
                   VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s)""",
                (
                    event_id,
                    transaction_id,
                    aggregate_id,
                    version,
                    event_type,
                    payload_json,
                    canonical_sha256(payload),
                    request_digest,
                    idempotency_key,
                    occurred_at,
                ),
            )
            cursor.execute(
                """INSERT INTO ocor_reconciliation_queue
                   (transaction_id, aggregate_id, aggregate_version, expected_event_id)
                   VALUES (%s, %s, %s, %s)""",
                (transaction_id, aggregate_id, version, event_id),
            )
            connection.commit()
            return PostgreSQLWriteReceipt(
                str(transaction_id), str(event_id), aggregate_id, version
            )
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()


class OutboxReconciler:
    """Repair a missing outbox row from durable reconciliation intent."""

    def __init__(self, connection_factory: Callable[[], Connection]) -> None:
        self._connection_factory = connection_factory

    def reconcile_once(self, *, limit: int = 100) -> int:
        if limit <= 0:
            raise ValueError("limit must be positive")
        connection = self._connection_factory()
        cursor = connection.cursor()
        repaired = 0
        try:
            cursor.execute(
                """SELECT q.transaction_id, q.aggregate_id, q.aggregate_version,
                          q.expected_event_id, a.document, a.updated_at
                   FROM ocor_reconciliation_queue q
                   JOIN ocor_aggregates a ON a.aggregate_id = q.aggregate_id
                   LEFT JOIN ocor_outbox o ON o.event_id = q.expected_event_id
                   WHERE q.reconciled_at IS NULL AND o.event_id IS NULL
                   ORDER BY a.updated_at, q.transaction_id
                   FOR UPDATE OF q SKIP LOCKED LIMIT %s""",
                (limit,),
            )
            rows = cursor.fetchall()
            for transaction_id, aggregate_id, version, event_id, document, occurred_at in rows:
                payload = document if isinstance(document, dict) else json.loads(document)
                cursor.execute(
                    """INSERT INTO ocor_outbox
                       (event_id, transaction_id, aggregate_id, aggregate_version,
                        event_type, payload, payload_digest, request_digest,
                        idempotency_key, occurred_at)
                       VALUES (%s, %s, %s, %s, 'reconciled', %s::jsonb, %s, %s, %s, %s)
                       ON CONFLICT (event_id) DO NOTHING""",
                    (
                        event_id,
                        transaction_id,
                        aggregate_id,
                        version,
                        json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
                        canonical_sha256(payload),
                        canonical_sha256(
                            {
                                "aggregateId": aggregate_id,
                                "document": payload,
                                "eventType": "reconciled",
                                "payload": payload,
                            }
                        ),
                        f"reconciled:{transaction_id}",
                        occurred_at,
                    ),
                )
                repaired += max(cursor.rowcount, 0)
            cursor.execute(
                """UPDATE ocor_reconciliation_queue q SET reconciled_at = NOW()
                   WHERE reconciled_at IS NULL
                     AND EXISTS (SELECT 1 FROM ocor_outbox o
                                 WHERE o.event_id = q.expected_event_id)"""
            )
            connection.commit()
            return repaired
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()


def select_atomic_backend(
    candidate: Any,
    *,
    postgres_connection_factory: Callable[[], Connection] | None = None,
) -> Any:
    """Use the candidate when atomic, otherwise instantiate the ratified fallback."""

    if bool(getattr(candidate, "supports_atomic_multi_document_writes", False)):
        return candidate
    if postgres_connection_factory is None:
        raise RuntimeError(
            "backend lacks atomic multi-document writes; a PostgreSQL connection "
            "factory is required for the approved fallback"
        )
    return PostgreSQLTransactionalOutbox(postgres_connection_factory)
