#!/usr/bin/env python3
"""Test semantici e strutturali fail-closed per OCOR ADD v1.2 Candidate.

Questi test verificano regole architetturali espresse nel testo che non sono
rappresentabili integralmente in JSON Schema. Non producono evidenza E1/E2.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADD = ROOT / "reports/OCOR_Architectural_Design_Document_v1.2_Candidate.md"
RESULTS = Path(__file__).with_name("v12_semantic_results.json")
TEXT = ADD.read_text(encoding="utf-8")
records: list[dict] = []


def record(case: str, expected: str, actual: str, reason: str) -> None:
    records.append({"case": case, "expected": expected, "actual": actual,
                    "pass": expected == actual, "reason": reason})


def principal_admission(body_principal: str, transport_principal: str,
                        transport_verified: bool) -> tuple[str, str]:
    if not transport_verified:
        return "REJECT", "UNVERIFIED_TRANSPORT_BINDING"
    if body_principal != transport_principal:
        return "REJECT", "GOVERNED_CONTEXT_MISMATCH"
    return "ACCEPT", "EFFECTIVE_PRINCIPAL_FROM_VERIFIED_BINDING"


for case, body, transport, verified, expected in (
    ("Principal coerente col transport binding", "p1", "p1", True, "ACCEPT"),
    ("Principal body divergente", "p-body", "p-transport", True, "REJECT"),
    ("Principal senza binding verificato", "p1", "p1", False, "REJECT"),
):
    actual, reason = principal_admission(body, transport, verified)
    record(case, expected, actual, reason)


PIN_FIELDS = (
    "state_revision", "policy_digest", "authority_ref", "approval_digest",
    "ontology_release_digest", "watermark", "stop_epoch", "lease_id",
    "audit_append_available", "command_deadline_valid", "circuit_breaker_closed",
    "adapter_conformant", "gate_package_digest",
)


def emission_fence(gate: dict, current: dict, *, lease_valid: bool) -> tuple[str, str]:
    if not lease_valid:
        return "INVALIDATED", "CAPABILITY_LEASE_EXPIRED"
    drift = [k for k in PIN_FIELDS if gate.get(k) != current.get(k)]
    if drift:
        return "INVALIDATED", "FRESHNESS_DRIFT:" + ",".join(drift)
    if not all((current["audit_append_available"], current["command_deadline_valid"],
                current["circuit_breaker_closed"], current["adapter_conformant"])):
        return "INVALIDATED", "G_DISPATCH_FALSE"
    return "EMIT", "EMISSION_FENCE_TRUE"


base = {k: True for k in PIN_FIELDS}
base.update(state_revision=7, policy_digest="pd", authority_ref="a", approval_digest="ap",
            ontology_release_digest="od", watermark="w7", stop_epoch=3,
            lease_id="lease-1", gate_package_digest="gp")
for case, mutate, lease_valid, expected in (
    ("dispatch con snapshot immutato", {}, True, "EMIT"),
    ("dispatch con state revision drift", {"state_revision": 8}, True, "INVALIDATED"),
    ("retry con policy drift", {"policy_digest": "pd2"}, True, "INVALIDATED"),
    ("compensation con stop epoch drift", {"stop_epoch": 4}, True, "INVALIDATED"),
    ("dispatch con lease scaduta", {}, False, "INVALIDATED"),
    ("dispatch senza audit append", {"audit_append_available": False}, True, "INVALIDATED"),
):
    current = dict(base); current.update(mutate)
    actual, reason = emission_fence(base, current, lease_valid=lease_valid)
    record(case, expected, actual, reason)


def canonical_admit(instance: dict) -> tuple[str, str]:
    required = (
        "decision_ref", "authority_ref", "evidence_set_ref", "claim_source_binding_ref",
        "aggregate_type_id", "aggregate_ref", "expected_revision",
        "precondition_binding_refs", "invariant_binding_refs", "idempotency_key",
        "gate_package_digest", "governed_context_digest",
    )
    missing = [k for k in required if not instance.get(k) and instance.get(k) != 0]
    if missing:
        return "REJECT", "MISSING_CANONICAL_BINDING:" + ",".join(missing)
    if instance.get("approval_mode") not in {"HUMAN_GATE", "DUAL_CONTROL"}:
        return "REJECT", "HUMAN_GATE_REQUIRED"
    if not instance.get("approver_roles") or instance.get("quorum", 0) < 1:
        return "REJECT", "NON_EMPTY_QUORUM_AND_ROLES_REQUIRED"
    return "ACCEPT", "CANONICAL_ADMISSION_COMPLETE"


canonical = {
    "decision_ref": "d", "authority_ref": "a", "evidence_set_ref": "e",
    "claim_source_binding_ref": "c", "aggregate_type_id": "t", "aggregate_ref": "r",
    "expected_revision": 0, "precondition_binding_refs": ["p"],
    "invariant_binding_refs": ["i"], "idempotency_key": "k",
    "gate_package_digest": "g", "governed_context_digest": "ctx",
    "approval_mode": "HUMAN_GATE", "approver_roles": ["DomainApprover"], "quorum": 1,
}
record("canonical commit completo", "ACCEPT", canonical_admit(canonical)[0], canonical_admit(canonical)[1])
for field in ("decision_ref", "authority_ref", "evidence_set_ref"):
    item = dict(canonical); item.pop(field)
    actual, reason = canonical_admit(item)
    record(f"canonical commit senza {field}", "REJECT", actual, reason)
for case, changes in (
    ("canonical commit approval NONE", {"approval_mode": "NONE"}),
    ("R2_CONTROLLED con ruoli vuoti", {"approver_roles": []}),
    ("R2_CONTROLLED con quorum zero", {"quorum": 0}),
):
    item = dict(canonical); item.update(changes)
    actual, reason = canonical_admit(item)
    record(case, "REJECT", actual, reason)


def marking_join(family: str, values: list[set[str]], known: set[str]) -> tuple[str, set[str] | str]:
    if any(not v <= known for v in values):
        return "DENY", "UNKNOWN_LABEL"
    if family == "RESTRICTION":
        return "ACCEPT", set().union(*values)
    if family == "PERMISSION":
        return "ACCEPT", set.intersection(*values) if values else set()
    return "DENY", "UNSUPPORTED_FAMILY"


status, result = marking_join("RESTRICTION", [{"A"}, {"B"}], {"A", "B"})
record("restriction join monotono", "ACCEPT:{A,B}", f"{status}:{{{','.join(sorted(result))}}}", "union")
status, result = marking_join("PERMISSION", [{"P1", "P2"}, {"P2"}], {"P1", "P2"})
record("permission join per intersezione", "ACCEPT:{P2}", f"{status}:{{{','.join(sorted(result))}}}", "intersection")
status, reason = marking_join("PERMISSION_AS_RESTRICTION", [{"P1"}, {"P2"}], {"P1", "P2"})
record("PERMISSION con operatore restriction", "DENY", status, str(reason))
status, reason = marking_join("RESTRICTION", [{"UNKNOWN"}], {"A", "B"})
record("unknown marking label fail-closed", "DENY", status, str(reason))


# FSM: confronto rigoroso sulle tuple (transition_id, source, destination).
diagram_match = re.search(r"```mermaid\nstateDiagram-v2\n(.*?)\n```", TEXT, re.S)
table_match = re.search(
    r"\| Transition ID \| Source \| Evento/guardia \| Effetto durevole \| Destination \|\n"
    r"\|[-|]+\|\n(.*?)(?=\n\n)", TEXT, re.S)
diagram: set[tuple[str, str, str]] = set()
table: set[tuple[str, str, str]] = set()
if diagram_match:
    for source, destination, tid in re.findall(
            r"^\s*([A-Z_*\[\]]+)\s*-->\s*([A-Z_]+):\s*(ACT-T\d+[a-z]?)\s*$",
            diagram_match.group(1), re.M):
        diagram.add((tid, source, destination))
if table_match:
    for line in table_match.group(1).splitlines():
        cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
        if len(cells) == 5 and re.fullmatch(r"ACT-T\d+[a-z]?", cells[0]):
            table.add((cells[0], cells[1], cells[4]))
record("FSM diagramma↔tabella sulle tuple", "MATCH", "MATCH" if diagram == table and diagram else "MISMATCH",
       f"diagram={len(diagram)} table={len(table)} only_diagram={sorted(diagram-table)} only_table={sorted(table-diagram)}")
record("FSM nessuna transizione senza source/destination", "PASS",
       "PASS" if table and all(s and d for _, s, d in table) else "FAIL", f"archi={len(table)}")
ids = [tid for tid, _, _ in table]
record("FSM transition ID univoci", "PASS", "PASS" if len(ids) == len(set(ids)) else "FAIL", f"ids={len(ids)}")
numbers = {int(re.search(r"\d+", tid).group()) for tid in ids}
record("FSM famiglia ACT-T contigua 01–31", "PASS", "PASS" if numbers == set(range(1, 32)) else "FAIL", str(sorted(numbers)))
graph: dict[str, set[str]] = defaultdict(set)
for _, source, destination in table:
    graph[source].add(destination)
seen = {"[*]"}; queue = deque(["[*]"])
while queue:
    source = queue.popleft()
    for destination in graph[source]:
        if destination not in seen:
            seen.add(destination); queue.append(destination)
states = {s for _, s, _ in table} | {d for _, _, d in table}
record("FSM stati raggiungibili", "PASS", "PASS" if states <= seen else "FAIL", str(sorted(states-seen)))


def reference_admit(identifier: str, universe: set[str]) -> tuple[str, str]:
    return ("ACCEPT", "KNOWN_ID") if identifier in universe else ("REJECT", "UNKNOWN_ID")


universe = {f"FR-{i:03d}" for i in range(1, 175)}
record("range ID esistente", "ACCEPT", reference_admit("FR-174", universe)[0], "FR-001–FR-174")
record("range o ID inesistente", "REJECT", reference_admit("FR-175", universe)[0], "UNKNOWN_ID")


def evidence_claim(status: str, e1: int, e2: int) -> tuple[str, str]:
    if status == "Verified" and (e1 == 0 or e2 == 0):
        return "REJECT", "EVIDENCE_FENCE"
    return "ACCEPT", "NO_UNSUPPORTED_PROMOTION"


actual, reason = evidence_claim("Verified", 0, 0)
record("claim Verified con E1=0/E2=0", "REJECT", actual, reason)
actual, reason = evidence_claim("Confirmed", 0, 0)
record("stato Confirmed con E1=0/E2=0", "ACCEPT", actual, reason)


summary = {
    "source": str(ADD.relative_to(ROOT)),
    "total": len(records),
    "passed": sum(r["pass"] for r in records),
    "failed": sum(not r["pass"] for r in records),
    "records": records,
}
RESULTS.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
for item in records:
    print("PASS" if item["pass"] else "FAIL", "—", item["case"], f"[{item['actual']}]")
print(f"TOTAL {summary['total']} PASS {summary['passed']} FAIL {summary['failed']}")
print(f"RESULTS {RESULTS.relative_to(ROOT)}")
sys.exit(1 if summary["failed"] else 0)
