"""Shared, dependency-free helpers for governed OCOR development bootstrap."""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
from pathlib import Path
from typing import Any


class BootstrapError(RuntimeError):
    """A bounded bootstrap operation failed."""


def root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], text=True, capture_output=True, check=False, timeout=10
    )
    if result.returncode:
        raise BootstrapError("not inside an OCOR Git worktree")
    return Path(result.stdout.strip()).resolve()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BootstrapError(f"cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise BootstrapError(f"expected object in {path}")
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], *, cwd: Path, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise BootstrapError(f"timeout after {timeout}s: {' '.join(command)}") from exc


def retry(command: list[str], *, cwd: Path, attempts: int = 3, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    last: subprocess.CompletedProcess[str] | None = None
    for attempt in range(attempts):
        last = run(command, cwd=cwd, timeout=timeout)
        if last.returncode == 0:
            return last
        if attempt + 1 < attempts:
            time.sleep(2**attempt)
    assert last is not None
    return last


def validate_locks(repository: Path) -> list[str]:
    errors: list[str] = []
    tools = load_json(repository / "infra/toolchain.lock.json")
    services = load_json(repository / "infra/services.lock.json")
    if tools.get("schema_version") != "1.0" or services.get("schema_version") != "1.0":
        errors.append("unsupported lock schema")
    for item in services.get("services", []):
        if "build" not in item and "@sha256:" not in str(item.get("image", "")):
            errors.append(f"service image is not digest-pinned: {item.get('id')}")
        build = item.get("build")
        if build and (
            "@sha256:" not in str(build.get("base_image", ""))
            or len(str(build.get("source_sha512", ""))) != 128
        ):
            errors.append(f"service build is not cryptographically pinned: {item.get('id')}")
    return errors
