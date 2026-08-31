#!/usr/bin/env python3
"""Regenerate the five-register candidate package in two clean local clones."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "reports/tests/full_memory_reproducibility_results.json"
GENERATOR = "reports/tests/build_full_memory_governance_candidates.py"
SOURCE_REF = "origin/main"
OUTPUTS = [
    "reports/governance_candidates/OCOR_CAP_ELM_Requirement_Crosswalk_v1.1_FULL_MEMORY_CANDIDATE.md",
    "reports/governance_candidates/OCOR_Decision_Register_v1.2_FULL_MEMORY_CANDIDATE.md",
    "reports/governance_candidates/OCOR_Decision_Traceability_Index_v1.2_FULL_MEMORY_CANDIDATE.md",
    "reports/governance_candidates/OCOR_Requirement_Register_v1.1_FULL_MEMORY_CANDIDATE.md",
    "reports/governance_candidates/OCOR_Requirement_Traceability_Index_v1.1_FULL_MEMORY_CANDIDATE.md",
    "reports/tests/full_memory_governance_candidate_results.json",
    "reports/OCOR_FULL_MEMORY_GOVERNANCE_CANDIDATE_SHA256SUMS",
]


def run(command: list[str], cwd: Path | None = None) -> bytes:
    completed = subprocess.run(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"command failed ({' '.join(command)}): {detail}")
    return completed.stdout


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def regenerate(
    clone: Path,
    commit: str,
    expected_source_commit: str,
    origin_url: str,
) -> dict[str, bytes]:
    run(["git", "clone", "--quiet", "--no-checkout", origin_url, str(clone)])
    run(["git", "fetch", "--quiet", str(ROOT), commit], cwd=clone)
    run(["git", "checkout", "--quiet", "--detach", "FETCH_HEAD"], cwd=clone)
    source_commit = run(["git", "rev-parse", SOURCE_REF], cwd=clone).decode("ascii").strip()
    if source_commit != expected_source_commit:
        raise RuntimeError(
            f"clean clone source mismatch: {SOURCE_REF}={source_commit}, expected={expected_source_commit}"
        )
    if run(["git", "status", "--porcelain"], cwd=clone):
        raise RuntimeError("clean clone is dirty before generation")
    run([sys.executable, GENERATOR], cwd=clone)
    payload: dict[str, bytes] = {}
    for relative_name in OUTPUTS:
        path = clone / relative_name
        if not path.is_file():
            raise FileNotFoundError(f"generator output missing: {path}")
        payload[relative_name] = path.read_bytes()
    return payload


def main() -> int:
    commit = run(["git", "rev-parse", "HEAD"], cwd=ROOT).decode("ascii").strip()
    source_commit = run(["git", "rev-parse", SOURCE_REF], cwd=ROOT).decode("ascii").strip()
    origin_url = run(["git", "remote", "get-url", "origin"], cwd=ROOT).decode("utf-8").strip()
    with tempfile.TemporaryDirectory(prefix="ocor-repro-") as temporary:
        base = Path(temporary)
        first = regenerate(base / "clone-1", commit, source_commit, origin_url)
        second = regenerate(base / "clone-2", commit, source_commit, origin_url)

    entries: dict[str, dict[str, object]] = {}
    for relative_name in OUTPUTS:
        first_bytes = first[relative_name]
        second_bytes = second[relative_name]
        workspace_path = ROOT / relative_name
        if not workspace_path.is_file():
            raise FileNotFoundError(f"workspace comparison target missing: {workspace_path}")
        workspace_bytes = workspace_path.read_bytes()
        entries[relative_name] = {
            "clone_1_sha256": digest(first_bytes),
            "clone_2_sha256": digest(second_bytes),
            "workspace_sha256": digest(workspace_bytes),
            "byte_identical_between_clones": first_bytes == second_bytes,
            "matches_workspace": first_bytes == workspace_bytes,
        }

    passed = all(
        entry["byte_identical_between_clones"] and entry["matches_workspace"]
        for entry in entries.values()
    )
    payload = {
        "artifact": "OCOR full-memory candidate clean-clone reproducibility",
        "status": "PASS" if passed else "FAIL",
        "generator_commit": commit,
        "source_ref": SOURCE_REF,
        "source_commit": source_commit,
        "clean_clones": 2,
        "outputs_compared": len(OUTPUTS),
        "entries": entries,
    }
    RESULT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "outputs": len(OUTPUTS)}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
