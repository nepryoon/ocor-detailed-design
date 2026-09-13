"""Real TypeDB-backed exact-at-commit projection adapter.

Implements ``ProjectionReadPort``/``WatermarkPort`` from
``ocor_runtime.c2.ports`` (OCOR-DEV-0012, sealed, reused unmodified) against
a real, live TypeDB instance, modeling a lagging, asynchronously-applied C4
projection: ``ingest``/``update_fact`` write a fact stamped with the
upstream commit that produced it, while ``advance_watermark`` is a
SEPARATE step simulating the moment the projection pipeline has fully
applied that commit and it becomes safe to read at. A fact's row can exist
in TypeDB before -- or move ahead of -- the watermark; the adapter's job is
to prove that race is never silently served as if it were exact.
"""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any

from ocor_runtime.c2.ports import (
    C2Error,
    NamedQueryRequest,
    NamedQueryResponse,
    ServedContext,
    Watermark,
)

TYPEDB_URL = "http://127.0.0.1:8000"
DATABASE = "ocor_default"
PROJECTION_ID = "urn:ocor:projection:spike-typedb-exact-commit"
BRANCH = "main"
# ServedContext requires a non-empty string for canonical_commit and
# projection_watermark (they are identifiers, not booleans); this sentinel
# stands in for "no commit has ever been applied yet" and is guaranteed
# never to equal a real commit id produced by this spike's tests.
NO_WATERMARK_SENTINEL = "urn:ocor:commit:none"

SCHEMA_QUERY = (
    "define "
    "attribute spike-fact-id, value string; "
    "attribute spike-commit-id, value string; "
    "attribute spike-payload, value string; "
    "entity spike-fact, owns spike-fact-id @key, owns spike-commit-id @card(1..1), "
    "owns spike-payload @card(1..1); "
    "entity spike-watermark, owns spike-commit-id @card(1..1);"
)


class TypeDBAdapterError(RuntimeError):
    pass


def _request(
    method: str, url: str, *, headers: dict[str, str] | None = None, body: bytes | None = None, timeout: float = 10.0
) -> tuple[int, str]:
    request = urllib.request.Request(url, method=method, data=body, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def _token() -> str:
    status, body = _request(
        "POST",
        f"{TYPEDB_URL}/v1/signin",
        headers={"Content-Type": "application/json"},
        body=json.dumps({"username": "admin", "password": "password"}).encode("utf-8"),
    )
    if status != 200:
        raise TypeDBAdapterError(f"cannot sign in to TypeDB: {status} {body}")
    token: str = json.loads(body)["token"]
    return token


def _transaction(kind: str, token: str) -> str:
    status, body = _request(
        "POST",
        f"{TYPEDB_URL}/v1/transactions/open",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        body=json.dumps({"databaseName": DATABASE, "transactionType": kind}).encode("utf-8"),
    )
    if status != 200:
        raise TypeDBAdapterError(f"cannot open a TypeDB {kind} transaction: {status} {body}")
    transaction_id: str = json.loads(body)["transactionId"]
    return transaction_id


def _query(transaction_id: str, query: str, token: str) -> tuple[int, dict[str, Any]]:
    status, body = _request(
        "POST",
        f"{TYPEDB_URL}/v1/transactions/{transaction_id}/query",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        body=json.dumps({"query": query}).encode("utf-8"),
    )
    parsed: dict[str, Any] = json.loads(body) if body else {}
    return status, parsed


def _commit(transaction_id: str, token: str) -> None:
    status, body = _request(
        "POST", f"{TYPEDB_URL}/v1/transactions/{transaction_id}/commit", headers={"Authorization": f"Bearer {token}"}
    )
    if status != 200:
        raise TypeDBAdapterError(f"failed to commit TypeDB transaction: {status} {body}")


def _close(transaction_id: str, token: str) -> None:
    _request(
        "POST", f"{TYPEDB_URL}/v1/transactions/{transaction_id}/close", headers={"Authorization": f"Bearer {token}"}
    )


def _write(query: str) -> dict[str, Any]:
    token = _token()
    transaction_id = _transaction("write", token)
    status, result = _query(transaction_id, query, token)
    if status != 200:
        _close(transaction_id, token)
        raise TypeDBAdapterError(f"write failed: {status} {result}")
    _commit(transaction_id, token)
    return result


def _schema_write(query: str) -> None:
    token = _token()
    transaction_id = _transaction("schema", token)
    status, result = _query(transaction_id, query, token)
    if status != 200:
        _close(transaction_id, token)
        raise TypeDBAdapterError(f"schema write failed: {status} {result}")
    _commit(transaction_id, token)


def _read(query: str) -> list[dict[str, Any]]:
    token = _token()
    transaction_id = _transaction("read", token)
    status, result = _query(transaction_id, query, token)
    _close(transaction_id, token)
    if status != 200:
        raise TypeDBAdapterError(f"read failed: {status} {result}")
    answers = result.get("answers") or []
    return list(answers)


def _ensure_database() -> None:
    # Check-before-mutate, matching deploy/bootstrap/init/initialize_services.py's
    # OCOR-DEV-0080 pattern: the ocor-bootstrap stack already has DATABASE
    # provisioned, but a fresh TypeDB instance (e.g. a CI-provisioned
    # ephemeral service container) does not, so this must create it rather
    # than assume it exists.
    token = _token()
    status, body = _request(
        "GET", f"{TYPEDB_URL}/v1/databases", headers={"Authorization": f"Bearer {token}"}
    )
    if status != 200:
        raise TypeDBAdapterError(f"cannot list TypeDB databases: {status} {body}")
    existing = {entry["name"] for entry in json.loads(body).get("databases", [])}
    if DATABASE in existing:
        return
    status, body = _request(
        "POST", f"{TYPEDB_URL}/v1/databases/{DATABASE}", headers={"Authorization": f"Bearer {token}"}
    )
    if status != 200:
        raise TypeDBAdapterError(f"failed to create TypeDB database {DATABASE!r}: {status} {body}")


class TypeDBExactCommitAdapter:
    """Reads spike-fact rows through the sealed C2 exact-at-commit contract
    against a real TypeDB projection whose watermark advances independently
    of fact ingestion. ``initialize`` ensures the target database exists
    (check-before-mutate, since a fresh instance -- e.g. a CI-provisioned
    ephemeral service container -- has none yet) then defines the schema;
    TypeDB's ``define`` was verified empirically to be idempotent on this
    version (redefining an identical schema is a no-op, not an error), so
    the schema step itself needs no check-before-mutate probe."""

    def initialize(self) -> None:
        _ensure_database()
        _schema_write(SCHEMA_QUERY)

    def reset(self) -> None:
        _write("match $f isa spike-fact; delete $f;")
        _write("match $w isa spike-watermark; delete $w;")

    def ingest(self, fact_id: str, commit_id: str, payload: str) -> None:
        existing = self._lookup_fact(fact_id)
        if existing is not None:
            _write(f'match $f isa spike-fact, has spike-fact-id "{fact_id}"; delete $f;')
        _write(
            f'insert $f isa spike-fact, has spike-fact-id "{fact_id}", '
            f'has spike-commit-id "{commit_id}", has spike-payload "{payload}";'
        )

    def advance_watermark(self, commit_id: str) -> None:
        if self.current_watermark() is not None:
            _write("match $w isa spike-watermark; delete $w;")
        _write(f'insert $w isa spike-watermark, has spike-commit-id "{commit_id}";')

    def current_watermark(self) -> str | None:
        rows = _read("match $w isa spike-watermark, has spike-commit-id $c;")
        if not rows:
            return None
        return str(rows[0]["data"]["c"]["value"])

    def _lookup_fact(self, fact_id: str) -> tuple[str, str] | None:
        rows = _read(
            f'match $f isa spike-fact, has spike-fact-id "{fact_id}", '
            f'has spike-commit-id $c, has spike-payload $p;'
        )
        if not rows:
            return None
        row = rows[0]["data"]
        return str(row["c"]["value"]), str(row["p"]["value"])

    def read(self, request: NamedQueryRequest) -> NamedQueryResponse:
        fact_id = request.parameters.get("fact_id")
        if not isinstance(fact_id, str) or not fact_id:
            raise C2Error("QUERY_CONTRACT_INVALID", "fact_id parameter is required")
        watermark = self.current_watermark()
        found = self._lookup_fact(fact_id)
        # canonical_commit reflects the ACTUAL row read, never the watermark
        # by assumption: a row can be ingested (or updated) ahead of the
        # watermark, and this must be independently detectable rather than
        # inferred as "whatever the watermark says".
        canonical_commit = found[0] if found is not None else (watermark or NO_WATERMARK_SENTINEL)
        served = ServedContext(
            branch=BRANCH,
            ontology_release_digest=request.governed_context.ontology_release_digest,
            canonical_commit=canonical_commit,
            projection_watermark=watermark or NO_WATERMARK_SENTINEL,
            staleness_ms=0,
            governed_context_digest=request.governed_context_digest,
            policy_bundle_digest=request.governed_context.policy_bundle_digest,
        )
        request.verify_served(served)
        if found is None:
            raise C2Error(
                "RESULT_NOT_FOUND", f"no fact projected for {fact_id!r} as of watermark {watermark!r}"
            )
        _, payload = found
        result_digest = "urn:sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return NamedQueryResponse(
            request_id=request.request_id,
            result_ref=f"urn:ocor:spike-fact:{fact_id}",
            result_digest=result_digest,
            served=served,
        )

    def watermark(self) -> Watermark:
        commit = self.current_watermark() or NO_WATERMARK_SENTINEL
        return Watermark(
            projection_id=PROJECTION_ID,
            branch=BRANCH,
            ontology_release_digest="urn:sha256:" + "0" * 64,
            canonical_commit=commit,
            observed_at=datetime.now(UTC),
        )
