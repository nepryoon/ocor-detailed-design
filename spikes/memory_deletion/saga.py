"""Distributed deletion saga across real, independent backends.

Proves that a deletion request spanning metadata (PostgreSQL), content
(TypeDB) and cache/index (Qdrant, via OCOR-DEV-0023's sealed
``QdrantHarness``, reused unmodified) reports ``DELETION_INCOMPLETE``
until every backend independently confirms the item is no longer
findable -- never trusting a single backend's own "delete succeeded"
signal. A ``DeletionReceipt`` can only claim ``DELETED`` when every
target's own ``contains()`` check, called fresh after the attempt,
returns ``False``.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

import psycopg

from spikes.vector_partition.oracle import QdrantHarness

TYPEDB_URL = "http://127.0.0.1:8000"
TYPEDB_DATABASE = "ocor_default"


class DeletionStatus(StrEnum):
    DELETED = "DELETED"
    DELETION_INCOMPLETE = "DELETION_INCOMPLETE"


class DeletionTarget(Protocol):
    name: str

    def put(self, item_id: str) -> None: ...
    def contains(self, item_id: str) -> bool: ...
    def tombstone(self, item_id: str) -> None: ...


@dataclass(frozen=True, slots=True)
class DeletionReceipt:
    item_id: str
    status: DeletionStatus
    acknowledged: tuple[str, ...]
    remaining: tuple[str, ...]


def run_deletion_saga(item_id: str, targets: list[DeletionTarget]) -> DeletionReceipt:
    """Attempt to tombstone ``item_id`` on every target, then -- regardless
    of whether ``tombstone`` raised or returned -- independently re-check
    ``contains`` as the sole arbiter of acknowledged-vs-remaining. A
    target's own claim of success is never trusted on its own; an
    unreachable target fails closed (counted as still-present), never as
    silently acknowledged.
    """
    acknowledged: list[str] = []
    remaining: list[str] = []
    for target in targets:
        try:
            target.tombstone(item_id)
        except Exception:  # noqa: BLE001 -- a failed tombstone call is not fatal to the saga
            pass
        try:
            still_present = target.contains(item_id)
        except Exception:  # noqa: BLE001 -- an unreachable target fails closed
            still_present = True
        (remaining if still_present else acknowledged).append(target.name)
    status = DeletionStatus.DELETION_INCOMPLETE if remaining else DeletionStatus.DELETED
    return DeletionReceipt(item_id, status, tuple(acknowledged), tuple(remaining))


class PostgresMetadataTarget:
    name = "metadata-postgres"

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        with psycopg.connect(dsn) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS spike_deletion_metadata "
                "(item_id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )

    def put(self, item_id: str) -> None:
        with psycopg.connect(self._dsn) as connection:
            connection.execute(
                "INSERT INTO spike_deletion_metadata (item_id, payload) VALUES (%s, %s) "
                "ON CONFLICT (item_id) DO UPDATE SET payload = EXCLUDED.payload",
                (item_id, "payload"),
            )

    def contains(self, item_id: str) -> bool:
        with psycopg.connect(self._dsn) as connection:
            row = connection.execute(
                "SELECT 1 FROM spike_deletion_metadata WHERE item_id = %s", (item_id,)
            ).fetchone()
            return row is not None

    def tombstone(self, item_id: str) -> None:
        with psycopg.connect(self._dsn) as connection:
            connection.execute("DELETE FROM spike_deletion_metadata WHERE item_id = %s", (item_id,))


def _request(
    method: str, url: str, *, headers: dict[str, str] | None = None, body: bytes | None = None, timeout: float = 10.0
) -> tuple[int, str]:
    request = urllib.request.Request(url, method=method, data=body, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


class TypeDBContentError(RuntimeError):
    pass


def _typedb_token() -> str:
    status, body = _request(
        "POST",
        f"{TYPEDB_URL}/v1/signin",
        headers={"Content-Type": "application/json"},
        body=json.dumps({"username": "admin", "password": "password"}).encode("utf-8"),
    )
    if status != 200:
        raise TypeDBContentError(f"cannot sign in to TypeDB: {status} {body}")
    token: str = json.loads(body)["token"]
    return token


def _typedb_transaction(kind: str, token: str) -> str:
    status, body = _request(
        "POST",
        f"{TYPEDB_URL}/v1/transactions/open",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        body=json.dumps({"databaseName": TYPEDB_DATABASE, "transactionType": kind}).encode("utf-8"),
    )
    if status != 200:
        raise TypeDBContentError(f"cannot open a TypeDB {kind} transaction: {status} {body}")
    transaction_id: str = json.loads(body)["transactionId"]
    return transaction_id


def _typedb_query(transaction_id: str, query: str, token: str) -> tuple[int, dict[str, Any]]:
    status, body = _request(
        "POST",
        f"{TYPEDB_URL}/v1/transactions/{transaction_id}/query",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        body=json.dumps({"query": query}).encode("utf-8"),
    )
    return status, (json.loads(body) if body else {})


def _typedb_commit(transaction_id: str, token: str) -> None:
    status, body = _request(
        "POST", f"{TYPEDB_URL}/v1/transactions/{transaction_id}/commit", headers={"Authorization": f"Bearer {token}"}
    )
    if status != 200:
        raise TypeDBContentError(f"failed to commit TypeDB transaction: {status} {body}")


def _typedb_close(transaction_id: str, token: str) -> None:
    _request(
        "POST", f"{TYPEDB_URL}/v1/transactions/{transaction_id}/close", headers={"Authorization": f"Bearer {token}"}
    )


def _typedb_write(query: str) -> None:
    token = _typedb_token()
    transaction_id = _typedb_transaction("write", token)
    status, result = _typedb_query(transaction_id, query, token)
    if status != 200:
        _typedb_close(transaction_id, token)
        raise TypeDBContentError(f"write failed: {status} {result}")
    _typedb_commit(transaction_id, token)


def _typedb_schema_write(query: str) -> None:
    token = _typedb_token()
    transaction_id = _typedb_transaction("schema", token)
    status, result = _typedb_query(transaction_id, query, token)
    if status != 200:
        _typedb_close(transaction_id, token)
        raise TypeDBContentError(f"schema write failed: {status} {result}")
    _typedb_commit(transaction_id, token)


def _typedb_read(query: str) -> list[dict[str, Any]]:
    token = _typedb_token()
    transaction_id = _typedb_transaction("read", token)
    status, result = _typedb_query(transaction_id, query, token)
    _typedb_close(transaction_id, token)
    if status != 200:
        raise TypeDBContentError(f"read failed: {status} {result}")
    answers = result.get("answers") or []
    return list(answers)


def _typedb_ensure_database() -> None:
    # A fresh TypeDB instance (e.g. a CI-provisioned ephemeral service
    # container, per OCOR-DEV-0017's same finding) has no databases at
    # all; the persistent ocor-bootstrap stack already has ocor_default
    # from OCOR-DEV-0080, so this is check-before-mutate.
    token = _typedb_token()
    status, body = _request(
        "GET", f"{TYPEDB_URL}/v1/databases", headers={"Authorization": f"Bearer {token}"}
    )
    if status != 200:
        raise TypeDBContentError(f"cannot list TypeDB databases: {status} {body}")
    existing = {entry["name"] for entry in json.loads(body).get("databases", [])}
    if TYPEDB_DATABASE in existing:
        return
    status, body = _request(
        "POST", f"{TYPEDB_URL}/v1/databases/{TYPEDB_DATABASE}", headers={"Authorization": f"Bearer {token}"}
    )
    if status != 200:
        raise TypeDBContentError(f"failed to create TypeDB database {TYPEDB_DATABASE!r}: {status} {body}")


class TypeDBContentTarget:
    name = "content-typedb"

    SCHEMA = (
        "define attribute deletion-item-id, value string; "
        "entity deletion-item, owns deletion-item-id @key;"
    )

    def __init__(self) -> None:
        _typedb_ensure_database()
        _typedb_schema_write(self.SCHEMA)

    def put(self, item_id: str) -> None:
        _typedb_write(f'insert $x isa deletion-item, has deletion-item-id "{item_id}";')

    def contains(self, item_id: str) -> bool:
        rows = _typedb_read(f'match $x isa deletion-item, has deletion-item-id "{item_id}";')
        return bool(rows)

    def tombstone(self, item_id: str) -> None:
        _typedb_write(f'match $x isa deletion-item, has deletion-item-id "{item_id}"; delete $x;')


class QdrantCacheTarget:
    name = "cache-qdrant"

    def __init__(self, qdrant: QdrantHarness, collection: str) -> None:
        self._qdrant = qdrant
        self._collection = collection
        qdrant.request("PUT", f"/collections/{collection}", {"vectors": {"size": 4, "distance": "Cosine"}})

    @staticmethod
    def _point_id(item_id: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, item_id))

    def put(self, item_id: str) -> None:
        self._qdrant.request(
            "PUT",
            f"/collections/{self._collection}/points?wait=true",
            {
                "points": [
                    {
                        "id": self._point_id(item_id),
                        "vector": [0.1, 0.2, 0.3, 0.4],
                        "payload": {"item_id": item_id},
                    }
                ]
            },
        )

    def contains(self, item_id: str) -> bool:
        response = self._qdrant.request(
            "POST", f"/collections/{self._collection}/points", {"ids": [self._point_id(item_id)]}
        )
        return len(response["result"]) > 0

    def tombstone(self, item_id: str) -> None:
        self._qdrant.request(
            "POST",
            f"/collections/{self._collection}/points/delete?wait=true",
            {"points": [self._point_id(item_id)]},
        )
