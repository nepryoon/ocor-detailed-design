#!/usr/bin/env python3
"""Conformance suite indipendente per i contratti formali dell'ADD v1.2 Candidate.

Legge l'ADD come dato, estrae i blocchi JSON/OpenAPI e valida casi positivi e
negativi. Non modifica le sorgenti normative e non produce evidenza E1/E2.
"""
from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
ADD = ROOT / "reports/OCOR_Architectural_Design_Document_v1.2_Candidate.md"
RESULTS = Path(__file__).with_name("v12_conformance_results.json")

DIGEST = "sha256:" + "a" * 64
CONTENT_REF = "urn:sha256:" + "b" * 64
UUID1 = "11111111-1111-4111-8111-111111111111"
UUID2 = "22222222-2222-4222-8222-222222222222"
NOW = "2026-08-30T10:00:00Z"


def blocks(text: str):
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = re.match(r"^(~~~|```)(\w*)\s*$", lines[i])
        if not m:
            i += 1
            continue
        fence, lang = m.groups()
        j = i + 1
        while j < len(lines) and not re.match(r"^" + re.escape(fence) + r"\s*$", lines[j]):
            j += 1
        yield lang or "text", i + 2, "\n".join(lines[i + 1:j])
        i = j + 1


text = ADD.read_text(encoding="utf-8")
schemas: dict[str, dict] = {}
openapi = None
for lang, line, body in blocks(text):
    if lang == "json":
        doc = json.loads(body)
        if "$schema" in doc:
            schemas[doc["$id"]] = doc
    elif lang == "yaml" and body.startswith("openapi:"):
        openapi = yaml.safe_load(body)

if len(schemas) != 5 or openapi is None:
    raise RuntimeError(f"estrazione inattesa: {len(schemas)} JSON Schema, OpenAPI={openapi is not None}")

records: list[dict] = []


def errors_for(schema: dict, instance) -> list[str]:
    v = Draft202012Validator(schema, format_checker=FormatChecker())
    return [f"{'.'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}" for e in v.iter_errors(instance)]


def check(schema_name: str, case: str, instance, expected: str, schema: dict | None = None):
    target = schema if schema is not None else schemas[schema_name]
    errs = errors_for(target, instance)
    actual = "ACCEPT" if not errs else "REJECT"
    records.append({
        "schema": schema_name,
        "case": case,
        "expected": expected,
        "actual": actual,
        "pass": actual == expected,
        "errors": errs[:4],
    })


def urn(name="x"):
    return f"urn:ocor:test:{name}"


def pin(name="schema"):
    return {"schema_id": urn(name), "version": "1.0.0", "digest": DIGEST}


def marking():
    return {
        "scheme_id": urn("scheme"), "labels": ["SYNTHETIC"],
        "mandatory_markings": ["SYNTHETIC"], "caveats": [],
        "dissemination_controls": ["INTERNAL"], "permitted_purposes": ["test"],
        "handling_instructions": ["NO_EXPORT"], "marking_digest": DIGEST,
    }


def ingestion(mode="BATCH", semantic="OBSERVATION"):
    transports = {
        "BATCH": {"mode": "BATCH", "batch_id": UUID2, "record_index": 0},
        "STREAM": {"mode": "STREAM", "stream_id": urn("stream"), "partition": 0, "offset": "opaque"},
        "CDC": {"mode": "CDC", "operation": "UPDATE", "source_transaction_id": "tx-1", "source_position": "pos-1"},
    }
    return {
        "envelope_version": "1.2", "event_id": UUID1,
        "tenant_id": urn("tenant"), "organization_id": urn("org"), "domain_id": urn("domain"),
        "compartments": [urn("compartment")], "world_ref": urn("world"),
        "ingest_mode": mode, "semantic_class": semantic, "event_type_id": urn("event-type"),
        "event_time": NOW, "ingest_time": NOW, "ordering_key": "aggregate-1",
        "idempotency_key": "1234567890abcdef", "purpose": "test",
        "source": {"source_id": urn("source"), "source_record_id": "r1", "adapter_id": urn("adapter"), "adapter_version": "1.0.0"},
        "aggregate": {"aggregate_type_id": urn("aggregate-type"), "aggregate_id": "a1", "expected_revision": 0},
        "payload_schema": {"schema_id": urn("payload"), "schema_version": "1.0.0", "schema_digest": DIGEST},
        "payload": {}, "classification_marking": marking(), "provenance_ref": CONTENT_REF,
        "integrity": {"payload_digest": DIGEST, "source_producer_principal_ref": urn("principal")},
        "effective_principal_id": urn("principal"), "actor_chain": [urn("principal")],
        "governed_context_digest": DIGEST, "ontology_release_digest": DIGEST,
        "policy_bundle_digest": DIGEST, "correlation_id": UUID2, "transport": transports[mode],
    }


def approval(mode="NONE", count=None, roles=None):
    x = {"mode": mode, "self_approval_allowed": False, "timeout_action": "DENY"}
    if count is not None:
        x["independent_approver_count"] = count
    if roles is not None:
        x["required_approver_roles"] = roles
    return x


def mcp(effect="READ_ONLY"):
    return {
        "contract_id": urn("mcp"), "version": "1.2.0", "contract_digest": DIGEST,
        "governed_context_ref": CONTENT_REF,
        "capability_id": urn("capability"), "input_schema": pin("input"), "output_schema": pin("output"),
        "effect_class": effect, "risk_class": "LOW", "allowed_autonomy_tiers": ["OBSERVE"],
        "preconditions": [], "policy_refs": [urn("policy")], "approval": approval(),
        "idempotency": {"scope": "REQUEST", "key_required": True, "duplicate_semantics": "REPLAY_RECEIPT"},
        "timeout_ms": 1000, "retry": {"retry_safe": True, "max_attempts": 1, "backoff": ["PT1S"]},
        "compensation": {"mode": "NOT_APPLICABLE", "irreversibility_class": "REVERSIBLE"},
        "provenance_requirements": {"record_input_digest": True, "record_output_digest": True, "record_policy_decision": True, "record_actor_chain": True, "record_tool_binding": True},
        "evidence_requirements": {"input_evidence": "OPTIONAL", "output_evidence": "OPTIONAL", "minimum_count": 0},
        "error_codes": ["POLICY_DENIED"],
    }


def timeouts():
    return {k: "PT1S" for k in (
        "proposal_ttl", "approval_ttl", "decision_dispatch_ttl", "predispatch_fence_ttl",
        "ack_timeout", "execution_confirmation_timeout", "reconciliation_deadline", "outcome_assessment_window")}


def action(target="EXTERNAL_ADAPTER"):
    x = {
        "action_type_id": urn("action"), "version": "1.1.0", "contract_digest": DIGEST,
        "governed_context_requirements": {
            "all_canonical_fields": True, "principal_from_verified_transport": True,
            "actor_chain_from_verified_delegation": True, "mismatch_fail_closed": True,
        },
        "target": target, "effect_class": "EXTERNAL_NOTIFICATION", "risk_class": "R1_ANALYZE",
        "parameters_schema": pin("parameters"), "expected_effect_schema": pin("effect"), "timeouts": timeouts(),
        "retry": {"retry_safe": True, "max_attempts": 1, "backoff": ["PT1S"]},
        "idempotency": {"key_required": True, "scope": "REQUEST", "duplicate_semantics": "REPLAY_RECEIPT"},
        "compensation": {"mode": "NOT_APPLICABLE", "irreversibility_class": "REVERSIBLE"},
        "approval": approval(), "policy_refs": [urn("policy")], "preconditions": [],
        "provenance_requirements": {"record_proposal_digest": True, "record_policy_decision": True, "record_actor_chain": True, "record_approval_set": True, "record_delivery_attempts": True},
        "evidence_requirements": {"proposal_evidence": "OPTIONAL", "confirmation_evidence": "REQUIRED", "minimum_count": 0},
        "error_codes": ["POLICY_DENIED"],
    }
    if target == "CANONICAL_COMMIT":
        x["effect_class"] = "CANONICAL_COMMIT"
        x["risk_class"] = "R2_CONTROLLED"
        x["approval"] = approval("HUMAN_GATE", 1, [urn("canonical-approver")])
        x["evidence_requirements"]["proposal_evidence"] = "REQUIRED"
        x["evidence_requirements"]["minimum_count"] = 1
        x["canonical_commit_binding"] = {
            "ownership_boundary": urn("boundary"), "aggregate_type_id": urn("aggregate-type"),
            "produced_assertion_class": "CanonicalAssertion",
            "requires_accepted_from_claim": True, "requires_evidence_set": True,
            "claim_source_binding_path": "/claim_source_binding_ref",
            "decision_ref_path": "/decision_ref", "authority_ref_path": "/authority_ref",
            "evidence_set_path": "/evidence_set_ref",
            "aggregate_ref_path": "/aggregate_ref", "expected_revision_path": "/expected_revision",
            "precondition_binding_refs": [urn("precondition")],
            "invariant_binding_refs": [urn("invariant")],
            "gate_package_digest_path": "/gate_package_digest",
            "idempotency_key_path": "/idempotency_key",
        }
    return x


def event_contract():
    return {
        "subscription_contract_id": urn("subscription"), "version": "1.1.0", "contract_digest": DIGEST,
        "governed_context_ref": CONTENT_REF,
        "event_type_refs": [urn("event-type")],
        "delivery": {"semantics": "AT_LEAST_ONCE", "consumer_must_deduplicate": True, "dedup_key": "event_id"},
        "ordering": {"guarantee": "PER_ORDERING_KEY", "ordering_key_field": "ordering_key"},
        "filter": {"filter_contract_id": urn("filter"), "arbitrary_predicates_allowed": False},
        "payload_schema": pin("event-payload"),
        "marking_policy": {"propagate_marking": True, "redact_unauthorized": True, "declare_redactions": True},
        "replay": {"replay_allowed": True, "cursor_opaque": True, "authorization_required": True, "max_replay_window": "P7D"},
        "error_codes": ["POLICY_DENIED"],
    }


# signed-canonical-ir: smoke positivo/negativo (nessun if/then).
signed = {
    "payloadType": "application/vnd.ocor.canonical-ir.v1+json", "payload": "e30=",
    "canonicalization": "RFC8785", "digest": DIGEST,
    "signingProfile": "urn:ocor:crypto-profile:test:1",
    "signatures": [{"keyid": "k1", "sig": "AA==", "certificateChainRef": CONTENT_REF, "signedAt": NOW}],
}
check("urn:ocor:schema:signed-canonical-ir:1.0", "baseline positivo", signed, "ACCEPT")
bad = copy.deepcopy(signed); bad["digest"] = "sha256:xyz"
check("urn:ocor:schema:signed-canonical-ir:1.0", "digest malformato", bad, "REJECT")

# Ingestion: tutti i 4 if/then e le alternative oneOf.
for mode, semantic in (("BATCH", "OBSERVATION"), ("STREAM", "OBSERVED_EVENT"), ("CDC", "CDC_CHANGE")):
    check("urn:ocor:schema:canonical-ingestion-envelope:1.2", f"positivo ingest_mode={mode}", ingestion(mode, semantic), "ACCEPT")
bad = ingestion("BATCH"); bad["transport"] = ingestion("STREAM", "OBSERVED_EVENT")["transport"]
check("urn:ocor:schema:canonical-ingestion-envelope:1.2", "negativo ramo BATCH: transport STREAM", bad, "REJECT")
bad = ingestion("STREAM", "OBSERVED_EVENT"); bad["transport"] = ingestion("BATCH")["transport"]
check("urn:ocor:schema:canonical-ingestion-envelope:1.2", "negativo ramo STREAM: transport BATCH", bad, "REJECT")
bad = ingestion("CDC", "OBSERVATION")
check("urn:ocor:schema:canonical-ingestion-envelope:1.2", "negativo ramo ingest CDC: semantic_class non CDC_CHANGE", bad, "REJECT")
bad = ingestion("CDC", "CDC_CHANGE"); bad["transport"] = ingestion("BATCH")["transport"]
check("urn:ocor:schema:canonical-ingestion-envelope:1.2", "negativo ramo ingest CDC: transport non CDC", bad, "REJECT")
bad = ingestion("STREAM", "CDC_CHANGE")
check("urn:ocor:schema:canonical-ingestion-envelope:1.2", "negativo ramo semantic CDC_CHANGE: ingest non CDC", bad, "REJECT")
for value in (NOW, None):
    x = ingestion(); x["effective_time"] = {"from": NOW, "to": value}
    check("urn:ocor:schema:canonical-ingestion-envelope:1.2", f"positivo oneOf effective_time.to={value!r}", x, "ACCEPT")
bad = ingestion(); bad["effective_time"] = {"from": NOW, "to": 7}
check("urn:ocor:schema:canonical-ingestion-envelope:1.2", "negativo oneOf effective_time.to", bad, "REJECT")
for value in (UUID1, None):
    x = ingestion(); x["causation_id"] = value
    check("urn:ocor:schema:canonical-ingestion-envelope:1.2", f"positivo oneOf causation_id={value!r}", x, "ACCEPT")
bad = ingestion(); bad["causation_id"] = 7
check("urn:ocor:schema:canonical-ingestion-envelope:1.2", "negativo oneOf causation_id", bad, "REJECT")
for field in ("before_digest", "after_digest"):
    for value in (DIGEST, None):
        x = ingestion("CDC", "CDC_CHANGE"); x["transport"][field] = value
        check("urn:ocor:schema:canonical-ingestion-envelope:1.2", f"positivo oneOf {field}={value!r}", x, "ACCEPT")
    bad = ingestion("CDC", "CDC_CHANGE"); bad["transport"][field] = 7
    check("urn:ocor:schema:canonical-ingestion-envelope:1.2", f"negativo oneOf {field}", bad, "REJECT")

# MCP: gli 11 rami if/then (incluso retry annidato).
x = mcp(); x["retry"] = {"retry_safe": False, "max_attempts": 1}
check("urn:ocor:schema:mcp-tool-contract:1.2", "positivo ramo retry_safe=false", x, "ACCEPT")
bad = copy.deepcopy(x); bad["retry"]["max_attempts"] = 2
check("urn:ocor:schema:mcp-tool-contract:1.2", "negativo ramo retry_safe=false", bad, "REJECT")
x = mcp(); x["risk_class"] = "HIGH"; x["approval"] = approval("DUAL_CONTROL", 2, [urn("r1"), urn("r2")])
check("urn:ocor:schema:mcp-tool-contract:1.2", "positivo ramo HIGH/CRITICAL", x, "ACCEPT")
bad = copy.deepcopy(x); bad["approval"]["independent_approver_count"] = 1
check("urn:ocor:schema:mcp-tool-contract:1.2", "negativo ramo HIGH/CRITICAL quorum", bad, "REJECT")
x = mcp("EXECUTE_APPROVED_ACTION"); x["allowed_autonomy_tiers"] = ["EXECUTE_APPROVED"]; x["approval"] = approval("HUMAN_GATE", 1, [urn("approver")]); x["error_codes"].append("EXECUTION_UNKNOWN"); x["evidence_requirements"].update(input_evidence="REQUIRED", minimum_count=1)
check("urn:ocor:schema:mcp-tool-contract:1.2", "positivo ramo EXECUTE_APPROVED_ACTION (vincoli 1)", x, "ACCEPT")
check("urn:ocor:schema:mcp-tool-contract:1.2", "positivo ramo EXECUTE_APPROVED_ACTION (vincoli 2)", x, "ACCEPT")
for label, mutate in (
    ("tier mancante", lambda y: y.update(allowed_autonomy_tiers=["OBSERVE"])),
    ("approval NONE", lambda y: y.update(approval=approval())),
    ("key_required false", lambda y: y["idempotency"].update(key_required=False)),
    ("EXECUTION_UNKNOWN mancante", lambda y: y.update(error_codes=["POLICY_DENIED"])),
):
    bad = copy.deepcopy(x); mutate(bad)
    check("urn:ocor:schema:mcp-tool-contract:1.2", f"negativo EXECUTE: {label}", bad, "REJECT")
x = mcp(); x["approval"] = approval("DUAL_CONTROL", 2, [urn("r1"), urn("r2")])
check("urn:ocor:schema:mcp-tool-contract:1.2", "positivo ramo DUAL_CONTROL", x, "ACCEPT")
bad = copy.deepcopy(x); bad["approval"]["independent_approver_count"] = 1
check("urn:ocor:schema:mcp-tool-contract:1.2", "negativo ramo DUAL_CONTROL", bad, "REJECT")
x = mcp(); x["compensation"] = {"mode": "HUMAN_AUTHORIZED", "irreversibility_class": "COMPENSATABLE", "compensation_contract_id": urn("comp")}
check("urn:ocor:schema:mcp-tool-contract:1.2", "positivo ramo compensation HUMAN_AUTHORIZED", x, "ACCEPT")
bad = copy.deepcopy(x); del bad["compensation"]["compensation_contract_id"]
check("urn:ocor:schema:mcp-tool-contract:1.2", "negativo ramo compensation HUMAN_AUTHORIZED", bad, "REJECT")
x = mcp(); x["approval"] = approval("HUMAN_GATE", 1, [urn("approver")])
check("urn:ocor:schema:mcp-tool-contract:1.2", "positivo ramo HUMAN_GATE", x, "ACCEPT")
bad = copy.deepcopy(x); del bad["approval"]["required_approver_roles"]
check("urn:ocor:schema:mcp-tool-contract:1.2", "negativo ramo HUMAN_GATE", bad, "REJECT")
for effect, tier in (("PROPOSE_ACTION", "PROPOSE"), ("SIMULATE", "SIMULATE"), ("ANALYZE", "ANALYZE")):
    x = mcp(effect); x["allowed_autonomy_tiers"] = [tier]
    check("urn:ocor:schema:mcp-tool-contract:1.2", f"positivo ramo {effect}", x, "ACCEPT")
    bad = copy.deepcopy(x); bad["allowed_autonomy_tiers"] = ["OBSERVE"]
    check("urn:ocor:schema:mcp-tool-contract:1.2", f"negativo ramo {effect}", bad, "REJECT")
check("urn:ocor:schema:mcp-tool-contract:1.2", "positivo ramo READ_ONLY", mcp(), "ACCEPT")
bad = mcp(); bad["allowed_autonomy_tiers"].append("EXECUTE_APPROVED")
check("urn:ocor:schema:mcp-tool-contract:1.2", "negativo ramo READ_ONLY con execute", bad, "REJECT")

# Action Type: gli 11 rami if/then (inclusi due annidati).
x = action("CANONICAL_COMMIT")
check("urn:ocor:schema:action-type-contract:1.1", "positivo ramo target CANONICAL_COMMIT", x, "ACCEPT")
check("urn:ocor:schema:action-type-contract:1.1", "positivo ramo produced CanonicalAssertion", x, "ACCEPT")
for label, mutate in (
    ("binding assente", lambda y: y.pop("canonical_commit_binding")),
    ("effect errato", lambda y: y.update(effect_class="INTERNAL_STATE_MUTATION")),
    ("accepted_from_claim false", lambda y: y["canonical_commit_binding"].update(requires_accepted_from_claim=False)),
):
    bad = copy.deepcopy(x); mutate(bad)
    check("urn:ocor:schema:action-type-contract:1.1", f"negativo canonical: {label}", bad, "REJECT")
bad = action("CANONICAL_COMMIT")
bad["risk_class"] = "R1_ANALYZE"
bad["approval"] = approval()
check(
    "urn:ocor:schema:action-type-contract:1.1",
    "negativo: CANONICAL_COMMIT R1 senza Human Gate",
    bad,
    "REJECT",
)
x = action()
check("urn:ocor:schema:action-type-contract:1.1", "positivo ramo target EXTERNAL_ADAPTER", x, "ACCEPT")
bad = copy.deepcopy(x); bad["canonical_commit_binding"] = action("CANONICAL_COMMIT")["canonical_commit_binding"]
check("urn:ocor:schema:action-type-contract:1.1", "negativo external con canonical binding", bad, "REJECT")
x = action(); x["risk_class"] = "R3_HIGH_IMPACT"; x["approval"] = approval("DUAL_CONTROL", 2, [urn("r1"), urn("r2")])
check("urn:ocor:schema:action-type-contract:1.1", "positivo ramo R3_HIGH_IMPACT", x, "ACCEPT")
bad = copy.deepcopy(x); bad["approval"] = approval("HUMAN_GATE", 1, [urn("r1")])
check("urn:ocor:schema:action-type-contract:1.1", "negativo ramo R3_HIGH_IMPACT", bad, "REJECT")
x = action(); x["risk_class"] = "R2_CONTROLLED"; x["approval"] = approval("HUMAN_GATE", 1, [urn("r1")])
check("urn:ocor:schema:action-type-contract:1.1", "positivo ramo R2_CONTROLLED", x, "ACCEPT")
bad = copy.deepcopy(x); bad["approval"] = approval()
check("urn:ocor:schema:action-type-contract:1.1", "negativo ramo R2_CONTROLLED", bad, "REJECT")
x = action(); x["compensation"] = {"mode": "HUMAN_AUTHORIZED", "irreversibility_class": "COMPENSATABLE", "compensation_action_type_id": urn("comp")}
check("urn:ocor:schema:action-type-contract:1.1", "positivo ramo compensation HUMAN_AUTHORIZED", x, "ACCEPT")
bad = copy.deepcopy(x); del bad["compensation"]["compensation_action_type_id"]
check("urn:ocor:schema:action-type-contract:1.1", "negativo ramo compensation HUMAN_AUTHORIZED", bad, "REJECT")
x = action(); x["risk_class"] = "R3_HIGH_IMPACT"; x["approval"] = approval("DUAL_CONTROL", 2, [urn("r1"), urn("r2")]); x["compensation"] = {"mode": "NOT_APPLICABLE", "irreversibility_class": "IRREVERSIBLE"}
check("urn:ocor:schema:action-type-contract:1.1", "positivo ramo IRREVERSIBLE", x, "ACCEPT")
bad = copy.deepcopy(x); bad["risk_class"] = "R2_CONTROLLED"; bad["approval"] = approval("HUMAN_GATE", 1, [urn("r1")])
check("urn:ocor:schema:action-type-contract:1.1", "negativo ramo IRREVERSIBLE risk R2", bad, "REJECT")
x = action(); x["retry"] = {"retry_safe": False, "max_attempts": 1}; x["error_codes"].append("EXECUTION_UNKNOWN")
check("urn:ocor:schema:action-type-contract:1.1", "positivo ramo retry_safe=false annidato", x, "ACCEPT")
check("urn:ocor:schema:action-type-contract:1.1", "positivo ramo retry_safe=false root", x, "ACCEPT")
bad = copy.deepcopy(x); bad["retry"]["max_attempts"] = 2
check("urn:ocor:schema:action-type-contract:1.1", "negativo retry_safe=false max_attempts", bad, "REJECT")
bad = copy.deepcopy(x); bad["error_codes"] = ["POLICY_DENIED"]
check("urn:ocor:schema:action-type-contract:1.1", "negativo retry_safe=false error code", bad, "REJECT")

# Event subscription: entrambi i rami replay e negativi strutturali.
x = event_contract()
check("urn:ocor:schema:event-subscription-contract:1.1", "baseline positivo", x, "ACCEPT")
bad = copy.deepcopy(x); del bad["replay"]["max_replay_window"]
check("urn:ocor:schema:event-subscription-contract:1.1", "negativo replay consentito senza window", bad, "REJECT")
x_no_replay = event_contract(); x_no_replay["replay"] = {"replay_allowed": False, "cursor_opaque": True, "authorization_required": True}
check("urn:ocor:schema:event-subscription-contract:1.1", "positivo replay vietato senza window", x_no_replay, "ACCEPT")
bad = copy.deepcopy(x_no_replay); bad["replay"]["max_replay_window"] = "P7D"
check("urn:ocor:schema:event-subscription-contract:1.1", "negativo replay vietato con window", bad, "REJECT")
for label, mutate in (
    ("exactly once vietato", lambda y: y["delivery"].update(semantics="EXACTLY_ONCE")),
    ("cursor non opaco", lambda y: y["replay"].update(cursor_opaque=False)),
    ("predicate arbitrario", lambda y: y["filter"].update(arbitrary_predicates_allowed=True)),
    ("marking non propagato", lambda y: y["marking_policy"].update(propagate_marking=False)),
):
    bad = copy.deepcopy(x); mutate(bad)
    check("urn:ocor:schema:event-subscription-contract:1.1", f"negativo {label}", bad, "REJECT")

# OpenAPI: wrapper Draft 2020-12 per componenti e risoluzione locale dei $ref.
def oas_schema(name: str):
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$ref": f"#/components/schemas/{name}", "components": openapi["components"]}


def qctx(mode="BEST_AVAILABLE"):
    c = {
        "request_id": UUID1, "correlation_id": UUID2, "tenant_id": urn("tenant"),
        "organization_id": urn("org"), "domain_id": urn("domain"), "compartments": [urn("comp")],
        "purpose": "test", "classification_marking_ref": CONTENT_REF,
        "ontology_release_digest": DIGEST, "policy_bundle_digest": DIGEST,
        "governed_context_digest": DIGEST,
        "logic_version": "1.0.0", "branch": "main", "consistency": {"mode": mode},
    }
    if mode != "BEST_AVAILABLE":
        c["consistency"]["required_commit"] = "c1"
    return c


resource = {"resource_type_id": urn("type"), "resource_id": "r1"}
call = {"contract_id": urn("contract"), "contract_version": "1.0.0", "contract_digest": DIGEST, "parameters": {}}
requests = {
    "GetObjectRequest": {"context": qctx(), "object_ref": resource, "view_contract": call},
    "ObjectSetRequest": {"context": qctx(), "object_set_contract": call, "page_size": 10},
    "SearchRequest": {"context": qctx(), "search_contract": call, "text": "x", "page_size": 10},
    "TraverseRequest": {"context": qctx(), "start": [resource], "traversal_contract": call},
    "ExplainRequest": {"context": qctx(), "target": resource, "explanation_contract": call},
    "ProvenanceRequest": {"context": qctx(), "target": resource, "direction": "BOTH", "max_depth": 2},
}
for name, instance in requests.items():
    check("OpenAPI 1.2.0", f"positivo request {name}", instance, "ACCEPT", oas_schema(name))
    bad = copy.deepcopy(instance); del bad[next(iter(bad))]
    check("OpenAPI 1.2.0", f"negativo required request {name}", bad, "REJECT", oas_schema(name))

snapshot = {
    "object_ref": resource, "object_schema": pin("object"),
    "valid_time": {"from": NOW, "to": None}, "system_time": {"from": NOW, "to": None},
    "values": {}, "epistemic_status": {"status": "CLAIMED", "accepting_decision_ref": None},
    "link_refs": [], "uncertainty": {"semantics": "NONE"}, "claim_refs": [urn("claim")],
    "evidence_refs": [CONTENT_REF], "identity_candidates": [], "provenance_ref": CONTENT_REF,
    "explanation_ref": CONTENT_REF, "marking_ref": CONTENT_REF,
}
check("OpenAPI 1.2.0", "positivo ObjectSnapshot completo", snapshot, "ACCEPT", oas_schema("ObjectSnapshot"))
for field in ("link_refs", "uncertainty", "explanation_ref"):
    bad = copy.deepcopy(snapshot); del bad[field]
    check("OpenAPI 1.2.0", f"negativo ObjectSnapshot senza {field}", bad, "REJECT", oas_schema("ObjectSnapshot"))

for mode in ("AT_LEAST_COMMIT", "EXACT_AT_COMMIT"):
    check("OpenAPI 1.2.0", f"positivo ramo Consistency {mode}", qctx(mode)["consistency"], "ACCEPT", oas_schema("Consistency"))
bad = {"mode": "EXACT_AT_COMMIT"}
check("OpenAPI 1.2.0", "negativo ramo Consistency senza required_commit", bad, "REJECT", oas_schema("Consistency"))
check("OpenAPI 1.2.0", "positivo Consistency BEST_AVAILABLE senza commit", {"mode": "BEST_AVAILABLE"}, "ACCEPT", oas_schema("Consistency"))

served = {"ontology_release": "1", "branch": "main", "served_commit": "c1", "watermark": "c1", "staleness_ms": 0, "result_marking_ref": CONTENT_REF, "provenance_ref": CONTENT_REF}
problem = {"type": "urn:problem:test", "title": "stale", "status": 409, "reason_code": "STALE_CONTEXT", "correlation_id": UUID1, "served": served}
check("OpenAPI 1.2.0", "positivo ramo Problem version-sensitive", problem, "ACCEPT", oas_schema("Problem"))
bad = copy.deepcopy(problem); del bad["served"]
check("OpenAPI 1.2.0", "negativo ramo Problem version-sensitive", bad, "REJECT", oas_schema("Problem"))
problem2 = {"type": "urn:problem:test", "title": "deferred", "status": 409, "reason_code": "CAPABILITY_DEFERRED", "correlation_id": UUID1, "deferred_element": "ELM-070"}
check("OpenAPI 1.2.0", "positivo ramo Problem CAPABILITY_DEFERRED", problem2, "ACCEPT", oas_schema("Problem"))
bad = copy.deepcopy(problem2); del bad["deferred_element"]
check("OpenAPI 1.2.0", "negativo ramo Problem CAPABILITY_DEFERRED", bad, "REJECT", oas_schema("Problem"))
for name, base, field in (
    ("TemporalInterval", {"from": NOW}, "to"),
    ("EpistemicStatus", {"status": "CLAIMED"}, "accepting_decision_ref"),
):
    values = (NOW, None) if name == "TemporalInterval" else (urn("decision"), None)
    for value in values:
        x = {**base, field: value}
        check("OpenAPI 1.2.0", f"positivo oneOf {name}.{field}={value!r}", x, "ACCEPT", oas_schema(name))
    bad = {**base, field: 7}
    check("OpenAPI 1.2.0", f"negativo oneOf {name}.{field}", bad, "REJECT", oas_schema(name))

# Verifica indipendente che tutti gli if estratti siano coperti nel conteggio atteso.
def count_ifs(node):
    if isinstance(node, dict):
        return (1 if "if" in node else 0) + sum(count_ifs(v) for v in node.values())
    if isinstance(node, list):
        return sum(count_ifs(v) for v in node)
    return 0


if_counts = {sid: count_ifs(doc) for sid, doc in schemas.items()}
if_counts["OpenAPI 1.2.0"] = count_ifs(openapi)
expected = {
    "urn:ocor:schema:signed-canonical-ir:1.0": 0,
    "urn:ocor:schema:canonical-ingestion-envelope:1.2": 4,
    "urn:ocor:schema:mcp-tool-contract:1.2": 11,
    "urn:ocor:schema:action-type-contract:1.1": 11,
    "urn:ocor:schema:event-subscription-contract:1.1": 2,
    "OpenAPI 1.2.0": 3,
}
records.append({"schema": "suite", "case": "conteggio if/then estratti", "expected": expected, "actual": if_counts, "pass": if_counts == expected, "errors": []})

summary = {
    "source": str(ADD.relative_to(ROOT)),
    "if_then_counts": if_counts,
    "total_cases": len(records),
    "passed": sum(1 for r in records if r["pass"]),
    "failed": sum(1 for r in records if not r["pass"]),
    "records": records,
}
RESULTS.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
for r in records:
    print(("PASS" if r["pass"] else "FAIL"), r["schema"], "—", r["case"], f"[{r['actual']}]")
print(f"TOTAL {summary['total_cases']} PASS {summary['passed']} FAIL {summary['failed']}")
print(f"RESULTS {RESULTS.relative_to(ROOT)}")
sys.exit(1 if summary["failed"] else 0)
