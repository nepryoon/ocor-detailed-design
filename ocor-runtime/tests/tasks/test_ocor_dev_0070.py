"""OCOR-DEV-0070 container-runtime availability qualification."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
VERIFY = ROOT / "scripts" / "verify_external_services.py"


def _run(*, docker_host: str | None = None) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    if docker_host is not None:
        environment["DOCKER_HOST"] = docker_host
        environment.pop("DOCKER_CONTEXT", None)
    return subprocess.run(
        [sys.executable, str(VERIFY), "--manifest-only"],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
        timeout=15,
    )


def test_manifest_check_proves_a_live_container_runtime() -> None:
    completed = _run()
    assert completed.returncode == 0, completed.stderr or completed.stdout
    result = json.loads(completed.stdout)
    assert result["status"] == "PASS"
    assert result["service_count"] >= 11
    assert result["container_runtime"]["available"] is True
    assert result["container_runtime"]["client_version"]
    assert result["container_runtime"]["server_version"]


def test_manifest_check_fails_closed_when_daemon_is_unreachable() -> None:
    completed = _run(docker_host="unix:///tmp/ocor-does-not-exist/docker.sock")
    assert completed.returncode == 2
    result = json.loads(completed.stdout)
    assert result["status"] == "ERROR"
    assert "container runtime unavailable" in result["error"]
