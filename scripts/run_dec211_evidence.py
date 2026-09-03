#!/usr/bin/env python3
"""Execute and seal reproducible DEC-211 RED/GREEN/REFACTOR evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from ocor_bootstrap_lib import BootstrapError, root


BASE = "d93e8870e975b2aeec715778f3c490ece0e0216f"
RED_SHA256 = "01bd89685cc2c1af54984dc52546cbe1e30cc9879b19ce3d5604ce4be4c1a3e4"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def execute(command: list[str], repository: Path, *, env: dict[str, str] | None = None, timeout: int = 900) -> tuple[int, bytes]:
    completed = subprocess.run(
        command,
        cwd=repository,
        env=env,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    output = b"$ " + " ".join(command).encode() + b"\n" + completed.stdout + completed.stderr
    return completed.returncode, output


def load_secret_environment(repository: Path) -> dict[str, str]:
    path = repository / ".ocor" / "bootstrap.env"
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or "=" not in line:
            raise BootstrapError("invalid disposable environment file")
        key, value = line.split("=", 1)
        if not key.startswith("OCOR_") or not value:
            raise BootstrapError("invalid disposable environment entry")
        values[key] = value
    environment = os.environ.copy()
    environment.update(values)
    environment["OCOR_LIVE_POSTGRES_DSN"] = (
        f"postgresql://ocor:{values['OCOR_LOCAL_POSTGRES_PASSWORD']}@127.0.0.1:55433/ocor"
    )
    return environment


def run_group(commands: list[list[str]], repository: Path, *, env: dict[str, str] | None = None) -> tuple[int, bytes]:
    chunks: list[bytes] = []
    for command in commands:
        code, output = execute(command, repository, env=env)
        chunks.append(output)
        if code:
            return code, b"\n".join(chunks)
    return 0, b"\n".join(chunks)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="run tests and write content-addressed evidence")
    parser.add_argument("--red-log", default="/tmp/ocor-dec211-red.log")
    args = parser.parse_args()
    repository = root()
    if not args.execute:
        print(json.dumps({"status": "PASS", "mode": "DRY_RUN", "decision_id": "DEC-211"}, sort_keys=True))
        return 0

    red_source = Path(args.red_log)
    red = red_source.read_bytes()
    if digest(red) != RED_SHA256:
        raise BootstrapError("RED log digest does not match the pre-implementation capture")

    green_commands = [
        [
            "ocor-runtime/.venv/bin/python",
            "-m",
            "unittest",
            "-v",
            "reports.tests.test_autonomous_tooling_policy",
            "reports.tests.test_bootstrap_lock_validation",
            "reports.tests.test_rccad_methodology",
        ],
        ["python3", "scripts/verify_external_services.py", "--manifest-only"],
        ["python3", "scripts/bootstrap_development_environment.py", "--execute", "--skip-start", "--timeout", "300"],
        [
            "ocor-runtime/.venv/bin/python",
            "scripts/validate_ocor_development_plan.py",
            "--base-ref",
            BASE,
            "--authorized-extension",
        ],
        ["ocor-runtime/.venv/bin/python", "scripts/validate_rccad.py", "--base-ref", BASE],
        ["python3", "scripts/verify_external_services.py"],
    ]
    green_code, green = run_group(green_commands, repository)
    if green_code:
        raise BootstrapError("GREEN evidence command failed")

    environment = load_secret_environment(repository)
    refactor_commands = [
        ["uv", "run", "--project", "ocor-runtime", "--frozen", "pytest", "-q", "ocor-runtime/tests/"],
        ["python3", "scripts/reset_test_environment.py", "--execute"],
        ["python3", "scripts/bootstrap_development_environment.py", "--execute", "--timeout", "300"],
        ["python3", "scripts/fault_inject_test_environment.py", "typedb", "pause", "--execute"],
    ]
    refactor_code, refactor = run_group(refactor_commands, repository, env=environment)
    if refactor_code:
        raise BootstrapError("REFACTOR setup or regression command failed")
    try:
        failed_probe, output = execute(
            ["python3", "scripts/verify_external_services.py", "--timeout", "0.5"], repository, env=environment
        )
        refactor += b"\n" + output
        if failed_probe != 1:
            raise BootstrapError("faulted TypeDB was not detected fail-closed")
    finally:
        _, output = execute(
            ["python3", "scripts/fault_inject_test_environment.py", "typedb", "unpause", "--execute"],
            repository,
            env=environment,
        )
        refactor += b"\n" + output
    recovered = False
    for _ in range(15):
        code, output = execute(
            ["python3", "scripts/verify_external_services.py", "--timeout", "1"], repository, env=environment
        )
        refactor += b"\n" + output
        if code == 0:
            recovered = True
            break
        time.sleep(2)
    if not recovered:
        raise BootstrapError("TypeDB did not recover within the bounded retry budget")

    evidence_dir = repository / "reports" / "tests" / "evidence" / "dec211"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    logs = {"red": red, "green": green, "refactor": refactor}
    for name, content in logs.items():
        (evidence_dir / f"{name}.log").write_bytes(content)

    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repository, text=True).strip()
    phases = []
    summaries = {
        "red": "expected pre-implementation failures=3 errors=2",
        "green": "acceptance, strict locks, plan, RCCAD and real-service probes passed",
        "refactor": "full runtime, clean rebuild and bounded TypeDB fault recovery passed",
    }
    for name, code, result in (("red", 1, "EXPECTED_FAILURE"), ("green", 0, "PASS"), ("refactor", 0, "PASS")):
        summary = summaries[name]
        phases.append(
            {
                "commands": (["pre-implementation unittest capture"] if name == "red" else (green_commands if name == "green" else refactor_commands)),
                "exit_code": code,
                "fingerprint": summary,
                "fingerprint_sha256": digest(summary.encode()),
                "phase": name.upper(),
                "raw_log": f"reports/tests/evidence/dec211/{name}.log",
                "raw_log_sha256": digest(logs[name]),
                "result": result,
            }
        )
    evidence = {
        "baseline_commit": BASE,
        "change_set": "CC-AUTONOMOUS-TOOLING-INFRASTRUCTURE-BOOTSTRAP",
        "decision_id": "DEC-211",
        "evidence_fence": {"E1": 0, "E2": 0},
        "implementation_commit": head,
        "phases": phases,
        "schema_version": "1.0",
        "test_scope": "governed development tooling and disposable infrastructure bootstrap only",
    }
    evidence_path = repository / "reports" / "tests" / "autonomous_tooling_tdd_evidence.json"
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "implementation_commit": head, "evidence_sha256": digest(evidence_path.read_bytes())}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (BootstrapError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, sort_keys=True))
        sys.exit(2)
