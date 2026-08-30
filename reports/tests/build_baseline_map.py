#!/usr/bin/env python3
"""Costruisce una mappa machine-readable della baseline OCOR senza modificarla."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
NORMATIVE = ROOT / "inputs" / "normative"
ADD = NORMATIVE / "OCOR_Architectural_Design_Document_v1.1.md"
OUTPUT = ROOT / "reports" / "remediation" / "checkpoints" / "baseline_map.json"

FAMILIES = (
    "DEC", "BR", "FR", "NFR", "ARC", "CAP", "ELM", "RSK", "EV", "OI",
    "ASM", "DEP", "BA", "AM", "DRAFT",
)
TOKEN_RE = re.compile(
    r"(?<![A-Z0-9-])(?:DEC|BR|FR|NFR|ARC|CAP|ELM|RSK|EV|OI|ASM|DEP)-\d{2,3}"
    r"|(?<![A-Z0-9-])(?:BA|AM)-\d{2}"
    r"|(?<![A-Z0-9-])DRAFT-[A-I](?![A-Z0-9-])"
)
RANGE_RE = re.compile(
    r"\b(DEC|BR|FR|NFR|ARC|CAP|ELM|RSK|EV|OI|ASM|DEP)-(\d{2,3})"
    r"\s*[–—-]\s*(?:(?:\1)-)?(\d{2,3})\b"
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def family(token: str) -> str:
    return "DRAFT" if token.startswith("DRAFT-") else token.split("-", 1)[0]


def expand_tokens(text: str) -> set[str]:
    result = set(TOKEN_RE.findall(text))
    for match in RANGE_RE.finditer(text):
        prefix, start_s, end_s = match.groups()
        start, end = int(start_s), int(end_s)
        width = max(len(start_s), len(end_s), 3)
        if start <= end and end - start <= 1000:
            result.update(f"{prefix}-{number:0{width}d}" for number in range(start, end + 1))
    return result


def markdown_rows(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and not all(re.fullmatch(r":?-{3,}:?", cell or "") for cell in cells):
            rows.append(cells)
    return rows


def canonical_id(cell: str) -> str | None:
    match = TOKEN_RE.search(cell.replace("`", ""))
    if not match:
        return None
    token = match.group(0)
    return token if cell.replace("`", "").strip().startswith(token) else None


def collect_best_rows(files: list[Path]) -> dict[str, dict[str, object]]:
    best: dict[str, dict[str, object]] = {}
    for path in files:
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.startswith("|"):
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if not cells:
                continue
            ident = canonical_id(cells[0])
            if not ident:
                continue
            record = {
                "id": ident,
                "source": str(path.relative_to(ROOT)),
                "line": line_no,
                "cells": cells,
                "references": sorted(expand_tokens(" ".join(cells)) - {ident}),
            }
            if ident not in best or len(cells) > len(best[ident]["cells"]):
                best[ident] = record
    return best


def main() -> None:
    normative_files = sorted(NORMATIVE.glob("*.md"))
    texts = {str(path.relative_to(ROOT)): path.read_text(encoding="utf-8") for path in normative_files}
    add_text = texts[str(ADD.relative_to(ROOT))]

    sections = []
    for line_no, line in enumerate(add_text.splitlines(), 1):
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if match:
            sections.append({"level": len(match.group(1)), "title": match.group(2), "line": line_no})

    mentioned_universe: dict[str, set[str]] = {name: set() for name in FAMILIES}
    occurrences: dict[str, list[dict[str, object]]] = {}
    for path_s, text in texts.items():
        for line_no, line in enumerate(text.splitlines(), 1):
            for token in expand_tokens(line):
                mentioned_universe.setdefault(family(token), set()).add(token)
                occurrences.setdefault(token, []).append({"source": path_s, "line": line_no})

    rows = collect_best_rows(normative_files)
    authoritative_universe: dict[str, set[str]] = {name: set() for name in FAMILIES}
    row_references: dict[str, set[str]] = {}
    for path in normative_files:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.startswith("|"):
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            ident = canonical_id(cells[0]) if cells else None
            if not ident:
                continue
            authoritative_universe.setdefault(family(ident), set()).add(ident)
            row_references.setdefault(ident, set()).update(expand_tokens(" ".join(cells)) - {ident})
    requirement_rows = collect_best_rows([NORMATIVE / "OCOR_Requirement_Register_v0.9.md"])
    requirements = {}
    for ident, row in requirement_rows.items():
        if family(ident) not in {"BR", "FR", "NFR"}:
            continue
        cells = row["cells"]
        priority = next(
            (cell for cell in cells[2:] if re.fullmatch(r"P[0-2](?:[^|]*)?", cell.strip())),
            None,
        )
        status_index = next(
            (index for index, cell in enumerate(cells) if cell.strip() in {"Confermato", "Differito"}),
            None,
        )
        status = cells[status_index] if status_index is not None else None
        release = cells[status_index + 1] if status_index is not None and status_index + 1 < len(cells) else None
        requirements[ident] = {
            **row,
            "title": cells[1] if len(cells) > 1 else None,
            "priority": priority,
            "status": status,
            "release": release,
            "mapping": {
                target: sorted(ref for ref in row_references.get(ident, set()) if family(ref) == target)
                for target in ("DEC", "ELM", "CAP", "RSK", "EV", "ARC", "DEP", "ASM", "OI")
            },
        }

    transitions = []
    for line_no, line in enumerate(add_text.splitlines(), 1):
        if not line.startswith("|") or "ACT-T" not in line:
            continue
        cells = [cell.strip().replace("`", "") for cell in line.strip().strip("|").split("|")]
        transition_ids = sorted(set(re.findall(r"ACT-T\d{2}[a-c]?", cells[0] if cells else "")))
        if transition_ids:
            transitions.append({"ids": transition_ids, "line": line_no, "cells": cells})

    contracts = []
    contract_patterns = {
        "signed-canonical-ir": r"urn:ocor:schema:signed-canonical-ir:([0-9.]+)",
        "canonical-ingestion-envelope": r"urn:ocor:schema:canonical-ingestion-envelope:([0-9.]+)",
        "mcp-tool-contract": r"urn:ocor:schema:mcp-tool-contract:([0-9.]+)",
        "action-type-contract": r"urn:ocor:schema:action-type-contract:([0-9.]+)",
        "event-subscription-contract": r"urn:ocor:schema:event-subscription-contract:([0-9.]+)",
        "openapi": r"version:\s*[\"']?([0-9]+\.[0-9]+\.[0-9]+)",
        "protobuf": r"package\s+([A-Za-z0-9_.]+);",
    }
    for name, pattern in contract_patterns.items():
        matches = sorted(set(re.findall(pattern, add_text)))
        contracts.append({"name": name, "versions_or_packages": matches})

    section_refs = []
    for line_no, line in enumerate(add_text.splitlines(), 1):
        for ref in re.findall(r"§\s*([0-9]+(?:\.[0-9]+)*)", line):
            section_refs.append({"reference": ref, "line": line_no})

    hard_invariant_lines = [
        {"line": line_no, "text": line.strip()}
        for line_no, line in enumerate(add_text.splitlines(), 1)
        if re.search(r"\b(?:invariante|invariant|fail[- ]closed|single.writer|E1=0|E2=0)\b", line, re.I)
    ]

    output = {
        "metadata": {
            "baseline": str(ADD.relative_to(ROOT)),
            "baseline_sha256": digest(ADD),
            "generated_by": str(Path(__file__).resolve().relative_to(ROOT)),
            "evidence_fence": {"E1": 0, "E2": 0, "verified_requirements": 0},
        },
        "source_digests": {path_s: digest(ROOT / path_s) for path_s in texts},
        "sections": sections,
        "universe": {
            name: {"count": len(values), "ids": sorted(values)}
            for name, values in authoritative_universe.items()
        },
        "mentioned_ids": {
            name: {"count": len(values), "ids": sorted(values)}
            for name, values in mentioned_universe.items()
        },
        "requirements": requirements,
        "records": rows,
        "occurrences": occurrences,
        "contracts": contracts,
        "fsm_transitions": transitions,
        "section_references": section_refs,
        "hard_invariant_lines": hard_invariant_lines,
        "scope_fence_mentions": [
            {"line": line_no, "text": line.strip()}
            for line_no, line in enumerate(add_text.splitlines(), 1)
            if re.search(r"\b(?:scope|perimetro|differit|deferred|future)\b", line, re.I)
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(OUTPUT.relative_to(ROOT)),
        "sections": len(sections),
        "requirements": len(requirements),
        "universe_counts": {name: len(values) for name, values in authoritative_universe.items()},
        "fsm_rows": len(transitions),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
