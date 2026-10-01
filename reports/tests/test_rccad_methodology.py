#!/usr/bin/env python3
"""Acceptance tests for the governed RCCAD methodology adoption."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REQUIRED = (
    "docs/development_methodology/README.md",
    "docs/development_methodology/OCOR_RCCAD_v1.0.md",
    "docs/development_methodology/OCOR_TEST_STRATEGY.md",
    "docs/development_methodology/OCOR_ARCHITECTURE_FITNESS_FUNCTIONS.md",
    "docs/development_methodology/OCOR_DEFINITION_OF_DONE.md",
    "docs/development_methodology/OCOR_MODEL_OPERATING_PROFILE.md",
    "docs/development_methodology/methodology.json",
    "docs/development_methodology/methodology.schema.json",
    "PLANS.md",
    "reports/development/EXECUTION_STATE.json",
    "reports/development/ITERATION_LOG.md",
    "reports/development/MODEL_HANDOFF.json",
    "reports/development/METHOD_COMPLIANCE.json",
    "reports/tests/rccad_tdd_evidence.json",
    "ocor-runtime/docs/governance_dossier/registers/OCOR_Decision_Register_v1.4_APPROVED.md",
    "ocor-runtime/docs/governance_dossier/registers/OCOR_Decision_Traceability_Index_v1.4_APPROVED.md",
    "scripts/validate_rccad.py",
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _init_repo(repo: Path) -> None:
    """Minimal git repo carrying only the files the validator needs to reach the
    immutable-input precheck: the three fail-closed component modules are read
    unconditionally, so they must exist or the validator fails closed with
    RCCAD-VALIDATOR-ERROR before emitting RCCAD-IMMUTABLE-INPUT."""
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t.t")
    _git(repo, "config", "user.name", "t")
    for rel, token in (
        ("ocor-runtime/src/ocor_runtime/c6_capabilities.py", "AuthorizationError"),
        ("ocor-runtime/src/ocor_runtime/c7_emission.py", "EmissionBlocked"),
        ("ocor-runtime/src/ocor_runtime/c8_agent.py", "SandboxViolation"),
    ):
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{token} = object()\n", encoding="utf-8")
    (repo / "README.md").write_text("baseline\n", encoding="utf-8")


def _commit_baseline(repo: Path) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "baseline")


def _run_validator(repo: Path, base_ref: str | None = None) -> "subprocess.CompletedProcess[str]":
    cmd = [sys.executable, str(ROOT / "scripts/validate_rccad.py"), "--root", str(repo)]
    if base_ref is not None:
        cmd += ["--base-ref", base_ref]
    return subprocess.run(cmd, cwd=repo, text=True, capture_output=True, check=False)


def _immutable_paths(payload: dict) -> set[str]:
    return {item["path"] for item in payload["findings"] if item["rule_id"] == "RCCAD-IMMUTABLE-INPUT"}


class RccadAdoptionTests(unittest.TestCase):
    def test_required_artifacts_exist(self) -> None:
        missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
        self.assertEqual([], missing)

    def test_manifest_is_valid_and_canonical(self) -> None:
        manifest_path = ROOT / "docs/development_methodology/methodology.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        rendered = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
        self.assertEqual(rendered, manifest_path.read_text(encoding="utf-8"))
        self.assertEqual("OCOR-RCCAD", manifest["methodology_id"])
        self.assertEqual("1.0", manifest["version"])
        self.assertEqual(["G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7"], manifest["lifecycle"])
        self.assertEqual({"E1": 0, "E2": 0}, manifest["evidence_fence"])

    def test_validator_accepts_repository_state(self) -> None:
        result = subprocess.run(
            ["python3", "scripts/validate_rccad.py", "--root", str(ROOT)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PASS_LOCAL_PRECHECK", payload["status"])
        self.assertEqual("CI_REQUIRED", payload["dynamic_assurance"])
        self.assertEqual({f"AFF-{number:03d}": "PASS_STATIC_PRECHECK" for number in range(1, 11)}, payload["fitness_results"])

    def test_validator_fails_closed_on_missing_required_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as _:
            result = subprocess.run(
                [
                    "python3",
                    "scripts/validate_rccad.py",
                    "--root",
                    str(ROOT),
                    "--simulate-missing",
                    "PLANS.md",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertNotEqual(0, result.returncode)
        payload = json.loads(result.stdout)
        self.assertEqual("FAIL", payload["status"])
        self.assertIn("RCCAD-ARTIFACT-MISSING", {item["rule_id"] for item in payload["findings"]})

    def test_validator_rejects_input_changes(self) -> None:
        result = subprocess.run(
            [
                "python3",
                "scripts/validate_rccad.py",
                "--root",
                str(ROOT),
                "--simulate-changed-path",
                "inputs/normative/forbidden.txt",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(0, result.returncode)
        payload = json.loads(result.stdout)
        self.assertIn("RCCAD-IMMUTABLE-INPUT", {item["rule_id"] for item in payload["findings"]})

    def test_git_changed_returns_unquoted_paths_for_special_filenames(self) -> None:
        """VF-002 / OCOR-DEV-REM-0015 regression.

        ``git diff --name-only`` (without ``-z``) quotes paths containing non-ASCII,
        tab or newline characters (e.g. ``"inputs/\\303\\251-vil.txt"``), so the
        ``relative.startswith("inputs/")`` predicate in ``validate_rccad.py`` misses
        them and ``RCCAD-IMMUTABLE-INPUT`` is never raised. ``git_changed`` must
        return the raw, unquoted paths for staged add/modify/delete/rename.
        """
        sys.path.insert(0, str(ROOT / "scripts"))
        import validate_rccad  # noqa: E402,F401  (stdlib, imported after sys.path)

        added = "inputs/add-\u00e9.txt"              # non-ASCII add
        modified = "inputs/mod-tab\tname.txt"        # tab modify
        deleted = "inputs/del-line\nname.txt"        # newline delete
        renamed_old = "inputs/ren-old.txt"
        renamed_new = "inputs/ren-\u00e9.txt"        # non-ASCII rename target
        expected = {added, modified, deleted, renamed_old, renamed_new}

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)

            def git(*args: str) -> None:
                subprocess.run(["git", *args], cwd=repo, check=True)

            git("init", "-q")
            git("config", "user.email", "t@t.t")
            git("config", "user.name", "t")

            # Baseline: tracked files that will later be modified / deleted / renamed.
            for rel in (modified, deleted, renamed_old):
                path = repo / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("baseline\n", encoding="utf-8")
            git("add", "-A")
            git("commit", "-q", "-m", "baseline")

            # Staged add / modify / delete / rename.
            add_path = repo / added
            add_path.parent.mkdir(parents=True, exist_ok=True)
            add_path.write_text("added\n", encoding="utf-8")
            (repo / modified).write_text("modified\n", encoding="utf-8")
            (repo / deleted).unlink()
            git("mv", renamed_old, renamed_new)
            git("add", "-A")

            changed = validate_rccad.git_changed(repo, None)

        self.assertEqual(expected, set(changed))
        for rel in changed:
            self.assertTrue(rel.startswith("inputs/"), rel)

    def test_validator_detects_unstaged_special_path_change(self) -> None:
        """Working-tree surface: an unstaged modification to a tracked inputs/
        file whose name carries Unicode must still raise RCCAD-IMMUTABLE-INPUT
        through the full validator (not just the git_changed() unit)."""
        modified = "inputs/mod-\u00e9.txt"
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _init_repo(repo)
            path = repo / modified
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("baseline\n", encoding="utf-8")
            _commit_baseline(repo)
            path.write_text("changed\n", encoding="utf-8")  # unstaged modify
            result = _run_validator(repo)
        self.assertNotEqual(0, result.returncode)
        payload = json.loads(result.stdout)
        self.assertEqual("FAIL", payload["status"])
        self.assertIn(modified, _immutable_paths(payload))

    def test_validator_detects_staged_special_path_changes(self) -> None:
        """Index surface: staged add/modify/delete/rename with Unicode, tab and
        newline names must each raise RCCAD-IMMUTABLE-INPUT through the full
        validator with the exact raw path."""
        added = "inputs/add-\u00e9.txt"          # non-ASCII add
        modified = "inputs/mod-tab\tname.txt"    # tab in modify
        deleted = "inputs/del-line\nname.txt"    # newline in delete
        renamed_old = "inputs/ren-old.txt"
        renamed_new = "inputs/ren-\u00e9.txt"    # non-ASCII rename target
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _init_repo(repo)
            for rel in (modified, deleted, renamed_old):
                path = repo / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("baseline\n", encoding="utf-8")
            _commit_baseline(repo)
            add_path = repo / added
            add_path.parent.mkdir(parents=True, exist_ok=True)
            add_path.write_text("added\n", encoding="utf-8")
            (repo / modified).write_text("modified\n", encoding="utf-8")
            (repo / deleted).unlink()
            (repo / renamed_old).rename(repo / renamed_new)
            _git(repo, "add", "-A")
            result = _run_validator(repo)
        self.assertNotEqual(0, result.returncode)
        payload = json.loads(result.stdout)
        self.assertEqual("FAIL", payload["status"])
        paths = _immutable_paths(payload)
        for rel in (added, modified, deleted, renamed_old, renamed_new):
            self.assertIn(rel, paths)

    def test_validator_detects_committed_special_path_change(self) -> None:
        """base..HEAD surface: a committed inputs/ change with a Unicode name
        must raise RCCAD-IMMUTABLE-INPUT via --base-ref."""
        changed = "inputs/committed-\u00e9.txt"
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _init_repo(repo)
            _commit_baseline(repo)
            path = repo / changed
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("added\n", encoding="utf-8")
            _git(repo, "add", "-A")
            _git(repo, "commit", "-q", "-m", "change inputs")
            result = _run_validator(repo, base_ref="HEAD~1")
        self.assertNotEqual(0, result.returncode)
        payload = json.loads(result.stdout)
        self.assertEqual("FAIL", payload["status"])
        self.assertIn(changed, _immutable_paths(payload))

    def test_validator_detects_rename_across_inputs_boundary(self) -> None:
        """Both sides of a rename across the inputs/ boundary: the inputs/ path
        that is renamed away must be caught, and the inputs/ path that is
        renamed into must be caught."""
        out_old = "inputs/leave-\u00e9.txt"       # rename out of inputs -> old side
        out_new = "docs/leave-\u00e9.txt"
        in_old = "docs/enter-\u00e9.txt"
        in_new = "inputs/enter-\u00e9.txt"        # rename into inputs -> new side
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _init_repo(repo)
            for rel in (out_old, in_old):
                path = repo / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("baseline\n", encoding="utf-8")
            _commit_baseline(repo)
            (repo / out_old).rename(repo / out_new)
            (repo / in_old).rename(repo / in_new)
            _git(repo, "add", "-A")
            result = _run_validator(repo)
        self.assertNotEqual(0, result.returncode)
        payload = json.loads(result.stdout)
        self.assertEqual("FAIL", payload["status"])
        paths = _immutable_paths(payload)
        self.assertIn(out_old, paths)   # the input side renamed away
        self.assertIn(in_new, paths)    # the input side renamed into

    def test_validator_allows_changes_outside_inputs(self) -> None:
        """Positive control: a staged change outside inputs/ must not raise
        RCCAD-IMMUTABLE-INPUT."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _init_repo(repo)
            _commit_baseline(repo)
            (repo / "docs").mkdir(exist_ok=True)
            (repo / "docs" / "x.txt").write_text("changed\n", encoding="utf-8")
            _git(repo, "add", "-A")
            result = _run_validator(repo)
        payload = json.loads(result.stdout)
        self.assertEqual(set(), _immutable_paths(payload))

    def test_validator_unchanged_state_has_no_input_findings(self) -> None:
        """Positive control: a clean repository produces no RCCAD-IMMUTABLE-INPUT."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _init_repo(repo)
            _commit_baseline(repo)
            result = _run_validator(repo)
        payload = json.loads(result.stdout)
        self.assertEqual(set(), _immutable_paths(payload))


if __name__ == "__main__":
    unittest.main()
