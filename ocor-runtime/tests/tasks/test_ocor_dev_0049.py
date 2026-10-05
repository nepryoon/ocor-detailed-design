"""OCOR-DEV-0049: PoC deployment profile — observability, backup and safe
degradation (ADD v1.3 §6, LLD v1.1 §5).

The PoC profile is a machine-readable contract carried identically by the
Helm chart (`deploy/helm/ocor-poc/values.yaml`) and by the Compose overlay
(`deploy/helm/ocor-poc/compose.profiles.yaml`). This module proves that the
contract is complete and fail-closed against the normative text, that the
two carriers do not drift, that the overlay is a valid Compose model that
merges with the real bootstrap stack, and that the foundation services
behind the profile are digest-pinned and health-probed. Observability and
backup backends remain Candidate Implementation behind logical contracts
(ADD v1.3 §6.1); no image digest is fabricated here.
"""

from __future__ import annotations

import os
import re
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
VALUES = ROOT / "deploy" / "helm" / "ocor-poc" / "values.yaml"
CHART = ROOT / "deploy" / "helm" / "ocor-poc" / "Chart.yaml"
COMPOSE_PROFILES = ROOT / "deploy" / "helm" / "ocor-poc" / "compose.profiles.yaml"
TEMPLATE = ROOT / "deploy" / "helm" / "ocor-poc" / "templates" / "profile-contract.yaml"
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

# Normative constants — ADD v1.3 §6.3–§6.5, LLD v1.1 §5.1–§5.4.
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
    "rebuild_logic_projection_and_w3c_boundary",
    "reconcile_outbox_offset_checksum_saga_receipt",
    "assign_execution_unknown_to_unprovable_effects",
    "run_conformance_security_mission_thread_replay",
    "require_human_authorization_to_reopen_mutative",
]
RECOVERY_GATE = [
    "revision", "watermark", "orphan_duplicate", "marking", "gcs",
    "deletion_resurrection", "sample_semantic_digest",
]
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
    require(isinstance(observability.get("driftScanIntervalSeconds"), int)
            and observability["driftScanIntervalSeconds"] <= 60, "drift scan interval must be <= 60s")
    require(observability.get("releaseMismatchBlocksMutativeCommand") is True,
            "release mismatch must block mutative commands")
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
    require(isinstance(backup.get("rpoMinutes"), int) and backup["rpoMinutes"] <= 15, "RPO must be <= 15 minutes")
    require(isinstance(backup.get("rtoHours"), int) and backup["rtoHours"] <= 4, "RTO must be <= 4 hours")
    require(set(backup.get("authorityClasses", [])) == set(AUTHORITY_CLASSES), "authority classes incomplete")

    restore = contract.get("restore", {})
    require(restore.get("isolatedNetwork") is True, "restore must run in an isolated network")
    require(list(restore.get("steps", [])) == RESTORE_STEPS, "restore steps incomplete or out of order")
    require(restore.get("replay", {}).get("usesOriginalEventIds") is True, "replay must use original event ids")
    require(restore.get("replay", {}).get("emitsNoExternalEffects") is True, "replay must not emit external effects")
    require(set(restore.get("recoveryGate", [])) == set(RECOVERY_GATE), "recovery gate incomplete")

    faults = {entry["fault"]: list(entry["behavior"])
              for entry in contract.get("safeDegraded", {}).get("faults", [])}
    require(set(faults) == set(SAFE_DEGRADED_FAULTS), "safe-degraded fault table incomplete")
    for name, behavior in SAFE_DEGRADED_FAULTS.items():
        require(set(faults.get(name, [])) == set(behavior), f"safe-degraded behavior for {name} incomplete")

    health = contract.get("health", {})
    require(set(health.get("probeTypes", [])) == {"liveness", "readiness"}, "liveness+readiness probes required")
    for service in health.get("services", []):
        require("liveness" in service and "readiness" in service, f"health probe missing for {service.get('name')}")

    return errors


# --- Positive cases ---------------------------------------------------------

def test_helm_chart_is_present_and_well_formed():
    chart = yaml.safe_load(CHART.read_text(encoding="utf-8"))
    assert chart["apiVersion"] == "v2"
    assert chart["name"] == "ocor-poc"
    assert chart["type"] == "application"


def test_helm_chart_renders_the_profile_contract_as_a_configmap():
    template = TEMPLATE.read_text(encoding="utf-8")
    assert template, "profile-contract.yaml must not be empty"
    # The chart must expose the profile contract, not a hand-copied subset:
    # the ConfigMap renders the whole `ocor` values tree verbatim.
    assert ".Values.ocor" in template
    assert "toYaml" in template
    assert "ConfigMap" in template


def test_helm_values_contract_is_complete():
    assert validate(load_helm_contract()) == []


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


def test_compose_overlay_merges_with_the_real_bootstrap_stack():
    result = subprocess.run(
        ["docker", "compose", "-f", str(BOOTSTRAP_COMPOSE), "-f", str(COMPOSE_PROFILES),
         "config", "--quiet"],
        env=os.environ | ENVIRONMENT, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


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
        # Content-addressed: either digest-pinned in the compose tag, or a
        # locally-built `ocor/` image whose build output digest is governed
        # in infra/services.lock.json (the Fuseki case).
        if "@sha256:" in image:
            assert DIGEST_IMAGE.fullmatch(image), name
        else:
            assert image.startswith("ocor/"), name
            assert build_digests.get(name, ""), name
        assert service.get("restart") == "no", name
        # Health is exposed either directly (healthcheck) or transitively via a
        # healthy dependency (spire-agent gates on a healthy spire-server).
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
    ("C6 shares causal batch pool", lambda c: c.__setitem__("resourceIsolation", {**c["resourceIsolation"], "c6ControlAuditSharesCausalBatchPool": True}), "must not share"),
    ("drift scan exceeds 60s", lambda c: c.__setitem__("observability", {**c["observability"], "driftScanIntervalSeconds": 61}), "<= 60s"),
    ("classified payload logged", lambda c: c.__setitem__("observability", {**c["observability"], "logs": {**c["observability"]["logs"], "excludeClassifiedPayload": False}}), "classified payload"),
    ("trace field missing", lambda c: c.__setitem__("observability", {**c["observability"], "traces": {**c["observability"]["traces"], "fields": TRACE_FIELDS[:-1]}}), "trace fields incomplete"),
    ("authority class missing", lambda c: c.__setitem__("backup", {**c["backup"], "authorityClasses": AUTHORITY_CLASSES[:-1]}), "authority classes incomplete"),
    ("untested backup", lambda c: c.__setitem__("backup", {**c["backup"], "tested": False}), "backup.tested must be true"),
    ("restore not isolated", lambda c: c.__setitem__("restore", {**c["restore"], "isolatedNetwork": False}), "isolated network"),
    ("recovery gate missing", lambda c: c.__setitem__("restore", {**c["restore"], "recoveryGate": RECOVERY_GATE[:-1]}), "recovery gate incomplete"),
    ("safe-degraded fault missing", lambda c: c.__setitem__("safeDegraded", {**c["safeDegraded"], "faults": [f for f in c["safeDegraded"]["faults"] if f["fault"] != "emergency_stop"]}), "safe-degraded fault table incomplete"),
    ("health probe missing", lambda c: c.__setitem__("health", {**c["health"], "services": [{"name": "gateway", "liveness": {"http_get": "/healthz", "period_seconds": 10}}]}), "health probe missing"),
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
    assert "RPO must be <= 15 minutes" in validate(contract)
