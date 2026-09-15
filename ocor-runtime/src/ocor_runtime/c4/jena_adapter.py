"""C4 -- retained Jena RDF SHACL adapter.

Completes the smallest contract-compliant, retained (non-spike)
extension of ``spikes.jena_marking.adapter`` (OCOR-DEV-0018) against a
real, live Fuseki instance: a real ``publish`` operation that produces
RDF/JSON-LD output, enforced by an explicit closed shape (the smallest
SHACL-equivalent this task needs -- a required-property and
closed-predicate check, expressed directly since no general SHACL
processor is a project dependency) and by the real marking join
already proven by OCOR-DEV-0018 (reused unmodified via
``ocor_runtime.c4_marking``).

Two negative acceptance criteria are enforced BEFORE any triple is
ever written: an unauthorized (non-allow-listed) predicate blocks
publication (``UNAUTHORIZED_PREDICATE``), and a missing or lossy
provenance reference blocks it too (``PROVENANCE_INVALID``) --
publication is all-or-nothing, so a rejected resource is never
partially visible.

Reads reuse the exact marking-join pattern OCOR-DEV-0018 already
proved for real: a resource is never returned without its
classification joined in the same query. ``to_json_ld`` serializes a
published, authorized resource's triples with ``rdflib`` (already a
project dependency), a real JSON-LD serializer, not a hand-rolled one.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from rdflib import Graph

from ..c4_marking import MarkingEngine, MarkingSet

FUSEKI_URL = "http://127.0.0.1:3030"
DATASET = "ocor"
VOCAB = "urn:ocor:vocab:"
PREFIX = f"PREFIX ocor: <{VOCAB}>"

# The closed predicate vocabulary this adapter will ever publish. A
# triple naming any other predicate is unauthorized and blocks the
# whole publication -- this task's own first negative acceptance
# criterion, made structural rather than merely documented.
ALLOWED_PREDICATES = frozenset({"label", "classification", "provenanceRef"})

REQUIRED_PROPERTIES = frozenset({"label", "classification", "provenanceRef"})


class JenaAdapterError(RuntimeError):
    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {message}")


def _request(
    method: str, url: str, *, headers: dict[str, str] | None = None, body: bytes | None = None, timeout: float = 10.0
) -> tuple[int, str]:
    request = urllib.request.Request(url, method=method, data=body, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def _update(sparql_update: str) -> None:
    status, body = _request(
        "POST",
        f"{FUSEKI_URL}/{DATASET}/update",
        headers={"Content-Type": "application/sparql-update"},
        body=sparql_update.encode("utf-8"),
    )
    if status not in (200, 204):
        raise JenaAdapterError("BACKEND_ERROR", f"SPARQL update failed: {status} {body}")


def _query(sparql_query: str) -> list[dict[str, Any]]:
    encoded = urllib.parse.urlencode({"query": sparql_query})
    status, body = _request(
        "GET",
        f"{FUSEKI_URL}/{DATASET}/sparql?{encoded}",
        headers={"Accept": "application/sparql-results+json"},
    )
    if status != 200:
        raise JenaAdapterError("BACKEND_ERROR", f"SPARQL query failed: {status} {body}")
    parsed = json.loads(body)
    bindings: list[dict[str, Any]] = parsed["results"]["bindings"]
    return bindings


def _construct(sparql_construct: str) -> str:
    encoded = urllib.parse.urlencode({"query": sparql_construct})
    status, body = _request(
        "GET",
        f"{FUSEKI_URL}/{DATASET}/sparql?{encoded}",
        headers={"Accept": "text/turtle"},
    )
    if status != 200:
        raise JenaAdapterError("BACKEND_ERROR", f"SPARQL construct failed: {status} {body}")
    return body


def _literal(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


# Characters an IRI reference can never contain inside SPARQL ``<...>``
# (SPARQL 1.1 IRIREF production): control chars plus < > " { } | ^ ` \ and
# space. Since C4 resource identifiers are URNs they always pass; a malformed
# identifier is rejected fail-closed before any triple is read or written,
# so it can never break out of the IRI and inject SPARQL.
_IRI_FORBIDDEN = frozenset('<>"{}|^`\\ ')


def _require_iri(resource_id: str) -> str:
    if not resource_id or any(char in _IRI_FORBIDDEN or ord(char) <= 0x20 for char in resource_id):
        raise JenaAdapterError(
            "RESOURCE_ID_INVALID",
            "resource_id must be a well-formed IRI with no SPARQL-breaking characters",
        )
    return resource_id


class JenaSHACLProjectionAdapter:
    """Retained C4 projection: a real Fuseki-backed publish/read path
    enforcing a closed predicate shape, mandatory non-lossy provenance,
    and the same marking join OCOR-DEV-0018 already proved for real."""

    def __init__(self, engine: MarkingEngine) -> None:
        self._engine = engine

    def reset(self) -> None:
        _update("DELETE WHERE { ?s ?p ?o }")

    def publish(self, resource_id: str, properties: dict[str, str]) -> None:
        """Validates the closed shape and non-lossy provenance BEFORE
        writing anything; a rejected resource never becomes partially
        visible."""
        _require_iri(resource_id)
        unauthorized = sorted(set(properties) - ALLOWED_PREDICATES)
        if unauthorized:
            raise JenaAdapterError(
                "UNAUTHORIZED_PREDICATE", f"predicate(s) outside the closed vocabulary: {unauthorized}"
            )
        missing = sorted(REQUIRED_PROPERTIES - set(properties))
        if missing:
            raise JenaAdapterError("SHAPE_VIOLATION", f"missing required propert(y/ies): {missing}")
        provenance = properties["provenanceRef"]
        if not provenance or not provenance.startswith("urn:ocor:provenance:"):
            raise JenaAdapterError(
                "PROVENANCE_INVALID", "provenanceRef must be a real, non-empty urn:ocor:provenance: reference"
            )

        triples = " ".join(
            f"ocor:{predicate} {_literal(value)} ;" for predicate, value in sorted(properties.items())
        )
        _update(f"{PREFIX} INSERT DATA {{ <{resource_id}> a ocor:Resource ; {triples[:-1]} . }}")

    def _authorized_rows(self, clearance: MarkingSet) -> list[dict[str, str]]:
        rows = _query(
            f"{PREFIX} SELECT ?resource ?label ?classification ?provenanceRef WHERE {{ "
            f"?resource a ocor:Resource ; ocor:label ?label ; ocor:classification ?classification ; "
            f"ocor:provenanceRef ?provenanceRef . }}"
        )
        authorized = [
            {
                "resource": row["resource"]["value"],
                "label": row["label"]["value"],
                "classification": row["classification"]["value"],
                "provenanceRef": row["provenanceRef"]["value"],
            }
            for row in rows
            if self._engine.is_authorized(MarkingSet({"classification": row["classification"]["value"]}), clearance)
        ]
        return sorted(authorized, key=lambda row: row["resource"])

    def list_authorized(self, clearance: MarkingSet) -> list[dict[str, str]]:
        return self._authorized_rows(clearance)

    def exists_authorized(self, resource_id: str, clearance: MarkingSet) -> bool:
        return any(row["resource"] == resource_id for row in self._authorized_rows(clearance))

    def to_json_ld(self, resource_id: str, clearance: MarkingSet) -> dict[str, Any]:
        """Serializes an authorized resource's triples to real JSON-LD
        via rdflib -- never for a resource the clearance does not
        authorize, structurally identical to the marking-safe read
        path (``exists_authorized`` is the same filtered source)."""
        _require_iri(resource_id)
        if not self.exists_authorized(resource_id, clearance):
            raise JenaAdapterError("MARKING_DENIED", "resource is not authorized for the requester's clearance")
        turtle = _construct(f"{PREFIX} CONSTRUCT {{ <{resource_id}> ?p ?o }} WHERE {{ <{resource_id}> ?p ?o }}")
        graph = Graph()
        graph.parse(data=turtle, format="turtle")
        serialized = graph.serialize(format="json-ld")
        result: dict[str, Any] = json.loads(serialized)
        return result

    def raw_unfiltered_triple_count(self) -> int:
        """The naive SPARQL COUNT ignoring marking entirely -- exposed
        only so tests can demonstrate why a naive count would leak;
        never used by the authorized read operations above."""
        rows = _query(f"{PREFIX} SELECT (COUNT(?resource) AS ?c) WHERE {{ ?resource a ocor:Resource . }}")
        return int(rows[0]["c"]["value"])
