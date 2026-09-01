#!/usr/bin/env python3
"""Reject immutable-path changes and validate the stable OCOR task ledger."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Sequence


TASK_ID = re.compile(r"^OCOR-DEV-[0-9]{4}$")
IMMUTABLE = (
    "inputs/",
    "docs/OCOR_LLD_v1.1.md",
    "ocor-runtime/docs/governance_dossier/OCOR_ADD_v1.3_APPROVED_BASELINE.md",
)


def is_immutable(path: str) -> bool:
    normalized = path.lstrip("./")
    return any(
        normalized == protected.rstrip("/") or normalized.startswith(protected)
        for protected in IMMUTABLE
    )


def changed_paths(root: Path, base: str, head: str) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(root), "diff", "--name-only", f"{base}...{head}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "git diff failed")
    paths = [line for line in result.stdout.splitlines() if line]
    status = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=False,
    )
    if status.returncode:
        raise RuntimeError(status.stderr.strip() or "git status failed")
    for line in status.stdout.splitlines():
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path)
    return sorted(set(paths))


def validate_ledger(root: Path) -> list[str]:
    backlog = json.loads(
        (root / "docs/development_plan/OCOR_IMPLEMENTATION_BACKLOG.json").read_text(encoding="utf-8")
    )
    identifiers = [str(task.get("id", "")) for task in backlog.get("tasks", [])]
    errors: list[str] = []
    if len(identifiers) != len(set(identifiers)):
        errors.append("task ledger contains duplicate identifiers")
    if any(not TASK_ID.fullmatch(identifier) for identifier in identifiers):
        errors.append("task ledger contains an invalid identifier")
    numeric = [int(identifier.rsplit("-", 1)[1]) for identifier in identifiers if TASK_ID.fullmatch(identifier)]
    if numeric != sorted(numeric):
        errors.append("task identifiers are not stored in stable ascending order")
    dependencies = {
        dependency
        for task in backlog.get("tasks", [])
        for dependency in task.get("hard_dependencies", []) + task.get("soft_dependencies", [])
    }
    unknown = sorted(dependencies - set(identifiers))
    if unknown:
        errors.append(f"unknown task dependencies: {', '.join(unknown)}")
    return errors


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--path", action="append", default=[])
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    root = args.repo.resolve()
    try:
        paths = args.path or changed_paths(root, args.base, args.head)
        errors = validate_ledger(root)
        forbidden = sorted(path for path in paths if is_immutable(path))
        if forbidden:
            errors.append(f"immutable path changes: {', '.join(forbidden)}")
        codeowners = (root / ".github/CODEOWNERS").read_text(encoding="utf-8")
        for required in ("/inputs/", "/docs/OCOR_LLD_v1.1.md", "/.github/"):
            if required not in codeowners:
                errors.append(f"CODEOWNERS lacks {required}")
        if errors:
            for error in errors:
                print(f"FAIL: {error}")
            return 1
        print(f"PASS: {len(paths)} changed path(s); immutable surfaces untouched; task ledger stable")
        return 0
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"NOT_EXECUTED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
