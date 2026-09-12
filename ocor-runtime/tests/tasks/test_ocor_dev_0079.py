"""OCOR-DEV-0079: typed service health checks in scripts/verify_external_services.py.

Unit/negative/contract coverage for the pure typed-status logic (no live
Docker or network dependency -- those are exercised for real, once, in the
sealed evidence at reports/evidence/G2/OCOR-DEV-0079.json, captured against
the live 11-service stack the same way OCOR-DEV-0073/0075's evidence was).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "scripts/verify_external_services.py"
sys.path.insert(0, str(ROOT / "scripts"))

SPEC = importlib.util.spec_from_file_location("verify_external_services_0079", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
verify = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = verify
SPEC.loader.exec_module(verify)


def test_service_status_is_a_closed_typed_set():
    assert {member.value for member in verify.ServiceStatus} == {
        "READY",
        "DEGRADED",
        "UNREACHABLE",
        "NOT_PROVISIONED",
    }


def test_service_health_to_json_is_stable():
    health = verify.ServiceHealth("terminusdb", verify.ServiceStatus.READY, {"ok_status": 200})
    assert health.to_json() == {"service": "terminusdb", "status": "READY", "detail": {"ok_status": 200}}


def test_lock_entry_finds_exactly_one_match():
    services = [{"id": "terminusdb", "image": "x@sha256:" + "a" * 64}]
    assert verify.lock_entry(services, "terminusdb")["id"] == "terminusdb"


@pytest.mark.parametrize(
    "services",
    [
        [],
        [{"id": "terminusdb"}, {"id": "terminusdb"}],
    ],
)
def test_lock_entry_rejects_missing_or_duplicate_ids(services):
    with pytest.raises(verify.BootstrapError, match="exactly one"):
        verify.lock_entry(services, "terminusdb")


def test_validate_running_and_pinned_accepts_a_healthy_pinned_loopback_service():
    inspection = {
        "State": {"Running": True, "Paused": False, "Health": {"Status": "healthy"}},
        "Config": {"Image": "typedb/typedb@sha256:" + "a" * 64},
        "NetworkSettings": {"Ports": {"1729/tcp": [{"HostIp": "127.0.0.1", "HostPort": "1729"}]}},
    }
    assert verify.validate_running_and_pinned(inspection, "typedb", "typedb/typedb@sha256:" + "a" * 64) == []


def test_validate_running_and_pinned_reports_missing_container_as_a_single_error():
    assert verify.validate_running_and_pinned(None, "typedb", "irrelevant") == ["container not found"]


@pytest.mark.parametrize(
    ("mutation", "expected_substring"),
    [
        ({"State": {"Running": False, "Health": {}}}, "is not running"),
        ({"State": {"Running": True, "Paused": True, "Health": {}}}, "is paused"),
        ({"State": {"Running": True, "Paused": False, "Health": {"Status": "unhealthy"}}}, "is not healthy"),
    ],
)
def test_validate_running_and_pinned_detects_each_unhealthy_condition(mutation, expected_substring):
    inspection = {
        "Config": {"Image": "typedb/typedb@sha256:" + "a" * 64},
        "NetworkSettings": {"Ports": {}},
    }
    inspection.update(mutation)
    errors = verify.validate_running_and_pinned(inspection, "typedb", "typedb/typedb@sha256:" + "a" * 64)
    assert any(expected_substring in error for error in errors)


def test_validate_running_and_pinned_rejects_mutated_image():
    inspection = {
        "State": {"Running": True, "Paused": False, "Health": {}},
        "Config": {"Image": "typedb/typedb:latest"},
        "NetworkSettings": {"Ports": {}},
    }
    errors = verify.validate_running_and_pinned(inspection, "typedb", "typedb/typedb@sha256:" + "a" * 64)
    assert any("differs from the exact services.lock.json entry" in error for error in errors)


def test_validate_running_and_pinned_rejects_non_loopback_publication():
    inspection = {
        "State": {"Running": True, "Paused": False, "Health": {}},
        "Config": {"Image": "typedb/typedb@sha256:" + "a" * 64},
        "NetworkSettings": {"Ports": {"1729/tcp": [{"HostIp": "0.0.0.0", "HostPort": "1729"}]}},
    }
    errors = verify.validate_running_and_pinned(inspection, "typedb", "typedb/typedb@sha256:" + "a" * 64)
    assert any("non-loopback" in error for error in errors)


def test_status_from_qualify_payload_maps_pass_to_ready():
    assert verify._status_from_qualify_payload({"result": "PASS"}, 0) is verify.ServiceStatus.READY
    assert verify._status_from_qualify_payload({"status": "PASS"}, 0) is verify.ServiceStatus.READY


def test_status_from_qualify_payload_maps_absent_container_to_not_provisioned():
    payload = {"result": "FAIL", "errors": ["typedb container is not found"]}
    assert verify._status_from_qualify_payload(payload, 1) is verify.ServiceStatus.NOT_PROVISIONED


def test_status_from_qualify_payload_maps_other_failure_to_degraded():
    payload = {"result": "FAIL", "errors": ["typedb image differs from lock"]}
    assert verify._status_from_qualify_payload(payload, 1) is verify.ServiceStatus.DEGRADED


def test_status_from_qualify_payload_maps_no_output_to_unreachable():
    assert verify._status_from_qualify_payload(None, 127) is verify.ServiceStatus.UNREACHABLE


def test_status_from_qualify_payload_never_reports_ready_on_nonzero_exit():
    # A qualification script that crashes after printing a stray PASS-shaped
    # partial payload must never be trusted -- the exit code is authoritative.
    assert verify._status_from_qualify_payload({"result": "PASS"}, 1) is not verify.ServiceStatus.READY
