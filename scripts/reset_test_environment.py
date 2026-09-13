#!/usr/bin/env python3
"""OCOR-DEV-0082: reset and teardown the disposable ocor-bootstrap environment.

Two distinct, complementary operations:

* ``--reset`` undoes exactly the governed scaffolding OCOR-DEV-0080's
  initialize_services.py creates (the "ocor" Keycloak realm, the
  "ocor_bootstrap" OPA policy, the "ocor" OpenBao KV mount, and the
  "ocor_default" TerminusDB/TypeDB databases), returning the stack to the
  freshly-provisioned-but-uninitialized state OCOR-DEV-0079 leaves it in --
  without stopping a single container. SPIRE trust is deliberately left
  untouched: OCOR-DEV-0080 only ever verifies it, never creates it, so
  there is nothing for reset to undo without breaking every service's
  identity.
* ``--teardown`` (the pre-existing behavior) stops and removes the entire
  disposable Compose project, containers and volumes included.

Both are dry-run by default and require ``--execute`` to actually mutate
anything, and both are idempotent: resetting or tearing down an
already-reset/torn-down environment is a documented no-op, never an error.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from ocor_bootstrap_lib import root, run

TERMINUSDB_URL = "http://127.0.0.1:6363"
TYPEDB_URL = "http://127.0.0.1:8000"
KEYCLOAK_URL = "http://127.0.0.1:8080"
OPA_URL = "http://127.0.0.1:8181"
OPENBAO_URL = "http://127.0.0.1:8200"

OCOR_REALM = "ocor"
OCOR_DATABASE = "ocor_default"
OPA_POLICY_ID = "ocor_bootstrap"
OPENBAO_MOUNT = "ocor"


class ResetError(RuntimeError):
    """A reset step failed closed."""


def _request(
    method: str, url: str, *, headers: dict[str, str] | None = None, body: bytes | None = None, timeout: float = 10.0
) -> tuple[int, str]:
    request = urllib.request.Request(url, method=method, data=body, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def _keycloak_admin_token(password: str) -> str:
    status, body = _request(
        "POST",
        f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        body=(
            f"client_id=admin-cli&username=ocor-admin&password={urllib.parse.quote(password)}&grant_type=password"
        ).encode("utf-8"),
    )
    if status != 200:
        raise ResetError(f"cannot obtain a Keycloak admin token: {status} {body}")
    token: str = json.loads(body)["access_token"]
    return token


def reset_keycloak_realm(password: str) -> dict[str, Any]:
    token = _keycloak_admin_token(password)
    status, body = _request("GET", f"{KEYCLOAK_URL}/admin/realms/{OCOR_REALM}", headers={"Authorization": f"Bearer {token}"})
    if status == 404:
        return {"step": "keycloak_realm", "result": "ALREADY_RESET"}
    if status != 200:
        raise ResetError(f"unexpected Keycloak realm lookup status: {status} {body}")
    delete_status, delete_body = _request(
        "DELETE", f"{KEYCLOAK_URL}/admin/realms/{OCOR_REALM}", headers={"Authorization": f"Bearer {token}"}
    )
    if delete_status != 204:
        raise ResetError(f"failed to delete Keycloak realm {OCOR_REALM!r}: {delete_status} {delete_body}")
    return {"step": "keycloak_realm", "result": "RESET"}


def reset_opa_policy() -> dict[str, Any]:
    status, _ = _request("GET", f"{OPA_URL}/v1/policies/{OPA_POLICY_ID}")
    if status == 404:
        return {"step": "opa_policy", "result": "ALREADY_RESET"}
    if status != 200:
        raise ResetError(f"unexpected OPA policy lookup status: {status}")
    delete_status, delete_body = _request("DELETE", f"{OPA_URL}/v1/policies/{OPA_POLICY_ID}")
    if delete_status != 200:
        raise ResetError(f"failed to delete OPA policy {OPA_POLICY_ID!r}: {delete_status} {delete_body}")
    return {"step": "opa_policy", "result": "RESET"}


def reset_openbao_paths(root_token: str) -> dict[str, Any]:
    headers = {"X-Vault-Token": root_token}
    status, body = _request("GET", f"{OPENBAO_URL}/v1/sys/mounts", headers=headers)
    if status != 200:
        raise ResetError(f"cannot list OpenBao mounts: {status} {body}")
    mounts = json.loads(body).get("data", {})
    if f"{OPENBAO_MOUNT}/" not in mounts:
        return {"step": "openbao_paths", "result": "ALREADY_RESET"}
    delete_status, delete_body = _request("DELETE", f"{OPENBAO_URL}/v1/sys/mounts/{OPENBAO_MOUNT}", headers=headers)
    if delete_status != 204:
        raise ResetError(f"failed to unmount OpenBao path {OPENBAO_MOUNT!r}: {delete_status} {delete_body}")
    return {"step": "openbao_paths", "result": "RESET"}


def reset_graph_databases(terminusdb_password: str) -> dict[str, Any]:
    detail: dict[str, str] = {}
    credentials = f"admin:{terminusdb_password}".encode()
    tdb_headers = {"Authorization": f"Basic {base64.b64encode(credentials).decode()}"}
    status, body = _request("GET", f"{TERMINUSDB_URL}/api/db", headers=tdb_headers)
    if status != 200:
        raise ResetError(f"cannot list TerminusDB databases: {status} {body}")
    existing_terminus = {entry["path"].split("/")[-1] for entry in json.loads(body)}
    if OCOR_DATABASE not in existing_terminus:
        detail["terminusdb"] = "ALREADY_RESET"
    else:
        delete_status, delete_body = _request(
            "DELETE", f"{TERMINUSDB_URL}/api/db/admin/{OCOR_DATABASE}", headers=tdb_headers
        )
        if delete_status != 200:
            raise ResetError(f"failed to delete TerminusDB database {OCOR_DATABASE!r}: {delete_status} {delete_body}")
        detail["terminusdb"] = "RESET"

    signin_status, signin_body = _request(
        "POST",
        f"{TYPEDB_URL}/v1/signin",
        headers={"Content-Type": "application/json"},
        body=json.dumps({"username": "admin", "password": "password"}).encode("utf-8"),
    )
    if signin_status != 200:
        raise ResetError(f"cannot sign in to TypeDB: {signin_status} {signin_body}")
    typedb_token = json.loads(signin_body)["token"]
    typedb_headers = {"Authorization": f"Bearer {typedb_token}"}
    list_status, list_body = _request("GET", f"{TYPEDB_URL}/v1/databases", headers=typedb_headers)
    if list_status != 200:
        raise ResetError(f"cannot list TypeDB databases: {list_status} {list_body}")
    existing_typedb = {entry["name"] for entry in json.loads(list_body).get("databases", [])}
    if OCOR_DATABASE not in existing_typedb:
        detail["typedb"] = "ALREADY_RESET"
    else:
        delete_status, delete_body = _request(
            "DELETE", f"{TYPEDB_URL}/v1/databases/{OCOR_DATABASE}", headers=typedb_headers
        )
        if delete_status != 200:
            raise ResetError(f"failed to delete TypeDB database {OCOR_DATABASE!r}: {delete_status} {delete_body}")
        detail["typedb"] = "RESET"

    overall = "RESET" if "RESET" in detail.values() else "ALREADY_RESET"
    return {"step": "graph_databases", "result": overall, "detail": detail}


def reset(*, terminusdb_password: str, keycloak_password: str, openbao_root_token: str) -> list[dict[str, Any]]:
    return [
        reset_keycloak_realm(keycloak_password),
        reset_opa_policy(),
        reset_openbao_paths(openbao_root_token),
        reset_graph_databases(terminusdb_password),
    ]


def teardown_command(repository: Path) -> list[str]:
    env_file = repository / ".ocor" / "bootstrap.env"
    command = ["docker", "compose"]
    if env_file.exists():
        command.extend(["--env-file", str(env_file)])
    command.extend(["-p", "ocor-bootstrap", "-f", "deploy/bootstrap/compose.yaml", "down", "--volumes", "--remove-orphans"])
    return command


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="undo OCOR-DEV-0080's initialization, keep containers")
    parser.add_argument("--env-file", type=Path, help="file with OCOR_LOCAL_* secrets (required with --reset)")
    parser.add_argument("--execute", action="store_true", help="confirm the mutating operation")
    args = parser.parse_args()
    repository = root()

    if args.reset:
        if args.env_file is None:
            print(json.dumps({"status": "ERROR", "error": "--reset requires --env-file"}, sort_keys=True))
            return 2
        env: dict[str, str] = {}
        for line in args.env_file.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                key, _, value = line.partition("=")
                env[key] = value
        if not args.execute:
            print(json.dumps({"status": "PASS", "mode": "DRY_RUN", "operation": "reset"}, indent=2, sort_keys=True))
            return 0
        try:
            steps = reset(
                terminusdb_password=env["OCOR_LOCAL_TERMINUSDB_PASSWORD"],
                keycloak_password=env["OCOR_LOCAL_KEYCLOAK_PASSWORD"],
                openbao_root_token=env["OCOR_LOCAL_OPENBAO_TOKEN"],
            )
            print(json.dumps({"status": "PASS", "steps": steps}, indent=2, sort_keys=True))
            return 0
        except (ResetError, KeyError, OSError, json.JSONDecodeError) as exc:
            print(json.dumps({"status": "FAIL", "error": str(exc)}, sort_keys=True))
            return 1

    command = teardown_command(repository)
    if not args.execute:
        print(json.dumps({"status": "PASS", "mode": "DRY_RUN", "command": command}, indent=2))
        return 0
    result = run(command, cwd=repository, timeout=180)
    print(json.dumps({"status": "PASS" if result.returncode == 0 else "ERROR", "stderr": result.stderr[-1000:]}, indent=2))
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
