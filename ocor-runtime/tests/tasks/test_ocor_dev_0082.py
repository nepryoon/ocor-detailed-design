"""OCOR-DEV-0082: reset and teardown of the disposable ocor-bootstrap environment.

Unit/negative/contract coverage for scripts/reset_test_environment.py's
--reset step logic, with every network call replaced by a deterministic
fake -- no live Docker dependency (those are exercised for real, once, in
the sealed evidence at reports/evidence/G2/OCOR-DEV-0082.json, captured
against the live 11-service stack, including a full reset -> re-init
round-trip proving reset genuinely returns to OCOR-DEV-0079's baseline).

--teardown itself is a thin wrapper around `docker compose ... down` and is
exercised structurally here (the exact command it would run); actually
tearing the stack down is destructive to every other backlog task still
depending on it and is out of scope for this suite.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "scripts/reset_test_environment.py"
sys.path.insert(0, str(ROOT / "scripts"))

SPEC = importlib.util.spec_from_file_location("reset_test_environment_0082", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
reset_mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = reset_mod
SPEC.loader.exec_module(reset_mod)


def _fake_request(responses: dict[tuple[str, str], tuple[int, str]]):
    def fake(method: str, url: str, *, headers: Any = None, body: Any = None, timeout: float = 10.0) -> tuple[int, str]:
        key = (method, url)
        if key not in responses:
            raise AssertionError(f"unexpected request: {method} {url}")
        return responses[key]

    return fake


def test_teardown_command_targets_only_the_ocor_bootstrap_project():
    command = reset_mod.teardown_command(ROOT)
    assert "-p" in command and command[command.index("-p") + 1] == "ocor-bootstrap"
    assert "down" in command and "--volumes" in command and "--remove-orphans" in command


def test_reset_keycloak_realm_deletes_when_present(monkeypatch):
    token_body = json.dumps({"access_token": "fake-token"})
    responses = {
        ("POST", f"{reset_mod.KEYCLOAK_URL}/realms/master/protocol/openid-connect/token"): (200, token_body),
        ("GET", f"{reset_mod.KEYCLOAK_URL}/admin/realms/{reset_mod.OCOR_REALM}"): (
            200,
            json.dumps({"realm": "ocor", "enabled": True}),
        ),
        ("DELETE", f"{reset_mod.KEYCLOAK_URL}/admin/realms/{reset_mod.OCOR_REALM}"): (204, ""),
    }
    monkeypatch.setattr(reset_mod, "_request", _fake_request(responses))
    outcome = reset_mod.reset_keycloak_realm("irrelevant-password")
    assert outcome["result"] == "RESET"


def test_reset_keycloak_realm_already_reset_when_absent(monkeypatch):
    token_body = json.dumps({"access_token": "fake-token"})
    responses = {
        ("POST", f"{reset_mod.KEYCLOAK_URL}/realms/master/protocol/openid-connect/token"): (200, token_body),
        ("GET", f"{reset_mod.KEYCLOAK_URL}/admin/realms/{reset_mod.OCOR_REALM}"): (404, "{}"),
    }
    monkeypatch.setattr(reset_mod, "_request", _fake_request(responses))
    outcome = reset_mod.reset_keycloak_realm("irrelevant-password")
    assert outcome["result"] == "ALREADY_RESET"


def test_reset_opa_policy_deletes_when_present(monkeypatch):
    responses = {
        ("GET", f"{reset_mod.OPA_URL}/v1/policies/{reset_mod.OPA_POLICY_ID}"): (200, json.dumps({"result": {}})),
        ("DELETE", f"{reset_mod.OPA_URL}/v1/policies/{reset_mod.OPA_POLICY_ID}"): (200, "{}"),
    }
    monkeypatch.setattr(reset_mod, "_request", _fake_request(responses))
    outcome = reset_mod.reset_opa_policy()
    assert outcome["result"] == "RESET"


def test_reset_opa_policy_already_reset_when_absent(monkeypatch):
    responses = {
        ("GET", f"{reset_mod.OPA_URL}/v1/policies/{reset_mod.OPA_POLICY_ID}"): (404, "{}"),
    }
    monkeypatch.setattr(reset_mod, "_request", _fake_request(responses))
    outcome = reset_mod.reset_opa_policy()
    assert outcome["result"] == "ALREADY_RESET"


def test_reset_openbao_paths_deletes_when_present(monkeypatch):
    responses = {
        ("GET", f"{reset_mod.OPENBAO_URL}/v1/sys/mounts"): (
            200,
            json.dumps({"data": {f"{reset_mod.OPENBAO_MOUNT}/": {"type": "kv"}}}),
        ),
        ("DELETE", f"{reset_mod.OPENBAO_URL}/v1/sys/mounts/{reset_mod.OPENBAO_MOUNT}"): (204, ""),
    }
    monkeypatch.setattr(reset_mod, "_request", _fake_request(responses))
    outcome = reset_mod.reset_openbao_paths("irrelevant-token")
    assert outcome["result"] == "RESET"


def test_reset_openbao_paths_already_reset_when_absent(monkeypatch):
    responses = {
        ("GET", f"{reset_mod.OPENBAO_URL}/v1/sys/mounts"): (200, json.dumps({"data": {"secret/": {"type": "kv"}}})),
    }
    monkeypatch.setattr(reset_mod, "_request", _fake_request(responses))
    outcome = reset_mod.reset_openbao_paths("irrelevant-token")
    assert outcome["result"] == "ALREADY_RESET"


def test_reset_graph_databases_deletes_both_when_present(monkeypatch):
    responses = {
        ("GET", f"{reset_mod.TERMINUSDB_URL}/api/db"): (200, json.dumps([{"path": f"admin/{reset_mod.OCOR_DATABASE}"}])),
        ("DELETE", f"{reset_mod.TERMINUSDB_URL}/api/db/admin/{reset_mod.OCOR_DATABASE}"): (200, "{}"),
        ("POST", f"{reset_mod.TYPEDB_URL}/v1/signin"): (200, json.dumps({"token": "fake-token"})),
        ("GET", f"{reset_mod.TYPEDB_URL}/v1/databases"): (200, json.dumps({"databases": [{"name": reset_mod.OCOR_DATABASE}]})),
        ("DELETE", f"{reset_mod.TYPEDB_URL}/v1/databases/{reset_mod.OCOR_DATABASE}"): (200, "{}"),
    }
    monkeypatch.setattr(reset_mod, "_request", _fake_request(responses))
    outcome = reset_mod.reset_graph_databases("irrelevant-password")
    assert outcome["result"] == "RESET"
    assert outcome["detail"] == {"terminusdb": "RESET", "typedb": "RESET"}


def test_reset_graph_databases_already_reset_when_absent(monkeypatch):
    responses = {
        ("GET", f"{reset_mod.TERMINUSDB_URL}/api/db"): (200, "[]"),
        ("POST", f"{reset_mod.TYPEDB_URL}/v1/signin"): (200, json.dumps({"token": "fake-token"})),
        ("GET", f"{reset_mod.TYPEDB_URL}/v1/databases"): (200, json.dumps({"databases": []})),
    }
    monkeypatch.setattr(reset_mod, "_request", _fake_request(responses))
    outcome = reset_mod.reset_graph_databases("irrelevant-password")
    assert outcome["result"] == "ALREADY_RESET"
    assert outcome["detail"] == {"terminusdb": "ALREADY_RESET", "typedb": "ALREADY_RESET"}


def test_reset_requires_env_file_argument(monkeypatch, capsys):
    # argparse itself does not make --env-file conditionally required on
    # --reset, so main() carries its own explicit guard -- this exercises
    # that guard, not argparse's.
    monkeypatch.setattr(sys, "argv", ["reset_test_environment.py", "--reset", "--execute"])
    exit_code = reset_mod.main()
    assert exit_code == 2
    assert "requires --env-file" in capsys.readouterr().out
