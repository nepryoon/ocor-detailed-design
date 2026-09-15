"""OCOR-DEV-REM-0012 — RCCAD immutable-input precheck must see staged changes.

Review finding RVW-05: ``scripts/validate_rccad.py`` computed the changed-path
set from ``git diff --name-only`` (working tree vs index) and, with a base ref,
``git diff --name-only <base> HEAD``. Neither shows a change that is *staged*
but not yet committed, so a staged-only edit under ``inputs/`` could slip past
the local ``RCCAD-IMMUTABLE-INPUT`` precheck. The set must also include
``git diff --cached --name-only``.
"""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "validate_rccad.py"


def _load_module() -> object:
    spec = importlib.util.spec_from_file_location("validate_rccad_rem0012", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


def _init_repo(repo: Path) -> None:
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "rem0012@example.invalid")
    _git(repo, "config", "user.name", "REM 0012")
    (repo / "inputs").mkdir()
    (repo / "inputs" / "seed.txt").write_text("baseline\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "baseline")


def test_git_changed_detects_a_staged_only_input_change(tmp_path: pytest.TempPathFactory) -> None:
    repo = Path(str(tmp_path))
    _init_repo(repo)
    module = _load_module()

    # A staged-but-uncommitted modification under inputs/ (the exact shape the
    # RCCAD-IMMUTABLE-INPUT precheck must catch).
    (repo / "inputs" / "seed.txt").write_text("tampered\n", encoding="utf-8")
    _git(repo, "add", "inputs/seed.txt")

    changed = module.git_changed(repo, None)
    assert "inputs/seed.txt" in changed


def test_git_changed_detects_a_staged_new_file(tmp_path: pytest.TempPathFactory) -> None:
    repo = Path(str(tmp_path))
    _init_repo(repo)
    module = _load_module()

    (repo / "inputs" / "injected.txt").write_text("new\n", encoding="utf-8")
    _git(repo, "add", "inputs/injected.txt")

    changed = module.git_changed(repo, None)
    assert "inputs/injected.txt" in changed
