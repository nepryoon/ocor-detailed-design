"""OCOR-DEV-0081: deterministic, content-addressed synthetic fixture loading.

Unit/negative/contract coverage for deploy/bootstrap/fixtures/load_fixtures.py's
step logic, with every network call replaced by a deterministic fake -- no
live Docker dependency (those are exercised for real, once, in the sealed
evidence at reports/evidence/G2/OCOR-DEV-0081.json, captured against the
live 11-service stack, including a real drift-detection/rollback drill,
mirroring OCOR-DEV-0080's evidence pattern).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "deploy/bootstrap/fixtures/load_fixtures.py"

SPEC = importlib.util.spec_from_file_location("load_fixtures_0081", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
loader = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = loader
SPEC.loader.exec_module(loader)

TERMINUSDB_FIXTURE = json.loads(loader.FIXTURES_PATH.read_text(encoding="utf-8"))["fixtures"][0]
TYPEDB_FIXTURE = json.loads(loader.FIXTURES_PATH.read_text(encoding="utf-8"))["fixtures"][1]
TX = "fake-transaction-id"


def test_fixture_result_is_a_closed_typed_set():
    assert {member.value for member in loader.FixtureResult} == {"CREATED", "ALREADY_INITIALIZED", "DRIFT_DETECTED"}


def test_fixture_outcome_to_json_is_stable():
    outcome = loader.FixtureOutcome("terminusdb", loader.FixtureResult.CREATED, 2, "src", "verify")
    assert outcome.to_json() == {
        "target": "terminusdb",
        "result": "CREATED",
        "operation_count": 2,
        "source_sha256": "src",
        "verification_sha256": "verify",
    }


def test_canonical_sha256_is_deterministic_regardless_of_key_order():
    assert loader.canonical_sha256({"a": 1, "b": 2}) == loader.canonical_sha256({"b": 2, "a": 1})


def test_parse_terminusdb_body_handles_the_status_404_prefix_quirk():
    # A live-verified TerminusDB quirk: a not-found single-document GET
    # returns real HTTP 200 with a body prefixed by a literal
    # "Status: 404\nContent-type: ...\n\n" text header before the JSON.
    body = 'Status: 404\nContent-type: application/json; charset=UTF-8\n\n{"api:status": "api:not_found"}'
    assert loader._parse_terminusdb_body(body) == {"api:status": "api:not_found"}


def test_parse_terminusdb_body_handles_a_clean_document_response():
    body = '{"@id": "SyntheticFixture/ocor-001", "name": "ocor-bootstrap-fixture", "value": 42}'
    parsed = loader._parse_terminusdb_body(body)
    assert parsed["value"] == 42


def _fake_request(responses: dict[tuple[str, str], tuple[int, str]]):
    def fake(method: str, url: str, *, headers: Any = None, body: Any = None, timeout: float = 10.0) -> tuple[int, str]:
        key = (method, url)
        if key not in responses:
            raise AssertionError(f"unexpected request: {method} {url}")
        return responses[key]

    return fake


def test_load_terminusdb_creates_when_absent(monkeypatch):
    not_found = json.dumps({"api:status": "api:not_found"})
    created = json.dumps({"name": "ocor-bootstrap-fixture", "value": 42})
    responses = {
        (
            "POST",
            f"{loader.TERMINUSDB_URL}/api/document/admin/ocor_default?graph_type=schema&author=ocor-bootstrap&message=synthetic-fixture-schema",
        ): (200, "[]"),
        (
            "POST",
            f"{loader.TERMINUSDB_URL}/api/document/admin/ocor_default?author=ocor-bootstrap&message=synthetic-fixture-data",
        ): (200, "[]"),
    }
    # First GET (absent) is the drift/existence check; the second GET (after
    # the writes above) is the post-load verification -- both share the
    # same URL, so a stateful fake distinguishes them by call order.
    call_state = {"n": 0}

    def sequenced(method, url, **kwargs):
        if method == "GET" and "id=SyntheticFixture" in url:
            call_state["n"] += 1
            return (200, not_found) if call_state["n"] == 1 else (200, created)
        return _fake_request(responses)(method, url, **kwargs)

    monkeypatch.setattr(loader, "_request", sequenced)
    outcome = loader.load_terminusdb_fixture(TERMINUSDB_FIXTURE, "irrelevant-password")
    assert outcome.result is loader.FixtureResult.CREATED
    assert outcome.operation_count == 2


def test_load_terminusdb_creates_when_absent_via_a_real_404_status(monkeypatch):
    # OCOR-DEV-0083 discovered TerminusDB does not always use the "200 with
    # a Status: 404 text prefix" quirk for a not-found document -- it has
    # also been observed returning a real HTTP 404 for the identical
    # condition. Both must be treated as absent.
    not_found = json.dumps({"api:status": "api:not_found"})
    created = json.dumps({"name": "ocor-bootstrap-fixture", "value": 42})
    responses = {
        (
            "POST",
            f"{loader.TERMINUSDB_URL}/api/document/admin/ocor_default?graph_type=schema&author=ocor-bootstrap&message=synthetic-fixture-schema",
        ): (200, "[]"),
        (
            "POST",
            f"{loader.TERMINUSDB_URL}/api/document/admin/ocor_default?author=ocor-bootstrap&message=synthetic-fixture-data",
        ): (200, "[]"),
    }
    call_state = {"n": 0}

    def sequenced(method, url, **kwargs):
        if method == "GET" and "id=SyntheticFixture" in url:
            call_state["n"] += 1
            return (404, not_found) if call_state["n"] == 1 else (200, created)
        return _fake_request(responses)(method, url, **kwargs)

    monkeypatch.setattr(loader, "_request", sequenced)
    outcome = loader.load_terminusdb_fixture(TERMINUSDB_FIXTURE, "irrelevant-password")
    assert outcome.result is loader.FixtureResult.CREATED


def test_load_terminusdb_already_initialized_when_matching(monkeypatch):
    body = json.dumps({"name": "ocor-bootstrap-fixture", "value": 42})
    responses = {
        ("GET", f"{loader.TERMINUSDB_URL}/api/document/admin/ocor_default?id=SyntheticFixture/ocor-001"): (200, body),
    }
    monkeypatch.setattr(loader, "_request", _fake_request(responses))
    outcome = loader.load_terminusdb_fixture(TERMINUSDB_FIXTURE, "irrelevant-password")
    assert outcome.result is loader.FixtureResult.ALREADY_INITIALIZED
    assert outcome.operation_count == 0


def test_load_terminusdb_detects_drift_and_never_overwrites(monkeypatch):
    body = json.dumps({"name": "mutated", "value": 999})
    responses = {
        ("GET", f"{loader.TERMINUSDB_URL}/api/document/admin/ocor_default?id=SyntheticFixture/ocor-001"): (200, body),
    }
    monkeypatch.setattr(loader, "_request", _fake_request(responses))
    with pytest.raises(loader.FixtureError, match="drift"):
        loader.load_terminusdb_fixture(TERMINUSDB_FIXTURE, "irrelevant-password")


def _typedb_scaffolding() -> dict[tuple[str, str], tuple[int, str]]:
    # Everything except /query is static across every scenario below;
    # /query shares one URL for every call in the flow (verify, schema
    # define, data insert, re-verify), so each test drives it with a
    # stateful callable instead of this map.
    return {
        ("POST", f"{loader.TYPEDB_URL}/v1/signin"): (200, json.dumps({"token": "fake-token"})),
        ("POST", f"{loader.TYPEDB_URL}/v1/transactions/open"): (200, json.dumps({"transactionId": TX})),
        ("POST", f"{loader.TYPEDB_URL}/v1/transactions/{TX}/commit"): (200, "{}"),
        ("POST", f"{loader.TYPEDB_URL}/v1/transactions/{TX}/close"): (200, "{}"),
    }


def test_load_typedb_already_initialized_when_matching(monkeypatch):
    responses = _typedb_scaffolding()
    query_url = f"{loader.TYPEDB_URL}/v1/transactions/{TX}/query"

    def fake(method, url, *, headers=None, body=None, timeout=10.0):
        if (method, url) == ("POST", query_url):
            return 200, json.dumps({"answers": [{"data": {"n": {"value": "ocor-bootstrap-fixture"}, "v": {"value": 42}}}]})
        return _fake_request(responses)(method, url, headers=headers, body=body, timeout=timeout)

    monkeypatch.setattr(loader, "_request", fake)
    outcome = loader.load_typedb_fixture(TYPEDB_FIXTURE)
    assert outcome.result is loader.FixtureResult.ALREADY_INITIALIZED
    assert outcome.operation_count == 0


def test_load_typedb_detects_drift_and_never_overwrites(monkeypatch):
    responses = _typedb_scaffolding()
    query_url = f"{loader.TYPEDB_URL}/v1/transactions/{TX}/query"

    def fake(method, url, *, headers=None, body=None, timeout=10.0):
        if (method, url) == ("POST", query_url):
            return 200, json.dumps({"answers": [{"data": {"n": {"value": "mutated"}, "v": {"value": 999}}}]})
        return _fake_request(responses)(method, url, headers=headers, body=body, timeout=timeout)

    monkeypatch.setattr(loader, "_request", fake)
    with pytest.raises(loader.FixtureError, match="drift"):
        loader.load_typedb_fixture(TYPEDB_FIXTURE)


def test_load_typedb_creates_schema_and_data_when_both_absent(monkeypatch):
    responses = _typedb_scaffolding()
    query_url = f"{loader.TYPEDB_URL}/v1/transactions/{TX}/query"
    call_state = {"n": 0}

    def fake(method, url, *, headers=None, body=None, timeout=10.0):
        if (method, url) == ("POST", query_url):
            call_state["n"] += 1
            if call_state["n"] == 1:
                return 400, json.dumps({"code": "INF2", "message": "Type label 'synthetic-fixture' not found."})
            if call_state["n"] in (2, 3):
                return 200, json.dumps({"queryType": "schema" if call_state["n"] == 2 else "write"})
            return 200, json.dumps({"answers": [{"data": {"n": {"value": "ocor-bootstrap-fixture"}, "v": {"value": 42}}}]})
        return _fake_request(responses)(method, url, headers=headers, body=body, timeout=timeout)

    monkeypatch.setattr(loader, "_request", fake)
    outcome = loader.load_typedb_fixture(TYPEDB_FIXTURE)
    assert outcome.result is loader.FixtureResult.CREATED
    assert outcome.operation_count == 2


def test_load_typedb_creates_only_data_when_schema_already_compatible(monkeypatch):
    responses = _typedb_scaffolding()
    query_url = f"{loader.TYPEDB_URL}/v1/transactions/{TX}/query"
    call_state = {"n": 0}

    def fake(method, url, *, headers=None, body=None, timeout=10.0):
        if (method, url) == ("POST", query_url):
            call_state["n"] += 1
            if call_state["n"] == 1:
                return 200, json.dumps({"answers": []})
            if call_state["n"] == 2:
                return 200, json.dumps({"queryType": "write"})
            return 200, json.dumps({"answers": [{"data": {"n": {"value": "ocor-bootstrap-fixture"}, "v": {"value": 42}}}]})
        return _fake_request(responses)(method, url, headers=headers, body=body, timeout=timeout)

    monkeypatch.setattr(loader, "_request", fake)
    outcome = loader.load_typedb_fixture(TYPEDB_FIXTURE)
    assert outcome.result is loader.FixtureResult.CREATED
    assert outcome.operation_count == 1
