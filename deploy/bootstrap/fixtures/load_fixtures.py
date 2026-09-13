#!/usr/bin/env python3
"""OCOR-DEV-0081: load deterministic, content-addressed synthetic fixtures.

Loads the fixed fixture set declared in synthetic_fixtures.json into the
TerminusDB and TypeDB databases OCOR-DEV-0080 initialized (`ocor_default`
on each). Per deploy/bootstrap/fixtures/README.md, each loader records the
source digest, target service, operation count and post-load verification
digest. Loading is check-before-mutate, mirroring OCOR-DEV-0080's
initialize_services.py: already-loaded-and-matching is a no-op, present but
different from the declared fixture fails closed as drift.

TerminusDB/TypeDB were the two services OCOR-DEV-0080 gave a governed
database shell to; PostgreSQL, Kafka and Qdrant were already provisioned
and evidenced by earlier, unrelated tasks (OCOR-DEV-0006/0015/0019/0023,
predating this WS-12 infrastructure-bootstrap-repair chain) and are out of
scope here.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

FIXTURES_PATH = Path(__file__).with_name("synthetic_fixtures.json")
TERMINUSDB_URL = "http://127.0.0.1:6363"
TYPEDB_URL = "http://127.0.0.1:8000"


class FixtureError(RuntimeError):
    """A deterministic fixture-load step failed closed."""


class FixtureResult(str, Enum):
    CREATED = "CREATED"
    ALREADY_INITIALIZED = "ALREADY_INITIALIZED"
    DRIFT_DETECTED = "DRIFT_DETECTED"


@dataclass(frozen=True)
class FixtureOutcome:
    target: str
    result: FixtureResult
    operation_count: int
    source_sha256: str
    verification_sha256: str

    def to_json(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "result": self.result.value,
            "operation_count": self.operation_count,
            "source_sha256": self.source_sha256,
            "verification_sha256": self.verification_sha256,
        }


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode("utf-8")).hexdigest()


def _request(
    method: str, url: str, *, headers: dict[str, str] | None = None, body: bytes | None = None, timeout: float = 10.0
) -> tuple[int, str]:
    request = urllib.request.Request(url, method=method, data=body, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def _parse_terminusdb_body(body: str) -> dict[str, Any]:
    # A GET on an absent single document returns a real HTTP 200 whose body
    # is prefixed with a literal "Status: 404\nContent-type: ...\n\n" text
    # header before the actual JSON error payload -- a live-verified quirk
    # of this TerminusDB version's single-document error serialization, not
    # a bug in this loader. Locate the JSON object regardless of any prefix.
    start = body.find("{")
    if start < 0:
        raise FixtureError(f"TerminusDB response has no JSON body: {body!r}")
    result: dict[str, Any] = json.loads(body[start:])
    return result


def load_terminusdb_fixture(fixture: dict[str, Any], password: str) -> FixtureOutcome:
    source_digest = canonical_sha256(fixture)
    database = fixture["database"]
    credentials = f"admin:{password}".encode()
    headers = {"Authorization": f"Basic {base64.b64encode(credentials).decode()}"}

    status, body = _request(
        "GET", f"{TERMINUSDB_URL}/api/document/admin/{database}?id={fixture['instance_id']}", headers=headers
    )
    # TerminusDB has been observed to report "document not found" two
    # different ways for the identical condition: a real HTTP 404, or an
    # HTTP 200 whose body is prefixed with a literal "Status: 404\n..."
    # text header (see _parse_terminusdb_body). Both must be treated as
    # absent; only a status that is neither is a genuine query failure.
    if status not in (200, 404):
        raise FixtureError(f"cannot query TerminusDB document: {status} {body}")
    parsed = _parse_terminusdb_body(body)
    if parsed.get("api:status") != "api:not_found":
        observed = {"name": parsed.get("name"), "value": parsed.get("value")}
        expected = {
            "name": fixture["instance_document"]["name"],
            "value": fixture["instance_document"]["value"],
        }
        if observed != expected:
            raise FixtureError(f"TerminusDB fixture {fixture['instance_id']!r} exists with different content (drift)")
        return FixtureOutcome("terminusdb", FixtureResult.ALREADY_INITIALIZED, 0, source_digest, canonical_sha256(observed))

    schema_status, schema_body = _request(
        "POST",
        f"{TERMINUSDB_URL}/api/document/admin/{database}?graph_type=schema&author=ocor-bootstrap&message=synthetic-fixture-schema",
        headers={**headers, "Content-Type": "application/json"},
        body=json.dumps(fixture["schema_document"]).encode("utf-8"),
    )
    if schema_status != 200:
        raise FixtureError(f"failed to load TerminusDB fixture schema: {schema_status} {schema_body}")
    instance_status, instance_body = _request(
        "POST",
        f"{TERMINUSDB_URL}/api/document/admin/{database}?author=ocor-bootstrap&message=synthetic-fixture-data",
        headers={**headers, "Content-Type": "application/json"},
        body=json.dumps(fixture["instance_document"]).encode("utf-8"),
    )
    if instance_status != 200:
        raise FixtureError(f"failed to load TerminusDB fixture instance: {instance_status} {instance_body}")

    verify_status, verify_body = _request(
        "GET", f"{TERMINUSDB_URL}/api/document/admin/{database}?id={fixture['instance_id']}", headers=headers
    )
    verified = _parse_terminusdb_body(verify_body) if verify_status == 200 else {}
    observed = {"name": verified.get("name"), "value": verified.get("value")}
    return FixtureOutcome("terminusdb", FixtureResult.CREATED, 2, source_digest, canonical_sha256(observed))


def _typedb_token() -> str:
    status, body = _request(
        "POST",
        f"{TYPEDB_URL}/v1/signin",
        headers={"Content-Type": "application/json"},
        body=json.dumps({"username": "admin", "password": "password"}).encode("utf-8"),
    )
    if status != 200:
        raise FixtureError(f"cannot sign in to TypeDB: {status} {body}")
    token: str = json.loads(body)["token"]
    return token


def _typedb_transaction(database: str, kind: str, token: str) -> str:
    status, body = _request(
        "POST",
        f"{TYPEDB_URL}/v1/transactions/open",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        body=json.dumps({"databaseName": database, "transactionType": kind}).encode("utf-8"),
    )
    if status != 200:
        raise FixtureError(f"cannot open a TypeDB {kind} transaction: {status} {body}")
    transaction_id: str = json.loads(body)["transactionId"]
    return transaction_id


def _typedb_query(transaction_id: str, query: str, token: str) -> tuple[int, dict[str, Any]]:
    status, body = _request(
        "POST",
        f"{TYPEDB_URL}/v1/transactions/{transaction_id}/query",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        body=json.dumps({"query": query}).encode("utf-8"),
    )
    parsed: dict[str, Any] = json.loads(body) if body else {}
    return status, parsed


def _typedb_commit(transaction_id: str, token: str) -> None:
    status, body = _request(
        "POST", f"{TYPEDB_URL}/v1/transactions/{transaction_id}/commit", headers={"Authorization": f"Bearer {token}"}
    )
    if status != 200:
        raise FixtureError(f"failed to commit TypeDB transaction: {status} {body}")


def _typedb_close(transaction_id: str, token: str) -> None:
    _request("POST", f"{TYPEDB_URL}/v1/transactions/{transaction_id}/close", headers={"Authorization": f"Bearer {token}"})


def load_typedb_fixture(fixture: dict[str, Any]) -> FixtureOutcome:
    source_digest = canonical_sha256(fixture)
    token = _typedb_token()
    database = fixture["database"]

    read_tx = _typedb_transaction(database, "read", token)
    verify_status, verify_body = _typedb_query(read_tx, fixture["verify_query"], token)
    _typedb_close(read_tx, token)

    schema_missing = verify_status != 200 and (
        verify_body.get("code") == "INF2" or "type label" in str(verify_body.get("message", "")).lower()
    )
    if verify_status == 200:
        answers = verify_body.get("answers") or []
        expected = {"name": "ocor-bootstrap-fixture", "value": 42}
        if answers:
            observed_rows = [
                {"name": row["data"]["n"]["value"], "value": row["data"]["v"]["value"]} for row in answers
            ]
            if observed_rows != [expected]:
                raise FixtureError("TypeDB fixture data exists with different content (drift)")
            return FixtureOutcome("typedb", FixtureResult.ALREADY_INITIALIZED, 0, source_digest, canonical_sha256(expected))
        operation_count = 1  # schema already compatible; only the data insert is needed
    elif schema_missing:
        operation_count = 2  # schema + data both needed
        schema_tx = _typedb_transaction(database, "schema", token)
        schema_status, schema_result = _typedb_query(schema_tx, fixture["schema_query"], token)
        if schema_status != 200:
            _typedb_close(schema_tx, token)
            raise FixtureError(f"failed to define TypeDB fixture schema: {schema_result}")
        _typedb_commit(schema_tx, token)
    else:
        raise FixtureError(f"unexpected TypeDB verify-query response: {verify_status} {verify_body}")

    write_tx = _typedb_transaction(database, "write", token)
    write_status, write_result = _typedb_query(write_tx, fixture["data_query"], token)
    if write_status != 200:
        _typedb_close(write_tx, token)
        raise FixtureError(f"failed to insert TypeDB fixture data: {write_result}")
    _typedb_commit(write_tx, token)

    verify_tx = _typedb_transaction(database, "read", token)
    _, verify_result = _typedb_query(verify_tx, fixture["verify_query"], token)
    _typedb_close(verify_tx, token)
    answers = verify_result.get("answers") or []
    if len(answers) != 1:
        raise FixtureError(f"post-load verification found {len(answers)} rows, expected exactly 1")
    observed = {
        "name": answers[0]["data"]["n"]["value"],
        "value": answers[0]["data"]["v"]["value"],
    }
    return FixtureOutcome("typedb", FixtureResult.CREATED, operation_count, source_digest, canonical_sha256(observed))


def run(*, terminusdb_password: str) -> list[FixtureOutcome]:
    manifest = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    outcomes = []
    for fixture in manifest["fixtures"]:
        if fixture["target"] == "terminusdb":
            outcomes.append(load_terminusdb_fixture(fixture, terminusdb_password))
        elif fixture["target"] == "typedb":
            outcomes.append(load_typedb_fixture(fixture))
        else:
            raise FixtureError(f"unknown fixture target: {fixture['target']}")
    return outcomes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True, help="file with OCOR_LOCAL_* secrets, never committed")
    args = parser.parse_args()
    env: dict[str, str] = {}
    for line in args.env_file.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            key, _, value = line.partition("=")
            env[key] = value
    try:
        outcomes = run(terminusdb_password=env["OCOR_LOCAL_TERMINUSDB_PASSWORD"])
        print(json.dumps({"status": "PASS", "fixtures": [o.to_json() for o in outcomes]}, indent=2, sort_keys=True))
        return 0
    except (FixtureError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    sys.exit(main())
