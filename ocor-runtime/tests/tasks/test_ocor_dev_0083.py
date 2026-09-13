"""OCOR-DEV-0083: bounded fault injection.

Unit/negative/contract coverage for scripts/fault_inject_test_environment.py's
--bounded cycle logic, with docker subprocess calls replaced by deterministic
fakes -- no live Docker dependency (those are exercised for real, once, in
the sealed evidence at reports/evidence/G2/OCOR-DEV-0083.json, captured
against the live 11-service stack: real bounded pause/unpause and restart
cycles, plus the disclosed, verified limitation that a bounded disconnect
cycle is not reliable via host-port reachability on this Docker Desktop
host).
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "scripts/fault_inject_test_environment.py"
sys.path.insert(0, str(ROOT / "scripts"))

SPEC = importlib.util.spec_from_file_location("fault_inject_test_environment_0083", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
fault_mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = fault_mod
SPEC.loader.exec_module(fault_mod)


def test_http_reachable_true_for_any_http_response(monkeypatch):
    def raise_http_error(*args, **kwargs):
        raise fault_mod.urllib.error.HTTPError("http://x", 404, "not found", None, None)

    monkeypatch.setattr(fault_mod.urllib.request, "urlopen", raise_http_error)
    # A real HTTP error response still means the round trip completed --
    # only a transport-level failure (OSError/URLError) means unreachable.
    assert fault_mod.http_reachable("http://127.0.0.1:1/does-not-matter") is True


def test_http_reachable_false_on_connection_failure(monkeypatch):
    def raise_os_error(*args, **kwargs):
        raise TimeoutError("timed out")

    monkeypatch.setattr(fault_mod.urllib.request, "urlopen", raise_os_error)
    assert fault_mod.http_reachable("http://127.0.0.1:1/does-not-matter") is False


def test_fault_command_maps_every_supported_fault():
    for fault in ("pause", "unpause", "restart", "disconnect", "reconnect"):
        command = fault_mod.fault_command("terminusdb", fault)
        assert "ocor-bootstrap-terminusdb-1" in command


def test_bounded_rejects_reconnect(tmp_path):
    with pytest.raises(fault_mod.BoundedFaultError, match="pause, disconnect or restart"):
        fault_mod.bounded_cycle(tmp_path, "opa", "reconnect", timeout=1.0)


def test_bounded_rejects_unpause_as_a_primary_fault(tmp_path):
    with pytest.raises(fault_mod.BoundedFaultError, match="pause, disconnect or restart"):
        fault_mod.bounded_cycle(tmp_path, "opa", "unpause", timeout=1.0)


def test_bounded_disconnect_rejected_for_a_service_with_no_published_health_endpoint(tmp_path):
    with pytest.raises(fault_mod.BoundedFaultError, match="no published health endpoint"):
        fault_mod.bounded_cycle(tmp_path, "spire-server", "disconnect", timeout=1.0)


def test_bounded_disconnect_cycle_detects_and_recovers(monkeypatch, tmp_path):
    reachable_sequence = iter([True, True, False, False, True])

    def fake_http_reachable(url: str, **kwargs: object) -> bool:
        return next(reachable_sequence)

    def fake_run(command, *, cwd, timeout):
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(fault_mod, "http_reachable", fake_http_reachable)
    monkeypatch.setattr(fault_mod, "run", fake_run)
    outcome = fault_mod.bounded_cycle(tmp_path, "opa", "disconnect", timeout=2.0)
    assert outcome["detected"] is True
    assert outcome["recovered"] is True
    assert outcome["recovery"] == "reconnect"


def test_bounded_pause_cycle_detects_and_recovers(monkeypatch, tmp_path):
    health_sequence = iter(["healthy", "healthy", "paused", "paused", "healthy"])

    def fake_container_healthy(container: str) -> bool:
        return next(health_sequence) == "healthy"

    def fake_run(command, *, cwd, timeout):
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(fault_mod, "container_healthy", fake_container_healthy)
    monkeypatch.setattr(fault_mod, "run", fake_run)
    outcome = fault_mod.bounded_cycle(tmp_path, "terminusdb", "pause", timeout=2.0)
    assert outcome["detected"] is True
    assert outcome["recovered"] is True
    assert outcome["recovery"] == "unpause"


def test_bounded_pause_cycle_fails_closed_when_never_detected(monkeypatch, tmp_path):
    def fake_container_healthy(container: str) -> bool:
        return True  # never reports unhealthy, no matter how long we poll

    def fake_run(command, *, cwd, timeout):
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    recovery_calls = []

    def fake_run_tracking(command, *, cwd, timeout):
        recovery_calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(fault_mod, "container_healthy", fake_container_healthy)
    monkeypatch.setattr(fault_mod, "run", fake_run_tracking)
    with pytest.raises(fault_mod.BoundedFaultError, match="never detected"):
        fault_mod.bounded_cycle(tmp_path, "terminusdb", "pause", timeout=0.2)
    # The fail-safe recovery command must still have been attempted even
    # though the fault was never detected as applied.
    assert any("unpause" in command for command in recovery_calls)


def test_bounded_pause_cycle_always_attempts_recovery_even_if_fault_command_fails(monkeypatch, tmp_path):
    calls = []

    def fake_run(command, *, cwd, timeout):
        calls.append(command)
        if "pause" in command and "unpause" not in command:
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="permission denied")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(fault_mod, "container_healthy", lambda container: True)
    monkeypatch.setattr(fault_mod, "run", fake_run)
    with pytest.raises(fault_mod.BoundedFaultError, match="pause command failed"):
        fault_mod.bounded_cycle(tmp_path, "terminusdb", "pause", timeout=1.0)
    assert any("unpause" in command for command in calls)


def test_bounded_restart_cycle_recovers(monkeypatch, tmp_path):
    def fake_run(command, *, cwd, timeout):
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(fault_mod, "container_healthy", lambda container: True)
    monkeypatch.setattr(fault_mod, "run", fake_run)
    outcome = fault_mod.bounded_cycle(tmp_path, "opa", "restart", timeout=1.0)
    assert outcome == {"service": "opa", "fault": "restart", "detected": True, "recovered": True}


def test_bounded_restart_fails_closed_if_command_fails(monkeypatch, tmp_path):
    def fake_run(command, *, cwd, timeout):
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="no such container")

    monkeypatch.setattr(fault_mod, "run", fake_run)
    with pytest.raises(fault_mod.BoundedFaultError, match="restart command failed"):
        fault_mod.bounded_cycle(tmp_path, "opa", "restart", timeout=1.0)
