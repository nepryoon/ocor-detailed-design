#!/usr/bin/env python3
"""Provision the complete disposable CI stack from the governed build recipes.

The local bootstrap's machine-specific Fuseki image identity check is unchanged.
CI builds the locked Dockerfile (pinned base and SHA-512 source), records its image
identity, and qualifies that image through the existing typed service validator.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from bootstrap_development_environment import replace_env, write_secret_file
from ocor_bootstrap_lib import BootstrapError, load_json, retry, root, run, validate_locks


def redact(text: str, secrets: list[str]) -> str:
    for value in secrets:
        if value:
            text = text.replace(value, "[REDACTED]")
    return re.sub(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----.*?-----END (?:RSA |EC )?PRIVATE KEY-----", "[REDACTED PRIVATE KEY]", text, flags=re.DOTALL)


def redact_campaign_log(repository: Path, path: Path) -> None:
    env_file = repository / ".ocor/bootstrap.env"
    secrets = [line.split("=", 1)[1] for line in env_file.read_text().splitlines()
               if "=" in line and line.split("=", 1)[0].endswith(("TOKEN", "PASSWORD"))]
    path.write_text(redact(path.read_text(), secrets))


def collect_stack_diagnostics(repository: Path, output: Path) -> None:
    """Capture only this Compose project; redact generated credentials in logs."""
    env_file = repository / ".ocor/bootstrap.env"
    secrets = []
    if env_file.exists():
        secrets = [line.split("=", 1)[1] for line in env_file.read_text().splitlines()
                   if "=" in line and line.split("=", 1)[0].endswith(("TOKEN", "PASSWORD"))]
    ids = run(["docker", "ps", "-aq", "--filter", "label=com.docker.compose.project=ocor-bootstrap"], cwd=repository, timeout=10).stdout.split()
    with output.open("w") as log:
        if not ids:
            log.write("No ocor-bootstrap containers\n")
            return
        stats = run(["docker", "stats", "--no-stream", *ids], cwd=repository, timeout=20)
        log.write(stats.stdout + stats.stderr)
        for identity in ids:
            result = run(["docker", "logs", "--tail", "100", identity], cwd=repository, timeout=10)
            text = result.stdout + result.stderr
            log.write(f"\nContainer {identity}\n{redact(text, secrets)}")


def execute(repository: Path, command: list[str], label: str, timeout: int) -> str:
    result = run(command, cwd=repository, timeout=timeout)
    print(json.dumps({"operation": label, "exit_code": result.returncode}), flush=True)
    if result.returncode:
        # Commands can contain generated tokens: never print their argument vectors.
        raise BootstrapError(f"{label} failed")
    return result.stdout


def owned_resources(repository: Path) -> dict[str, list[str]]:
    """Inventory every resource kind under the exact disposable Compose label."""
    commands = {
        "containers": ["docker", "ps", "-aq"],
        "volumes": ["docker", "volume", "ls", "-q"],
        "networks": ["docker", "network", "ls", "-q"],
    }
    return {
        kind: execute(repository, command + ["--filter", "label=com.docker.compose.project=ocor-bootstrap"],
                      f"teardown inventory {kind}", 10).split()
        for kind, command in commands.items()
    }


def teardown(repository: Path) -> dict[str, object]:
    """Allow credential-free teardown only when absence is positively verified."""
    if not (repository / ".ocor/bootstrap.env").is_file():
        residual = owned_resources(repository)
        if any(residual.values()):
            raise BootstrapError("teardown credentials absent but owned resources remain")
        return {"status": "PASS", "operation": "teardown", "result": "ALREADY_REMOVED", "residual": residual}
    execute(repository, [sys.executable, "scripts/reset_test_environment.py", "--execute"], "governed teardown", 180)
    residual = owned_resources(repository)
    if any(residual.values()):
        raise BootstrapError("owned resources remain after teardown")
    return {"status": "PASS", "operation": "teardown", "result": "REMOVED", "residual": residual}


def prepare_ca(repository: Path, env_file: Path) -> None:
    values = dict(line.split("=", 1) for line in env_file.read_text().splitlines() if "=" in line)
    directory = Path(values["OCOR_SPIRE_BOOTSTRAP_DIR"]).resolve()
    if directory != repository / ".ocor/spire":
        raise BootstrapError("CI CA must be owned by this worktree")
    paths = [directory / "ca.key", directory / "ca.crt", directory]
    if any(path.is_symlink() for path in paths) or not all(path.exists() for path in paths):
        raise BootstrapError("invalid CI CA paths")
    # SPIRE's pinned image runs as 1000:1000. Hosted runners can have a different UID.
    # Restrict chown to the generated CA, leaving the runner-owned env file 0600.
    for path in paths:
        if (path.stat().st_uid, path.stat().st_gid) != (1000, 1000):
            execute(repository, ["sudo", "-n", "chown", "1000:1000", str(path)], "CA ownership", 10)
    # Modes were set before chown by write_secret_file; changing them after chown
    # would require an unnecessary second privileged operation on hosted runners.


def ci_resources(repository: Path) -> Path:
    """Constrain Fuseki's default 4 GiB heap within its unchanged 2 GiB cgroup."""
    profile = repository / ".ocor/ci-resources.yaml"
    if profile.is_symlink():
        raise BootstrapError("CI resource profile must not be a symlink")
    # JSON is a YAML subset. Keep the governed Compose, image and Dockerfile intact.
    profile.write_text(json.dumps({"services": {"fuseki": {"environment": {
        "JVM_ARGS": "-Xms128m -Xmx1G"
    }}}}, indent=2, sort_keys=True) + "\n")
    return profile


def running_jvm_args(processes: str) -> list[str]:
    rows = [line.split() for line in processes.splitlines() if line.split()]
    commands = [row[1:] if row[0].isdigit() else row for row in rows]
    jvms = [argv for argv in commands if argv and Path(argv[0]).name == "java"]
    if len(jvms) != 1:
        raise BootstrapError("Fuseki Java process is absent or ambiguous")
    argv = jvms[0]
    heap_args = [arg for arg in argv if arg.startswith(("-Xms", "-Xmx"))]
    if heap_args != ["-Xms128m", "-Xmx1G"] or any(arg.startswith(("-XX:MaxHeapSize", "-XX:InitialHeapSize", "-XX:MaxRAM")) for arg in argv):
        raise BootstrapError("Fuseki running JVM did not consume the CI heap bounds")
    return argv


def provision(repository: Path, timeout: int) -> dict[str, object]:
    errors = validate_locks(repository)
    if errors:
        raise BootstrapError("; ".join(errors))
    env_file = repository / ".ocor/bootstrap.env"
    if env_file.exists():
        raise BootstrapError("CI provisioning requires a fresh worktree-local credential file")
    present = execute(repository, ["docker", "ps", "-aq", "--filter", "label=com.docker.compose.project=ocor-bootstrap"], "single stack guard", 30)
    if present.strip():
        raise BootstrapError("reset the existing ocor-bootstrap stack before CI provisioning")
    services = load_json(repository / "infra/services.lock.json")["services"]
    for service in services:
        if "image" in service:
            result = retry(["docker", "pull", service["image"]], cwd=repository, attempts=5, timeout=timeout)
            if result.returncode:
                raise BootstrapError(f"pinned pull failed: {service['id']}")
    fuseki = next(service for service in services if service["id"] == "fuseki")["build"]
    dockerfile = (repository / fuseki["dockerfile"]).read_text()
    if f"FROM {fuseki['base_image']}\n" not in dockerfile or fuseki["source_sha512"] not in dockerfile:
        raise BootstrapError("Fuseki recipe differs from the locked base/source")
    execute(repository, ["docker", "build", "--pull", "-t", fuseki["output_image"], "infra/fuseki"], "Fuseki recipe build", timeout)
    image_id = execute(repository, ["docker", "image", "inspect", fuseki["output_image"], "--format", "{{.Id}}"], "Fuseki identity capture", 30).strip()
    env_file = write_secret_file(repository)
    ca = repository / ".ocor/spire"
    ca.chmod(0o700)
    (ca / "ca.key").chmod(0o600)
    (ca / "ca.crt").chmod(0o600)
    prepare_ca(repository, env_file)
    resources = ci_resources(repository)
    compose = ["docker", "compose", "-p", "ocor-bootstrap", "--env-file", str(env_file), "-f", "deploy/bootstrap/compose.yaml", "-f", str(resources)]
    server_image = next(service for service in services if service["id"] == "spire-server")["image"]
    user = execute(repository, ["docker", "image", "inspect", server_image, "--format", "{{.Config.User}}"], "SPIRE image UID", 30).strip()
    if user != "1000:1000":
        raise BootstrapError("unexpected pinned SPIRE image UID")
    execute(repository, compose + ["up", "--detach", "--wait", "--wait-timeout", str(timeout), "spire-server"], "SPIRE server", timeout + 60)
    token = execute(repository, compose + ["exec", "-T", "spire-server", "/opt/spire/bin/spire-server", "token", "generate", "-socketPath", "/run/spire/sockets/server.sock"], "SPIRE token", 30)
    if "Token:" not in token:
        raise BootstrapError("SPIRE token output invalid")
    replace_env(env_file, "OCOR_SPIRE_JOIN_TOKEN", token.split("Token:", 1)[1].splitlines()[0].strip())
    execute(repository, compose + ["up", "--detach", "--wait", "--wait-timeout", str(timeout), "--no-build"], "complete stack", timeout + 60)
    # The pinned image contains a JRE, not jcmd, and PID 1 is Docker's init.
    # Bind the actual Java process to a flag probe in that same runtime.
    processes = execute(repository, ["docker", "top", "ocor-bootstrap-fuseki-1", "-eo", "pid,args"], "Fuseki running JVM arguments", 30)
    running_jvm_args(processes)
    flags = execute(repository, ["docker", "exec", "ocor-bootstrap-fuseki-1", "java", "-Xms128m", "-Xmx1G", "-XX:+PrintFlagsFinal", "-version"], "Fuseki JVM heap flag probe", 30)
    if not re.search(r"\bMaxHeapSize\s*=\s*1073741824\b", flags):
        raise BootstrapError("Fuseki heap is not bounded to 1 GiB inside its 2 GiB cgroup")
    agent = ["docker", "exec", "ocor-bootstrap-spire-agent-1", "/opt/spire/bin/spire-agent"]
    ready = retry(agent + ["healthcheck", "-socketPath", "/run/spire/sockets/agent.sock"], cwd=repository, attempts=5, timeout=10)
    if ready.returncode:
        raise BootstrapError("SPIRE agent did not become healthy")
    server = ["docker", "exec", "ocor-bootstrap-spire-server-1", "/opt/spire/bin/spire-server"]
    agents = json.loads(execute(repository, server + ["agent", "list", "-socketPath", "/run/spire/sockets/server.sock", "-output", "json"], "SPIRE attested agent", 30))["agents"]
    if len(agents) != 1 or agents[0]["id"]["trust_domain"] != "ocor.test":
        raise BootstrapError("unexpected SPIRE attested agent set")
    identity = agents[0]["id"]
    parent = f"spiffe://{identity['trust_domain']}{identity['path']}"
    execute(repository, server + ["entry", "create", "-socketPath", "/run/spire/sockets/server.sock", "-parentID", parent, "-spiffeID", "spiffe://ocor.test/ocor/control-plane", "-selector", "unix:uid:0"], "control-plane workload entry", 30)
    material = retry(agent + ["api", "fetch", "x509", "-socketPath", "/run/spire/sockets/agent.sock", "-output", "json"], cwd=repository, attempts=5, timeout=15)
    if material.returncode or not any(item.get("spiffe_id") == "spiffe://ocor.test/ocor/control-plane" for item in json.loads(material.stdout).get("svids", [])):
        raise BootstrapError("control-plane SVID absent")
    print(json.dumps({"operation": "control-plane SVID", "exit_code": 0}), flush=True)
    for script in ("deploy/bootstrap/init/initialize_services.py", "deploy/bootstrap/fixtures/load_fixtures.py"):
        execute(repository, [sys.executable, script, "--env-file", str(env_file)], script, timeout)
    health = json.loads(execute(repository, [sys.executable, "scripts/verify_external_services.py", "--execute", "--typed"], "typed service health", timeout))
    return {"status": "PASS", "fuseki_built_image_id": image_id, "fuseki_lock_image_id": fuseki["output_sha256"], "fuseki_max_heap_bytes": 1073741824, "services": health}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--teardown", action="store_true", help="remove this disposable CI stack or verify its absence")
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    if not 1 <= args.timeout <= 600:
        parser.error("timeout must be between 1 and 600 seconds")
    repository = root()
    if args.teardown:
        if not args.execute:
            print(json.dumps({"mode": "CHECK_ONLY", "operation": "teardown", "status": "PASS"}))
            return 0
        try:
            print(json.dumps(teardown(repository), indent=2, sort_keys=True))
            return 0
        except (BootstrapError, OSError, ValueError, subprocess.SubprocessError) as exc:
            print(json.dumps({"status": "FAIL", "operation": "teardown", "error": str(exc)}))
            return 1
    if not args.execute:
        errors = validate_locks(repository)
        print(json.dumps({"mode": "CHECK_ONLY", "status": "FAIL" if errors else "PASS", "errors": errors}))
        return int(bool(errors))
    try:
        print(json.dumps(provision(repository, args.timeout), indent=2, sort_keys=True))
        return 0
    except (BootstrapError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}))
        collect_stack_diagnostics(repository, repository / "reports/tests/ci_bootstrap_diagnostics.log")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
