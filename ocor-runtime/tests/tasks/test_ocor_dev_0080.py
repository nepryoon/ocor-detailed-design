"""OCOR-DEV-0080: deterministic, idempotent service initialization.

Unit/negative/contract coverage for deploy/bootstrap/init/initialize_services.py's
step logic, with every network/subprocess call replaced by a deterministic
fake -- no live Docker or service dependency (those are exercised for real,
once, in the sealed evidence at reports/evidence/G2/OCOR-DEV-0080.json,
captured against the live 11-service stack the same way OCOR-DEV-0079's
evidence was, including a real drift-detection run).
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "deploy/bootstrap/init/initialize_services.py"

SPEC = importlib.util.spec_from_file_location("initialize_services_0080", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
init = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = init
SPEC.loader.exec_module(init)


def test_init_result_is_a_closed_typed_set():
    assert {member.value for member in init.InitResult} == {"CREATED", "ALREADY_INITIALIZED", "DRIFT_DETECTED"}


def test_step_outcome_to_json_is_stable():
    outcome = init.StepOutcome("opa_policy", init.InitResult.CREATED, {"policy_id": "ocor_bootstrap"})
    assert outcome.to_json() == {"step": "opa_policy", "result": "CREATED", "detail": {"policy_id": "ocor_bootstrap"}}


def _fake_request(responses: dict[tuple[str, str], tuple[int, str]]):
    def fake(method: str, url: str, *, headers: Any = None, body: Any = None, timeout: float = 10.0) -> tuple[int, str]:
        key = (method, url)
        if key not in responses:
            raise AssertionError(f"unexpected request: {method} {url}")
        return responses[key]

    return fake


def test_step_opa_policy_creates_when_absent(monkeypatch):
    responses = {
        ("GET", f"{init.OPA_URL}/v1/policies/{init.OPA_POLICY_ID}"): (404, "{}"),
        ("PUT", f"{init.OPA_URL}/v1/policies/{init.OPA_POLICY_ID}"): (200, "{}"),
    }
    monkeypatch.setattr(init, "_request", _fake_request(responses))
    outcome = init.step_opa_policy()
    assert outcome.result is init.InitResult.CREATED


def test_step_opa_policy_already_initialized_when_identical(monkeypatch):
    expected = init.OPA_POLICY_PATH.read_text(encoding="utf-8")
    responses = {
        ("GET", f"{init.OPA_URL}/v1/policies/{init.OPA_POLICY_ID}"): (
            200,
            json.dumps({"result": {"raw": expected}}),
        ),
    }
    monkeypatch.setattr(init, "_request", _fake_request(responses))
    outcome = init.step_opa_policy()
    assert outcome.result is init.InitResult.ALREADY_INITIALIZED


def test_step_opa_policy_detects_drift_and_never_overwrites(monkeypatch):
    responses = {
        ("GET", f"{init.OPA_URL}/v1/policies/{init.OPA_POLICY_ID}"): (
            200,
            json.dumps({"result": {"raw": "package ocor.bootstrap\n\ndefault allow = true\n"}}),
        ),
    }
    monkeypatch.setattr(init, "_request", _fake_request(responses))
    with pytest.raises(init.InitError, match="drift"):
        init.step_opa_policy()


def test_step_keycloak_realm_creates_when_absent(monkeypatch):
    responses = {
        ("GET", f"{init.KEYCLOAK_URL}/admin/realms/{init.OCOR_REALM}"): (404, "{}"),
        ("POST", f"{init.KEYCLOAK_URL}/admin/realms"): (201, ""),
    }
    monkeypatch.setattr(init, "_request", _fake_request(responses))
    outcome = init.step_keycloak_realm("test-token")
    assert outcome.result is init.InitResult.CREATED


def test_step_keycloak_realm_already_initialized_when_enabled(monkeypatch):
    responses = {
        ("GET", f"{init.KEYCLOAK_URL}/admin/realms/{init.OCOR_REALM}"): (
            200,
            json.dumps({"realm": init.OCOR_REALM, "enabled": True}),
        ),
    }
    monkeypatch.setattr(init, "_request", _fake_request(responses))
    outcome = init.step_keycloak_realm("test-token")
    assert outcome.result is init.InitResult.ALREADY_INITIALIZED


def test_step_keycloak_realm_detects_disabled_drift(monkeypatch):
    responses = {
        ("GET", f"{init.KEYCLOAK_URL}/admin/realms/{init.OCOR_REALM}"): (
            200,
            json.dumps({"realm": init.OCOR_REALM, "enabled": False}),
        ),
    }
    monkeypatch.setattr(init, "_request", _fake_request(responses))
    with pytest.raises(init.InitError, match="disabled"):
        init.step_keycloak_realm("test-token")


def test_step_openbao_paths_creates_when_absent(monkeypatch):
    responses = {
        ("GET", f"{init.OPENBAO_URL}/v1/sys/mounts"): (200, json.dumps({"data": {"secret/": {"type": "kv"}}})),
        ("POST", f"{init.OPENBAO_URL}/v1/sys/mounts/{init.OPENBAO_MOUNT}"): (204, ""),
    }
    monkeypatch.setattr(init, "_request", _fake_request(responses))
    outcome = init.step_openbao_paths("test-token")
    assert outcome.result is init.InitResult.CREATED


def test_step_openbao_paths_already_initialized_when_matching(monkeypatch):
    responses = {
        ("GET", f"{init.OPENBAO_URL}/v1/sys/mounts"): (
            200,
            json.dumps({"data": {f"{init.OPENBAO_MOUNT}/": {"type": "kv", "options": {"version": "2"}}}}),
        ),
    }
    monkeypatch.setattr(init, "_request", _fake_request(responses))
    outcome = init.step_openbao_paths("test-token")
    assert outcome.result is init.InitResult.ALREADY_INITIALIZED


def test_step_openbao_paths_detects_type_drift(monkeypatch):
    responses = {
        ("GET", f"{init.OPENBAO_URL}/v1/sys/mounts"): (
            200,
            json.dumps({"data": {f"{init.OPENBAO_MOUNT}/": {"type": "kv", "options": {"version": "1"}}}}),
        ),
    }
    monkeypatch.setattr(init, "_request", _fake_request(responses))
    with pytest.raises(init.InitError, match="drift"):
        init.step_openbao_paths("test-token")


def test_step_spire_trust_reports_already_initialized_for_a_real_bundle(monkeypatch):
    def fake_run(command, *, text, capture_output, check, timeout):
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"keys": [{"use": "x509-svid"}]}), stderr="")

    monkeypatch.setattr(init.subprocess, "run", fake_run)
    outcome = init.step_spire_trust()
    assert outcome.result is init.InitResult.ALREADY_INITIALIZED
    assert outcome.detail["key_count"] == 1


def test_step_spire_trust_fails_closed_on_empty_bundle(monkeypatch):
    def fake_run(command, *, text, capture_output, check, timeout):
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"keys": []}), stderr="")

    monkeypatch.setattr(init.subprocess, "run", fake_run)
    with pytest.raises(init.InitError, match="no keys"):
        init.step_spire_trust()


def test_step_spire_trust_fails_closed_on_command_error(monkeypatch):
    def fake_run(command, *, text, capture_output, check, timeout):
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="socket unreachable")

    monkeypatch.setattr(init.subprocess, "run", fake_run)
    with pytest.raises(init.InitError, match="not readable"):
        init.step_spire_trust()


def test_step_graph_databases_creates_both_when_absent(monkeypatch):
    responses = {
        ("GET", f"{init.TERMINUSDB_URL}/api/db"): (200, "[]"),
        ("POST", f"{init.TERMINUSDB_URL}/api/db/admin/{init.OCOR_DATABASE}"): (200, "{}"),
        ("POST", f"{init.TYPEDB_URL}/v1/signin"): (200, json.dumps({"token": "test-token"})),
        ("GET", f"{init.TYPEDB_URL}/v1/databases"): (200, json.dumps({"databases": []})),
        ("POST", f"{init.TYPEDB_URL}/v1/databases/{init.OCOR_DATABASE}"): (200, "{}"),
    }
    monkeypatch.setattr(init, "_request", _fake_request(responses))
    outcome = init.step_graph_databases("irrelevant-password")
    assert outcome.result is init.InitResult.CREATED
    assert outcome.detail == {"terminusdb": "CREATED", "typedb": "CREATED"}


def test_step_graph_databases_already_initialized_when_both_present(monkeypatch):
    responses = {
        ("GET", f"{init.TERMINUSDB_URL}/api/db"): (200, json.dumps([{"path": f"admin/{init.OCOR_DATABASE}"}])),
        ("POST", f"{init.TYPEDB_URL}/v1/signin"): (200, json.dumps({"token": "test-token"})),
        ("GET", f"{init.TYPEDB_URL}/v1/databases"): (200, json.dumps({"databases": [{"name": init.OCOR_DATABASE}]})),
    }
    monkeypatch.setattr(init, "_request", _fake_request(responses))
    outcome = init.step_graph_databases("irrelevant-password")
    assert outcome.result is init.InitResult.ALREADY_INITIALIZED
    assert outcome.detail == {"terminusdb": "ALREADY_INITIALIZED", "typedb": "ALREADY_INITIALIZED"}
