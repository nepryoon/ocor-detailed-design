#!/usr/bin/env python3
"""Execute the pinned OpenAPI validator without rewriting approved evidence."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path
from typing import Any

import yaml
from openapi_spec_validator import validate
from openapi_spec_validator.readers import read_from_filename


ROOT = Path(__file__).resolve().parents[2]
INPUT_ADD = ROOT / "inputs/normative/OCOR_Architectural_Design_Document_v1.1.md"
APPROVED_ADD = ROOT / "ocor-runtime/docs/governance_dossier/OCOR_ADD_v1.3_APPROVED_BASELINE.md"
RUNTIME_SPEC = ROOT / "ocor-runtime/schemas/ocor.openapi.yaml"
AUTHORITATIVE_SPECS = (
    ROOT / "ocor-runtime/docs/governance_dossier/contracts/ocor-named-query-gateway.openapi.yaml",
    ROOT / "ocor-runtime/docs/governance_dossier/contracts/ocor-governed-memory.openapi.yaml",
)
PROFILE = ROOT / "ocor-runtime/docs/governance_dossier/OCOR_OPENAPI_VALIDATION_PROFILE_v1.0.md"
LOCK = ROOT / "ocor-runtime/uv.lock"
OUTPUT = ROOT / "reports/tests/c5_openapi_validation_results.json"
EXPECTED_VERSION = "0.9.0"
EXPECTED_WHEEL_SHA256 = "222fecffc7714f6d0a6ad62c0e4b66cc2b7dbfafb7b93acfc6c308abbdb51af8"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def embedded_openapi(path: Path) -> tuple[str, dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    documents: list[tuple[str, dict[str, Any]]] = []
    pattern = re.compile(r"^(~~~|```)(?:yaml|yml)\s*\n(.*?)^\1\s*$", re.MULTILINE | re.DOTALL)
    for match in pattern.finditer(text):
        body = match.group(2)
        if "openapi:" not in body:
            continue
        document = yaml.safe_load(body)
        if isinstance(document, dict) and "openapi" in document:
            documents.append((body, document))
    if len(documents) != 1:
        raise ValueError(f"{path}: expected one embedded OpenAPI document, found {len(documents)}")
    return documents[0]


def validate_embedded(path: Path) -> dict[str, Any]:
    body, document = embedded_openapi(path)
    validate(document)
    return {
        "subject": str(path.relative_to(ROOT)) + "#embedded-openapi",
        "status": "PASS",
        "container_sha256": digest(path),
        "openapi_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "openapi": document["openapi"],
        "api_version": document.get("info", {}).get("version"),
        "paths": len(document.get("paths", {})),
        "component_schemas": len(document.get("components", {}).get("schemas", {})),
    }


def main() -> int:
    installed_version = version("openapi-spec-validator")
    lock_text = LOCK.read_text(encoding="utf-8")
    profile_text = PROFILE.read_text(encoding="utf-8")
    preflight = {
        "validator_version_exact": installed_version == EXPECTED_VERSION,
        "lock_version_present": f'name = "openapi-spec-validator"\nversion = "{EXPECTED_VERSION}"' in lock_text,
        "locked_wheel_sha256_present": f'hash = "sha256:{EXPECTED_WHEEL_SHA256}"' in lock_text,
        "profile_declares_validator": f"openapi-spec-validator=={EXPECTED_VERSION}" in profile_text,
    }
    records: list[dict[str, Any]] = [
        {
            "subject": "validator_profile",
            "status": "PASS" if all(preflight.values()) else "FAIL",
            "checks": preflight,
        }
    ]
    for subject in (INPUT_ADD, APPROVED_ADD):
        try:
            records.append(validate_embedded(subject))
        except Exception as exc:
            records.append(
                {
                    "subject": str(subject.relative_to(ROOT)) + "#embedded-openapi",
                    "status": "FAIL",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    for subject in AUTHORITATIVE_SPECS:
        try:
            document, base_uri = read_from_filename(str(subject))
            validate(document, base_uri=base_uri)
            records.append(
                {
                    "subject": str(subject.relative_to(ROOT)),
                    "status": "PASS",
                    "sha256": digest(subject),
                    "openapi": document["openapi"],
                    "api_version": document.get("info", {}).get("version"),
                    "paths": len(document.get("paths", {})),
                    "component_schemas": len(document.get("components", {}).get("schemas", {})),
                }
            )
        except Exception as exc:
            records.append(
                {
                    "subject": str(subject.relative_to(ROOT)),
                    "status": "FAIL",
                    "sha256": digest(subject),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    try:
        runtime_document, base_uri = read_from_filename(str(RUNTIME_SPEC))
        validate(runtime_document, base_uri=base_uri)
        records.append(
            {
                "subject": str(RUNTIME_SPEC.relative_to(ROOT)),
                "status": "PASS",
                "sha256": digest(RUNTIME_SPEC),
                "openapi": runtime_document["openapi"],
                "api_version": runtime_document.get("info", {}).get("version"),
                "paths": len(runtime_document.get("paths", {})),
                "component_schemas": len(runtime_document.get("components", {}).get("schemas", {})),
                "base_uri": "repo:///" + RUNTIME_SPEC.relative_to(ROOT).as_posix(),
            }
        )
    except Exception as exc:
        records.append(
            {
                "subject": str(RUNTIME_SPEC.relative_to(ROOT)),
                "status": "FAIL",
                "sha256": digest(RUNTIME_SPEC),
                "error": f"{type(exc).__name__}: {exc}",
            }
        )

    chain = subprocess.run(
        [sys.executable, "reports/tests/build_authoritative_chain_assurance.py", "--promotion-gate"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    records.append(
        {
            "subject": "authoritative_irb_add_lld_chain",
            "status": "PASS" if chain.returncode == 0 else "FAIL",
            "detail": chain.stdout.strip() or chain.stderr.strip(),
        }
    )

    failed = [record for record in records if record["status"] != "PASS"]
    result = {
        "artifact": "OCOR FASE C.5 OpenAPI semantic validation",
        "validator": "openapi-spec-validator",
        "validator_version": installed_version,
        "validator_locked_wheel_sha256": EXPECTED_WHEEL_SHA256,
        "lock_path": str(LOCK.relative_to(ROOT)),
        "lock_sha256": digest(LOCK),
        "profile_path": str(PROFILE.relative_to(ROOT)),
        "profile_sha256": digest(PROFILE),
        "total": len(records),
        "passed": len(records) - len(failed),
        "failed": len(failed),
        "not_executed": 0,
        "records": records,
    }
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for record in records:
        print(f"{record['status']} — {record['subject']}")
    print(f"TOTAL {result['total']} PASS {result['passed']} FAIL {result['failed']} NOT_EXECUTED 0")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
