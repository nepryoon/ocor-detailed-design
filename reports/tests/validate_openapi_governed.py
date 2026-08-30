#!/usr/bin/env python3
"""Governed OpenAPI 3.1 validation for approved and runtime contracts."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from typing import Any

import yaml
from openapi_spec_validator import validate
from openapi_spec_validator.readers import read_from_filename

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "ocor-runtime/docs/governance_dossier/OCOR_ADD_v1.2_APPROVED_BASELINE.md"
RUNTIME_SPEC = ROOT / "ocor-runtime/schemas/ocor.openapi.yaml"
PROFILE = ROOT / "ocor-runtime/docs/governance_dossier/OCOR_OPENAPI_VALIDATION_PROFILE_v1.0.md"
LOCK = ROOT / "ocor-runtime/uv.lock"
OUTPUT = ROOT / "reports/tests/openapi_31_validation_results.json"
EXPECTED_VERSION = "0.9.0"
EXPECTED_WHEEL_SHA256 = "222fecffc7714f6d0a6ad62c0e4b66cc2b7dbfafb7b93acfc6c308abbdb51af8"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fenced_blocks(text: str):
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        match = re.match(r"^(~~~|```)(\w*)\s*$", lines[index])
        if not match:
            index += 1
            continue
        fence, language = match.groups()
        end = index + 1
        while end < len(lines) and not re.match("^" + re.escape(fence) + r"\s*$", lines[end]):
            end += 1
        yield language, "\n".join(lines[index + 1:end])
        index = end + 1


records: list[dict[str, Any]] = []
validator_version = version("openapi-spec-validator")
lock_text = LOCK.read_text(encoding="utf-8")
profile_text = PROFILE.read_text(encoding="utf-8")
preflight = {
    "validator_version_exact": validator_version == EXPECTED_VERSION,
    "lock_version_present": f'name = "openapi-spec-validator"\nversion = "{EXPECTED_VERSION}"' in lock_text,
    "locked_wheel_sha256_present": f'hash = "sha256:{EXPECTED_WHEEL_SHA256}"' in lock_text,
    "profile_declares_validator": f"openapi-spec-validator=={EXPECTED_VERSION}" in profile_text,
}
records.append({"subject": "validator_profile", "status": "PASS" if all(preflight.values()) else "FAIL", "checks": preflight})

embedded = []
for language, body in fenced_blocks(BASELINE.read_text(encoding="utf-8")):
    if language in {"yaml", "yml"} and "openapi:" in body:
        document = yaml.safe_load(body)
        if isinstance(document, dict) and "openapi" in document:
            embedded.append((body, document))

if len(embedded) != 1:
    records.append({"subject": str(BASELINE.relative_to(ROOT)), "status": "FAIL", "error": f"expected one embedded OpenAPI document, found {len(embedded)}"})
else:
    body, document = embedded[0]
    try:
        if not re.fullmatch(r"3\.1\.\d+", str(document.get("openapi", ""))):
            raise ValueError(f"not OpenAPI 3.1.x: {document.get('openapi')}")
        validate(document)
        records.append({
            "subject": str(BASELINE.relative_to(ROOT)) + "#embedded-openapi",
            "status": "PASS",
            "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            "openapi": document["openapi"],
            "api_version": document.get("info", {}).get("version"),
            "paths": len(document.get("paths", {})),
            "component_schemas": len(document.get("components", {}).get("schemas", {})),
        })
    except Exception as exc:
        records.append({"subject": str(BASELINE.relative_to(ROOT)) + "#embedded-openapi", "status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})

try:
    runtime_document, base_uri = read_from_filename(str(RUNTIME_SPEC))
    if not re.fullmatch(r"3\.1\.\d+", str(runtime_document.get("openapi", ""))):
        raise ValueError(f"not OpenAPI 3.1.x: {runtime_document.get('openapi')}")
    validate(runtime_document, base_uri=base_uri)
    records.append({
        "subject": str(RUNTIME_SPEC.relative_to(ROOT)),
        "status": "PASS",
        "sha256": digest(RUNTIME_SPEC),
        "openapi": runtime_document["openapi"],
        "api_version": runtime_document.get("info", {}).get("version"),
        "paths": len(runtime_document.get("paths", {})),
        "component_schemas": len(runtime_document.get("components", {}).get("schemas", {})),
        "base_uri": base_uri,
    })
except Exception as exc:
    records.append({"subject": str(RUNTIME_SPEC.relative_to(ROOT)), "status": "FAIL", "sha256": digest(RUNTIME_SPEC), "error": f"{type(exc).__name__}: {exc}"})

failed = [record for record in records if record["status"] != "PASS"]
result = {
    "profile": str(PROFILE.relative_to(ROOT)),
    "profile_sha256": digest(PROFILE),
    "validator": "openapi-spec-validator",
    "validator_version": validator_version,
    "validator_locked_wheel_sha256": EXPECTED_WHEEL_SHA256,
    "executed_at_utc": datetime.now(timezone.utc).isoformat(),
    "total": len(records),
    "passed": len(records) - len(failed),
    "failed": len(failed),
    "waiver_required": bool(failed),
    "records": records,
}
OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
for record in records:
    print(f"{record['status']} — {record['subject']}")
print(f"TOTAL {result['total']} PASS {result['passed']} FAIL {result['failed']}")
print(f"RESULTS {OUTPUT.relative_to(ROOT)}")
sys.exit(1 if failed else 0)
