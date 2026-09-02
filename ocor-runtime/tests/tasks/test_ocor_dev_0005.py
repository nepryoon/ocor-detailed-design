from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github/workflows/ocor-supply-chain.yml"


def workflow() -> dict:
    return yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def scanner_source() -> str:
    steps = workflow()["jobs"]["supply-chain"]["steps"]
    run = next(step["run"] for step in steps if step.get("name") == "Run pinned in-repository scanners")
    run = run.rstrip()
    prefix = "python - <<'PY'\n"
    assert run.startswith(prefix) and run.endswith("\nPY")
    return run[len(prefix) : -3]


def fixture(root: Path, *, license_name: str = "MIT", source: str = "value = 1\n") -> None:
    (root / "app.py").write_text(source, encoding="utf-8")
    (root / "ocor-runtime").mkdir()
    (root / "ocor-runtime/uv.lock").write_text(
        "\n".join(
            (
                "version = 1",
                "[[package]]",
                'name = "safe-package"',
                'version = "1.2.3"',
                f'license = "{license_name}"',
                'source = { registry = "https://pypi.org/simple" }',
                'wheels = [{ url = "https://example.invalid/safe.whl", hash = "sha256:'
                + "a" * 64
                + '" }]',
                "",
            )
        ),
        encoding="utf-8",
    )


def scan(root: Path, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", scanner_source()],
        env=os.environ
        | {
            "OCOR_SCAN_ROOT": str(root),
            "OCOR_SCAN_OUTPUT": str(output),
            "OCOR_SCANNER_VERSION": "1.0.0",
        },
        capture_output=True,
        text=True,
        check=False,
    )


def test_workflow_is_read_only_and_uploads_machine_readable_results():
    document = workflow()
    assert document["on"]["pull_request"]["branches"] == ["main"]
    assert document["permissions"] == {"contents": "read"}
    job = document["jobs"]["supply-chain"]
    assert job["continue-on-error"] == "false"
    assert int(job["timeout-minutes"]) <= 15
    upload = next(step for step in job["steps"] if step.get("name") == "Upload machine-readable findings and SBOM")
    assert upload["if"] == "${{ always() }}"
    assert upload["with"]["if-no-files-found"] == "error"


def test_clean_fixture_emits_pinned_findings_and_cyclonedx_sbom(tmp_path: Path):
    fixture(tmp_path)
    output = tmp_path / "out"
    result = scan(tmp_path, output)
    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads((output / "summary.json").read_text())
    assert summary == {
        "blocking_findings": 0,
        "result": "PASS",
        "scanner": "ocor-supply-chain",
        "scanner_version": "1.0.0",
    }
    for name in ("static", "secrets", "dependencies"):
        report = json.loads((output / f"{name}.json").read_text())
        assert report["scanner_version"] == "1.0.0"
        assert report["result"] == "PASS"
    sbom = json.loads((output / "sbom.cdx.json").read_text())
    assert sbom["bomFormat"] == "CycloneDX"
    assert sbom["specVersion"] == "1.5"
    assert sbom["components"][0]["purl"] == "pkg:pypi/safe-package@1.2.3"


def test_seeded_secret_is_a_blocking_critical_finding(tmp_path: Path):
    secret = "ghp" + "_" + "x" * 36
    fixture(tmp_path, source=f'token = "{secret}"\n')
    output = tmp_path / "out"
    assert scan(tmp_path, output).returncode != 0
    report = json.loads((output / "secrets.json").read_text())
    assert report["result"] == "FAIL"
    assert report["findings"][0]["severity"] == "CRITICAL"


def test_disallowed_license_is_a_blocking_high_finding(tmp_path: Path):
    fixture(tmp_path, license_name="GPL-3.0-only")
    output = tmp_path / "out"
    assert scan(tmp_path, output).returncode != 0
    report = json.loads((output / "dependencies.json").read_text())
    assert report["result"] == "FAIL"
    assert any(item["rule_id"] == "DISALLOWED_LICENSE" for item in report["findings"])


def test_static_syntax_failure_blocks_and_reports_path(tmp_path: Path):
    fixture(tmp_path, source="def broken(:\n")
    output = tmp_path / "out"
    assert scan(tmp_path, output).returncode != 0
    report = json.loads((output / "static.json").read_text())
    assert report["findings"][0]["rule_id"] == "PYTHON_SYNTAX_ERROR"
    assert report["findings"][0]["path"] == "app.py"


def test_sbom_is_byte_deterministic(tmp_path: Path):
    fixture(tmp_path)
    first = tmp_path / "first"
    second = tmp_path / "second"
    assert scan(tmp_path, first).returncode == 0
    assert scan(tmp_path, second).returncode == 0
    assert (first / "sbom.cdx.json").read_bytes() == (second / "sbom.cdx.json").read_bytes()
