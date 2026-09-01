#!/usr/bin/env python3
"""Positive/negative conformance tests for every current JSON Schema branch.

The result is documentation/contract assurance, never E1 or E2 evidence.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "ocor-runtime/docs/governance_dossier/contracts"
OUTPUT = ROOT / "reports/tests/authoritative_contract_conformance_results.json"
SCHEMAS = [
    CONTRACTS / "governed-context.schema.json",
    CONTRACTS / "capability-lease.schema.json",
    CONTRACTS / "governed-memory-item.schema.json",
]
DIGEST = "urn:sha256:" + "a" * 64
NOW = "2026-09-01T19:00:00Z"


def resolve(schema: dict, node: dict) -> dict:
    if "$ref" not in node:
        return node
    ref = node["$ref"]
    if not ref.startswith("#/$defs/"):
        raise ValueError(f"unsupported ref {ref}")
    return schema["$defs"][ref.rsplit("/", 1)[1]]


def value_for(schema: dict, node: dict):
    node = resolve(schema, node)
    if "const" in node:
        return node["const"]
    if "enum" in node:
        return node["enum"][0]
    kind = node.get("type")
    if kind == "string":
        if node.get("format") == "date-time":
            return NOW
        if "sha256" in node.get("pattern", ""):
            return DIGEST
        return "x"
    if kind == "integer":
        return max(1, node.get("minimum", 0))
    if kind == "number":
        return node.get("minimum", 0)
    if kind == "boolean":
        return False
    if kind == "array":
        return [value_for(schema, node.get("items", {"type": "string"}))] if node.get("minItems", 0) else []
    if kind == "object":
        return fixture(schema if node is schema else node)
    raise ValueError(f"cannot synthesize value from {node}")


def fixture(schema: dict) -> dict:
    properties = schema.get("properties", {})
    return {name: value_for(schema, properties[name]) for name in schema.get("required", [])}


def errors(schema: dict, instance: dict) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [error.message for error in validator.iter_errors(instance)]


def apply_predicate(schema: dict, instance: dict, predicate: dict) -> None:
    for field, condition in predicate.get("properties", {}).items():
        condition = resolve(schema, condition)
        if "const" in condition:
            instance[field] = condition["const"]
        elif "enum" in condition:
            instance[field] = condition["enum"][0]
        elif "contains" in condition:
            instance[field] = [value_for(schema, condition["contains"])]
        else:
            raise ValueError(f"unsupported branch predicate {condition}")


def main() -> int:
    records: list[dict[str, object]] = []
    branch_count = 0
    for path in SCHEMAS:
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        base = fixture(schema)
        # DOMAIN is the only enumerated memory scope without an additional
        # conditional key, making it the neutral fixture for non-scope branches.
        if "memory_scope" in base:
            base["memory_scope"] = "DOMAIN"
        baseline_errors = errors(schema, base)
        records.append({"schema": path.name, "case": "positive baseline", "expected": "ACCEPT", "actual": "ACCEPT" if not baseline_errors else "REJECT", "errors": baseline_errors})

        for required in schema.get("required", []):
            negative = copy.deepcopy(base)
            negative.pop(required)
            actual_errors = errors(schema, negative)
            records.append({"schema": path.name, "case": f"negative required {required}", "expected": "REJECT", "actual": "REJECT" if actual_errors else "ACCEPT", "errors": actual_errors[:2]})

        unexpected = copy.deepcopy(base)
        unexpected["unexpected_property"] = True
        actual_errors = errors(schema, unexpected)
        records.append({"schema": path.name, "case": "negative closed record", "expected": "REJECT", "actual": "REJECT" if actual_errors else "ACCEPT", "errors": actual_errors[:2]})

        for index, conditional in enumerate(schema.get("allOf", []), start=1):
            if "if" not in conditional or "then" not in conditional:
                continue
            branch_count += 1
            positive = copy.deepcopy(base)
            apply_predicate(schema, positive, conditional["if"])
            for field in conditional["then"].get("required", []):
                positive[field] = value_for(schema, schema["properties"][field])
            positive_errors = errors(schema, positive)
            records.append({"schema": path.name, "branch": index, "case": "positive conditional branch", "expected": "ACCEPT", "actual": "ACCEPT" if not positive_errors else "REJECT", "errors": positive_errors[:2]})

            negative = copy.deepcopy(positive)
            omitted = conditional["then"]["required"][0]
            negative.pop(omitted)
            negative_errors = errors(schema, negative)
            records.append({"schema": path.name, "branch": index, "case": f"negative conditional branch missing {omitted}", "expected": "REJECT", "actual": "REJECT" if negative_errors else "ACCEPT", "errors": negative_errors[:2]})

    for record in records:
        record["status"] = "PASS" if record["expected"] == record["actual"] else "FAIL"
    failures = [record for record in records if record["status"] == "FAIL"]
    payload = {
        "artifact": "OCOR authoritative contract branch conformance",
        "schemas": len(SCHEMAS),
        "conditional_branches": branch_count,
        "positive_conditional_cases": branch_count,
        "negative_conditional_cases": branch_count,
        "cases": len(records),
        "passed": len(records) - len(failures),
        "failed": len(failures),
        "not_executed": 0,
        "verdict": "PASS" if not failures else "FAIL",
        "evidence_fence": "documentation/contract assurance only; E1=0; E2=0; NOT runtime evidence",
        "records": records,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("schemas", "conditional_branches", "cases", "passed", "failed", "not_executed", "verdict")}, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
