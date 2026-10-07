#!/usr/bin/env python3
"""Run the complete runtime suite, stopping on stack failure or the 45-minute limit."""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from bootstrap_ci_environment import collect_stack_diagnostics, redact_campaign_log


class CampaignError(RuntimeError):
    """The campaign cannot supply qualifying evidence."""


def check_stack(initial: dict[str, Any], current: dict[str, Any]) -> None:
    if not initial or initial.keys() != current.keys():
        raise CampaignError("mandatory stack disappeared")
    for name, before in initial.items():
        after = current[name]
        if (after["Id"] != before["Id"] or after["RestartCount"] != before["RestartCount"]
                or after["State"].get("StartedAt") != before["State"].get("StartedAt")
                or not after["State"]["Running"] or after["State"].get("OOMKilled")):
            raise CampaignError(f"service restarted, stopped or OOM killed: {name}")


def check_junit(path: Path, *, required_modules: list[str] | None = None) -> dict[str, int]:
    try:
        tree = ET.parse(path).getroot()
        suites = [tree] if tree.tag == "testsuite" else list(tree.iter("testsuite"))
        counts = {key: sum(int(suite.get(key, "0")) for suite in suites) for key in ("tests", "failures", "errors", "skipped")}
        if not counts["tests"] or any(counts[key] for key in ("failures", "errors", "skipped")) or list(tree.iter("skipped")):
            raise CampaignError(f"nonqualifying JUnit: {counts}")
        modules = {part for case in tree.iter("testcase") for part in case.get("classname", "").split(".")}
        if missing := set(required_modules or []) - modules:
            raise CampaignError(f"required guard not executed: {sorted(missing)}")
        return counts
    except (OSError, ET.ParseError, ValueError) as exc:
        raise CampaignError("JUnit absent or invalid") from exc


def verify_revision(repository: Path, expected_head: str) -> None:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repository, capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    if head != expected_head:
        raise CampaignError(f"candidate HEAD mismatch: {head}")
    dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=repository, capture_output=True, text=True, timeout=10, check=True).stdout
    if dirty:
        raise CampaignError("candidate has tracked changes")


def inspect_stack() -> dict[str, Any]:
    ids = subprocess.run(["docker", "ps", "-aq", "--filter", "label=com.docker.compose.project=ocor-bootstrap"], capture_output=True, text=True, timeout=10, check=True).stdout.split()
    if not ids:
        return {}
    raw = subprocess.run(["docker", "inspect", *ids], capture_output=True, text=True, timeout=10, check=True).stdout
    return {entry["Name"]: entry for entry in json.loads(raw)}


def stop(process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGINT)
    try:
        process.wait(timeout=60)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=10)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repository", type=Path, help="separate, immutable candidate checkout; always runs its FULL suite")
    parser.add_argument("--expected-head", help="exact candidate commit, required with --repository")
    args = parser.parse_args()
    if bool(args.repository) != bool(args.expected_head):
        parser.error("--repository and --expected-head must be supplied together")
    repository = Path(__file__).resolve().parents[1]
    suite_repository = args.repository.resolve() if args.repository else repository
    required_modules = ["test_ocor_dev_0048", "test_ocor_dev_0049"] if args.repository else ["test_ocor_dev_0048"]
    if not args.execute:
        if args.expected_head:
            verify_revision(suite_repository, args.expected_head)
        print(json.dumps({"status": "PASS", "mode": "CHECK_ONLY", "repository": str(suite_repository), "suite": "ocor-runtime/tests/", "limit_seconds": 2700}))
        return 0
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    junit = output / "runtime_junit_post_approval.xml"
    command = [sys.executable, "-m", "pytest", "-v", "--cov=src", "--cov-report=term-missing", f"--cov-report=json:{output / 'runtime_coverage_post_approval.json'}", f"--junitxml={junit}", "tests/"]
    process: subprocess.Popen[Any] | None = None
    try:
        if args.expected_head:
            verify_revision(suite_repository, args.expected_head)
        initial = inspect_stack()
        if len(initial) != 11:
            raise CampaignError(f"expected 11 mandatory containers, found {len(initial)}")
        check_stack(initial, initial)
        start = time.monotonic()
        with (output / "post_remediation_runtime.log").open("w") as log:
            process = subprocess.Popen(command, cwd=suite_repository / "ocor-runtime", stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            while process.poll() is None:
                check_stack(initial, inspect_stack())
                if time.monotonic() - start >= 2700:
                    raise CampaignError("45-minute campaign limit reached")
                time.sleep(5)
            check_stack(initial, inspect_stack())
        if process.returncode:
            raise CampaignError(f"pytest exit code {process.returncode}")
        if args.expected_head:
            verify_revision(suite_repository, args.expected_head)
        result = {"status": "PASS", "counts": check_junit(junit, required_modules=required_modules), "duration_seconds": time.monotonic() - start, "candidate_head": args.expected_head, "required_modules": required_modules}
        (output / "campaign_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print(json.dumps(result))
        return 0
    except (CampaignError, OSError, subprocess.SubprocessError, KeyError, ValueError) as exc:
        if process is not None:
            stop(process)
        collect_stack_diagnostics(repository, output / "docker-stats.log")
        result = {"status": "FAIL", "error": str(exc)}
        (output / "campaign_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print(json.dumps(result))
        return 1
    finally:
        if process is not None:
            stop(process)
            redact_campaign_log(repository, output / "post_remediation_runtime.log")
            if junit.exists():
                redact_campaign_log(repository, junit)


if __name__ == "__main__":
    raise SystemExit(main())
