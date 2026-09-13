"""OCOR-DEV-0084: capture reproducible environment evidence.

Unit/negative/contract coverage for scripts/capture_environment_evidence.py's
own logic, with the typed health check faked -- no live Docker dependency
(that is exercised for real, once, in the sealed evidence at
reports/evidence/G2/OCOR-DEV-0084.json, captured against the live
11-service stack, including a real fault-injection case: capturing
evidence while a service is paused correctly reports DEGRADED, not a
silent PASS).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "scripts/capture_environment_evidence.py"
sys.path.insert(0, str(ROOT / "scripts"))

SPEC = importlib.util.spec_from_file_location("capture_environment_evidence_0084", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
capture_mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = capture_mod
SPEC.loader.exec_module(capture_mod)


class _FakeStatus:
    READY = "READY"
    DEGRADED = "DEGRADED"


class _FakeServiceHealth:
    def __init__(self, service: str, status: str):
        self.service = service
        self.status = status

    def to_json(self) -> dict[str, Any]:
        return {"service": self.service, "status": self.status}


class _FakeVerifyModule:
    def __init__(self, statuses: list[str]):
        self.ServiceStatus = _FakeStatus
        self._statuses = statuses

    def typed_health_checks(self, repository: Path, services: list[Any], *, execute: bool) -> list[_FakeServiceHealth]:
        return [_FakeServiceHealth(f"service-{i}", status) for i, status in enumerate(self._statuses)]


def test_artifact_paths_include_every_new_ws12_deliverable():
    expected = {
        "deploy/bootstrap/init/initialize_services.py",
        "deploy/bootstrap/init/opa/bootstrap.rego",
        "deploy/bootstrap/fixtures/load_fixtures.py",
        "deploy/bootstrap/fixtures/synthetic_fixtures.json",
    }
    assert expected.issubset(set(capture_mod.ARTIFACT_PATHS))


def test_capture_environment_status_reports_pass_when_all_services_ready(monkeypatch, tmp_path):
    monkeypatch.setattr(capture_mod, "_load_typed_health_checks", lambda repo: _FakeVerifyModule(["READY", "READY"]))
    monkeypatch.setattr(capture_mod, "load_json", lambda path: {"services": []})
    result = capture_mod.capture_environment_status(tmp_path)
    assert result["status"] == "PASS"
    assert len(result["services"]) == 2


def test_capture_environment_status_reports_degraded_when_any_service_is_not_ready(monkeypatch, tmp_path):
    monkeypatch.setattr(
        capture_mod, "_load_typed_health_checks", lambda repo: _FakeVerifyModule(["READY", "DEGRADED", "READY"])
    )
    monkeypatch.setattr(capture_mod, "load_json", lambda path: {"services": []})
    result = capture_mod.capture_environment_status(tmp_path)
    assert result["status"] == "DEGRADED"
    assert any(s["status"] == "DEGRADED" for s in result["services"])


def test_capture_environment_status_never_silently_reports_pass_for_a_single_fault(monkeypatch, tmp_path):
    # A single non-READY service among many must still flip the aggregate,
    # never be averaged away or ignored.
    statuses = ["READY"] * 10 + ["DEGRADED"]
    monkeypatch.setattr(capture_mod, "_load_typed_health_checks", lambda repo: _FakeVerifyModule(statuses))
    monkeypatch.setattr(capture_mod, "load_json", lambda path: {"services": []})
    result = capture_mod.capture_environment_status(tmp_path)
    assert result["status"] == "DEGRADED"
