"""OCOR-DEV-0002 deterministic toolchain contract tests."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
DEVCONTAINER = ROOT / "ocor-runtime/devcontainer.json"
LOCK = ROOT / "ocor-runtime/uv.lock"
PROJECT = ROOT / "ocor-runtime/pyproject.toml"
DIGEST_PIN = re.compile(r"^[a-z0-9./_-]+:[A-Za-z0-9._-]+@sha256:[0-9a-f]{64}$")


def load_contract(path: Path = DEVCONTAINER) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def fingerprint(root: Path) -> tuple[str, str, str]:
    contract = json.loads((root / "devcontainer.json").read_text(encoding="utf-8"))
    lock_digest = hashlib.sha256((root / "uv.lock").read_bytes()).hexdigest()
    project_digest = hashlib.sha256((root / "pyproject.toml").read_bytes()).hexdigest()
    return lock_digest, project_digest, str(contract["image"])


def materialize_clean_environment(target: Path) -> Path:
    target.mkdir()
    for source in (DEVCONTAINER, LOCK, PROJECT):
        shutil.copyfile(source, target / source.name)
    return target


def test_two_clean_environments_resolve_identical_lock_and_image_digests(tmp_path):
    first = materialize_clean_environment(tmp_path / "first")
    second = materialize_clean_environment(tmp_path / "second")
    assert fingerprint(first) == fingerprint(second)
    for environment in (first, second):
        result = subprocess.run(
            ["uv", "lock", "--project", str(environment), "--check"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr


def test_python_and_service_images_are_immutable_and_locally_resolvable():
    contract = load_contract()
    image = str(contract["image"])
    environment = contract["containerEnv"]
    assert isinstance(environment, dict)
    postgres = str(environment["OCOR_POSTGRES_IMAGE"])
    assert DIGEST_PIN.fullmatch(image)
    assert DIGEST_PIN.fullmatch(postgres)
    for reference in (image, postgres):
        inspected = subprocess.run(
            ["docker", "image", "inspect", reference, "--format", "{{json .RepoDigests}}"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert inspected.returncode == 0, inspected.stderr
        assert reference.split("@", 1)[1] in inspected.stdout


def test_runtime_versions_and_frozen_sync_are_fail_closed():
    contract = load_contract()
    environment = contract["containerEnv"]
    assert isinstance(environment, dict)
    assert environment == {
        "OCOR_POSTGRES_IMAGE": "postgres:16@sha256:33f923b05f64ca54ac4401c01126a6b92afe839a0aa0a52bc5aeb5cc958e5f20",
        "OCOR_PYTHON_VERSION": "3.11.15",
        "OCOR_UV_VERSION": "0.12.5",
        "PYTHONHASHSEED": "0",
        "TZ": "UTC",
    }
    command = str(contract["postCreateCommand"])
    assert "uv --version" in command
    assert "uv 0.12.5" in command
    assert "Python 3.11.15" in command
    assert "uv sync --project ocor-runtime --frozen --extra test" in command


@pytest.mark.parametrize(
    "bad_image",
    [
        "python:3.11",
        "python:latest",
        "python@sha256:not-a-digest",
    ],
)
def test_mutable_or_malformed_image_references_are_rejected(bad_image):
    assert DIGEST_PIN.fullmatch(bad_image) is None


def test_fault_injected_lock_drift_changes_clean_environment_fingerprint(tmp_path):
    first = materialize_clean_environment(tmp_path / "first")
    second = materialize_clean_environment(tmp_path / "second")
    with (second / "uv.lock").open("a", encoding="utf-8") as stream:
        stream.write("# injected drift\n")
    assert fingerprint(first) != fingerprint(second)
