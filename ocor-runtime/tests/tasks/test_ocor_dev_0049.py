"""OCOR-DEV-0049: PoC deployment profiles — health, metrics, logs, traces,
backup/replay and bounded safe-degraded modes (ADD v1.3 Part I §6, Part II §2.13;
LLD v1.1 §5).

Repair cycle 2 (implementer: Claude Code; verifier: Codex). Every criterion is
proven on behaviour of real processes on the digest-pinned stack, never on
configuration booleans or string searches:

* the ops agent (single source: `configs.ocor-ops-agent` of
  `deploy/helm/ocor-poc/compose.profiles.yaml`, mounted by the Helm chart from
  the same file) is executed as a real process: it refuses to start on an
  invalid profile, serves `/livez` `/readyz` `/metrics` `/traces` `/posture`
  `/admit`, and probes every mandatory dependency semantically;
* readiness is observed to block on a paused dependency, an untested or
  tampered restore, release drift and an open public egress path;
* backups are produced from the real PostgreSQL/Kafka/Qdrant/OPA backends,
  encrypted and signed by OpenBao transit, written immutably to a vault outside
  the workload fault domain, restored on an isolated network with tombstone
  replay before retrieval, and rejected when tampered or inconsistent;
* default-deny is observed with allowed and denied connections;
* the Helm chart is installed on a disposable kind cluster (DEC-211) and its
  pod readiness, egress denial and fault behaviour are observed.

A missing mandatory environment or service is an explicit FAILURE, never a
skip (verdict OCOR-DEV-0049-2c5a574a5f3a-1 VF-006). E1=0, E2=0, no Verified
requirement and no G6 qualification are claimed.
"""

from __future__ import annotations

import base64
import json
import os
import re
import secrets
import shutil
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
CHART_DIR = ROOT / "deploy" / "helm" / "ocor-poc"
VALUES = CHART_DIR / "values.yaml"
OVERLAY = CHART_DIR / "compose.profiles.yaml"
OPS_IMAGE = "python:3.11@sha256:c7220863385ee39fb6d822da81f4469d0cd33ff893d92ce94105e5c3f4b95fe2"
BOOTSTRAP_NETWORK = "ocor-bootstrap_ocor-bootstrap"
BOOTSTRAP_SERVICES = [
    "terminusdb", "typedb", "fuseki", "opa", "keycloak", "openbao",
    "postgresql", "kafka", "qdrant", "spire-server",
]
LOG_FIELDS = ["correlation_id", "component", "operation", "release", "policy_digest", "reason_code"]
RECOVERY_GATE = [
    "revision", "watermark", "orphan_duplicate", "marking", "gcs",
    "deletion_resurrection", "projection_drift_or_stale_deletion_epoch",
    "sample_semantic_digest",
]
EXIT_CONFIG, EXIT_BACKPRESSURE, EXIT_VERIFY, EXIT_GATE = 78, 75, 65, 66


# --------------------------------------------------------------------------- sources


def overlay() -> dict:
    return yaml.safe_load(OVERLAY.read_text(encoding="utf-8"))


def agent_source() -> str:
    return overlay()["configs"]["ocor-ops-agent"]["content"]


def helm_profile() -> dict:
    return yaml.safe_load(VALUES.read_text(encoding="utf-8"))["ocor"]


def compose_profile() -> dict:
    # Compose interpolation turns `$$` into `$`; the agent source has no `$`.
    return json.loads(overlay()["configs"]["ocor-poc-profile"]["content"].replace("$$", "$"))


@pytest.fixture(scope="session")
def agent_dir(tmp_path_factory) -> Path:
    path = tmp_path_factory.mktemp("ocor-ops-agent")
    (path / "ocor_ops_agent.py").write_text(agent_source(), encoding="utf-8")
    (path / "profile.json").write_text(json.dumps(helm_profile()), encoding="utf-8")
    return path


def run_agent(agent_dir: Path, *args: str, profile: dict | None = None,
              env: dict | None = None, timeout: int = 60) -> subprocess.CompletedProcess:
    prof = agent_dir / "profile.json"
    if profile is not None:
        prof = agent_dir / f"profile-{uuid.uuid4().hex}.json"
        prof.write_text(json.dumps(profile), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(agent_dir / "ocor_ops_agent.py"), args[0], "--profile", str(prof), *args[1:]],
        capture_output=True, text=True, timeout=timeout, env={**os.environ, **(env or {})}, check=False)


def tool(name: str) -> str:
    # DEC-211 tools (helm, kind, kubectl) are acquired with verified checksums into
    # the untracked `.ocor/tools/bin` of the checkout (a worktree walks up to it).
    for parent in (ROOT, *Path(__file__).resolve().parents):
        candidate = parent / ".ocor" / "tools" / "bin" / name
        if candidate.exists():
            return str(candidate)
    found = shutil.which(name)
    if not found:
        pytest.fail(f"mandatory tool {name} is unavailable (DEC-211 provisioning required); not a skip")
    return found


# --------------------------------------------------------------------------- contract


def test_agent_is_a_single_source_shared_by_compose_and_helm():
    rendered = helm_template()
    configmap = next(d for d in rendered if d["kind"] == "ConfigMap")
    assert configmap["data"]["ocor_ops_agent.py"] == agent_source()
    assert json.loads(configmap["data"]["profile.json"]) == helm_profile()
    assert compose_profile() == helm_profile(), "Compose and Helm profile carriers drift"


def test_agent_source_passes_ruff_and_mypy_strict(agent_dir):
    """The embedded program stays under the repository quality gates."""
    ruff = subprocess.run([tool("ruff"), "check", "--config", str(ROOT / "pyproject.toml"),
                           str(agent_dir / "ocor_ops_agent.py")], capture_output=True, text=True, check=False)
    assert ruff.returncode == 0, ruff.stdout + ruff.stderr
    mypy = subprocess.run([sys.executable, "-m", "mypy", "--strict", "--python-version", "3.11",
                           "--no-incremental", str(agent_dir / "ocor_ops_agent.py")],
                          capture_output=True, text=True, check=False, cwd=agent_dir)
    assert mypy.returncode == 0, mypy.stdout + mypy.stderr


def test_valid_profile_is_accepted_by_the_startup_gate(agent_dir):
    result = run_agent(agent_dir, "validate")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["reason_code"] == "PROFILE_VALID"


def _set(path: str, value):
    def mutate(profile: dict) -> None:
        node = profile
        keys = path.split(".")
        for key in keys[:-1]:
            node = node[int(key)] if isinstance(node, list) else node[key]
        last = keys[-1]
        if isinstance(node, list):
            node[int(last)] = value
        else:
            node[last] = value
    return mutate


def _drop_dependency(name: str):
    def mutate(profile: dict) -> None:
        profile["health"]["dependencies"] = [d for d in profile["health"]["dependencies"] if d["name"] != name]
    return mutate


def _reorder_tombstone(profile: dict) -> None:
    steps = profile["restore"]["steps"]
    steps.remove("replay_memory_deletion_tombstones_before_reopen_retrieval")
    steps.append("replay_memory_deletion_tombstones_before_reopen_retrieval")


NEGATIVE_PROFILES = [
    ("public network dependency", _set("images.publicNetworkDependencyAtRuntime", True), "public-network runtime dependency"),
    ("public egress allowed", _set("isolation.egressPublicNetwork", True), "public egress must be denied"),
    ("no egress probes", _set("isolation.egressDenyProbes", []), "egress deny probes required"),
    ("public allowed flow", _set("isolation.allowedFlows.0", {"host": "registry.npmjs.org", "port": 443}), "allowed flow must be intra-site"),
    ("empty allowed flows", _set("isolation.allowedFlows", []), "allowedFlows must be non-empty"),
    ("image pin by tag", _set("images.pins.ops", "python:3.11"), "image pin ops must be digest-pinned"),
    ("no image pins", _set("images.pins", {}), "image pins required"),
    ("namespace not per subsystem", _set("isolation.namespacePerSubsystem", False), "namespacePerSubsystem"),
    ("service account not per subsystem", _set("isolation.serviceAccountPerSubsystem", False), "serviceAccountPerSubsystem"),
    ("one synthetic compartment", _set("isolation.syntheticCompartmentsMin", 1), "two synthetic compartments"),
    ("exporters not local", _set("observability.exportersLocal", False), "exporters must stay local"),
    ("drift scan 0", _set("observability.driftScanIntervalSeconds", 0), "drift scan interval"),
    ("drift scan negative", _set("observability.driftScanIntervalSeconds", -1), "drift scan interval"),
    ("drift scan 61", _set("observability.driftScanIntervalSeconds", 61), "drift scan interval"),
    ("probe interval 61", _set("observability.probeIntervalSeconds", 61), "probe interval"),
    ("metric set incomplete", _set("observability.metrics.set", ["audit_gap"]), "metric set incomplete"),
    ("trace fields incomplete", _set("observability.traces.fields", ["trace_id"]), "trace fields incomplete"),
    ("classified payload logged", _set("observability.logs.excludeClassifiedPayload", False), "classified payload"),
    ("RPO 16", _set("backup.rpoMinutes", 16), "RPO must be in [1, 15]"),
    ("RPO negative", _set("backup.rpoMinutes", -1), "RPO must be in [1, 15]"),
    ("RTO 5", _set("backup.rtoHours", 5), "RTO must be in [1, 4]"),
    ("RTO negative", _set("backup.rtoHours", -1), "RTO must be in [1, 4]"),
    ("backup unencrypted", _set("backup.encrypted", False), "backup.encrypted"),
    ("backup unsigned", _set("backup.signed", False), "backup.signed"),
    ("restore untested", _set("backup.tested", False), "backup.tested"),
    ("same key for encryption and signature", _set("backup.keys.signing", "ocor-poc-backup-enc"), "separate encryption and signing keys"),
    ("authority class missing", _set("backup.authorityClasses", ["canonical"]), "authority classes incomplete"),
    ("memory deletion epochs unbound", _set("backup.memory.deletionEpochs", False), "memory manifest field deletionEpochs"),
    ("tombstone replay out of order", _reorder_tombstone, "restore steps incomplete or out of order"),
    ("replay pins empty", _set("restore.replay.pins", []), "replay pins incomplete"),
    ("recovery gate incomplete", _set("restore.recoveryGate", RECOVERY_GATE[:-1]), "recovery gate incomplete"),
    ("restore not isolated", _set("restore.isolatedNetwork", False), "isolated network"),
    ("resource limit zero", _set("resourceLimits.topK", 0), "resource limit topK"),
    ("semantic downgrade", _set("resourceLimits.quotaBehavior.semanticDowngrade", True), "semantic downgrade"),
    ("emergency stop fault missing", lambda p: p["safeDegraded"].__setitem__("faults", p["safeDegraded"]["faults"][:-1]), "safe-degraded fault table incomplete"),
    ("health dependencies empty", _set("health.dependencies", []), "health.dependencies must be non-empty"),
    ("mandatory dependency missing", _drop_dependency("spire-server"), "cover every mandatory foundation service"),
    ("dependency not mandatory", _set("health.dependencies.0.mandatory", False), "must be mandatory"),
    ("dependency without probe", _set("health.dependencies.0.probe", {}), "health probe missing"),
    ("dependency outside allowlist", _set("health.dependencies.0.port", 7000), "not in allowedFlows"),
]


@pytest.mark.parametrize("description,mutate,expected", NEGATIVE_PROFILES, ids=[c[0] for c in NEGATIVE_PROFILES])
def test_invalid_profile_blocks_startup(agent_dir, description, mutate, expected):
    profile = deepcopy(helm_profile())
    mutate(profile)
    result = run_agent(agent_dir, "validate", profile=profile)
    assert result.returncode == EXIT_CONFIG, (description, result.stdout, result.stderr)
    errors = json.loads(result.stderr)["errors"]
    assert any(expected in e for e in errors), (description, errors)


@pytest.mark.parametrize("path,value", [
    ("backup.rpoMinutes", 15), ("backup.rpoMinutes", 1), ("backup.rtoHours", 4),
    ("observability.driftScanIntervalSeconds", 60), ("observability.driftScanIntervalSeconds", 1),
])
def test_boundary_values_are_accepted(agent_dir, path, value):
    profile = deepcopy(helm_profile())
    _set(path, value)(profile)
    assert run_agent(agent_dir, "validate", profile=profile).returncode == 0


def helm_template(*sets: str, expect_ok: bool = True) -> list[dict]:
    args = [tool("helm"), "template", "ocor-poc", str(CHART_DIR),
            "--set", "operational.secretName=ocor-poc-ops", "--set", "operational.vault.existingClaim=ocor-poc-vault",
            "--set", "operational.restoreDrill.enabled=true", "--set", "operational.dependencyCidr=172.16.0.0/12"]
    for item in sets:
        args += ["--set", item]
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if not expect_ok:
        return [{"returncode": result.returncode, "stderr": result.stderr}]
    assert result.returncode == 0, result.stderr
    return [d for d in yaml.safe_load_all(result.stdout) if d]


def test_helm_chart_renders_operational_workloads():
    docs = {(d["kind"], d["metadata"]["name"]): d for d in helm_template()}
    deployment = docs[("Deployment", "ocor-poc-ops")]["spec"]["template"]["spec"]
    container = deployment["containers"][0]
    assert container["image"] == OPS_IMAGE
    assert container["command"][:3] == ["python3", "/opt/ocor/ocor_ops_agent.py", "serve"]
    assert container["readinessProbe"]["httpGet"] == {"path": "/readyz", "port": "http"}
    assert container["livenessProbe"]["httpGet"] == {"path": "/livez", "port": "http"}
    assert container["ports"] == [{"name": "http", "containerPort": 8080}]
    assert container["securityContext"]["readOnlyRootFilesystem"] is True
    assert deployment["automountServiceAccountToken"] is False
    service = docs[("Service", "ocor-poc-ops")]["spec"]
    assert service["ports"][0]["targetPort"] == "http"
    vault = next(v for v in deployment["volumes"] if v["name"] == "vault")
    assert vault["persistentVolumeClaim"]["claimName"] == "ocor-poc-vault"
    cron = docs[("CronJob", "ocor-poc-backup")]["spec"]
    assert cron["schedule"] == "*/15 * * * *", "RPO <= 15 min requires a 15-minute cadence"
    pod = cron["jobTemplate"]["spec"]["template"]["spec"]
    assert [c["name"] for c in pod["initContainers"]] == ["capture-postgresql", "capture-kafka"]
    assert "seal" in pod["containers"][0]["command"][2]
    assert all(v.get("emptyDir") is None or v["name"] != "vault" for v in pod["volumes"])
    deny = docs[("NetworkPolicy", "ocor-poc-default-deny")]["spec"]
    assert deny == {"podSelector": {}, "policyTypes": ["Ingress", "Egress"]}
    allow = docs[("NetworkPolicy", "ocor-poc-intra-site")]["spec"]
    ports = {p["port"] for rule in allow["egress"][1:] for p in rule["ports"]}
    assert ports == {f["port"] for f in helm_profile()["isolation"]["allowedFlows"]}
    drill = docs[("Job", "ocor-poc-restore-drill-1")]["spec"]["template"]["spec"]
    assert [c["name"] for c in drill["initContainers"]] == [
        "restore-prepare", "restore-postgresql", "restore-qdrant", "restore-load-postgresql"]


@pytest.mark.parametrize("missing", ["operational.secretName=", "operational.vault.existingClaim="])
def test_helm_chart_refuses_to_render_without_secret_or_external_vault(missing):
    result = helm_template(missing, expect_ok=False)[0]
    assert result["returncode"] != 0
    assert "required" in result["stderr"]


# --------------------------------------------------------------------------- live environment


def _env_file() -> Path | None:
    if os.environ.get("OCOR_BOOTSTRAP_ENV"):
        candidate = Path(os.environ["OCOR_BOOTSTRAP_ENV"])
        return candidate if candidate.exists() else None
    for candidate in (Path.home() / ".ocor-bootstrap-secrets" / "ocor-bootstrap.env", ROOT / ".ocor" / "bootstrap.env"):
        if candidate.exists():
            return candidate
    for parent in Path(__file__).resolve().parents:
        candidate = parent / ".ocor" / "bootstrap.env"
        if candidate.exists():
            return candidate
    return None


def require_live_environment() -> dict[str, str]:
    """Mandatory qualifying environment: absence FAILS (never skips)."""
    env_file = _env_file()
    if env_file is None:
        pytest.fail("ocor-bootstrap env file not found: the real stack is mandatory qualifying evidence")
    if shutil.which("docker") is None:
        pytest.fail("docker is unavailable: the real stack is mandatory qualifying evidence")
    missing = []
    for service in BOOTSTRAP_SERVICES:
        result = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}} {{.State.Paused}}",
                                 f"ocor-bootstrap-{service}-1"], capture_output=True, text=True, check=False)
        if result.returncode != 0 or result.stdout.strip() != "true false":
            missing.append(service)
    if missing:
        pytest.fail(f"mandatory ocor-bootstrap services are not running: {sorted(missing)}")
    return dict(line.strip().split("=", 1) for line in env_file.read_text().splitlines() if "=" in line)


class Stack:
    """Compose carrier of the PoC profile against the running ocor-bootstrap stack."""

    def __init__(self, env: dict[str, str], vault: Path, work: Path) -> None:
        self.env = env
        self.vault = vault
        self.work = work
        self.operator_token = secrets.token_hex(16)
        self.projects: set[str] = set()

    def compose_env(self, vault: Path | None = None) -> dict[str, str]:
        return {**os.environ, **self.env, "OCOR_OPS_OPERATOR_TOKEN": self.operator_token,
                "OCOR_BACKUP_VAULT_DIR": str(vault or self.vault),
                "OCOR_OPS_UID": str(os.getuid()), "OCOR_OPS_GID": str(os.getgid())}

    def compose(self, project: str, *args: str, vault: Path | None = None, extra_files: tuple[Path, ...] = (),
                timeout: int = 600) -> subprocess.CompletedProcess:
        self.projects.add(project)
        files = ["-f", str(OVERLAY)]
        for f in extra_files:
            files += ["-f", str(f)]
        return subprocess.run(["docker", "compose", "-p", project, *files, *args], capture_output=True, text=True,
                              env=self.compose_env(vault), timeout=timeout, check=False, cwd=ROOT)

    def run_stage(self, project: str, profile: str, service: str, vault: Path | None = None,
                  extra_files: tuple[Path, ...] = ()) -> tuple[int, str]:
        result = self.compose(project, "--profile", profile, "up", "--exit-code-from", service, service,
                              vault=vault, extra_files=extra_files)
        logs = self.compose(project, "--profile", profile, "logs", "--no-color", vault=vault,
                            extra_files=extra_files).stdout
        return result.returncode, result.stdout + result.stderr + logs

    def down(self, project: str, profile: str = "full") -> None:
        self.compose(project, "--profile", "full", "--profile", "restore-drill", "down", "-v", "--remove-orphans")


def http_from(container: str, url: str, method: str = "GET", headers: dict | None = None) -> tuple[int, str]:
    """Issue an HTTP request from inside a container (the profile networks are internal)."""
    code = (
        "import json,sys,urllib.request,urllib.error\n"
        f"r=urllib.request.Request({url!r},method={method!r},headers={json.dumps(headers or {})})\n"
        "try:\n"
        "    resp=urllib.request.urlopen(r,timeout=10); print(resp.status); print(resp.read().decode())\n"
        "except urllib.error.HTTPError as e:\n"
        "    print(e.code); print(e.read().decode())\n"
        "except OSError as e:\n"
        "    print(0); print(json.dumps({'error': type(e).__name__, 'reasons': []}))\n"
    )
    result = subprocess.run(["docker", "exec", container, "python3", "-c", code], capture_output=True, text=True,
                            check=False, timeout=30)
    assert result.returncode == 0, result.stderr
    status, _, body = result.stdout.partition("\n")
    return int(status), body


def connect_from(container: str, host: str, port: int) -> str:
    code = (
        "import socket\n"
        "try:\n"
        f"    socket.create_connection(({host!r}, {port}), 4).close(); print('CONNECTED')\n"
        "except socket.gaierror:\n"
        "    print('DNS_DENIED')\n"
        "except OSError as e:\n"
        "    print('DENIED:' + type(e).__name__)\n"
    )
    result = subprocess.run(["docker", "exec", container, "python3", "-c", code], capture_output=True, text=True,
                            check=False, timeout=30)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def wait_for(predicate, timeout: float, interval: float = 1.0, message: str = ""):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = predicate()
        if last:
            return last
        time.sleep(interval)
    pytest.fail(f"timed out after {timeout}s: {message} (last={last!r})")


def readyz(container: str) -> tuple[int, dict]:
    status, body = http_from(container, "http://ocor-ops:8080/readyz")
    return status, json.loads(body)


def scanned(result: tuple[int, dict]) -> bool:
    return result[0] in (200, 503) and result[1].get("reasons") not in ([], ["NOT_YET_SCANNED"], None)


def metrics(container: str) -> dict[str, float]:
    status, body = http_from(container, "http://ocor-ops:8080/metrics")
    assert status == 200
    out: dict[str, float] = {}
    for line in filter(None, body.splitlines()):
        name, _, value = line.rpartition(" ")
        out[name] = float(value)  # every exported sample is a real number
    return out


# --------------------------------------------------------------------------- drill fixture


def postgres_dsn(env: dict[str, str], db: str = "ocor") -> str:
    return f"host=127.0.0.1 port=55433 user=ocor password={env['OCOR_LOCAL_POSTGRES_PASSWORD']} dbname={db}"


def qdrant_call(method: str, path: str, body: dict | None = None) -> dict:
    request = urllib.request.Request(f"http://127.0.0.1:16333{path}", method=method,
                                     data=None if body is None else json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(request, timeout=30).read())
    except urllib.error.HTTPError as exc:
        return {"status_code": exc.code}


def memory_point_id(item_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"ocor-memory:{item_id}"))


def load_drill_fixture(env: dict[str, str], consistent: bool, items: int = 5) -> None:
    """Synthetic memory drill: m2/m4 are deleted in metadata while the index still
    holds them at the cut. `consistent=False` drops the m4 tombstone from the
    journal (stale deletion epoch -> resurrection risk)."""
    import psycopg

    with psycopg.connect(postgres_dsn(env), autocommit=True) as conn:
        conn.execute("drop database if exists ocor_poc_drill with (force)")
        conn.execute("create database ocor_poc_drill")
    with psycopg.connect(postgres_dsn(env, "ocor_poc_drill"), autocommit=True) as conn:
        conn.execute(
            "create table memory_item(item_id text primary key, tenant_id text not null, compartment text not null,"
            " representation_version int not null, lifecycle_epoch int not null, lifecycle_state text not null,"
            " deletion_epoch bigint, content_ref text not null, classification_marking_ref text not null)")
        conn.execute("create table memory_deletion_journal(event_id text primary key, item_id text not null,"
                     " deletion_epoch bigint not null)")
        for n in range(1, items + 1):
            item = f"m{n}"
            deleted = {"m2": 6, "m4": 7}.get(item)
            conn.execute("insert into memory_item values (%s,%s,%s,2,3,%s,%s,%s,'SYNTHETIC-UNCLASSIFIED')",
                         (item, "tenant-a" if n % 2 else "tenant-b", "c1" if n % 2 else "c2",
                          "deleted" if deleted else "active", deleted, f"cas:sha256:{item}"))
        conn.execute("insert into memory_deletion_journal values ('evt-del-m2','m2',6)")
        if consistent:
            conn.execute("insert into memory_deletion_journal values ('evt-del-m4','m4',7)")
    collection = "/collections/ocor_poc_drill_memory"
    qdrant_call("DELETE", collection)
    assert qdrant_call("PUT", collection, {"vectors": {"size": 4, "distance": "Cosine"}}).get("status") == "ok"
    points = []
    for n in range(1, items + 1):
        tenant, compartment = ("tenant-a", "c1") if n % 2 else ("tenant-b", "c2")
        points.append({"id": memory_point_id(f"m{n}"), "vector": [0.1 * n, 0.2, 0.3, 0.4],
                       "payload": {"item_id": f"m{n}", "tenant_id": tenant, "compartment": compartment,
                                   "classification_marking_ref": "SYNTHETIC-UNCLASSIFIED",
                                   "governed_context_digest": f"gcd-{tenant}-{compartment}",
                                   "representation_version": 2, "lifecycle_epoch": 3}})
    assert qdrant_call("PUT", collection + "/points?wait=true", {"points": points}).get("status") == "ok"


def drop_drill_fixture(env: dict[str, str]) -> None:
    import psycopg

    with psycopg.connect(postgres_dsn(env), autocommit=True) as conn:
        conn.execute("drop database if exists ocor_poc_drill with (force)")
    qdrant_call("DELETE", "/collections/ocor_poc_drill_memory")


def make_writable(path: Path) -> None:
    for p in [path, *path.rglob("*")]:
        if p.is_dir():
            p.chmod(stat.S_IRWXU)
        elif p.exists():
            p.chmod(stat.S_IRUSR | stat.S_IWUSR)


def latest_receipt(vault: Path) -> dict:
    return json.loads(sorted((vault / "restore-receipts").glob("*.json"))[-1].read_bytes())


def profile_override(work: Path, mutate) -> Path:
    profile = deepcopy(helm_profile())
    mutate(profile)
    path = work / f"override-{uuid.uuid4().hex}.yaml"
    content = json.dumps(profile, sort_keys=True).replace("$", "$$")
    path.write_text(yaml.safe_dump({"configs": {"ocor-poc-profile": {"content": content}}}), encoding="utf-8")
    return path


# --------------------------------------------------------------------------- live compose stack


@pytest.fixture(scope="module")
def stack(tmp_path_factory):
    env = require_live_environment()
    work = tmp_path_factory.mktemp("ocor-poc")
    vault = work / "vault"
    vault.mkdir()
    st = Stack(env, vault, work)
    st.ops_project = f"ocor-poc-ops-{uuid.uuid4().hex[:6]}"
    st.ops = f"{st.ops_project}-ocor-ops-1"
    st.relay = f"{st.ops_project}-ocor-relay-1"
    load_drill_fixture(env, consistent=True)
    try:
        result = st.compose(st.ops_project, "--profile", "observability", "up", "-d")
        assert result.returncode == 0, result.stderr
        wait_for(lambda: http_from(st.relay, "http://ocor-ops:8080/livez")[0] == 200, 60,
                 message="ops agent did not start listening")
        yield st
    finally:
        for project in sorted(st.projects):
            st.down(project)
        drop_drill_fixture(env)
        make_writable(work)


def test_ops_process_serves_health_and_blocks_readiness_until_restore_is_tested(stack):
    status, body = http_from(stack.relay, "http://ocor-ops:8080/livez")
    assert (status, json.loads(body)["status"]) == (200, "ALIVE")
    status, ready = wait_for(lambda: scanned(r := readyz(stack.relay)) and r, 30)
    assert status == 503
    assert ready["reasons"] == ["RESTORE_UNTESTED"], "all ten dependencies must be up; only the restore is missing"
    m = metrics(stack.relay)
    for dependency in BOOTSTRAP_SERVICES:
        assert m[f'ocor_dependency_up{{dependency="{dependency}"}}'] == 1.0
        for q in ("0.5", "0.95", "0.99"):
            assert m[f'ocor_dependency_probe_duration_seconds{{dependency="{dependency}",quantile="{q}"}}'] > 0
    assert m["ocor_readiness_ready"] == 0.0
    assert m["ocor_egress_public_reachable"] == 0.0
    mounted = subprocess.run(["docker", "exec", stack.ops, "cat", "/etc/ocor/profile.json"],
                             capture_output=True, text=True, check=True).stdout
    assert json.loads(mounted) == helm_profile(), "the running process consumes the governed profile"


def test_backup_seals_an_encrypted_signed_immutable_recovery_point(stack):
    project = f"ocor-poc-backup-{uuid.uuid4().hex[:6]}"
    code, logs = stack.run_stage(project, "backup", "ocor-backup-seal")
    assert code == 0, logs
    stack.down(project)  # workload fault domain removed, including its volumes
    points = sorted((stack.vault / "recovery-points").iterdir())
    assert len(points) == 1
    rp = points[0]
    raw = (rp / "manifest.json").read_bytes()
    manifest = json.loads(raw)
    assert manifest["memory"]["status"] == "PRESENT"
    assert manifest["memory"]["journalCheckpoints"] == {"entries": 2, "max_deletion_epoch": 7,
                                                        "last_event_id": "evt-del-m4"}
    assert manifest["memory"]["representationVersions"] == [2]
    assert manifest["memory"]["lifecycleEpochs"] == [3]
    assert manifest["memory"]["contentRefs"] == [f"cas:sha256:m{n}" for n in range(1, 6)]
    assert {"canonical", "audit", "event", "governance", "definition", "projection", "key_custody"} <= set(
        manifest["authority_classes_present"])
    assert set(manifest["authority_classes_without_store"]) == {"action", "model_scenario"}
    names = {a["name"] for a in manifest["artifacts"]}
    assert {"postgresql/ocor.dump", "postgresql/ocor_poc_drill.dump", "kafka/offsets.txt",
            "qdrant/ocor_poc_drill_memory.snapshot", "memory/memory-deletion-journal.csv",
            "opa/policies.json"} <= names
    for artifact in manifest["artifacts"]:
        blob_path = rp / "objects" / f"{artifact['ciphertext_sha256']}.enc"
        blob = blob_path.read_bytes()
        assert blob_path.stat().st_mode & 0o777 == 0o444
        assert b"PGDMP" not in blob and b"tenant-a" not in blob and b"evt-del" not in blob
        assert all(c.startswith("vault:v1:") for c in json.loads(blob)["chunks"])
    with pytest.raises(PermissionError):
        (rp / "manifest.json").write_bytes(b"{}")
    signature = (rp / "manifest.sig").read_text()
    assert transit_verify(stack.env, raw, signature) is True
    assert transit_verify(stack.env, raw.replace(b"PRESENT", b"ABSENT_"), signature) is False


def transit_verify(env: dict[str, str], data: bytes, signature: str) -> bool:
    request = urllib.request.Request(
        "http://127.0.0.1:8200/v1/ocor-poc-transit/verify/ocor-poc-backup-sign", method="POST",
        data=json.dumps({"input": base64.b64encode(data).decode(), "signature": signature}).encode(),
        headers={"X-Vault-Token": env["OCOR_LOCAL_OPENBAO_TOKEN"]})
    return bool(json.loads(urllib.request.urlopen(request, timeout=10).read())["data"]["valid"])


def test_isolated_restore_replays_tombstones_and_passes_the_recovery_gate(stack):
    project = f"ocor-poc-restore-{uuid.uuid4().hex[:6]}"
    code, logs = stack.run_stage(project, "restore-drill", "ocor-restore-finalize")
    assert code == 0, logs
    networks = json.loads(subprocess.run(["docker", "network", "inspect", f"{project}_restore"],
                                         capture_output=True, text=True, check=True).stdout)
    assert networks[0]["Internal"] is True
    attached = json.loads(subprocess.run(
        ["docker", "inspect", "-f", "{{json .NetworkSettings.Networks}}", f"{project}-ocor-restore-postgresql-1"],
        capture_output=True, text=True, check=True).stdout)
    assert list(attached) == [f"{project}_restore"], "restored stores live only on the isolated network"
    staged = subprocess.run(["docker", "run", "--rm", "-v", f"{project}_restore-staging:/r", OPS_IMAGE,
                             "find", "/r", "-type", "f"], capture_output=True, text=True, check=True).stdout
    assert staged.strip() == "", "decrypted plaintext must be erased after the restore"
    stack.down(project)
    receipt = latest_receipt(stack.vault)
    assert receipt["outcome"] == "PASSED"
    assert receipt["replayed_event_ids"] == ["evt-del-m2", "evt-del-m4"], "original ids, journal order"
    assert all(receipt["recovery_gate"][name]["pass"] for name in RECOVERY_GATE)
    assert receipt["retrieval_reopened"] is False
    assert receipt["isolated_network"] is True
    steps = [s["step"] for s in receipt["steps"]]
    assert steps.index("replay_memory_deletion_tombstones_before_reopen_retrieval") < steps.index(
        "rebuild_logic_projection_and_w3c_boundary")
    stack.replay_digest = receipt["replay_digest"]


def test_readiness_turns_ready_only_with_a_signed_passed_restore_receipt(stack):
    status, ready = wait_for(lambda: (r := readyz(stack.relay))[0] == 200 and r, 30,
                             message="readiness must turn READY after the tested restore")
    assert ready["reasons"] == ["READY"]
    m = metrics(stack.relay)
    assert m["ocor_restore_tested"] == 1.0
    assert m["ocor_recovery_point_within_rpo"] == 1.0
    health = wait_for(lambda: subprocess.run(["docker", "inspect", "-f", "{{.State.Health.Status}}", stack.ops],
                                             capture_output=True, text=True).stdout.strip() == "healthy", 30)
    assert health


def test_restore_replay_is_deterministic(stack):
    project = f"ocor-poc-restore-{uuid.uuid4().hex[:6]}"
    code, logs = stack.run_stage(project, "restore-drill", "ocor-restore-finalize")
    stack.down(project)
    assert code == 0, logs
    assert latest_receipt(stack.vault)["replay_digest"] == stack.replay_digest


def _copy_vault(stack, name: str) -> Path:
    copy = stack.work / name
    shutil.copytree(stack.vault, copy)
    make_writable(copy)
    return copy


@pytest.mark.parametrize("target,expected", [
    ("object", "CIPHERTEXT_DIGEST_MISMATCH"), ("manifest", "SIGNATURE_INVALID")])
def test_tampered_recovery_point_is_rejected_before_restore(stack, target, expected):
    vault = _copy_vault(stack, f"tampered-{target}")
    shutil.rmtree(vault / "restore-receipts")
    rp = next((vault / "recovery-points").iterdir())
    path = sorted((rp / "objects").iterdir())[0] if target == "object" else rp / "manifest.json"
    data = bytearray(path.read_bytes())
    data[len(data) // 2] ^= 0x01
    path.write_bytes(bytes(data))
    project = f"ocor-poc-tamper-{uuid.uuid4().hex[:6]}"
    code, logs = stack.run_stage(project, "restore-drill", "ocor-restore-prepare", vault=vault)
    stack.down(project)
    assert code == EXIT_VERIFY, logs
    assert expected in logs
    assert not (vault / "restore-receipts").exists(), "no receipt may be produced from a tampered point"


def _standalone_ops(stack, vault: Path, network: str, profile_path: Path | None = None) -> str:
    name = f"ocor-poc-probe-{uuid.uuid4().hex[:6]}"
    agent = stack.work / "agent.py"
    agent.write_text(agent_source(), encoding="utf-8")
    profile = profile_path or stack.work / "profile.json"
    if profile_path is None:
        profile.write_text(json.dumps(helm_profile()), encoding="utf-8")
    result = subprocess.run(
        ["docker", "run", "-d", "--name", name, "--network", network, "--user", f"{os.getuid()}:{os.getgid()}",
         "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true",
         "-e", f"OCOR_OPENBAO_TOKEN={stack.env['OCOR_LOCAL_OPENBAO_TOKEN']}",
         "-e", f"OCOR_OPS_OPERATOR_TOKEN={stack.operator_token}",
         "-v", f"{agent}:/opt/ocor/ocor_ops_agent.py:ro", "-v", f"{profile}:/etc/ocor/profile.json:ro",
         "-v", f"{vault}:/vault:ro", OPS_IMAGE, "python3", "/opt/ocor/ocor_ops_agent.py", "serve",
         "--profile", "/etc/ocor/profile.json", "--vault", "/vault"],
        capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    return name


def _standalone_readyz(name: str) -> tuple[int, dict]:
    status, body = http_from(name, "http://127.0.0.1:8080/readyz")
    return status, json.loads(body)


def test_tampered_restore_receipt_blocks_readiness(stack):
    vault = _copy_vault(stack, "tampered-receipt")
    receipt = sorted((vault / "restore-receipts").glob("*.json"))[-1]
    receipt.write_bytes(receipt.read_bytes().replace(b'"PASSED"', b'"PASSES"'))
    name = _standalone_ops(stack, vault, f"{stack.ops_project}_site")
    try:
        _, ready = wait_for(lambda: scanned(r := _standalone_readyz(name)) and r, 30)
        assert ready["reasons"] == ["RESTORE_RECEIPT_INVALID"]
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, check=False)


def test_inconsistent_deletion_journal_blocks_materialisation_and_readiness(stack):
    """Stale deletion epoch: m4 is deleted in metadata but its tombstone is missing
    from the journal; the restored index would resurrect it."""
    vault = stack.work / "vault-inconsistent"
    vault.mkdir()
    load_drill_fixture(stack.env, consistent=False)
    try:
        project = f"ocor-poc-backup-{uuid.uuid4().hex[:6]}"
        code, logs = stack.run_stage(project, "backup", "ocor-backup-seal", vault=vault)
        stack.down(project)
        assert code == 0, logs
        project = f"ocor-poc-restore-{uuid.uuid4().hex[:6]}"
        code, logs = stack.run_stage(project, "restore-drill", "ocor-restore-finalize", vault=vault)
        stack.down(project)
        assert code == EXIT_GATE, logs
        receipt = latest_receipt(vault)
        assert receipt["outcome"] == "FAILED"
        assert receipt["materialisation"] == "BLOCKED"
        assert receipt["recovery_gate"]["deletion_resurrection"] == {"pass": False, "detail": ["m4"]}
        assert receipt["recovery_gate"]["projection_drift_or_stale_deletion_epoch"]["pass"] is False
        assert receipt["recovery_gate"]["sample_semantic_digest"]["pass"] is True
        name = _standalone_ops(stack, vault, f"{stack.ops_project}_site")
        try:
            _, ready = wait_for(lambda: scanned(r := _standalone_readyz(name)) and r, 30)
            assert ready["reasons"] == ["RESTORE_FAILED"]
        finally:
            subprocess.run(["docker", "rm", "-f", name], capture_output=True, check=False)
    finally:
        load_drill_fixture(stack.env, consistent=True)


@pytest.mark.parametrize("limit,value,observed", [("itemCount", 2, 5), ("embeddingDimensions", 3, 4)])
def test_quota_exceeded_backpressures_without_semantic_downgrade(stack, limit, value, observed):
    vault = stack.work / f"vault-quota-{limit}"
    vault.mkdir()
    override = profile_override(stack.work, _set(f"resourceLimits.{limit}", value))
    project = f"ocor-poc-backup-{uuid.uuid4().hex[:6]}"
    code, logs = stack.run_stage(project, "backup", "ocor-backup-seal", vault=vault, extra_files=(override,))
    stack.down(project)
    assert code == EXIT_BACKPRESSURE, logs
    record = next(json.loads(line.split("|", 1)[1]) for line in logs.splitlines()
                  if "QUOTA_BACKPRESSURE" in line and "|" in line)
    assert (record["limit"], record["observed"], record["semantic_downgrade"]) == (limit, observed, False)
    assert not (vault / "recovery-points").exists(), "no partial (downgraded) recovery point is written"


FAULTS = [
    # victim, fault class, operation class that must be denied, operation class still admitted
    ("qdrant", "projection_lag_or_failure", "high_impact", "mutative"),
    ("opa", "idp_or_policy_engine_unavailable", "governed_new", "read"),
    ("postgresql", "audit_append_unavailable", "mutative", "read"),
    ("kafka", "broker_unavailable", None, "mutative"),
    ("spire-server", "idp_or_policy_engine_unavailable", "dispatch", "read"),
]


@pytest.mark.parametrize("victim,fault,denied,admitted", FAULTS, ids=[f[0] for f in FAULTS])
def test_dependency_fault_blocks_readiness_and_degrades_posture(stack, victim, fault, denied, admitted):
    container = f"ocor-bootstrap-{victim}-1"
    wait_for(lambda: readyz(stack.relay)[0] == 200, 60, message="precondition: READY before the fault")
    before = metrics(stack.relay).get(
        f'ocor_dependency_probe_errors_total{{dependency="{victim}",reason_code="DEPENDENCY_DOWN"}}', 0.0)
    subprocess.run(["docker", "pause", container], check=True, capture_output=True)
    try:
        status, ready = wait_for(lambda: (r := readyz(stack.relay))[0] == 503 and r, 30,
                                 message=f"readiness must block while {victim} is paused")
        assert f"DEPENDENCY_DOWN:{victim}" in ready["reasons"]
        _, posture = http_from(stack.relay, "http://ocor-ops:8080/posture")
        posture = json.loads(posture)
        assert fault in posture["faults"]
        if denied:
            code, body = http_from(stack.relay, f"http://ocor-ops:8080/admit?class={denied}")
            assert (code, json.loads(body)["decision"]) == (503, "DENY")
        code, body = http_from(stack.relay, f"http://ocor-ops:8080/admit?class={admitted}")
        assert (code, json.loads(body)["decision"]) == (200, "ADMIT")
        if victim == "kafka":
            assert posture["projection_freshness_claim"] is False
        if victim == "qdrant":
            assert posture["consistency"] == "PROJECTION_NOT_READY"
        m = metrics(stack.relay)
        assert m[f'ocor_dependency_up{{dependency="{victim}"}}'] == 0.0
        assert m[f'ocor_dependency_probe_errors_total{{dependency="{victim}",reason_code="DEPENDENCY_DOWN"}}'] > before
        assert m[f'ocor_safe_degraded_fault_active{{fault="{fault}"}}'] == 1.0
        _, traces = http_from(stack.relay, "http://ocor-ops:8080/traces")
        spans = [s for s in json.loads(traces)["spans"] if s.get("dependency") == victim
                 and s["reason_code"] == "DEPENDENCY_DOWN"]
        assert spans and spans[-1]["fault_class"] == fault and spans[-1]["causation_id"]
    finally:
        subprocess.run(["docker", "unpause", container], check=False, capture_output=True)
    wait_for(lambda: readyz(stack.relay)[0] == 200, 60, message=f"readiness must recover after {victim}")
    _, posture = http_from(stack.relay, "http://ocor-ops:8080/posture")
    assert json.loads(posture)["faults"] == []


def test_emergency_stop_denies_mutative_capabilities_within_10_seconds(stack):
    code, _ = http_from(stack.relay, "http://ocor-ops:8080/emergency-stop", "POST",
                        {"Authorization": "Bearer wrong-token"})
    assert code == 401
    assert http_from(stack.relay, "http://ocor-ops:8080/admit?class=mutative")[0] == 200
    started = time.monotonic()
    code, body = http_from(stack.relay, "http://ocor-ops:8080/emergency-stop", "POST",
                           {"Authorization": f"Bearer {stack.operator_token}"})
    assert code == 200 and json.loads(body)["reason_code"] == "EMERGENCY_STOP_ACTIVE"
    wait_for(lambda: http_from(stack.relay, "http://ocor-ops:8080/admit?class=mutative")[0] == 503, 10, 0.2)
    assert time.monotonic() - started <= 10.0
    assert http_from(stack.relay, "http://ocor-ops:8080/admit?class=read")[0] == 200
    code, body = http_from(stack.relay, "http://ocor-ops:8080/emergency-stop/clear", "POST",
                           {"Authorization": f"Bearer {stack.operator_token}"})
    assert code == 200 and json.loads(body)["reason_code"] == "EMERGENCY_STOP_CLEARED_BY_HUMAN"
    assert http_from(stack.relay, "http://ocor-ops:8080/admit?class=mutative")[0] == 200


def test_release_drift_blocks_readiness_and_mutative_commands(stack):
    profile = deepcopy(helm_profile())
    profile["observability"]["driftScanIntervalSeconds"] = 2
    profile["observability"]["probeIntervalSeconds"] = 2
    path = stack.work / "drift-profile.json"
    path.write_text(json.dumps(profile), encoding="utf-8")
    name = _standalone_ops(stack, stack.vault, f"{stack.ops_project}_site", profile_path=path)
    try:
        wait_for(lambda: _standalone_readyz(name)[0] == 200, 30, message="standalone ops must be READY")
        changed = deepcopy(profile)
        changed["profile"]["release"] = "ocor-poc-unapproved"
        path.write_text(json.dumps(changed), encoding="utf-8")
        _, ready = wait_for(lambda: (r := _standalone_readyz(name))[0] == 503 and r, 10,
                            message="drift must be detected within the scan interval")
        assert ready["reasons"] == ["RELEASE_DRIFT"]
        code, body = http_from(name, "http://127.0.0.1:8080/admit?class=mutative")
        assert code == 503 and "release_mismatch" in json.loads(body)["reason_code"]
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, check=False)


def test_default_deny_admits_only_allowlisted_intra_site_flows(stack):
    inspect = json.loads(subprocess.run(["docker", "network", "inspect", f"{stack.ops_project}_site"],
                                        capture_output=True, text=True, check=True).stdout)
    assert inspect[0]["Internal"] is True
    for flow in helm_profile()["isolation"]["allowedFlows"]:
        assert connect_from(stack.ops, flow["host"], flow["port"]) == "CONNECTED", flow
    assert connect_from(stack.ops, "1.1.1.1", 443).startswith("DENIED")
    assert connect_from(stack.ops, "registry.npmjs.org", 443) == "DNS_DENIED"
    assert connect_from(stack.ops, "ocor-bootstrap-postgresql-1", 5432) == "DNS_DENIED"
    assert connect_from(stack.ops, "postgresql", 22).startswith("DENIED"), "port outside the allowlist"
    assert connect_from(stack.ops, "keycloak", 8080).startswith("DENIED"), "admin port outside the allowlist"
    # Positive control: the same probe succeeds where egress is NOT denied, so the
    # denial above is produced by the profile, not by an offline host.
    control = subprocess.run(["docker", "run", "--rm", "--network", BOOTSTRAP_NETWORK, OPS_IMAGE, "python3", "-c",
                              "import socket; socket.create_connection(('1.1.1.1', 443), 5).close(); print('CONNECTED')"],
                             capture_output=True, text=True, check=False)
    assert control.stdout.strip() == "CONNECTED", "positive control failed: host egress unavailable"


def test_open_public_egress_blocks_readiness(stack):
    """The agent placed on a network WITH public egress must refuse readiness."""
    name = _standalone_ops(stack, stack.vault, BOOTSTRAP_NETWORK)
    try:
        _, ready = wait_for(lambda: scanned(r := _standalone_readyz(name)) and r, 30)
        assert ready["reasons"] == ["PUBLIC_EGRESS_OPEN"], "dependencies are up; only egress must block"
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, check=False)


def test_public_network_dependency_prevents_the_process_from_starting(stack):
    profile = deepcopy(helm_profile())
    profile["images"]["publicNetworkDependencyAtRuntime"] = True
    path = stack.work / "public-dependency.json"
    path.write_text(json.dumps(profile), encoding="utf-8")
    result = subprocess.run(
        ["docker", "run", "--rm", "--network", f"{stack.ops_project}_site",
         "-v", f"{stack.work / 'agent.py'}:/opt/ocor/ocor_ops_agent.py:ro", "-v", f"{path}:/etc/ocor/profile.json:ro",
         OPS_IMAGE, "python3", "/opt/ocor/ocor_ops_agent.py", "serve", "--profile", "/etc/ocor/profile.json"],
        capture_output=True, text=True, check=False, timeout=60)
    assert result.returncode == EXIT_CONFIG
    assert "public-network runtime dependency blocks startup" in result.stderr


def test_logs_and_traces_carry_governed_fields_and_no_secrets(stack):
    logs = subprocess.run(["docker", "logs", stack.ops], capture_output=True, text=True, check=True).stdout
    records = [json.loads(line) for line in logs.splitlines() if line.startswith("{")]
    assert records
    for record in records:
        assert set(LOG_FIELDS) <= set(record), record
        assert record["classification_marking_ref"] == "SYNTHETIC-UNCLASSIFIED"
    assert any(r["reason_code"] == "DEPENDENCY_DOWN" for r in records), "fault telemetry observed"
    assert any(r["reason_code"] == "READY" for r in records), "positive event telemetry observed"
    assert any(r["policy_digest"] for r in records), "policy digest read from the real OPA"
    spans = [r["span"] for r in records if r["operation"] == "span"]
    assert all(s["trace_id"] and s["span_id"] and s["correlation_id"] for s in spans)
    everything = logs
    for project in stack.projects:
        everything += stack.compose(project, "--profile", "full", "--profile", "restore-drill", "logs").stdout
    for secret in (stack.env["OCOR_LOCAL_OPENBAO_TOKEN"], stack.env["OCOR_LOCAL_POSTGRES_PASSWORD"],
                   stack.operator_token):
        assert secret not in everything


# --------------------------------------------------------------------------- Helm on Kubernetes


KIND_CLUSTER = "ocor-poc"
KIND_NODE_IMAGE = ("kindest/node:v1.33.1@sha256:"
                   "050072256b9a903bd914c0b2866828150cb229cea0efe5892e2b644d5dd3b34f")
KIND_VAULT_ROOT = Path.home() / ".ocor-poc" / "kind-vault"


def kubectl(*args: str, check: bool = True, timeout: int = 180) -> subprocess.CompletedProcess:
    result = subprocess.run([tool("kubectl"), "--context", f"kind-{KIND_CLUSTER}", *args], capture_output=True,
                            text=True, check=False, timeout=timeout)
    if check:
        assert result.returncode == 0, result.stdout + result.stderr
    return result


@pytest.fixture(scope="module")
def kind(stack):
    """Disposable Kubernetes (DEC-211): kind node with the vault mounted from the
    host (outside the cluster fault domain) and attached to the bootstrap network."""
    clusters = subprocess.run([tool("kind"), "get", "clusters"], capture_output=True, text=True, check=False)
    created = KIND_CLUSTER not in clusters.stdout.split()
    if created:
        KIND_VAULT_ROOT.mkdir(parents=True, exist_ok=True)
        config = stack.work / "kind.yaml"
        config.write_text(yaml.safe_dump({
            "kind": "Cluster", "apiVersion": "kind.x-k8s.io/v1alpha4",
            "nodes": [{"role": "control-plane", "image": KIND_NODE_IMAGE,
                       "extraMounts": [{"hostPath": str(KIND_VAULT_ROOT), "containerPath": "/ocor-vault"}]}]}))
        result = subprocess.run([tool("kind"), "create", "cluster", "--name", KIND_CLUSTER, "--config", str(config),
                                 "--wait", "180s"], capture_output=True, text=True, check=False, timeout=600)
        assert result.returncode == 0, result.stderr
    node = f"{KIND_CLUSTER}-control-plane"
    subprocess.run(["docker", "network", "connect", BOOTSTRAP_NETWORK, node], capture_output=True, check=False)
    images = {v for k, v in yaml.safe_load(VALUES.read_text())["operational"].items() if k.endswith("mage")}
    for image in sorted(images):
        for attempt in range(3):
            if subprocess.run(["docker", "exec", node, "crictl", "inspecti", image], capture_output=True).returncode == 0:
                break
            subprocess.run(["docker", "exec", node, "crictl", "pull", image], capture_output=True, timeout=900)
            time.sleep(attempt * 5)
        assert subprocess.run(["docker", "exec", node, "crictl", "inspecti", image],
                              capture_output=True).returncode == 0, f"image {image} unavailable in kind"
    run = uuid.uuid4().hex[:6]
    namespace = f"ocor-poc-{run}"
    vault = KIND_VAULT_ROOT / run
    vault.mkdir(parents=True)
    bootstrap = json.loads(subprocess.run(["docker", "network", "inspect", BOOTSTRAP_NETWORK], capture_output=True,
                                          text=True, check=True).stdout)[0]
    aliases = {}
    for container in bootstrap["Containers"].values():
        match = re.fullmatch(r"ocor-bootstrap-(.+)-1", container["Name"])
        if match and match.group(1) in BOOTSTRAP_SERVICES:
            aliases[match.group(1)] = container["IPv4Address"].split("/")[0]
    cidr = bootstrap["IPAM"]["Config"][0]["Subnet"]
    kubectl("create", "namespace", namespace)
    kubectl("-n", namespace, "create", "secret", "generic", "ocor-poc-ops",
            f"--from-literal=OCOR_OPENBAO_TOKEN={stack.env['OCOR_LOCAL_OPENBAO_TOKEN']}",
            f"--from-literal=OCOR_OPS_OPERATOR_TOKEN={stack.operator_token}",
            f"--from-literal=PGPASSWORD={stack.env['OCOR_LOCAL_POSTGRES_PASSWORD']}")
    storage = stack.work / f"vault-{run}.yaml"
    storage.write_text(yaml.safe_dump_all([
        {"apiVersion": "v1", "kind": "PersistentVolume", "metadata": {"name": namespace},
         "spec": {"capacity": {"storage": "2Gi"}, "accessModes": ["ReadWriteOnce"], "storageClassName": "ocor-vault",
                  "persistentVolumeReclaimPolicy": "Retain", "hostPath": {"path": f"/ocor-vault/{run}"},
                  "claimRef": {"namespace": namespace, "name": "ocor-poc-vault"}}},
        {"apiVersion": "v1", "kind": "PersistentVolumeClaim", "metadata": {"name": "ocor-poc-vault",
                                                                           "namespace": namespace},
         "spec": {"accessModes": ["ReadWriteOnce"], "storageClassName": "ocor-vault", "volumeName": namespace,
                  "resources": {"requests": {"storage": "2Gi"}}}}]))
    kubectl("apply", "-f", str(storage))
    values = stack.work / f"values-{run}.yaml"
    values.write_text(yaml.safe_dump({"operational": {
        "secretName": "ocor-poc-ops", "vault": {"existingClaim": "ocor-poc-vault"},
        "runAsUser": os.getuid(), "dependencyCidr": cidr,
        "hostAliases": [{"ip": ip, "hostnames": [name]} for name, ip in sorted(aliases.items())]}}))
    ctx = {"namespace": namespace, "vault": vault, "values": values, "release": "ocor-poc"}
    try:
        result = subprocess.run([tool("helm"), "--kube-context", f"kind-{KIND_CLUSTER}", "install", "ocor-poc",
                                 str(CHART_DIR), "-n", namespace, "-f", str(values)],
                                capture_output=True, text=True, check=False, timeout=300)
        assert result.returncode == 0, result.stderr
        yield ctx
    finally:
        kubectl("delete", "namespace", namespace, "--wait=true", check=False, timeout=300)
        kubectl("delete", "pv", namespace, check=False)
        if created and os.environ.get("OCOR_KEEP_KIND") != "1":
            subprocess.run([tool("kind"), "delete", "cluster", "--name", KIND_CLUSTER], capture_output=True,
                           check=False, timeout=300)
        make_writable(vault)
        shutil.rmtree(vault, ignore_errors=True)


def pod_name(ns: str, component: str) -> str:
    return kubectl("-n", ns, "get", "pod", "-l", f"app.kubernetes.io/component={component}",
                   "-o", "jsonpath={.items[0].metadata.name}").stdout


def pod_ready(ns: str, component: str) -> bool:
    out = kubectl("-n", ns, "get", "pod", "-l", f"app.kubernetes.io/component={component}", "-o",
                  "jsonpath={.items[0].status.conditions[?(@.type=='Ready')].status}", check=False).stdout
    return out == "True"


def pod_python(ns: str, pod: str, code: str) -> str:
    return kubectl("-n", ns, "exec", pod, "--", "python3", "-c", code).stdout.strip()


def run_job(ns: str, args: list[str], name: str, timeout: int = 600) -> tuple[str, str]:
    kubectl("-n", ns, *args)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = kubectl("-n", ns, "get", "job", name, "-o",
                         "jsonpath={.status.succeeded}/{.status.failed}", check=False).stdout
        if status.startswith("1/") or status.endswith("/1"):
            logs = kubectl("-n", ns, "logs", f"job/{name}", "--all-containers=true", check=False).stdout
            return status, logs
        time.sleep(3)
    pytest.fail(f"job {name} did not finish")


def test_helm_profile_on_kubernetes_backs_up_restores_and_gates_readiness(kind):
    ns, vault = kind["namespace"], kind["vault"]
    ops = wait_for(lambda: pod_name(kind["namespace"], "ops"), 120, 2, "ops pod scheduled")
    wait_for(lambda: kubectl("-n", ns, "get", "pod", ops, "-o", "jsonpath={.status.phase}",
                             check=False).stdout == "Running", 300, 3, "ops pod running")
    time.sleep(8)
    assert not pod_ready(ns, "ops"), "pod must not be Ready before a tested restore exists"
    probe = pod_python(ns, ops, "import urllib.request,urllib.error\ntry: urllib.request.urlopen("
                       "'http://127.0.0.1:8080/readyz',timeout=5)\nexcept urllib.error.HTTPError as e: "
                       "print(e.code, e.read().decode())")
    assert probe.startswith("503") and "RESTORE_UNTESTED" in probe, probe
    status, logs = run_job(ns, ["create", "job", "ocor-poc-backup-manual", "--from=cronjob/ocor-poc-backup"],
                           "ocor-poc-backup-manual")
    assert status.startswith("1/"), logs
    assert len(list((vault / "recovery-points").iterdir())) == 1, "backup written to the external vault"
    result = subprocess.run([tool("helm"), "--kube-context", f"kind-{KIND_CLUSTER}", "upgrade", "ocor-poc",
                             str(CHART_DIR), "-n", ns, "-f", str(kind["values"]), "--set",
                             "operational.restoreDrill.enabled=true"], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    status, logs = run_job(ns, ["get", "job", "ocor-poc-restore-drill-2"], "ocor-poc-restore-drill-2")
    assert status.startswith("1/"), logs
    receipt = latest_receipt(vault)
    assert receipt["outcome"] == "PASSED" and receipt["replayed_event_ids"] == ["evt-del-m2", "evt-del-m4"]
    ops = pod_name(ns, "ops")
    wait_for(lambda: pod_ready(ns, "ops"), 60, 2, "ops pod Ready after a tested restore")
    egress = pod_python(ns, ops, "import socket\nfor t in [('1.1.1.1',443),('postgresql',5432),('opa',8181)]:\n"
                        "    try: socket.create_connection(t,4).close(); print(t[0],'CONNECTED')\n"
                        "    except OSError as e: print(t[0],'DENIED')")
    assert egress.splitlines() == ["1.1.1.1 DENIED", "postgresql CONNECTED", "opa CONNECTED"], egress
    subprocess.run(["docker", "pause", "ocor-bootstrap-qdrant-1"], check=True, capture_output=True)
    try:
        wait_for(lambda: not pod_ready(ns, "ops"), 60, 2, "pod readiness must drop while qdrant is paused")
    finally:
        subprocess.run(["docker", "unpause", "ocor-bootstrap-qdrant-1"], check=False, capture_output=True)
    wait_for(lambda: pod_ready(ns, "ops"), 90, 2, "pod readiness must recover")


# --------------------------------------------------------------------------- VF-006


def test_missing_environment_fails_instead_of_skipping(tmp_path):
    """A byte-identical copy of this module, run where no bootstrap env exists,
    must FAIL (non-zero, zero skips) rather than silently pass."""
    copy = tmp_path / "isolated" / "test_copy.py"
    copy.parent.mkdir()
    shutil.copy2(Path(__file__), copy)
    env = {k: v for k, v in os.environ.items() if not k.startswith("OCOR_")}
    env.update({"HOME": str(tmp_path), "OCOR_BOOTSTRAP_ENV": str(tmp_path / "absent.env")})
    result = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(copy),
                             "-k", "test_ops_process_serves_health", "--junitxml", str(tmp_path / "r.xml")],
                            capture_output=True, text=True, env=env, cwd=tmp_path, check=False, timeout=300)
    assert result.returncode == 1, result.stdout
    report = (tmp_path / "r.xml").read_text()
    assert 'skipped="0"' in report, report
    assert 'errors="1"' in report or 'failures="1"' in report, report
    assert "ocor-bootstrap env file not found" in result.stdout
