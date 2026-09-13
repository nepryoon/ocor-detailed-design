"""Real Jena/Fuseki-backed marking-safe RDF projection.

Proves that an RDF projection preserves marking joins and filters
existence/count paths: a resource is never returned without its
classification marking joined in the same SPARQL query (so a resource
missing its marking triple is never disclosed, at any clearance), and the
publicly exposed count/existence operations are structurally derived from
the SAME filtered list as ordinary listing, so they can never diverge from
it or leak information through a distinguishable shape.

Reuses ``ocor_runtime.c4_marking``'s sealed, unmodified ``MarkingEngine``/
``MarkingSchemeDefinition``/``MarkingSet`` (C4's finite marking lattice) for
the actual authorization decision; this module only adds the real
Fuseki-backed storage/query layer and the projection port around it.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from ocor_runtime.c4_marking import MarkingEngine, MarkingSet

FUSEKI_URL = "http://127.0.0.1:3030"
DATASET = "ocor"
VOCAB = "urn:ocor:vocab:"
PREFIX = f"PREFIX ocor: <{VOCAB}>"


class JenaAdapterError(RuntimeError):
    pass


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
        raise JenaAdapterError(f"SPARQL update failed: {status} {body}")


def _query(sparql_query: str) -> list[dict[str, Any]]:
    encoded = urllib.parse.urlencode({"query": sparql_query})
    status, body = _request(
        "GET",
        f"{FUSEKI_URL}/{DATASET}/sparql?{encoded}",
        headers={"Accept": "application/sparql-results+json"},
    )
    if status != 200:
        raise JenaAdapterError(f"SPARQL query failed: {status} {body}")
    parsed = json.loads(body)
    bindings: list[dict[str, Any]] = parsed["results"]["bindings"]
    return bindings


def _literal(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


class JenaMarkingProjectionAdapter:
    """A marking-safe projection port over a real Fuseki dataset.

    ``list_authorized``/``count_authorized``/``exists_authorized`` are the
    only public read operations; ``count_authorized`` and
    ``exists_authorized`` are deliberately derived from
    ``list_authorized``'s own result rather than independent SPARQL COUNT
    or ASK queries, so the three can never diverge -- the negative
    acceptance criterion this spike must satisfy.
    """

    def __init__(self, engine: MarkingEngine) -> None:
        self._engine = engine

    def reset(self) -> None:
        _update("DELETE WHERE { ?s ?p ?o }")

    def ingest_marked(self, resource_id: str, label: str, classification: str) -> None:
        _update(
            f"{PREFIX} INSERT DATA {{ <{resource_id}> a ocor:Resource ; "
            f"ocor:label {_literal(label)} ; ocor:classification {_literal(classification)} . }}"
        )

    def ingest_unmarked(self, resource_id: str, label: str) -> None:
        """Insert a resource deliberately missing its classification triple
        -- used only to prove the marking join itself is fail-closed."""
        _update(f"{PREFIX} INSERT DATA {{ <{resource_id}> a ocor:Resource ; ocor:label {_literal(label)} . }}")

    def _marked_rows(self) -> list[dict[str, str]]:
        # A single basic graph pattern joins the resource with its
        # classification: a resource can only ever be returned here
        # together with its marking, never separately. This is the
        # "marking join" the spike must preserve -- a row missing the
        # ocor:classification triple structurally cannot appear at all.
        rows = _query(
            f"{PREFIX} SELECT ?resource ?label ?classification WHERE {{ "
            f"?resource a ocor:Resource ; ocor:label ?label ; ocor:classification ?classification . }}"
        )
        return [
            {
                "resource": row["resource"]["value"],
                "label": row["label"]["value"],
                "classification": row["classification"]["value"],
            }
            for row in rows
        ]

    def raw_unfiltered_count(self) -> int:
        """The naive SPARQL COUNT over ALL ocor:Resource instances,
        ignoring marking entirely. Exposed only so tests can demonstrate
        why a naive count would leak information; never used by the
        authorized read operations below."""
        rows = _query(f"{PREFIX} SELECT (COUNT(?resource) AS ?c) WHERE {{ ?resource a ocor:Resource . }}")
        return int(rows[0]["c"]["value"])

    def list_authorized(self, clearance: MarkingSet) -> list[dict[str, str]]:
        authorized = [
            row
            for row in self._marked_rows()
            if self._engine.is_authorized(MarkingSet({"classification": row["classification"]}), clearance)
        ]
        return sorted(authorized, key=lambda row: row["resource"])

    def count_authorized(self, clearance: MarkingSet) -> int:
        return len(self.list_authorized(clearance))

    def exists_authorized(self, resource_id: str, clearance: MarkingSet) -> bool:
        return any(row["resource"] == resource_id for row in self.list_authorized(clearance))
