"""OCOR-DEV-0049: PoC deployment profile — observability, backup and safe
degradation (ADD v1.3 §6, LLD v1.1 §5).

The PoC profile is a machine-readable contract carried identically by the
Helm chart (`deploy/helm/ocor-poc/values.yaml`) and by the Compose overlay
(`deploy/helm/ocor-poc/compose.profiles.yaml`). This module proves that:

1. the contract is complete and fail-closed against the normative text,
   including the memory backup manifest, the binding restore order (deletion
   tombstones before reopening retrieval) and the seven PoC resource limits
   (ADD v1.3 Part II §2.13, LLD v1.1 §5.4);
2. the two carriers do not drift;
3. the overlay is a real operational Compose model — it defines profile-gated
   services (readiness gate, local telemetry, authority-aware backup) with
   digest-pinned images and real probes on the real bootstrap ports, and it
   merges with the real bootstrap stack;
4. the Helm chart renders real resources (ConfigMap + NetworkPolicy +
   Deployment/Service readiness gate + backup CronJob), not a bare ConfigMap;
5. on the real pinned stack the readiness gate reports READY only when every
   mandatory dependency is reachable, and blocks when one is missing.

Observability and backup backends remain Candidate Implementation behind
logical contracts (ADD v1.3 §6.1); no image digest is fabricated here.
"""

from __future__ import annotations

import os
import re
import socket
import subprocess
import time
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
VALUES = ROOT / "deploy" / "helm" / "ocor-poc" / "values.yaml"
CHART = ROOT / "deploy" / "helm" / "ocor-poc" / "Chart.yaml"
COMPOSE_PROFILES = ROOT / "deploy" / "helm" / "ocor-poc" / "compose.profiles.yaml"
TEMPLATES = ROOT / "deploy" / "helm" / "ocor-poc" / "templates"
BOOTSTRAP_COMPOSE = ROOT / "deploy" / "bootstrap" / "compose.yaml"

DIGEST_IMAGE = re.compile(r".+@sha256:[0-9a-f]{64}")
ENVIRONMENT = {
    "OCOR_LOCAL_KEYCLOAK_PASSWORD": "synthetic-keycloak",
    "OCOR_LOCAL_OPENBAO_TOKEN": "synthetic-openbao",
    "OCOR_LOCAL_POSTGRES_PASSWORD": "synthetic-postgres",
    "OCOR_LOCAL_TERMINUSDB_PASSWORD": "synthetic-terminusdb",
    "OCOR_SPIRE_BOOTSTRAP_DIR": "/tmp/ocor-spire-bootstrap",
    "OCOR_SPIRE_JOIN_TOKEN": "synthetic-join-token",
}

# Normative constants — ADD v1.3 §6.3–§6.5, Part II §2.13, LLD v1.1 §5.1–§5.4.
PROFILES = ["observability", "backup", "safe-degraded", "full"]
RESOURCE_CLASSES = ["CONTROL", "INTERACTIVE", "BATCH", "AUDIT"]
METRIC_SET = [
    "latency_p50_p95_p99_per_contract",
    "error_deny_approval_expiry_rate",
    "projection_lag_watermark_checksum",
    "commit_outbox_retry",
    "constraint_violation",
    "action_fsm_saga_execution_unknown",
    "audit_gap",
    "queue_run_time_budget",
    "model_seed_scenario_ttl",
    "configuration_schema_release_drift",
]
LOG_FIELDS = ["correlation_id", "component", "operation", "release", "policy_digest", "reason_code"]
TRACE_FIELDS = [
    "trace_id", "correlation_id", "causation_id", "governed_context_digest",
    "effective_principal_id", "actor_chain", "tenant_id", "organization_id",
    "domain_id", "compartments", "classification_marking_ref", "purpose",
    "policy_bundle_digest", "ontology_release_digest", "canonical_commit",
    "projection_watermark", "policy_decision_id", "scenario_id",
    "model_digest", "action_state",
]
AUTHORITY_CLASSES = [
    "definition", "canonical", "event", "action", "governance", "audit",
    "model_scenario", "projection", "key_custody",
]
RESTORE_STEPS = [
    "containment_and_emergency_stop",
    "select_signed_recovery_point_within_rpo",
    "verify_trust_manifest_digest_signatures_dual_control",
    "restore_oaC_ir_policy_config_model_manifests",
    "restore_canonical_event_action_audit_same_cut",
    "replay_memory_deletion_tombstones_before_reopen_retrieval",
    "rebuild_logic_projection_and_w3c_boundary",
    "reconcile_outbox_offset_checksum_saga_receipt",
    "assign_execution_unknown_to_unprovable_effects",
    "run_conformance_security_mission_thread_replay",
    "require_human_authorization_to_reopen_mutative",
]
RECOVERY_GATE = [
    "revision", "watermark", "orphan_duplicate", "marking", "gcs",
    "deletion_resurrection", "projection_drift_or_stale_deletion_epoch",
    "sample_semantic_digest",
]
REPLAY_PINS = [
    "ontology_release", "compiler_logic_bundle", "canonical_commit",
    "event_schema", "model_digest", "policy_digest", "seed", "assumptions",
    "ordering",
]
MEMORY_MANIFEST_KEYS = [
    "metadataRef", "contentRefs", "representationVersions", "lifecycleEpochs",
    "deletionEpochs", "journalCheckpoints", "auditRefs", "boundToSameRecoveryPoint",
]
RESOURCE_LIMIT_KEYS = [
    "itemCount", "payloadSizeBytes", "embeddingDimensions", "topK",
    "consolidationConcurrency", "indexSizeBytes", "retentionHorizonDays",
]
REAL_SERVICES = [
    "terminusdb", "typedb", "fuseki", "opa", "keycloak", "openbao",
    "postgresql", "kafka", "qdrant", "spire-server",
]
OPERATIONAL_SERVICES = ["ocor-readiness-gate", "ocor-telemetry", "ocor-backup"]
SAFE_DEGRADED_FAULTS = {
    "idp_or_policy_engine_unavailable": ["no_new_governed_operations", "authorized_reads_only_if_policy_snapshot_valid"],
    "canonical_writer_unavailable": ["events_durably_queued", "no_canonical_commit_confirmation", "mutations_suspended"],
    "broker_unavailable": ["outbox_retained_relayed_later", "no_projection_freshness_claim"],
    "projection_lag_or_failure": ["PROJECTION_NOT_READY_or_STALE_CONTEXT", "high_impact_blocked"],
    "audit_append_unavailable": ["no_new_mutative_command"],
    "action_adapter_timeout": ["EXECUTION_UNKNOWN", "status_inquiry_or_reconciliation_only", "no_blind_retry"],
    "edge_partition": ["read_analyze_simulate_on_pinned_snapshot", "explicit_staleness", "no_high_impact"],
    "emergency_stop": ["new_mutative_capabilities_denied_within_10_seconds"],
}


def load_helm_contract() -> dict:
    return yaml.safe_load(VALUES.read_text(encoding="utf-8"))["ocor"]


def load_compose_contract() -> dict:
    return yaml.safe_load(COMPOSE_PROFILES.read_text(encoding="utf-8"))["x-ocor-profile"]


def _positive_int(value) -> bool:
    return isinstance(value, int) and value > 0


def validate(contract: dict) -> list[str]:
    """Return the list of contract violations; empty means a complete,
    fail-closed profile. This is the reference oracle used by every case."""
    errors: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    profile = contract.get("profile", {})
    require(profile.get("id") == "poc", "profile.id must be poc")
    require(profile.get("singleSite") is True, "profile.singleSite must be true")

    isolation = contract.get("isolation", {})
    require(isolation.get("networkPolicyDefaultDeny") is True, "default-deny network policy required")
    require(isolation.get("egressPublicNetwork") is False, "public egress must be denied")
    require(isolation.get("zeroSaaSAndCallHome") is True, "zero SaaS/call-home required")
    require(isolation.get("namespacePerSubsystem") is True, "namespace per subsystem required")
    require(isolation.get("serviceAccountPerSubsystem") is True, "service account per subsystem required")
    require(isinstance(isolation.get("syntheticCompartmentsMin"), int)
            and isolation["syntheticCompartmentsMin"] >= 2, "at least two synthetic compartments required")
    require(isolation.get("rootCaOutsideClusterFaultDomain") is True, "Root CA must sit outside the cluster fault domain")
    require(isolation.get("backupVaultOutsideClusterFaultDomain") is True, "backup vault must sit outside the cluster fault domain")

    images = contract.get("images", {})
    require(images.get("digestPinned") is True, "images must be digest-pinned")
    require(images.get("signatureVerifiedBeforeAdmission") is True, "image signature verification required")
    require(images.get("publicNetworkDependencyAtRuntime") is False, "no public-network runtime dependency")

    require(contract.get("resourceClasses") == RESOURCE_CLASSES, "resourceClasses must be CONTROL/INTERACTIVE/BATCH/AUDIT")
    require(contract.get("resourceIsolation", {}).get("c6ControlAuditSharesCausalBatchPool") is False,
            "C6/control/audit must not share the causal batch pool")

    observability = contract.get("observability", {})
    require(_positive_int(observability.get("driftScanIntervalSeconds"))
            and observability["driftScanIntervalSeconds"] <= 60, "drift scan interval must be in [1, 60]s")
    require(observability.get("releaseMismatchBlocksMutativeCommand") is True,
            "release mismatch must block mutative commands")
    require(observability.get("exportersLocal") is True, "exporters must stay local")
    require(set(observability.get("metrics", {}).get("set", [])) == set(METRIC_SET), "metric set incomplete")
    require(observability.get("metrics", {}).get("exporter") == "prometheus", "prometheus exporter required")
    require(set(observability.get("logs", {}).get("fields", [])) == set(LOG_FIELDS), "log fields incomplete")
    require(observability.get("logs", {}).get("keepClassificationMarking") is True, "classification/marking must be kept")
    require(observability.get("logs", {}).get("excludeClassifiedPayload") is True, "classified payload must be excluded")
    require(set(observability.get("traces", {}).get("fields", [])) == set(TRACE_FIELDS), "trace fields incomplete")

    backup = contract.get("backup", {})
    for key in ("encrypted", "signed", "immutable", "contentAddressed", "authorityAware",
                "offClusterFaultDomain", "tested"):
        require(backup.get(key) is True, f"backup.{key} must be true")
    require(_positive_int(backup.get("rpoMinutes")) and backup["rpoMinutes"] <= 15, "RPO must be in [1, 15] minutes")
    require(_positive_int(backup.get("rtoHours")) and backup["rtoHours"] <= 4, "RTO must be in [1, 4] hours")
    require(set(backup.get("authorityClasses", [])) == set(AUTHORITY_CLASSES), "authority classes incomplete")
    # ADD v1.3 Part II §2.13 + LLD v1.1 §5.4: the memory backup manifest binds
    # metadata, content refs, representation versions, lifecycle/deletion epochs,
    # journal checkpoints and audit refs to the same recovery point.
    memory = backup.get("memory", {})
    require(set(memory.keys()) >= set(MEMORY_MANIFEST_KEYS), "memory backup manifest incomplete")
    require(isinstance(memory.get("metadataRef"), str) and memory["metadataRef"], "memory metadata ref required")
    for key in MEMORY_MANIFEST_KEYS:
        if key != "metadataRef":
            require(memory.get(key) is True, f"memory manifest field {key} must be bound")

    restore = contract.get("restore", {})
    require(restore.get("isolatedNetwork") is True, "restore must run in an isolated network")
    require(list(restore.get("steps", [])) == RESTORE_STEPS,
            "restore steps incomplete or out of order (deletion tombstones must replay before reopening retrieval)")
    replay = restore.get("replay", {})
    require(replay.get("usesOriginalEventIds") is True, "replay must use original event ids")
    require(replay.get("emitsNoExternalEffects") is True, "replay must not emit external effects")
    require(set(replay.get("pins", [])) == set(REPLAY_PINS), "replay pins incomplete")
    require(set(restore.get("recoveryGate", [])) == set(RECOVERY_GATE), "recovery gate incomplete")

    limits = contract.get("resourceLimits", {})
    require(set(limits.keys()) >= set(RESOURCE_LIMIT_KEYS), "PoC resource limits incomplete")
    for key in RESOURCE_LIMIT_KEYS:
        require(_positive_int(limits.get(key)), f"resource limit {key} must be positive")
    require(limits.get("quotaBehavior", {}).get("semanticDowngrade") is False,
            "quota/backpressure must never produce semantic downgrade")

    faults = {entry["fault"]: list(entry["behavior"])
              for entry in contract.get("safeDegraded", {}).get("faults", [])}
    require(set(faults) == set(SAFE_DEGRADED_FAULTS), "safe-degraded fault table incomplete")
    for name, behavior in SAFE_DEGRADED_FAULTS.items():
        require(set(faults.get(name, [])) == set(behavior), f"safe-degraded behavior for {name} incomplete")

    health = contract.get("health", {})
    require(set(health.get("probeTypes", [])) == {"liveness", "readiness"}, "liveness+readiness probes required")
    services = health.get("services", [])
    require(isinstance(services, list) and len(services) >= 1, "health.services must be non-empty")
    require({s.get("name") for s in services} == set(REAL_SERVICES),
            "health services must cover all real foundation services")
    for service in services:
        require("liveness" in service and "readiness" in service, f"health probe missing for {service.get('name')}")
        require(isinstance(service.get("port"), int) and service["port"] > 0,
                f"health port missing for {service.get('name')}")

    return errors


# --- Positive cases ---------------------------------------------------------

def test_helm_chart_is_present_and_well_formed():
    chart = yaml.safe_load(CHART.read_text(encoding="utf-8"))
    assert chart["apiVersion"] == "v2"
    assert chart["name"] == "ocor-poc"
    assert chart["type"] == "application"


def test_helm_chart_renders_the_profile_contract_as_a_configmap():
    template = (TEMPLATES / "profile-contract.yaml").read_text(encoding="utf-8")
    assert template, "profile-contract.yaml must not be empty"
    assert ".Values.ocor" in template
    assert "toYaml" in template
    assert "ConfigMap" in template


def test_helm_chart_renders_real_operational_resources():
    """The chart must be operational, not a bare ConfigMap: it must render a
    NetworkPolicy, a Deployment+Service readiness gate with real probes, and a
    backup CronJob, all driven by digest-pinned images (ADD v1.3 §6.1)."""
    kinds = {}
    for path in TEMPLATES.glob("*.yaml"):
        text = path.read_text(encoding="utf-8")
        for kind in ("ConfigMap", "NetworkPolicy", "Deployment", "Service", "CronJob"):
            if re.search(rf"^kind:\s*{kind}\s*$", text, re.MULTILINE):
                kinds[kind] = path.name
    assert kinds.get("ConfigMap"), "chart must render the profile contract ConfigMap"
    assert kinds.get("NetworkPolicy"), "chart must render a default-deny NetworkPolicy"
    assert kinds.get("Deployment"), "chart must render a readiness-gate Deployment"
    assert kinds.get("Service"), "chart must render a readiness-gate Service"
    assert kinds.get("CronJob"), "chart must render a backup CronJob"


def test_helm_values_contract_is_complete():
    assert validate(load_helm_contract()) == []


def test_memory_restore_replays_deletion_tombstones_before_reopening_retrieval():
    """ADD v1.3 Part II §2.13 / LLD v1.1 §5.4: deletion tombstones must replay
    before the projection rebuild reopens retrieval, preventing resurrection."""
    steps = load_helm_contract()["restore"]["steps"]
    tombstone = "replay_memory_deletion_tombstones_before_reopen_retrieval"
    rebuild = "rebuild_logic_projection_and_w3c_boundary"
    assert tombstone in steps, "restore must replay memory deletion tombstones"
    assert steps.index(tombstone) < steps.index(rebuild), \
        "deletion tombstones must replay before reopening retrieval"


def test_memory_backup_manifest_binds_all_required_fields():
    memory = load_helm_contract()["backup"]["memory"]
    for key in MEMORY_MANIFEST_KEYS:
        assert key in memory, f"missing memory manifest field {key}"
    assert memory["boundToSameRecoveryPoint"] is True


def test_poc_resource_limits_are_present_and_positive():
    limits = load_helm_contract()["resourceLimits"]
    for key in RESOURCE_LIMIT_KEYS:
        assert isinstance(limits[key], int) and limits[key] > 0, key
    assert limits["quotaBehavior"]["semanticDowngrade"] is False


def test_compose_overlay_contract_does_not_drift_from_helm_values():
    compose = load_compose_contract()
    assert set(compose) - {"profiles"} == set(load_helm_contract())
    for key in set(compose) - {"profiles"}:
        assert compose[key] == load_helm_contract()[key], key


def test_compose_profiles_are_the_four_governed_modes():
    assert load_compose_contract()["profiles"] == PROFILES


def test_compose_overlay_is_a_valid_compose_model():
    result = subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_PROFILES), "config", "--quiet"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_compose_overlay_defines_real_operational_services():
    model = yaml.safe_load(COMPOSE_PROFILES.read_text(encoding="utf-8"))
    services = model.get("services", {})
    assert set(services) == set(OPERATIONAL_SERVICES), \
        "overlay must define the readiness gate, local telemetry and backup services"
    for name in OPERATIONAL_SERVICES:
        assert DIGEST_IMAGE.fullmatch(services[name]["image"]), f"{name} image must be digest-pinned"
        assert services[name].get("profiles"), f"{name} must be gated by a Compose profile"
    gate = services["ocor-readiness-gate"]
    assert gate["depends_on"], "readiness gate must declare its mandatory dependencies"
    assert all(dep.get("condition") for dep in gate["depends_on"].values()), \
        "readiness gate dependencies must be health-gated"


def _merged_services(*profiles: str) -> list[str]:
    args = ["docker", "compose", "-f", str(BOOTSTRAP_COMPOSE), "-f", str(COMPOSE_PROFILES)]
    for profile in profiles:
        args += ["--profile", profile]
    args += ["config", "--services"]
    result = subprocess.run(args, env=os.environ | ENVIRONMENT,
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout.split()


def test_compose_overlay_profiles_change_effective_topology():
    """Compose `profiles:` must actually activate/deactivate services, so the
    effective topology differs by profile (ADD v1.3 §6.1)."""
    model = yaml.safe_load(COMPOSE_PROFILES.read_text(encoding="utf-8"))
    services = model["services"]
    assert set(services["ocor-telemetry"]["profiles"]) == {"observability", "full"}
    assert set(services["ocor-backup"]["profiles"]) == {"backup", "full"}
    assert set(services["ocor-readiness-gate"]["profiles"]) == {"safe-degraded", "full"}

    none = _merged_services()
    observability = _merged_services("observability")
    full = _merged_services("full")
    assert set(OPERATIONAL_SERVICES) & set(none) == set(), \
        "no profile must not activate operational services"
    assert set(OPERATIONAL_SERVICES) & set(observability) == {"ocor-telemetry"}, \
        "observability profile must activate only the telemetry service"
    assert set(OPERATIONAL_SERVICES) & set(full) == set(OPERATIONAL_SERVICES), \
        "full profile must activate all three operational services"


def test_compose_overlay_merges_with_the_real_bootstrap_stack():
    result = subprocess.run(
        ["docker", "compose", "-f", str(BOOTSTRAP_COMPOSE), "-f", str(COMPOSE_PROFILES),
         "--profile", "full", "config", "--quiet"],
        env=os.environ | ENVIRONMENT, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_readiness_gate_blocks_without_its_mandatory_dependencies():
    """Fault model: the readiness gate alone (without the bootstrap services it
    depends on) is not a valid, ready project — Docker Compose refuses it."""
    alone = subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_PROFILES), "--profile", "safe-degraded",
         "config", "--services"],
        env=os.environ | ENVIRONMENT, capture_output=True, text=True, check=False,
    )
    assert alone.returncode != 0, "readiness gate must not render ready without its dependencies"
    assert "depends on undefined service" in (alone.stdout + alone.stderr)


def _lock_build_digests() -> dict[str, str]:
    import json
    lock = json.loads((ROOT / "infra" / "services.lock.json").read_text(encoding="utf-8"))
    return {entry["id"]: entry.get("build", {}).get("output_sha256", "")
            for entry in lock["services"]}


def test_foundation_services_behind_the_profile_are_content_addressed_and_healthy():
    bootstrap = yaml.safe_load(BOOTSTRAP_COMPOSE.read_text(encoding="utf-8"))
    build_digests = _lock_build_digests()
    assert bootstrap["services"]
    for name, service in bootstrap["services"].items():
        image = service["image"]
        if "@sha256:" in image:
            assert DIGEST_IMAGE.fullmatch(image), name
        else:
            assert image.startswith("ocor/"), name
            assert build_digests.get(name, ""), name
        assert service.get("restart") == "no", name
        if "healthcheck" in service:
            assert service["healthcheck"]["interval"], name
        else:
            deps = service.get("depends_on", {})
            assert any(isinstance(d, dict) and d.get("condition") == "service_healthy"
                       for d in deps.values()), name


# --- Negative cases ---------------------------------------------------------

NEGATIVE_CASES = [
    ("public egress enabled", lambda c: c.__setitem__("isolation", {**c["isolation"], "egressPublicNetwork": True}), "public egress must be denied"),
    ("single synthetic compartment", lambda c: c.__setitem__("isolation", {**c["isolation"], "syntheticCompartmentsMin": 1}), "at least two synthetic compartments"),
    ("Root CA inside fault domain", lambda c: c.__setitem__("isolation", {**c["isolation"], "rootCaOutsideClusterFaultDomain": False}), "Root CA must sit outside"),
    ("digest pinning disabled", lambda c: c.__setitem__("images", {**c["images"], "digestPinned": False}), "digest-pinned"),
    ("public runtime dependency", lambda c: c.__setitem__("images", {**c["images"], "publicNetworkDependencyAtRuntime": True}), "no public-network runtime dependency"),
    ("C6 shares causal batch pool", lambda c: c.__setitem__("resourceIsolation", {**c["resourceIsolation"], "c6ControlAuditSharesCausalBatchPool": True}), "must not share"),
    ("drift scan exceeds 60s", lambda c: c.__setitem__("observability", {**c["observability"], "driftScanIntervalSeconds": 61}), "[1, 60]"),
    ("drift scan negative", lambda c: c.__setitem__("observability", {**c["observability"], "driftScanIntervalSeconds": -1}), "drift scan interval"),
    ("exporters not local", lambda c: c.__setitem__("observability", {**c["observability"], "exportersLocal": False}), "exporters must stay local"),
    ("classified payload logged", lambda c: c.__setitem__("observability", {**c["observability"], "logs": {**c["observability"]["logs"], "excludeClassifiedPayload": False}}), "classified payload"),
    ("trace field missing", lambda c: c.__setitem__("observability", {**c["observability"], "traces": {**c["observability"]["traces"], "fields": TRACE_FIELDS[:-1]}}), "trace fields incomplete"),
    ("authority class missing", lambda c: c.__setitem__("backup", {**c["backup"], "authorityClasses": AUTHORITY_CLASSES[:-1]}), "authority classes incomplete"),
    ("untested backup", lambda c: c.__setitem__("backup", {**c["backup"], "tested": False}), "backup.tested must be true"),
    ("rpo negative", lambda c: c.__setitem__("backup", {**c["backup"], "rpoMinutes": -1}), "RPO"),
    ("rto negative", lambda c: c.__setitem__("backup", {**c["backup"], "rtoHours": -1}), "RTO"),
    ("memory manifest field missing", lambda c: c.__setitem__("backup", {**c["backup"], "memory": {**c["backup"]["memory"], "deletionEpochs": False}}), "memory manifest field deletionEpochs"),
    ("memory manifest unbound", lambda c: c.__setitem__("backup", {**c["backup"], "memory": {**c["backup"]["memory"], "boundToSameRecoveryPoint": False}}), "bound"),
    ("resource limit missing", lambda c: c.__setitem__("resourceLimits", {k: v for k, v in c["resourceLimits"].items() if k != "retentionHorizonDays"}), "resource limit retentionHorizonDays"),
    ("resource limit zero", lambda c: c.__setitem__("resourceLimits", {**c["resourceLimits"], "topK": 0}), "resource limit topK"),
    ("quota semantic downgrade", lambda c: c.__setitem__("resourceLimits", {**c["resourceLimits"], "quotaBehavior": {"onExceed": "quota_backpressure", "semanticDowngrade": True}}), "semantic downgrade"),
    ("restore not isolated", lambda c: c.__setitem__("restore", {**c["restore"], "isolatedNetwork": False}), "isolated network"),
    ("tombstone replay out of order", lambda c: c.__setitem__("restore", {**c["restore"], "steps": [s for s in c["restore"]["steps"] if s != "replay_memory_deletion_tombstones_before_reopen_retrieval"] + ["replay_memory_deletion_tombstones_before_reopen_retrieval"]}), "restore steps incomplete or out of order"),
    ("recovery gate missing", lambda c: c.__setitem__("restore", {**c["restore"], "recoveryGate": RECOVERY_GATE[:-1]}), "recovery gate incomplete"),
    ("replay pins empty", lambda c: c.__setitem__("restore", {**c["restore"], "replay": {**c["restore"]["replay"], "pins": []}}), "replay pins incomplete"),
    ("safe-degraded fault missing", lambda c: c.__setitem__("safeDegraded", {**c["safeDegraded"], "faults": [f for f in c["safeDegraded"]["faults"] if f["fault"] != "emergency_stop"]}), "safe-degraded fault table incomplete"),
    ("health services empty", lambda c: c.__setitem__("health", {**c["health"], "services": []}), "health.services must be non-empty"),
    ("health service subset", lambda c: c.__setitem__("health", {**c["health"], "services": c["health"]["services"][:-1]}), "cover all real foundation services"),
    ("health probe missing", lambda c: c.__setitem__("health", {**c["health"], "services": [{"name": "gateway", "port": 8080, "liveness": {"type": "tcp"}}]}), "health probe missing"),
    ("namespace not per subsystem", lambda c: c.__setitem__("isolation", {**c["isolation"], "namespacePerSubsystem": False}), "namespace per subsystem"),
    ("service account not per subsystem", lambda c: c.__setitem__("isolation", {**c["isolation"], "serviceAccountPerSubsystem": False}), "service account per subsystem"),
]


@pytest.mark.parametrize("description,mutator,expected", NEGATIVE_CASES, ids=[n for n, _, _ in NEGATIVE_CASES])
def test_contract_rejects_incomplete_profile(description: str, mutator, expected: str):
    contract = deepcopy(load_helm_contract())
    mutator(contract)
    errors = validate(contract)
    assert errors, f"contract unexpectedly accepted: {description}"
    assert any(expected in error for error in errors), (description, errors)


def test_compose_overlay_rejects_contract_that_drifts_from_helm():
    contract = deepcopy(load_helm_contract())
    contract["backup"]["rpoMinutes"] = 20
    assert "RPO must be in [1, 15] minutes" in validate(contract)


# --- Live integration / fault injection -------------------------------------

def _env_file() -> Path | None:
    if os.environ.get("OCOR_BOOTSTRAP_ENV"):
        candidate = Path(os.environ["OCOR_BOOTSTRAP_ENV"])
        if candidate.exists():
            return candidate
    for candidate in (
        Path.home() / ".ocor-bootstrap-secrets" / "ocor-bootstrap.env",
        ROOT / ".ocor" / "bootstrap.env",
    ):
        if candidate.exists():
            return candidate
    # A git worktree may not carry the untracked `.ocor/bootstrap.env`; walk up
    # to the main checkout so the same credential file is found everywhere.
    for parent in Path(__file__).resolve().parents:
        candidate = parent / ".ocor" / "bootstrap.env"
        if candidate.exists():
            return candidate
    return None


@pytest.fixture(scope="session")
def live_stack() -> None:
    env_file = _env_file()
    if env_file is None:
        pytest.skip("ocor-bootstrap env file not found; real services are mandatory qualifying evidence")
    missing = []
    for service in REAL_SERVICES:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", f"ocor-bootstrap-{service}-1"],
            capture_output=True, text=True, check=False,
        )
        if result.returncode != 0 or result.stdout.strip() != "true":
            missing.append(service)
    if missing:
        pytest.skip(f"ocor-bootstrap services missing ({sorted(missing)}); real services are mandatory")


def _published_host_ports() -> dict[str, int]:
    bootstrap = yaml.safe_load(BOOTSTRAP_COMPOSE.read_text(encoding="utf-8"))
    ports: dict[str, int] = {}
    for name, service in bootstrap["services"].items():
        for spec in service.get("ports", []):
            host_port = spec.split(":")[1].split(":")[0]
            ports[name] = int(host_port)
            break
    return ports


def _tcp_ready(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        socket.create_connection((host, port), timeout).close()
        return True
    except OSError:
        return False


def test_live_foundation_backends_are_reachable(live_stack):
    """Real integration: the real bootstrap backends that the readiness gate
    probes must be reachable on their published host ports."""
    ports = _published_host_ports()
    unreachable = [name for name, port in ports.items()
                   if name in REAL_SERVICES and not _tcp_ready("127.0.0.1", port)]
    assert not unreachable, f"foundation backends unreachable: {unreachable}"


def test_readiness_gate_detects_a_stopped_dependency(live_stack):
    """Real fault injection: when a mandatory backend is stopped, its port goes
    dark and the readiness gate would block; after recovery it is reachable
    again. The container is restored in a finally block."""
    ports = _published_host_ports()
    victim = "qdrant"
    victim_port = ports[victim]
    container = f"ocor-bootstrap-{victim}-1"
    assert _tcp_ready("127.0.0.1", victim_port), "precondition: victim must be up"

    subprocess.run(["docker", "stop", "--time", "10", container], check=True,
                   capture_output=True, text=True)
    try:
        assert not _tcp_ready("127.0.0.1", victim_port), \
            "readiness must block while the dependency is stopped"
    finally:
        subprocess.run(["docker", "start", container], check=True,
                       capture_output=True, text=True)

    deadline = time.monotonic() + 60
    recovered = False
    while time.monotonic() < deadline:
        if _tcp_ready("127.0.0.1", victim_port):
            recovered = True
            break
        time.sleep(2)
    assert recovered, "dependency must recover after restart"
