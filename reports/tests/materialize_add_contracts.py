#!/usr/bin/env python3
"""Materialize the authoritative OpenAPI and Proto blocks embedded in ADD v1.2."""

from __future__ import annotations

import re
from pathlib import Path


HERE = Path(__file__).resolve()
if HERE.parents[2].name == "remediation-output":
    root = HERE.parents[3]
    out = root / "remediation-output" / "reports" / "contracts"
    sources = [root / "audit-src" / "OCOR_ADD_v1.2_APPROVED_BASELINE.md"]
else:
    root = HERE.parents[2]
    out = root / "reports" / "contracts"
    sources = [root / "ocor-runtime" / "docs" / "governance_dossier" / "OCOR_ADD_v1.2_APPROVED_BASELINE.md"]

source = next((path for path in sources if path.exists()), None)
if source is None:
    raise SystemExit("ADD v1.2 approved baseline not found")

text = source.read_text(encoding="utf-8")


def fenced_after(heading: str, language: str) -> str:
    start = text.index(heading)
    match = re.search(rf"~~~{re.escape(language)}\n(.*?)\n~~~", text[start:], re.S)
    if not match:
        raise SystemExit(f"{language} block not found after {heading}")
    return match.group(1) + "\n"


out.mkdir(parents=True, exist_ok=True)
(out / "ocor-named-query-gateway.openapi.yaml").write_text(
    fenced_after("## 3.3 Named Query Gateway", "yaml"), encoding="utf-8"
)
(out / "ocor_registry.proto").write_text(
    fenced_after("## 3.4 Function & Model Registry", "proto"), encoding="utf-8"
)
print("Materialized authoritative OpenAPI and Proto from ADD v1.2")
