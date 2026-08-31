#!/usr/bin/env python3
"""Deterministic IRB -> ADD -> LLD alignment audit for OCOR.

This checker deliberately distinguishes identifier allocation from semantic
realisation.  It uses only the Python standard library and never mutates the
reviewed baselines.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


REQ_ID = re.compile(r"(?:BR|FR|NFR)-\d{3}")


def table_rows(text: str) -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        if cells and REQ_ID.fullmatch(cells[0]):
            rows.setdefault(cells[0], cells)
    return rows


def allocation_kind(identifier: str, text: str) -> str:
    exact = rf"(?<![A-Z0-9-]){re.escape(identifier)}(?![A-Z0-9-])"
    if re.search(exact, text):
        return "DIRECT"
    prefix, number = identifier.split("-")
    value = int(number)
    range_pattern = rf"(?<![A-Z0-9-]){prefix}-(\d{{3}})\s*[–—-]\s*(?:{prefix}-)?(\d{{3}})(?![A-Z0-9-])"
    for match in re.finditer(range_pattern, text):
        if int(match.group(1)) <= value <= int(match.group(2)):
            return "RANGE"
    return "NONE"


def fenced_block(text: str, marker: str) -> str:
    start = text.index(marker)
    fence_start = text.index("```", start)
    fence_end = text.index("```", fence_start + 3)
    return text[fence_start + 3 : fence_end]


def identifiers_from_block(block: str) -> list[str]:
    result: list[str] = []
    for line in block.splitlines():
        value = line.strip()
        if not value or value.startswith(("text", "python", "@dataclass", "class ")):
            continue
        value = value.split(":", 1)[0].strip()
        value = value.rstrip("[]")
        if re.fullmatch(r"[a-z][a-z0-9_]*", value):
            result.append(value)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    root = args.root
    register_path = root / "ocor-runtime/docs/governance_dossier/registers/OCOR_Requirement_Register_v1.0_APPROVED.md"
    trace_path = root / "ocor-runtime/docs/governance_dossier/registers/OCOR_Requirement_Traceability_Index_v1.0_APPROVED.md"
    add_path = root / "ocor-runtime/docs/governance_dossier/OCOR_ADD_v1.2_APPROVED_BASELINE.md"
    lld_path = root / "docs/OCOR_LLD_v1.0.md"

    register = register_path.read_text(encoding="utf-8")
    trace = trace_path.read_text(encoding="utf-8")
    add = add_path.read_text(encoding="utf-8")
    lld = lld_path.read_text(encoding="utf-8")
    rows = table_rows(register)

    matrix = []
    for requirement_id, cells in rows.items():
        priorities = sorted(set(re.findall(r"\bP[0-2]\b", " | ".join(cells))))
        releases = sorted(set(re.findall(r"\b(?:PoC|MVP|Production|Future)\b", " | ".join(cells))))
        matrix.append(
            {
                "requirement_id": requirement_id,
                "title": cells[1] if len(cells) > 1 else "",
                "priorities": priorities,
                "releases": releases,
                "approved_trace_index": allocation_kind(requirement_id, trace),
                "add_allocation": allocation_kind(requirement_id, add),
                "lld_allocation": allocation_kind(requirement_id, lld),
            }
        )

    add_gcs = identifiers_from_block(fenced_block(add, "record canonico **`GovernedContext` v1.2**"))
    lld_gcs = identifiers_from_block(fenced_block(lld, "`GovernedContext` is immutable"))
    required_contracts = [
        "schemas/openapi/ocor-named-query-gateway.openapi.yaml",
        "schemas/proto/ocor_registry.proto",
    ]

    findings = [
        {
            "id": "IALLD-001",
            "severity": "BLOCKER",
            "check": "LLD requirement allocation",
            "passed": all(row["lld_allocation"] != "NONE" for row in matrix),
            "detail": f"{sum(row['lld_allocation'] != 'NONE' for row in matrix)}/{len(matrix)} IRB requirements are individually or range-allocated by the LLD",
        },
        {
            "id": "IALLD-002",
            "severity": "BLOCKER",
            "check": "GovernedContext exact field equality",
            "passed": add_gcs == lld_gcs,
            "detail": {"add": add_gcs, "lld": lld_gcs},
        },
        {
            "id": "IALLD-003",
            "severity": "BLOCKER",
            "check": "Referenced public contracts exist",
            "passed": all((root / path).is_file() for path in required_contracts),
            "detail": {path: (root / path).is_file() for path in required_contracts},
        },
        {
            "id": "IALLD-004",
            "severity": "MAJOR",
            "check": "FR-118/FR-119 versus ELM-084 scope",
            "passed": not (
                "| `FR-118`" in register
                and "| `FR-119`" in register
                and "`ELM-084` — Agent Memory" in add
                and "Nessuna memoria persistente generale" in add
            ),
            "detail": "FR-118 and FR-119 are Confirmed P0/PoC while ADD defers ELM-084 and specifies no persistent general memory",
        },
        {
            "id": "IALLD-005",
            "severity": "BLOCKER",
            "check": "CapabilityLease exact contract",
            "passed": "class CapabilityLease" in lld or "CapabilityLease {" in lld,
            "detail": "LLD supplies validation prose with fields not equal to the closed ADD CapabilityLease record, but no exact LLD data contract",
        },
        {
            "id": "IALLD-006",
            "severity": "MAJOR",
            "check": "C3 idempotency binding in local atomic unit",
            "passed": "idempotency binding" in lld[lld.index("### 3.2 Atomic"):lld.index("### 3.3 Marking")],
            "detail": "DEC-201 requires aggregate revision, canonical commit, idempotency binding and outbox in one local commit",
        },
        {
            "id": "IALLD-007",
            "severity": "BLOCKER",
            "check": "FSM guard and durable-effect completeness",
            "passed": "Evento/guardia" in lld and "Effetto durevole" in lld,
            "detail": "LLD preserves 44 source/destination tuples but omits the ADD transition-by-transition event/guard and durable-effect columns",
        },
        {
            "id": "IALLD-008",
            "severity": "MAJOR",
            "check": "Security and emergency-control detail",
            "passed": all(token in lld for token in ("R3_HIGH_IMPACT", "Break-glass", "Emergency Control Plane", "RESET_PENDING")),
            "detail": "LLD has no executable design for the ADD Human Gate risk classes, break-glass and emergency-stop state model",
        },
        {
            "id": "IALLD-009",
            "severity": "MAJOR",
            "check": "Operations and recovery detail",
            "passed": all(token in lld.lower() for token in ("backup authority-aware", "deterministic replay", "safe-degraded", "egress")),
            "detail": "ADD deployment, isolation, backup, restore, recovery and degraded-operation prescriptions are not decomposed in the LLD",
        },
    ]

    result = {
        "audit": "OCOR IRB -> ADD v1.2 -> LLD v1.0 exhaustive alignment",
        "requirements_total": len(matrix),
        "requirements_by_prefix": {
            prefix: sum(row["requirement_id"].startswith(prefix + "-") for row in matrix)
            for prefix in ("BR", "FR", "NFR")
        },
        "add_allocated": sum(row["add_allocation"] != "NONE" for row in matrix),
        "lld_allocated": sum(row["lld_allocation"] != "NONE" for row in matrix),
        "passed": len(matrix) == 285 and all(item["passed"] for item in findings),
        "findings": findings,
        "requirement_matrix": matrix,
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
