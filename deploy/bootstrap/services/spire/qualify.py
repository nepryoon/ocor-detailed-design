#!/usr/bin/env python3
"""Fail-closed qualification and bounded recovery for local SPIRE provisioning."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


SERVER = "ocor-bootstrap-spire-server-1"
AGENT = "ocor-bootstrap-spire-agent-1"
SERVER_SOCKET = "/run/spire/sockets/server.sock"
AGENT_SOCKET = "/run/spire/sockets/agent.sock"
WORKLOAD_ID = "spiffe://ocor.test/workload/ocor-dev-0077"
IMAGE = re.compile(r"^ghcr\.io/spiffe/spire-(server|agent)@sha256:[0-9a-f]{64}$")


class QualificationError(RuntimeError):
    """A mandatory SPIRE qualification control failed."""


def run(command: list[str], *, timeout: float = 30, check: bool = True) -> str:
    try:
        completed = subprocess.run(
            command, check=False, capture_output=True, text=True, timeout=timeout
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise QualificationError(f"command unavailable or timed out: {command[0]}") from exc
    if check and completed.returncode:
        raise QualificationError(f"command failed ({completed.returncode}): {command[0]}")
    return completed.stdout if completed.stdout else completed.stderr


def validate_lock(lock: dict[str, Any]) -> dict[str, dict[str, Any]]:
    selected = [
        item
        for item in lock.get("services", [])
        if item.get("id") in {"spire-server", "spire-agent"}
    ]
    counts = {
        identifier: sum(item.get("id") == identifier for item in selected)
        for identifier in ("spire-server", "spire-agent")
    }
    if counts != {"spire-server": 1, "spire-agent": 1}:
        raise QualificationError("service lock must contain one SPIRE server and agent")
    pair = {str(item["id"]): item for item in selected}
    for identifier, entry in pair.items():
        expected_source = f"https://github.com/spiffe/spire/pkgs/container/{identifier}"
        if not IMAGE.fullmatch(str(entry.get("image", ""))):
            raise QualificationError(f"{identifier} image is not digest-pinned")
        if entry.get("version") != "1.15.3" or entry.get("source") != expected_source:
            raise QualificationError(f"{identifier} version or source differs from policy")
        if entry.get("official_source") is not True or entry.get("license") != "Apache-2.0":
            raise QualificationError(f"{identifier} provenance metadata differs from policy")
    return pair


def validate_configs(server: str, agent: str) -> None:
    def exact(config: str, key: str, expected: str) -> None:
        observed = re.findall(
            rf'^\s*{re.escape(key)}\s*=\s*"([^"]+)"\s*$', config, flags=re.MULTILINE
        )
        if observed != [expected]:
            raise QualificationError(f"SPIRE config requires exactly one {key}={expected}")

    exact(server, "trust_domain", "ocor.test")
    exact(server, "socket_path", "/run/spire/sockets/server.sock")
    exact(server, "bind_address", "0.0.0.0")
    exact(agent, "trust_domain", "ocor.test")
    exact(agent, "socket_path", "/run/spire/sockets/agent.sock")
    exact(agent, "server_address", "spire-server")


def validate_inspection(
    inspection: dict[str, Any], expected_image: str, identifier: str
) -> dict[str, Any]:
    if inspection.get("Config", {}).get("Image") != expected_image:
        raise QualificationError(f"running {identifier} image differs from the lock")
    state = inspection.get("State", {})
    if state.get("Running") is not True or state.get("Paused") is True:
        raise QualificationError(f"{identifier} is not running and unpaused")
    if identifier == "spire-server" and state.get("Health", {}).get("Status") != "healthy":
        raise QualificationError("SPIRE server Docker health is not healthy")
    ports = inspection.get("NetworkSettings", {}).get("Ports") or {}
    if any(bindings for bindings in ports.values()):
        raise QualificationError(f"{identifier} unexpectedly publishes a host port")
    if inspection.get("HostConfig", {}).get("SecurityOpt") != ["no-new-privileges:true"]:
        raise QualificationError(f"{identifier} lacks no-new-privileges")
    return {"image": expected_image, "running": True, "host_ports": 0}


def inspect(container: str) -> dict[str, Any]:
    payload = json.loads(run(["docker", "inspect", container]))
    if not isinstance(payload, list) or len(payload) != 1:
        raise QualificationError("docker inspect returned an unexpected result")
    return payload[0]


def replace_env(path: Path, key: str, value: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", value):
        raise QualificationError("generated token has an invalid representation")
    if not path.is_file() or path.stat().st_mode & 0o077:
        raise QualificationError("environment file must exist with mode 0600")
    entries = dict(
        line.split("=", 1)
        for line in path.read_text(encoding="utf-8").splitlines()
        if "=" in line
    )
    entries[key] = value
    handle, temporary = tempfile.mkstemp(prefix=".bootstrap.", dir=path.parent)
    try:
        os.fchmod(handle, 0o600)
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write("".join(f"{name}={item}\n" for name, item in sorted(entries.items())))
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def wait_agent(timeout: float = 45) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        inspection = inspect(AGENT)
        if inspection.get("State", {}).get("Running"):
            command = [
                "docker", "exec", AGENT, "/opt/spire/bin/spire-agent", "healthcheck",
                "-socketPath", AGENT_SOCKET,
            ]
            try:
                run(command, timeout=5)
                return
            except QualificationError:
                pass
        time.sleep(0.5)
    raise QualificationError("SPIRE agent did not become healthy within the bound")


def agent_id(value: Any) -> str:
    if not isinstance(value, dict):
        raise QualificationError("attested agent ID has an unexpected representation")
    identity = f"spiffe://{value.get('trust_domain', '')}{value.get('path', '')}"
    if not identity.startswith("spiffe://ocor.test/spire/agent/"):
        raise QualificationError("attested agent has an unexpected SPIFFE ID")
    return identity


def prune_superseded_agents() -> tuple[str, int]:
    agents = json.loads(run([
        "docker", "exec", SERVER, "/opt/spire/bin/spire-server", "agent", "list",
        "-socketPath", SERVER_SOCKET, "-output", "json",
    ])).get("agents", [])
    if not agents:
        raise QualificationError("SPIRE server reports no attested agent")
    current = max(agents, key=lambda item: int(item.get("x509svid_expires_at", 0)))
    current_id = agent_id(current.get("id"))
    stale = [agent_id(item.get("id")) for item in agents if item is not current]
    for identity in stale:
        run([
            "docker", "exec", SERVER, "/opt/spire/bin/spire-server", "agent", "evict",
            "-socketPath", SERVER_SOCKET, "-spiffeID", identity,
        ])
    return current_id, len(stale)


def recover_agent(env_file: Path, compose_file: Path) -> dict[str, Any]:
    token_payload = json.loads(
        run([
            "docker", "exec", SERVER, "/opt/spire/bin/spire-server", "token", "generate",
            "-socketPath", SERVER_SOCKET, "-ttl", "600", "-output", "json",
        ])
    )
    token = str(token_payload.get("value", ""))
    replace_env(env_file, "OCOR_SPIRE_JOIN_TOKEN", token)
    run([
        "docker", "compose", "--env-file", str(env_file), "-p", "ocor-bootstrap",
        "-f", str(compose_file), "up", "--detach", "--force-recreate", "--no-deps",
        "spire-agent",
    ], timeout=60)
    wait_agent()
    _, pruned = prune_superseded_agents()
    return {
        "token_rotated": True,
        "agent_recreated": True,
        "agent_health": "READY",
        "superseded_agents_pruned": pruned,
    }


def validate_svid_output(output: str) -> str:
    identities = set(re.findall(r"spiffe://[^\s\"']+", output))
    if WORKLOAD_ID not in identities:
        raise QualificationError("expected workload SVID was not issued")
    return WORKLOAD_ID


def cleanup_workload_entries() -> int:
    payload = json.loads(run([
        "docker", "exec", SERVER, "/opt/spire/bin/spire-server", "entry", "show",
        "-socketPath", SERVER_SOCKET, "-output", "json",
    ]))
    stale = [
        str(entry["id"])
        for entry in payload.get("entries", [])
        if entry.get("spiffe_id")
        == {"trust_domain": "ocor.test", "path": "/workload/ocor-dev-0077"}
    ]
    for entry_id in stale:
        run([
            "docker", "exec", SERVER, "/opt/spire/bin/spire-server", "entry", "delete",
            "-socketPath", SERVER_SOCKET, "-entryID", entry_id,
        ])
    return len(stale)


def workload_svid() -> dict[str, Any]:
    cleanup_workload_entries()
    agents = json.loads(run([
        "docker", "exec", SERVER, "/opt/spire/bin/spire-server", "agent", "list",
        "-socketPath", SERVER_SOCKET, "-output", "json",
    ])).get("agents", [])
    if not agents:
        raise QualificationError("SPIRE server reports no attested agent")
    parent = max(agents, key=lambda item: int(item.get("x509svid_expires_at", 0))).get("id")
    parent_id = agent_id(parent)
    created = json.loads(run([
        "docker", "exec", SERVER, "/opt/spire/bin/spire-server", "entry", "create",
        "-socketPath", SERVER_SOCKET, "-parentID", str(parent_id),
        "-spiffeID", WORKLOAD_ID, "-selector", "unix:uid:0", "-x509SVIDTTL", "300",
        "-output", "json",
    ]))
    entries = created.get("entries") or [
        item.get("entry", {})
        for item in created.get("results", [])
        if item.get("status", {}).get("code") in (0, None)
    ] or ([created] if created.get("id") else [])
    if len(entries) != 1 or not entries[0].get("id"):
        raise QualificationError("SPIRE workload registration returned no entry ID")
    entry_id = str(entries[0]["id"])
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            output = run([
                "docker", "exec", AGENT, "/opt/spire/bin/spire-agent", "api", "fetch", "x509",
                "-socketPath", AGENT_SOCKET,
            ], timeout=8, check=False)
            try:
                identity = validate_svid_output(output)
                return {"workload_svid": identity, "entry_cleanup": "PENDING"}
            except QualificationError:
                time.sleep(0.5)
        raise QualificationError("workload SVID was not delivered within the bound")
    finally:
        run([
            "docker", "exec", SERVER, "/opt/spire/bin/spire-server", "entry", "delete",
            "-socketPath", SERVER_SOCKET, "-entryID", entry_id,
        ])
        if cleanup_workload_entries():
            raise QualificationError("workload registration cleanup was incomplete")


def bounded_fault() -> dict[str, Any]:
    run(["docker", "pause", AGENT])
    unavailable = False
    try:
        try:
            run([
                "docker", "exec", AGENT, "/opt/spire/bin/spire-agent", "healthcheck",
                "-socketPath", AGENT_SOCKET,
            ], timeout=2)
        except QualificationError:
            unavailable = True
    finally:
        run(["docker", "unpause", AGENT])
    if not unavailable:
        raise QualificationError("paused SPIRE agent did not fail closed")
    wait_agent()
    return {"paused_agent_unavailable": True, "unpause_recovery": "PASS"}


def container_absent(name: str) -> bool:
    inspected = subprocess.run(
        ["docker", "inspect", name], capture_output=True, text=True, check=False, timeout=10
    )
    if inspected.returncode == 0:
        return False
    if "no such object" in inspected.stderr.lower():
        return True
    raise QualificationError("invalid-token container absence could not be established")


def remove_container(name: str, *, allow_absent: bool) -> None:
    removed = subprocess.run(
        ["docker", "rm", "--force", name], capture_output=True, text=True, check=False, timeout=15
    )
    if removed.returncode:
        if allow_absent and container_absent(name):
            return
        raise QualificationError("invalid-token container removal failed")
    if not container_absent(name):
        raise QualificationError("invalid-token container remains after removal")


def invalid_token_control(
    *, image: str, agent_config: Path, bootstrap_dir: Path
) -> dict[str, Any]:
    name = "ocor-dev-0077-invalid-token"
    remove_container(name, allow_absent=True)
    unready = False
    try:
        run([
            "docker", "run", "--detach", "--name", name,
            "--network", "ocor-bootstrap_ocor-bootstrap",
            "--security-opt", "no-new-privileges:true",
            "--mount", f"type=bind,src={agent_config.resolve()},dst=/run/spire/config/agent.conf,readonly",
            "--mount", f"type=bind,src={bootstrap_dir.resolve()},dst=/run/spire/bootstrap,readonly",
            "--tmpfs", "/run/spire/data:rw,noexec,nosuid,size=128m",
            "--tmpfs", "/run/spire/sockets:rw,noexec,nosuid,size=16m",
            image, "-config", "/run/spire/config/agent.conf",
            "-joinToken", "invalid-negative-control",
        ])
        time.sleep(3)
        health = subprocess.run(
            [
                "docker", "exec", name, "/opt/spire/bin/spire-agent", "healthcheck",
                "-socketPath", AGENT_SOCKET,
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if health.returncode == 0:
            raise QualificationError("invalid-token SPIRE agent became healthy")
        unready = True
    finally:
        remove_container(name, allow_absent=False)
    return {"invalid_token_agent_unready": unready, "cleanup": "PASS"}


def env_value(path: Path, key: str) -> str:
    if not path.is_file() or path.stat().st_mode & 0o077:
        raise QualificationError("environment file must exist with mode 0600")
    entries = dict(
        line.split("=", 1)
        for line in path.read_text(encoding="utf-8").splitlines()
        if "=" in line
    )
    value = entries.get(key, "")
    if not value:
        raise QualificationError(f"environment file lacks {key}")
    return value


def validate_mutation_flags(args: argparse.Namespace) -> None:
    requested = args.recover_agent or args.workload_svid or args.fault or args.invalid_token
    if requested and not args.execute:
        raise QualificationError("every mutating SPIRE control requires --execute")
    if (args.recover_agent or args.invalid_token) and args.env_file is None:
        raise QualificationError("credential controls require --env-file")


def qualify(args: argparse.Namespace) -> dict[str, Any]:
    validate_mutation_flags(args)
    lock = validate_lock(json.loads(args.lock.read_text(encoding="utf-8")))
    validate_configs(
        args.server_config.read_text(encoding="utf-8"),
        args.agent_config.read_text(encoding="utf-8"),
    )
    server = validate_inspection(inspect(SERVER), lock["spire-server"]["image"], "spire-server")
    recovery: dict[str, Any] = {}
    if args.recover_agent:
        assert args.env_file is not None
        recovery = recover_agent(args.env_file, args.compose_file.resolve())
    wait_agent()
    agent = validate_inspection(inspect(AGENT), lock["spire-agent"]["image"], "spire-agent")
    server_version = run(["docker", "exec", SERVER, "/opt/spire/bin/spire-server", "-version"]).strip()
    agent_version = run([
        "docker", "exec", AGENT, "/opt/spire/bin/spire-agent", "-version",
    ]).strip()
    if {server_version, agent_version} != {"1.15.3"}:
        raise QualificationError("live SPIRE version differs from the lock")
    svid: dict[str, Any] = {}
    if args.workload_svid:
        svid = workload_svid()
        svid["entry_cleanup"] = "PASS"
    fault: dict[str, Any] = {}
    if args.fault:
        fault = bounded_fault()
    invalid: dict[str, Any] = {}
    if args.invalid_token:
        assert args.env_file is not None
        invalid = invalid_token_control(
            image=lock["spire-agent"]["image"],
            agent_config=args.agent_config,
            bootstrap_dir=Path(env_value(args.env_file, "OCOR_SPIRE_BOOTSTRAP_DIR")),
        )
    return {
        "schema_version": "1.0",
        "result": "PASS",
        "service": "spiffe-spire",
        "trust_domain": "ocor.test",
        "versions": {"spire-server": server_version, "spire-agent": agent_version},
        "runtime": {"spire-server": server, "spire-agent": agent},
        "identity": svid,
        "recovery": recovery,
        "fault": fault,
        "invalid_token": invalid,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=Path("infra/services.lock.json"))
    parser.add_argument("--server-config", type=Path, default=Path("deploy/bootstrap/spire/server.conf"))
    parser.add_argument("--agent-config", type=Path, default=Path("deploy/bootstrap/spire/agent.conf"))
    parser.add_argument("--compose-file", type=Path, default=Path("deploy/bootstrap/compose.yaml"))
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--recover-agent", action="store_true")
    parser.add_argument("--workload-svid", action="store_true")
    parser.add_argument("--invalid-token", action="store_true")
    parser.add_argument("--fault", action="store_true")
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args()


def main() -> int:
    try:
        print(json.dumps(qualify(parse_args()), indent=2, sort_keys=True))
        return 0
    except (OSError, json.JSONDecodeError, QualificationError) as exc:
        print(json.dumps({"result": "FAIL", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
