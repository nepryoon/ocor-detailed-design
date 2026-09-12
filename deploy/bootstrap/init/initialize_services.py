#!/usr/bin/env python3
"""OCOR-DEV-0080: deterministic, idempotent, ordered service initialization.

Runs the 5 steps declared in this directory's README, in the declared order
(SPIRE trust, Keycloak realm, OPA policy, OpenBao paths, graph databases),
against the real disposable stack `deploy/bootstrap/compose.yaml` starts.
Every step is idempotent: it first checks whether the target already exists
in the exact expected shape and, if so, reports ``ALREADY_INITIALIZED``
without mutating anything; if it exists but differs from the expected shape,
it reports ``DRIFT_DETECTED`` and fails closed rather than silently
overwriting or ignoring the difference. Nothing here authors real security
policy content (OPA/Keycloak authorization rules are WS-11's scope, not
WS-12's) -- the OPA step seeds only a fail-closed default-deny placeholder
that establishes a safe initial state.
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

TERMINUSDB_URL = "http://127.0.0.1:6363"
TYPEDB_URL = "http://127.0.0.1:8000"
KEYCLOAK_URL = "http://127.0.0.1:8080"
OPA_URL = "http://127.0.0.1:8181"
OPENBAO_URL = "http://127.0.0.1:8200"

OCOR_REALM = "ocor"
OCOR_DATABASE = "ocor_default"
OPA_POLICY_ID = "ocor_bootstrap"
OPA_POLICY_PATH = Path(__file__).with_name("opa").joinpath("bootstrap.rego")
OPENBAO_MOUNT = "ocor"


class InitError(RuntimeError):
    """A deterministic initialization step failed closed."""


class InitResult(str, Enum):
    CREATED = "CREATED"
    ALREADY_INITIALIZED = "ALREADY_INITIALIZED"
    DRIFT_DETECTED = "DRIFT_DETECTED"


@dataclass(frozen=True)
class StepOutcome:
    step: str
    result: InitResult
    detail: dict[str, Any]

    def to_json(self) -> dict[str, Any]:
        return {"step": self.step, "result": self.result.value, "detail": self.detail}


def _request(
    method: str, url: str, *, headers: dict[str, str] | None = None, body: bytes | None = None, timeout: float = 10.0
) -> tuple[int, str]:
    request = urllib.request.Request(url, method=method, data=body, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def step_spire_trust() -> StepOutcome:
    """Verify (never mutate) that the SPIRE trust bundle established at
    compose-up time is present and non-empty. Trust material itself is
    provisioned once, out of band, by the operator-supplied bootstrap CA
    (see reports/evidence/G2/OCOR-DEV-0079.json); this step's job is
    idempotent verification, not (re)issuance.
    """
    completed = subprocess.run(
        [
            "docker", "exec", "ocor-bootstrap-spire-server-1",
            "/opt/spire/bin/spire-server", "bundle", "show",
            "-socketPath", "/run/spire/sockets/server.sock", "-format", "spiffe",
        ],
        text=True,
        capture_output=True,
        check=False,
        timeout=15,
    )
    if completed.returncode != 0:
        raise InitError(f"SPIRE trust bundle is not readable: {completed.stderr.strip()}")
    try:
        bundle = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise InitError(f"SPIRE trust bundle is not valid JSON: {exc}") from exc
    keys = bundle.get("keys", [])
    if not keys:
        raise InitError("SPIRE trust bundle has no keys")
    return StepOutcome("spire_trust", InitResult.ALREADY_INITIALIZED, {"key_count": len(keys)})


def step_keycloak_realm(admin_token: str) -> StepOutcome:
    headers = {"Authorization": f"Bearer {admin_token}"}
    status, body = _request("GET", f"{KEYCLOAK_URL}/admin/realms/{OCOR_REALM}", headers=headers)
    if status == 200:
        realm = json.loads(body)
        if realm.get("enabled") is not True:
            raise InitError(f"realm {OCOR_REALM!r} exists but is disabled (drift)")
        return StepOutcome("keycloak_realm", InitResult.ALREADY_INITIALIZED, {"realm": OCOR_REALM})
    if status != 404:
        raise InitError(f"unexpected Keycloak realm lookup status: {status}")
    create_status, create_body = _request(
        "POST",
        f"{KEYCLOAK_URL}/admin/realms",
        headers={**headers, "Content-Type": "application/json"},
        body=json.dumps({"realm": OCOR_REALM, "enabled": True}).encode("utf-8"),
    )
    if create_status != 201:
        raise InitError(f"failed to create Keycloak realm {OCOR_REALM!r}: {create_status} {create_body}")
    return StepOutcome("keycloak_realm", InitResult.CREATED, {"realm": OCOR_REALM})


def step_opa_policy() -> StepOutcome:
    expected = OPA_POLICY_PATH.read_text(encoding="utf-8")
    status, body = _request("GET", f"{OPA_URL}/v1/policies/{OPA_POLICY_ID}")
    if status == 200:
        current = json.loads(body).get("result", {}).get("raw", "")
        if current == expected:
            return StepOutcome("opa_policy", InitResult.ALREADY_INITIALIZED, {"policy_id": OPA_POLICY_ID})
        raise InitError(f"OPA policy {OPA_POLICY_ID!r} exists with different content (drift)")
    if status != 404:
        raise InitError(f"unexpected OPA policy lookup status: {status}")
    put_status, put_body = _request(
        "PUT",
        f"{OPA_URL}/v1/policies/{OPA_POLICY_ID}",
        headers={"Content-Type": "text/plain"},
        body=expected.encode("utf-8"),
    )
    if put_status != 200:
        raise InitError(f"failed to load OPA policy {OPA_POLICY_ID!r}: {put_status} {put_body}")
    return StepOutcome("opa_policy", InitResult.CREATED, {"policy_id": OPA_POLICY_ID})


def step_openbao_paths(root_token: str) -> StepOutcome:
    headers = {"X-Vault-Token": root_token}
    status, body = _request("GET", f"{OPENBAO_URL}/v1/sys/mounts", headers=headers)
    if status != 200:
        raise InitError(f"cannot list OpenBao mounts: {status} {body}")
    mounts = json.loads(body).get("data", {})
    existing = mounts.get(f"{OPENBAO_MOUNT}/")
    if existing is not None:
        if existing.get("type") != "kv" or existing.get("options", {}).get("version") != "2":
            raise InitError(f"OpenBao mount {OPENBAO_MOUNT!r} exists with a different type/version (drift)")
        return StepOutcome("openbao_paths", InitResult.ALREADY_INITIALIZED, {"mount": OPENBAO_MOUNT})
    create_status, create_body = _request(
        "POST",
        f"{OPENBAO_URL}/v1/sys/mounts/{OPENBAO_MOUNT}",
        headers={**headers, "Content-Type": "application/json"},
        body=json.dumps(
            {"type": "kv", "options": {"version": "2"}, "description": "OCOR governed secrets (deterministic init)"}
        ).encode("utf-8"),
    )
    if create_status != 204:
        raise InitError(f"failed to mount OpenBao path {OPENBAO_MOUNT!r}: {create_status} {create_body}")
    return StepOutcome("openbao_paths", InitResult.CREATED, {"mount": OPENBAO_MOUNT})


def step_graph_databases(terminusdb_password: str) -> StepOutcome:
    detail: dict[str, Any] = {}
    outcomes: list[InitResult] = []

    tdb_credentials = f"admin:{terminusdb_password}".encode()
    tdb_headers = {"Authorization": f"Basic {base64.b64encode(tdb_credentials).decode()}"}
    status, body = _request("GET", f"{TERMINUSDB_URL}/api/db", headers=tdb_headers)
    if status != 200:
        raise InitError(f"cannot list TerminusDB databases: {status} {body}")
    existing_terminus = {entry["path"].split("/")[-1] for entry in json.loads(body)}
    if OCOR_DATABASE in existing_terminus:
        outcomes.append(InitResult.ALREADY_INITIALIZED)
        detail["terminusdb"] = "ALREADY_INITIALIZED"
    else:
        create_status, create_body = _request(
            "POST",
            f"{TERMINUSDB_URL}/api/db/admin/{OCOR_DATABASE}",
            headers={**tdb_headers, "Content-Type": "application/json"},
            body=json.dumps({"label": OCOR_DATABASE, "comment": "OCOR default database (deterministic init)"}).encode(
                "utf-8"
            ),
        )
        if create_status != 200:
            raise InitError(f"failed to create TerminusDB database {OCOR_DATABASE!r}: {create_status} {create_body}")
        outcomes.append(InitResult.CREATED)
        detail["terminusdb"] = "CREATED"

    signin_status, signin_body = _request(
        "POST",
        f"{TYPEDB_URL}/v1/signin",
        headers={"Content-Type": "application/json"},
        body=json.dumps({"username": "admin", "password": "password"}).encode("utf-8"),
    )
    if signin_status != 200:
        raise InitError(f"cannot sign in to TypeDB: {signin_status} {signin_body}")
    typedb_token = json.loads(signin_body)["token"]
    typedb_headers = {"Authorization": f"Bearer {typedb_token}"}
    list_status, list_body = _request("GET", f"{TYPEDB_URL}/v1/databases", headers=typedb_headers)
    if list_status != 200:
        raise InitError(f"cannot list TypeDB databases: {list_status} {list_body}")
    existing_typedb = {entry["name"] for entry in json.loads(list_body).get("databases", [])}
    if OCOR_DATABASE in existing_typedb:
        outcomes.append(InitResult.ALREADY_INITIALIZED)
        detail["typedb"] = "ALREADY_INITIALIZED"
    else:
        create_status, create_body = _request(
            "POST", f"{TYPEDB_URL}/v1/databases/{OCOR_DATABASE}", headers=typedb_headers
        )
        if create_status != 200:
            raise InitError(f"failed to create TypeDB database {OCOR_DATABASE!r}: {create_status} {create_body}")
        outcomes.append(InitResult.CREATED)
        detail["typedb"] = "CREATED"

    overall = InitResult.CREATED if InitResult.CREATED in outcomes else InitResult.ALREADY_INITIALIZED
    return StepOutcome("graph_databases", overall, detail)


def run(*, terminusdb_password: str, keycloak_admin_token: str, openbao_root_token: str) -> list[StepOutcome]:
    return [
        step_spire_trust(),
        step_keycloak_realm(keycloak_admin_token),
        step_opa_policy(),
        step_openbao_paths(openbao_root_token),
        step_graph_databases(terminusdb_password),
    ]


def _keycloak_admin_token(password: str) -> str:
    status, body = _request(
        "POST",
        f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        body=(
            f"client_id=admin-cli&username=ocor-admin&password={urllib.parse.quote(password)}"
            "&grant_type=password"
        ).encode("utf-8"),
    )
    if status != 200:
        raise InitError(f"cannot obtain a Keycloak admin token: {status} {body}")
    token: str = json.loads(body)["access_token"]
    return token


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
        keycloak_admin_token = _keycloak_admin_token(env["OCOR_LOCAL_KEYCLOAK_PASSWORD"])
        outcomes = run(
            terminusdb_password=env["OCOR_LOCAL_TERMINUSDB_PASSWORD"],
            keycloak_admin_token=keycloak_admin_token,
            openbao_root_token=env["OCOR_LOCAL_OPENBAO_TOKEN"],
        )
        status = "PASS"
        print(json.dumps({"status": status, "steps": [outcome.to_json() for outcome in outcomes]}, indent=2, sort_keys=True))
        return 0
    except (InitError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    sys.exit(main())
