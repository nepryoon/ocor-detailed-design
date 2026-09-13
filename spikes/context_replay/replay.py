"""Deterministic context-assembly replay.

Proves that a context-assembly receipt digest is a pure, deterministic
function of exactly five pinned dimensions -- item versions, ordering
(a real cosine-similarity ranking against Qdrant, OCOR-DEV-0023's
sealed ``QdrantHarness``, reused unmodified), redactions, truncation
and representation -- so that replaying assembly against the identical
pinned inputs reproduces the identical receipt digest byte-for-byte,
and changing any one dimension changes the digest. Uses
``ocor_runtime.kernel.canonical.canonical_digest`` (sealed RFC 8785
canonicalization) for the digest itself, never a hand-rolled hash.
"""

from __future__ import annotations

from dataclasses import dataclass

from ocor_runtime.kernel.canonical import canonical_digest

from spikes.vector_partition.oracle import QdrantHarness, VectorPartitionError

REPRESENTATION_VERSION = "context-replay-v1"


class ContextReplayError(RuntimeError):
    """Real backend/ranking failure during assembly -- never a silent partial context."""


@dataclass(frozen=True, slots=True)
class PinnedItem:
    item_id: str
    version: str
    content: str


@dataclass(frozen=True, slots=True)
class AssemblyRequest:
    query_vector: tuple[float, ...]
    top_k: int
    redact_fields: tuple[str, ...]
    truncation_chars: int
    representation_version: str = REPRESENTATION_VERSION


@dataclass(frozen=True, slots=True)
class ContextReceipt:
    receipt_digest: str
    ordered_item_refs: tuple[str, ...]
    redacted_fields: tuple[str, ...]
    truncated: bool
    representation_version: str


def _redact(content: str, fields: tuple[str, ...]) -> str:
    lines = []
    for line in content.splitlines():
        key = line.split(":", 1)[0].strip() if ":" in line else None
        lines.append(f"{key}: [REDACTED]" if key in fields else line)
    return "\n".join(lines)


def assemble_context(
    qdrant: QdrantHarness,
    collection: str,
    request: AssemblyRequest,
    pinned_items: tuple[PinnedItem, ...],
) -> ContextReceipt:
    """Assemble a receipted context from ``pinned_items``, ordered by a
    real Qdrant similarity search. Raises ``ContextReplayError`` (never
    a silently incomplete or reordered result) if ranking cannot be
    performed at all.
    """
    try:
        response = qdrant.request(
            "POST",
            f"/collections/{collection}/points/search",
            {"vector": list(request.query_vector), "limit": request.top_k, "with_payload": True},
        )
    except VectorPartitionError as error:
        raise ContextReplayError(f"real ranking backend unreachable: {error}") from error

    by_id = {item.item_id: item for item in pinned_items}
    ranked_ids = [hit["payload"]["item_id"] for hit in response["result"]]
    ordered = [by_id[item_id] for item_id in ranked_ids if item_id in by_id]

    pieces: list[dict[str, str]] = []
    truncated = False
    budget = request.truncation_chars
    for item in ordered:
        redacted_content = _redact(item.content, request.redact_fields)
        if len(redacted_content) > budget:
            redacted_content = redacted_content[:budget]
            truncated = True
        pieces.append({"item_id": item.item_id, "version": item.version, "content": redacted_content})
        budget -= len(redacted_content)
        if budget <= 0:
            break

    representation = {"representation_version": request.representation_version, "items": pieces}
    digest = canonical_digest(representation)
    ordered_refs = tuple(f"{piece['item_id']}@{piece['version']}" for piece in pieces)
    return ContextReceipt(digest, ordered_refs, request.redact_fields, truncated, request.representation_version)
