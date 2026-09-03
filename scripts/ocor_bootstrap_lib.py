"""Shared, dependency-free helpers for governed OCOR development bootstrap."""

from __future__ import annotations

import hashlib
import json
import platform
import re
import subprocess
import time
from datetime import datetime
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
    for name, value in (("toolchain", tools), ("services", services)):
        path = repository / f"infra/{name}.lock.json"
        if path.read_text(encoding="utf-8") != canonical_json(value):
            errors.append(f"{name} lock is not canonical JSON")
    if tools.get("schema_version") != "1.0" or services.get("schema_version") != "1.0":
        errors.append("unsupported lock schema")
    if set(tools) != {"schema_version", "architecture", "acquired_at", "tools"}:
        errors.append("toolchain lock root does not match its closed schema")
    if set(services) != {"schema_version", "architecture", "acquired_at", "services"}:
        errors.append("services lock root does not match its closed schema")
    for name, value in (("toolchain", tools), ("services", services)):
        if value.get("architecture") != platform.machine():
            errors.append(f"{name} lock architecture does not match host")
        try:
            acquired = str(value["acquired_at"])
            datetime.fromisoformat(acquired.replace("Z", "+00:00"))
        except (KeyError, ValueError):
            errors.append(f"{name} lock acquisition timestamp is invalid")

    tool_items = tools.get("tools", [])
    service_items = services.get("services", [])
    if not isinstance(tool_items, list):
        errors.append("tools must be an array")
        tool_items = []
    if not isinstance(service_items, list):
        errors.append("services must be an array")
        service_items = []
    for label, items in (("tool", tool_items), ("service", service_items)):
        identifiers = [str(item.get("id")) for item in items if isinstance(item, dict)]
        if len(identifiers) != len(set(identifiers)):
            errors.append(f"duplicate {label} id")

    sha256_pattern = re.compile(r"^[0-9a-f]{64}$")
    sha512_pattern = re.compile(r"^[0-9a-f]{128}$")
    image_pattern = re.compile(r"^[^\s@]+@sha256:([0-9a-f]{64})$")
    for item in tool_items:
        if not isinstance(item, dict):
            errors.append("tool entry must be an object")
            continue
        common = {"id", "version", "source", "official_source", "license", "provider", "integrity"}
        provider = item.get("provider")
        provider_fields = (
            {"container_image", "version_env"}
            if provider == "container"
            else {"command", "version_args", "version_pattern"}
        )
        if set(item) != common | provider_fields:
            errors.append(f"tool fields do not match closed schema: {item.get('id')}")
        if not re.fullmatch(r"[a-z0-9-]+", str(item.get("id", ""))):
            errors.append(f"tool id is invalid: {item.get('id')}")
        if not all(isinstance(item.get(field), str) and item[field] for field in ("version", "license")):
            errors.append(f"tool version/license is invalid: {item.get('id')}")
        if item.get("official_source") is not True or not str(item.get("source", "")).startswith("https://"):
            errors.append(f"tool source is not marked official HTTPS: {item.get('id')}")
        if not sha256_pattern.fullmatch(str(item.get("integrity", ""))):
            errors.append(f"tool integrity is not an exact SHA-256: {item.get('id')}")
        if provider == "container":
            match = image_pattern.fullmatch(str(item.get("container_image", "")))
            if not match or match.group(1) != item.get("integrity"):
                errors.append(f"containerized tool image/integrity mismatch: {item.get('id')}")
        elif provider not in {"host", "repository"}:
            errors.append(f"unsupported tool provider: {item.get('id')}")
        elif (
            not isinstance(item.get("version_args"), list)
            or not item["version_args"]
            or not all(isinstance(argument, str) for argument in item["version_args"])
        ):
            errors.append(f"tool version arguments are invalid: {item.get('id')}")
        try:
            re.compile(str(item.get("version_pattern", "")))
        except re.error:
            errors.append(f"tool version pattern is invalid: {item.get('id')}")

    for item in service_items:
        if not isinstance(item, dict):
            errors.append("service entry must be an object")
            continue
        common = {"id", "version", "source", "official_source", "license"}
        mode = {"build"} if "build" in item else {"image"}
        if set(item) != common | mode:
            errors.append(f"service fields do not match closed schema: {item.get('id')}")
        if not re.fullmatch(r"[a-z0-9-]+", str(item.get("id", ""))):
            errors.append(f"service id is invalid: {item.get('id')}")
        if not all(isinstance(item.get(field), str) and item[field] for field in ("version", "license")):
            errors.append(f"service version/license is invalid: {item.get('id')}")
        if item.get("official_source") is not True or not str(item.get("source", "")).startswith("https://"):
            errors.append(f"service source is not marked official HTTPS: {item.get('id')}")
        has_image = "image" in item
        has_build = "build" in item
        if has_image == has_build:
            errors.append(f"service must declare exactly one of image/build: {item.get('id')}")
        if has_image and not image_pattern.fullmatch(str(item.get("image", ""))):
            errors.append(f"service image is not digest-pinned: {item.get('id')}")
        build = item.get("build")
        if build is not None and not isinstance(build, dict):
            errors.append(f"service build must be an object: {item.get('id')}")
            continue
        if build and set(build) != {
            "base_image",
            "dockerfile",
            "output_image",
            "output_sha256",
            "source_sha512",
        }:
            errors.append(f"service build fields do not match closed schema: {item.get('id')}")
        if build and (
            not image_pattern.fullmatch(str(build.get("base_image", "")))
            or not sha512_pattern.fullmatch(str(build.get("source_sha512", "")))
            or not sha256_pattern.fullmatch(str(build.get("output_sha256", "")))
            or not (repository / str(build.get("dockerfile", ""))).is_file()
        ):
            errors.append(f"service build is not cryptographically pinned: {item.get('id')}")
    return errors
