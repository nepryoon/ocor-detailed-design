#!/usr/bin/env python3
"""Validate OCOR LLD v1.0 structural alignment with the approved ADD v1.2."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Final

COMPONENTS: Final = (
    ("C1", "Ontology Compiler & IR Pipeline", "compiler/"),
    ("C2", "Unified Semantic Gateway", "gateway/"),
    ("C3", "Canonical State Service & Outbox Worker", "state/"),
    ("C4", "Projection Adapters", "projection/"),
    ("C5", "Event Backbone", "eventing/"),
    ("C6", "Action Engine & Saga Coordinator", "actions/"),
    ("C7", "Causal Runtime & Scenario Orchestrator", "causal/"),
    ("C8", "Governed Agent Kernel", "agents/"),
)

TRANSITIONS: Final = (
    ("ACT-T01", "[*]", "PROPOSAL_RECORDED"),
    ("ACT-T02", "PROPOSAL_RECORDED", "PROPOSAL_RECORDED"),
    ("ACT-T03", "[*]", "DENIED"),
    ("ACT-T04", "PROPOSAL_RECORDED", "CONTROL_CHECK"),
    ("ACT-T05", "CONTROL_CHECK", "DENIED"),
    ("ACT-T06", "CONTROL_CHECK", "APPROVAL_PENDING"),
    ("ACT-T07", "CONTROL_CHECK", "APPROVAL_RESOLVED"),
    ("ACT-T08", "APPROVAL_PENDING", "APPROVAL_RESOLVED"),
    ("ACT-T09a", "APPROVAL_PENDING", "APPROVAL_REJECTED"),
    ("ACT-T09b", "APPROVAL_PENDING", "APPROVAL_EXPIRED"),
    ("ACT-T10a", "DECISION_PENDING", "DECISION_REJECTED"),
    ("ACT-T10b", "DECISION_PENDING", "INTENT_RECORDED"),
    ("ACT-T11", "INTENT_RECORDED", "PRE_DISPATCH_CHECK"),
    ("ACT-T12", "PRE_DISPATCH_CHECK", "COMMAND_READY"),
    ("ACT-T13", "PRE_DISPATCH_CHECK", "INVALIDATED"),
    ("ACT-T14", "COMMAND_READY", "DISPATCHED"),
    ("ACT-T15", "DISPATCHED", "ACKNOWLEDGED"),
    ("ACT-T16", "ACKNOWLEDGED", "EXECUTION_CONFIRMED"),
    ("ACT-T17a", "DISPATCHED", "EXECUTION_FAILED"),
    ("ACT-T17b", "ACKNOWLEDGED", "EXECUTION_FAILED"),
    ("ACT-T18a", "DISPATCHED", "EXECUTION_UNKNOWN"),
    ("ACT-T18b", "ACKNOWLEDGED", "EXECUTION_UNKNOWN"),
    ("ACT-T19", "COMMAND_READY", "DISPATCHED"),
    ("ACT-T20a", "EXECUTION_UNKNOWN", "EXECUTION_CONFIRMED"),
    ("ACT-T20b", "EXECUTION_UNKNOWN", "EXECUTION_FAILED"),
    ("ACT-T20c", "EXECUTION_UNKNOWN", "EXECUTION_UNKNOWN"),
    ("ACT-T21", "EXECUTION_FAILED", "COMPENSATING"),
    ("ACT-T21a", "COMPENSATING", "COMPENSATED"),
    ("ACT-T21b", "COMPENSATING", "COMPENSATION_FAILED"),
    ("ACT-T21c", "COMPENSATING", "COMPENSATION_UNKNOWN"),
    ("ACT-T21d", "COMPENSATION_UNKNOWN", "COMPENSATED"),
    ("ACT-T21e", "COMPENSATION_UNKNOWN", "COMPENSATION_FAILED"),
    ("ACT-T22", "OUTCOME_PENDING", "OUTCOME_ASSESSED"),
    ("ACT-T23a", "PRE_DISPATCH_CHECK", "CANCELLED"),
    ("ACT-T23b", "COMMAND_READY", "CANCELLED"),
    ("ACT-T24", "EXECUTION_UNKNOWN", "EXECUTION_INDETERMINATE"),
    ("ACT-T25", "COMPENSATION_UNKNOWN", "COMPENSATION_INDETERMINATE"),
    ("ACT-T26", "APPROVAL_RESOLVED", "DECISION_PENDING"),
    ("ACT-T27", "EXECUTION_CONFIRMED", "OUTCOME_PENDING"),
    ("ACT-T28", "OUTCOME_PENDING", "OUTCOME_UNOBSERVED"),
    ("ACT-T29", "COMMAND_READY", "CANONICAL_COMMIT_PENDING"),
    ("ACT-T30", "CANONICAL_COMMIT_PENDING", "EXECUTION_CONFIRMED"),
    ("ACT-T31a", "CANONICAL_COMMIT_PENDING", "EXECUTION_FAILED"),
    ("ACT-T31b", "CANONICAL_COMMIT_PENDING", "INVALIDATED"),
)

OPENAPI_PATHS: Final = (
    "/v1/queries/get-object",
    "/v1/queries/query-object-set",
    "/v1/queries/search",
    "/v1/queries/traverse",
    "/v1/queries/explain",
    "/v1/queries/get-provenance",
)

SCHEMA_IDS: Final = (
    "urn:ocor:schema:signed-canonical-ir:1.0",
    "urn:ocor:schema:canonical-ingestion-envelope:1.2",
    "urn:ocor:schema:mcp-tool-contract:1.2",
    "urn:ocor:schema:action-type-contract:1.1",
    "urn:ocor:schema:event-subscription-contract:1.1",
)


def section(text: str, start: str, end: str) -> str:
    begin = text.index(start)
    finish = text.index(end, begin)
    return text[begin:finish]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--add", type=Path, default=Path(
        "ocor-runtime/docs/governance_dossier/OCOR_ADD_v1.2_APPROVED_BASELINE.md"
    ))
    parser.add_argument("--lld", type=Path, default=Path("docs/OCOR_LLD_v1.0.md"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    add = args.add.read_text(encoding="utf-8")
    lld = args.lld.read_text(encoding="utf-8")
    checks: list[dict[str, object]] = []

    def check(name: str, condition: bool, detail: str) -> None:
        checks.append({"name": name, "passed": condition, "detail": detail})

    for code, name, package in COMPONENTS:
        check(
            f"component-{code}",
            name in add and name in lld and package in lld,
            f"{code} {name} mapped to {package}",
        )

    fsm = section(
        lld,
        "### 3.4 Approved C6 action FSM",
        "### 3.5 Guards, precedence and indeterminacy",
    )
    rows = tuple(
        (transition, source, destination)
        for transition, source, destination in re.findall(
            r"^\| (ACT-T[0-9]+[a-e]?) \| `([^`]+)` \| `([^`]+)` \|$",
            fsm,
            flags=re.MULTILINE,
        )
    )
    check("fsm-count", len(rows) == 44, f"found {len(rows)} transition rows")
    check("fsm-exact-tuples", rows == TRANSITIONS, "ordered tuple equality with ADD v1.2")
    check(
        "fsm-startup-integrity",
        "fail process startup" in fsm and "extra tuples" in fsm,
        "registry rejects missing, extra and mismatched tuples",
    )

    ba = section(lld, "### 9.2 ADD acceptance behaviours", "### 9.3 Runtime behavioural assertions")
    rba = section(lld, "### 9.3 Runtime behavioural assertions", "### 9.4 EV-001")
    for number in range(1, 9):
        check(
            f"BA-{number:02d}-reserved",
            f"BA-{number:02d}" in ba and f"RBA-{number:02d}" in rba,
            "ADD acceptance ID and compatibility RBA ID both explicit",
        )
    check(
        "ba-selected-cis",
        all(token in ba for token in (
            "TerminusDB", "TypeDB", "Jena", "Temporal/PostgreSQL",
            "S3/PostgreSQL", "Kafka/Strimzi", "OPA/Keycloak/SPIFFE/OpenBao"
        )),
        "all ADD-selected CI families present",
    )

    public_wire = section(lld, "### 8.1 Public OpenAPI", "### 8.2 Proto3")
    check(
        "openapi-exact-paths",
        all(public_wire.count(path) == 1 for path in OPENAPI_PATHS)
        and public_wire.count("POST /v1/queries/") == 6,
        "six named-query operations",
    )
    proto = section(lld, "### 8.2 Proto3", "### 8.3 Authoritative")
    check(
        "proto-registry",
        all(token in proto for token in ("ocor.registry.v1", "FunctionRegistry", "ModelRegistry")),
        "approved package and services",
    )
    check(
        "schema-identifiers",
        all(lld.count(schema_id) == 1 for schema_id in SCHEMA_IDS),
        "five canonical ADD schema IDs",
    )

    invariant_tokens = (
        "GovernedContext",
        "governed_context_digest",
        "RFC 8785",
        "EMISSION-FENCE",
        "G-FRESHNESS",
        "G-DISPATCH",
        "permitted_purposes",
        "intersection",
        "signed transition",
        "not_before <= trusted_now < expires_at",
        "VersionedAssertedState",
        "TerminusDB",
        "no distributed 2PC",
    )
    for token in invariant_tokens:
        check(f"invariant-{token}", token in lld, f"required token: {token}")

    for blocker in ("LLD-BL-004", "LLD-BL-005", "LLD-BL-006"):
        pattern = rf"\| {re.escape(blocker)} \|[^\n]+\| \*\*CLOSED_IN_LLD\*\* \|"
        check(f"closure-{blocker}", re.search(pattern, lld) is not None, "document conflict closed")
    for gap in range(1, 8):
        gap_id = f"LLD-IG-{gap:03d}"
        check(f"implementation-gap-{gap_id}", gap_id in lld, "implementation gap retained")

    passed = all(bool(item["passed"]) for item in checks)
    result = {
        "validator": "OCOR LLD/ADD alignment",
        "add": str(args.add),
        "lld": str(args.lld),
        "passed": passed,
        "checks_total": len(checks),
        "checks_passed": sum(bool(item["passed"]) for item in checks),
        "checks": checks,
    }
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
