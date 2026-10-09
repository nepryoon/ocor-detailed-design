"""OCOR-DEV-0051: Implement memory metadata, content and index stores.

Acceptance (backlog): metadata, content, lexical and vector representations
commit with versioned pointers and compartment partitions.  Negative: partial
store visibility or an unbound representation is non-queryable and reconciled;
a SKIPPED, UNAVAILABLE, mock-only or NOT_EXECUTED qualifying case is not
accepted.

Oracles: ADD v1.3 Part II §§2.5-2.8 and 2.13 (full isolation tuple on state,
content and indexes; encrypted content-addressed payloads; rebuildable,
policy-partitioned, representation-versioned projections; projection drift
blocks materialisation), LLD v1.1 §§2.8.1-2.8.4 (ports, backend IDs never cross
them, projections bound to the same item/version digest) and change-control §7
(every index entry carries item/version, content digest, representation
digest, marking, policy, scope and deletion epoch).

Qualifying cases run on real, pinned backends: PostgreSQL 16 from
``OCOR_LIVE_POSTGRES_DSN`` (metadata, encrypted content objects and the
full-text index, one isolated schema per run), Qdrant 1.15.1 (vector index,
provisioned through OCOR-DEV-0023's sealed ``QdrantHarness``) and OpenBao 2.6.2
transit (authenticated encryption with a key derived from each content address,
a disposable dev server with a generated token).  Images are the digests of
``infra/services.lock.json``; a missing backend fails, it never skips.  Records
come from the real OCOR-DEV-0050 admission service.  The unit cases at the top
use explicit in-memory port fixtures only for branch logic; none of them is a
qualifying store case.
"""

from __future__ import annotations

import base64
import contextlib
import dataclasses
import hashlib
import json
import os
import secrets
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import psycopg
import pytest
from ocor_runtime.c4_marking import MarkingSchemeDefinition
from ocor_runtime.kernel.canonical import canonical_bytes, format_utc_timestamp
from ocor_runtime.kernel.governance import EvidenceRecord, InMemoryTrustedClock, ProvenanceRecord
from ocor_runtime.kernel.governed_context import GovernedContext, VerifiedGovernedContextBinding
from ocor_runtime.memory.model import (
    AdmissionLimits,
    AdmittedMemoryVersion,
    FederationPolicy,
    GovernedMemoryItem,
    InMemoryMemoryVersionLedger,
    InstructionApproval,
    LatticeMarkingResolver,
    MemoryAdmissionService,
    MemoryPolicyDecision,
    MemoryScope,
    memory_version_ref,
)
from ocor_runtime.memory.stores import (
    IndexHit,
    LexicalProfile,
    MemoryPartition,
    MemoryStoreCoordinator,
    MemoryStoreCorrupted,
    MemoryStoreError,
    RepresentationPointer,
    SealedContent,
    StagedVersion,
    StoredVersion,
    StoreLimits,
    VectorProfile,
    VersionState,
    content_object_ref,
    lexical_document,
    predecessor_not_committed,
    stage_conflict,
    validate_embedding,
    vector_digest,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from spikes.vector_partition.oracle import QDRANT_IMAGE, QdrantHarness  # noqa: E402

SERVICES_LOCK = json.loads((REPOSITORY_ROOT / "infra/services.lock.json").read_text("utf-8"))
LOCKED_IMAGES = {entry["id"]: entry.get("image") for entry in SERVICES_LOCK["services"]}

NOW = datetime(2026, 10, 9, 12, 0, 0, tzinfo=UTC)
CORRELATION = "4b8e2f1a-9c3d-4e5f-8a7b-1c2d3e4f5a6b"
CAUSATION = "7d6c5b4a-3f2e-4d1c-9b8a-0f1e2d3c4b5a"
DIMENSIONS = 8


def d(label: str | bytes) -> str:
    raw = label.encode() if isinstance(label, str) else label
    return "urn:sha256:" + hashlib.sha256(raw).hexdigest()


M_UNCLASSIFIED = d("marking:UNCLASSIFIED")
M_RESTRICTED = d("marking:RESTRICTED")
POLICY_BUNDLE = d("policy-bundle:memory:1")
ONTOLOGY = d("ontology-release:1")
SOURCE_DIGEST = d("source:telemetry-1")
VECTOR_MODEL = {
    "embedding_model_ref": "embedding-model:fixture-hash-8:1",
    "embedding_model_digest": d("embedding-model:fixture-hash-8:1"),
    "embedding_dimensions": DIMENSIONS,
    "embedding_normalization_profile": "l2-unit",
}


def embed(text: str) -> list[float]:
    """Deterministic fixture embedding (the embedding model itself is OCOR-DEV-0053)."""

    raw = hashlib.sha256(text.encode()).digest()
    values = [((byte % 17) + 1) / 17.0 for byte in raw[:DIMENSIONS]]
    norm = sum(v * v for v in values) ** 0.5
    return [v / norm for v in values]


# --------------------------------------------------------------------------
# Admission world: records come from the real OCOR-DEV-0050 admission service
# --------------------------------------------------------------------------


def gcs(compartment: str) -> GovernedContext:
    return GovernedContext(
        tenant_id="tenant-a",
        organization_id="org-a",
        domain_id="domain-ops",
        compartments=(compartment,),
        classification_marking_ref=M_RESTRICTED,
        purpose="mission-planning",
        effective_principal_id="agent-principal-1",
        actor_chain=("human-operator-1", "agent-principal-1"),
        ontology_release_digest=ONTOLOGY,
        policy_bundle_digest=POLICY_BUNDLE,
        correlation_id=CORRELATION,
    )


@dataclass
class Resolver:
    def source_digest(self, source_ref: str, ctx: GovernedContext) -> str | None:
        return SOURCE_DIGEST if source_ref == "src-telemetry-1" else None

    def evidence(self, evidence_ref: str, ctx: GovernedContext) -> EvidenceRecord | None:
        if evidence_ref != "ev-1":
            return None
        return EvidenceRecord(
            evidence_id="ev-1",
            content_digest=d("evidence:ev-1"),
            source_ref="src-telemetry-1",
            acquired_at=NOW - timedelta(hours=1),
            acquirer_principal_id="sensor-gateway-1",
            method_ref="method:telemetry-capture:1",
            chain_of_custody=("sensor-gateway-1",),
            marking_ref=M_UNCLASSIFIED,
            retention_until=NOW + timedelta(days=30),
        )

    def provenance(self, provenance_ref: str, ctx: GovernedContext) -> ProvenanceRecord | None:
        if provenance_ref != "prov-1":
            return None
        return ProvenanceRecord(
            provenance_id="prov-1",
            evidence_refs=("ev-1",),
            source_refs=("src-telemetry-1",),
            activity_refs=("activity:capture-1",),
            actor_refs=("sensor-gateway-1",),
            governed_context_digest=ctx.digest(),
            correlation_id=CORRELATION,
            causation_id=CAUSATION,
            created_at=NOW - timedelta(hours=1),
        )

    def instruction_approval(self, ref: str, ctx: GovernedContext) -> InstructionApproval | None:
        return None

    def federation_policy(self, ref: str, ctx: GovernedContext) -> FederationPolicy | None:
        return None


class Policy:
    def authorize_admission(self, item: GovernedMemoryItem, ctx: GovernedContext) -> MemoryPolicyDecision:
        return MemoryPolicyDecision(
            permitted=True,
            decision_ref=f"decision:{item.version_ref}",
            policy_bundle_digest=ctx.policy_bundle_digest,
        )


class Admission:
    """The real admission service over one ledger shared by every compartment."""

    def __init__(self) -> None:
        self.ledger = InMemoryMemoryVersionLedger()
        self.clock = InMemoryTrustedClock(NOW)
        scheme = MarkingSchemeDefinition("ocor-classification", ["UNCLASSIFIED", "RESTRICTED", "SECRET"])
        self.service = MemoryAdmissionService(
            ledger=self.ledger,
            resolver=Resolver(),
            policy=Policy(),
            markings=LatticeMarkingResolver(
                scheme, {M_UNCLASSIFIED: "UNCLASSIFIED", M_RESTRICTED: "RESTRICTED"}
            ),
            clock=self.clock,
            limits=AdmissionLimits(retention_horizons={"retention:standard": timedelta(days=365)}),
        )
        self._ops = 0

    def admit(
        self,
        item_id: str,
        text: str,
        *,
        compartment: str = "alpha",
        version: int = 1,
        vector: bool = True,
        scope: str = "PROJECT",
        scope_fields: Mapping[str, str] | None = None,
    ) -> tuple[AdmittedMemoryVersion, bytes, list[float] | None]:
        payload = text.encode()
        context = gcs(compartment)
        candidate: dict[str, Any] = {
            "memory_item_id": item_id,
            "memory_version": version,
            "memory_kind": "EPISODIC",
            "memory_scope": scope,
            "owner_principal_id": context.effective_principal_id,
            "tenant_id": context.tenant_id,
            "organization_id": context.organization_id,
            "domain_id": context.domain_id,
            "compartments": [compartment],
            "classification_marking_ref": M_RESTRICTED,
            "purpose": context.purpose,
            "content_schema_ref": "urn:ocor:memory-content:episode:1.0",
            "content_ref": "content:" + d(payload).removeprefix("urn:sha256:"),
            "content_digest": d(payload),
            "source_kind": "OBSERVATION",
            "source_ref": "src-telemetry-1",
            "source_digest": SOURCE_DIGEST,
            "evidence_refs": ["ev-1"],
            "provenance_refs": ["prov-1"],
            "derived_from_refs": [],
            "consolidates_refs": [],
            "created_at": format_utc_timestamp(self.clock.now()),
            "valid_from": format_utc_timestamp(NOW - timedelta(minutes=10)),
            "retention_policy_ref": "retention:standard",
            "confidence": 0.8,
            "policy_bundle_digest": POLICY_BUNDLE,
            "ontology_release_digest": ONTOLOGY,
            "governed_context_digest": context.digest(),
            "instruction_eligible": False,
            "taint_labels": ["EXTERNAL_DATA"],
            "representation_kinds": ["STRUCTURED", "FULL_TEXT"],
            "lifecycle_status": "ACTIVE",
        }
        candidate.update(scope_fields if scope_fields is not None else {"project_id": "project-1"})
        if version > 1:
            candidate["supersedes_ref"] = memory_version_ref(item_id, version - 1)
        embedding = embed(text) if vector else None
        if embedding is not None:
            candidate["representation_kinds"] = ["STRUCTURED", "FULL_TEXT", "VECTOR"]
            candidate.update(VECTOR_MODEL)
            candidate["embedding_ref"] = f"embedding:{item_id}:v{version}"
            candidate["embedding_digest"] = vector_digest(embedding)
        self._ops += 1
        self.service.admit(
            {
                "operation_id": f"op-{self._ops}",
                "governed_context": context.to_mapping(),
                "governed_context_digest": context.digest(),
                "deadline": format_utc_timestamp(self.clock.now() + timedelta(seconds=30)),
                "candidate": candidate,
            },
            binding=VerifiedGovernedContextBinding(binding_ref="binding:keycloak-1", expected=context),
            payload=payload,
        )
        record = self.ledger.get(item_id, version)
        assert record is not None
        return record, payload, embedding


def partition_of(record: AdmittedMemoryVersion) -> MemoryPartition:
    return MemoryPartition.for_item(record.item)


# --------------------------------------------------------------------------
# Explicit in-memory port fixtures (unit cases only, never qualifying)
# --------------------------------------------------------------------------


class FixtureCipher:
    """Context-bound reversible transform for unit branch logic -- not cryptography."""

    def seal(self, *, context: Mapping[str, str], plaintext: bytes) -> SealedContent:
        tag = hashlib.sha256(canonical_bytes(dict(context))).digest()
        return SealedContent("urn:ocor:memory-key:fixture", tag + bytes(b ^ 0x5A for b in plaintext))

    def open(self, *, context: Mapping[str, str], sealed: SealedContent) -> bytes:
        tag = hashlib.sha256(canonical_bytes(dict(context))).digest()
        if sealed.ciphertext[:32] != tag:
            raise ValueError("context mismatch")
        return bytes(b ^ 0x5A for b in sealed.ciphertext[32:])


class MemMetadata:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, int], StoredVersion] = {}
        self.heads: dict[str, int] = {}
        self.writes = 0

    def stage(self, staged: StagedVersion) -> StoredVersion:
        key = (staged.memory_item_id, staged.memory_version)
        existing = self.rows.get(key)
        if existing is not None:
            if existing.staged.stage_digest != staged.stage_digest:
                raise stage_conflict(staged.memory_version_ref)
            return existing
        self.writes += 1
        self.rows[key] = StoredVersion(staged, VersionState.PENDING, None)
        return self.rows[key]

    def get(self, memory_item_id: str, memory_version: int) -> StoredVersion | None:
        return self.rows.get((memory_item_id, memory_version))

    def commit(self, memory_item_id: str, memory_version: int, *, stage_digest: str, committed_at: str) -> StoredVersion:
        stored = self.rows[(memory_item_id, memory_version)]
        assert stored.staged.stage_digest == stage_digest
        if stored.state is VersionState.COMMITTED:
            return stored
        if self.heads.get(memory_item_id, 0) != memory_version - 1:
            raise predecessor_not_committed(stored.staged.memory_version_ref)
        self.writes += 1
        self.rows[(memory_item_id, memory_version)] = StoredVersion(stored.staged, VersionState.COMMITTED, committed_at)
        self.heads[memory_item_id] = memory_version
        return self.rows[(memory_item_id, memory_version)]

    def head(self, memory_item_id: str) -> int:
        return self.heads.get(memory_item_id, 0)

    def pointer(self, store_ref: str) -> tuple[RepresentationPointer, VersionState] | None:
        for stored in self.rows.values():
            for pointer in stored.staged.pointers:
                if pointer.store_ref == store_ref:
                    return pointer, stored.state
        return None

    def versions_in(self, partition_digest: str) -> tuple[StoredVersion, ...]:
        return tuple(s for s in self.rows.values() if s.staged.partition.digest == partition_digest)

    def partitions(self) -> tuple[MemoryPartition, ...]:
        return tuple({s.staged.partition.digest: s.staged.partition for s in self.rows.values()}.values())


class MemContent:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[str, SealedContent]] = {}
        self.writes = 0

    def put(self, object_ref: str, partition_digest: str, sealed: SealedContent) -> None:
        if object_ref not in self.objects:
            self.writes += 1
            self.objects[object_ref] = (partition_digest, sealed)

    def get(self, object_ref: str) -> SealedContent | None:
        entry = self.objects.get(object_ref)
        return None if entry is None else entry[1]

    def delete(self, object_ref: str) -> None:
        self.objects.pop(object_ref, None)

    def refs(self, partition_digest: str) -> tuple[str, ...]:
        return tuple(ref for ref, (p, _) in self.objects.items() if p == partition_digest)


class MemIndex:
    """Lexical (token overlap) or vector (dot product) fixture index."""

    def __init__(self) -> None:
        self.entries_by_layout: dict[tuple[str, str], dict[str, tuple[Mapping[str, object], Any]]] = {}
        self.writes = 0

    def upsert(self, partition: MemoryPartition, profile: Any, store_ref: str, payload: Mapping[str, object], data: Any) -> None:
        self.writes += 1
        layout = (partition.digest, profile.representation_version)
        self.entries_by_layout.setdefault(layout, {})[store_ref] = (dict(payload), data)

    def _score(self, data: Any, query: Any) -> float:
        if isinstance(query, str):
            return float(len(set(query.lower().split()) & set(str(data).lower().split())))
        return float(sum(a * b for a, b in zip(data, query, strict=True)))

    def search(self, partition: MemoryPartition, representation_version: str, query: Any, *, limit: int, offset: int) -> Sequence[IndexHit]:
        entries = self.entries_by_layout.get((partition.digest, representation_version), {})
        scored = sorted(
            (IndexHit(ref, payload, self._score(data, query)) for ref, (payload, data) in entries.items()),
            key=lambda hit: (-hit.score, hit.store_ref),
        )
        return [hit for hit in scored if hit.score > 0][offset : offset + limit]

    def get(self, partition: MemoryPartition, representation_version: str, store_ref: str) -> Mapping[str, object] | None:
        entry = self.entries_by_layout.get((partition.digest, representation_version), {}).get(store_ref)
        return None if entry is None else entry[0]

    def entries(self, partition: MemoryPartition, representation_version: str) -> Sequence[IndexHit]:
        layout = self.entries_by_layout.get((partition.digest, representation_version), {})
        return [IndexHit(ref, payload, 0.0) for ref, (payload, _) in layout.items()]

    def remove(self, partition: MemoryPartition, representation_version: str, store_ref: str) -> None:
        self.entries_by_layout.get((partition.digest, representation_version), {}).pop(store_ref, None)


@dataclass
class UnitWorld:
    admission: Admission = field(default_factory=Admission)
    metadata: MemMetadata = field(default_factory=MemMetadata)
    content: MemContent = field(default_factory=MemContent)
    lexical: MemIndex = field(default_factory=MemIndex)
    vector: MemIndex = field(default_factory=MemIndex)

    def coordinator(self, **limits: Any) -> MemoryStoreCoordinator:
        return MemoryStoreCoordinator(
            ledger=self.admission.ledger,
            metadata=self.metadata,
            content=self.content,
            cipher=FixtureCipher(),
            lexical=self.lexical,  # type: ignore[arg-type]
            vector=self.vector,  # type: ignore[arg-type]
            clock=self.admission.clock,
            limits=StoreLimits(**limits),
        )

    def writes(self) -> tuple[int, int, int, int]:
        return (self.metadata.writes, self.content.writes, self.lexical.writes, self.vector.writes)


# --------------------------------------------------------------------------
# Unit branch logic (fixtures above; not qualifying store evidence)
# --------------------------------------------------------------------------


PARTITION_ATTRIBUTES = [
    ("tenant_id", "tenant-b"),
    ("organization_id", "org-b"),
    ("domain_id", "domain-b"),
    ("compartments", ("alpha", "bravo")),
    ("classification_marking_ref", M_UNCLASSIFIED),
    ("purpose", "other-purpose"),
    ("policy_bundle_digest", d("policy-bundle:memory:2")),
    ("ontology_release_digest", d("ontology-release:2")),
    ("memory_scope", MemoryScope.DOMAIN),
    ("scope_bindings", (("project_id", "project-2"),)),
]


@pytest.mark.parametrize(("attribute", "value"), PARTITION_ATTRIBUTES, ids=[a for a, _ in PARTITION_ATTRIBUTES])
def test_every_isolation_attribute_changes_the_partition(attribute: str, value: Any) -> None:
    record, _, _ = Admission().admit("mem-p", "partition fixture")
    base = partition_of(record)
    changed = MemoryPartition(**{**{f: getattr(base, f) for f in base.__slots__}, attribute: value})
    assert changed.digest != base.digest
    assert MemoryPartition.from_mapping(changed.to_mapping()) == changed


def test_partition_is_canonical_and_binds_the_scope_owner() -> None:
    admission = Admission()
    agent_1, _, _ = admission.admit("mem-a1", "agent one", scope="AGENT", scope_fields={"agent_id": "agent-1"})
    agent_2, _, _ = admission.admit("mem-a2", "agent two", scope="AGENT", scope_fields={"agent_id": "agent-2"})
    assert partition_of(agent_1).scope_bindings == (("agent_id", "agent-1"),)
    assert partition_of(agent_1).digest != partition_of(agent_2).digest
    reordered = partition_of(agent_1).to_mapping()
    reordered["compartments"] = ["zulu", "alpha"]
    with pytest.raises(MemoryStoreCorrupted):
        MemoryPartition.from_mapping(reordered)
    with pytest.raises(MemoryStoreCorrupted):
        MemoryPartition.from_mapping({**partition_of(agent_1).to_mapping(), "extra": "x"})


def _pointer_mapping() -> dict[str, object]:
    world = UnitWorld()
    record, payload, vector = world.admission.admit("mem-ptr", "pointer fixture text")
    receipt = world.coordinator().commit(record, payload=payload, embedding=vector)
    stored = world.metadata.get("mem-ptr", 1)
    assert stored is not None and receipt.state == "COMMITTED"
    return stored.staged.pointers[0].to_mapping()


@pytest.mark.parametrize(
    "mutation",
    [
        lambda m: m.update(extra="x"),
        lambda m: m.pop("deletion_epoch"),
        lambda m: m.update(deletion_epoch=True),
        lambda m: m.update(deletion_epoch=-1),
        lambda m: m.update(item_digest="sha256:abc"),
        lambda m: m.update(representation_kind="HYBRID"),
        lambda m: m.update(memory_scope="GLOBAL"),
        lambda m: m.update(memory_version_ref=""),
    ],
    ids=["extra", "missing", "bool-epoch", "negative-epoch", "bad-digest", "bad-kind", "bad-scope", "empty-ref"],
)
def test_representation_pointer_is_a_closed_record(mutation: Any) -> None:
    mapping = _pointer_mapping()
    assert RepresentationPointer.from_mapping(mapping).to_mapping() == mapping
    mutation(mapping)
    with pytest.raises(MemoryStoreCorrupted):
        RepresentationPointer.from_mapping(mapping)


def test_embedding_must_be_exactly_the_digested_vector() -> None:
    record, _, vector = Admission().admit("mem-v", "vector fixture")
    assert vector is not None
    assert validate_embedding(record.item, vector) == tuple(vector)
    cases: list[tuple[Any, str]] = [
        (vector[:-1], "EMBEDDING_DIMENSION_MISMATCH"),
        ([*vector[:-1], float("nan")], "EMBEDDING_INVALID"),
        ([0.0] * DIMENSIONS, "EMBEDDING_INVALID"),
        ([True] * DIMENSIONS, "EMBEDDING_INVALID"),
        ("abcdefgh", "EMBEDDING_INVALID"),
        ([v * 2 for v in vector], "EMBEDDING_DIGEST_MISMATCH"),
    ]
    for bad, detail in cases:
        with pytest.raises(MemoryStoreError) as caught:
            validate_embedding(record.item, bad)
        assert (caught.value.reason_code, caught.value.detail_code) == ("MEMORY_SCHEMA_INVALID", detail)


@pytest.mark.parametrize("payload", [b"\xff\xfe", b"text\x00nul", b"   "], ids=["not-utf8", "nul", "blank"])
def test_lexical_document_requires_a_rebuildable_utf8_payload(payload: bytes) -> None:
    assert lexical_document(b"pump vibration") == "pump vibration"
    with pytest.raises(MemoryStoreError) as caught:
        lexical_document(payload)
    assert caught.value.detail_code == "LEXICAL_DOCUMENT_INVALID"


def test_invalid_commits_are_rejected_before_any_store_write() -> None:
    world = UnitWorld()
    coordinator = world.coordinator()
    record, payload, vector = world.admission.admit("mem-u", "unit fixture text")
    plain, plain_payload, _ = world.admission.admit("mem-plain", "no vector", vector=False)
    foreign, foreign_payload, foreign_vector = Admission().admit("mem-foreign", "not in this ledger")
    tampered = AdmittedMemoryVersion(
        item=record.item,
        item_digest=d("forged"),
        idempotency_key=record.idempotency_key,
        lifecycle_event=record.lifecycle_event,
        audit_event=record.audit_event,
        receipt=record.receipt,
    )
    cases: list[tuple[Any, dict[str, Any], str, str]] = [
        ("not-a-record", {"payload": payload}, "MEMORY_SCHEMA_INVALID", "RECORD_INVALID"),
        (tampered, {"payload": payload, "embedding": vector}, "MEMORY_SCHEMA_INVALID", "RECORD_INVALID"),
        (foreign, {"payload": foreign_payload, "embedding": foreign_vector}, "MEMORY_VERSION_NOT_FOUND", "VERSION_NOT_ADMITTED"),
        (record, {"payload": payload + b"!", "embedding": vector}, "MEMORY_SCHEMA_INVALID", "CONTENT_DIGEST_MISMATCH"),
        (record, {"payload": payload}, "MEMORY_SCHEMA_INVALID", "EMBEDDING_MISSING"),
        (record, {"payload": payload, "embedding": vector[:-1] if vector else []}, "MEMORY_SCHEMA_INVALID", "EMBEDDING_DIMENSION_MISMATCH"),
        (plain, {"payload": plain_payload, "embedding": embed("x")}, "MEMORY_SCHEMA_INVALID", "UNBOUND_REPRESENTATION"),
    ]
    for candidate, kwargs, reason, detail in cases:
        with pytest.raises(MemoryStoreError) as caught:
            coordinator.commit(candidate, **kwargs)
        assert (caught.value.reason_code, caught.value.detail_code) == (reason, detail)
        assert world.writes() == (0, 0, 0, 0), detail
        if isinstance(candidate, AdmittedMemoryVersion):
            assert caught.value.to_problem()["correlation_id"] == CORRELATION


def test_stage_verification_detects_tampered_metadata() -> None:
    world = UnitWorld()
    record, payload, vector = world.admission.admit("mem-t", "tamper fixture")
    world.coordinator().commit(record, payload=payload, embedding=vector)
    stored = world.metadata.get("mem-t", 1)
    assert stored is not None
    body = stored.staged.body()
    assert StagedVersion.from_body(body, stored.staged.staged_at).stage_digest == stored.staged.stage_digest
    for mutate in (
        lambda b: b["item"].update(confidence=0.1),
        lambda b: b.update(content_object_ref="urn:ocor:memory-content-object:00"),
        lambda b: b["pointers"].pop(),
        lambda b: b["partition"].update(purpose="other"),
        lambda b: b.update(extra=1),
    ):
        broken = json.loads(json.dumps(body))
        mutate(broken)
        with pytest.raises(MemoryStoreCorrupted):
            StagedVersion.from_body(broken, stored.staged.staged_at)


def test_unbound_backlog_beyond_the_scan_bound_fails_closed() -> None:
    world = UnitWorld()
    record, payload, vector = world.admission.admit("mem-b", "backlog pump")
    coordinator = world.coordinator(page_size=4, max_scanned_hits=8)
    coordinator.commit(record, payload=payload, embedding=vector)
    partition = partition_of(record)
    version = LexicalProfile().representation_version
    for n in range(12):
        world.lexical.upsert(partition, LexicalProfile(), f"urn:forged:{n:02d}", {"forged": n}, "backlog pump pump")
    with pytest.raises(MemoryStoreError) as caught:
        coordinator.lexical_candidates(partition, "backlog pump", limit=1)
    assert caught.value.detail_code == "UNBOUND_BACKLOG"
    report = coordinator.reconcile()
    assert len(report.unbound_removed) == 12
    hits = coordinator.lexical_candidates(partition, "backlog pump", limit=1)
    assert [hit.memory_version_ref for hit in hits] == [record.item.version_ref]
    assert version == hits[0].representation_version


def test_query_inputs_are_validated() -> None:
    world = UnitWorld()
    record, payload, vector = world.admission.admit("mem-q", "query fixture")
    coordinator = world.coordinator()
    coordinator.commit(record, payload=payload, embedding=vector)
    partition = partition_of(record)
    profile = VectorProfile.for_item(record.item)
    for call in (
        lambda: coordinator.lexical_candidates(partition, "  ", limit=1),
        lambda: coordinator.lexical_candidates(partition, "query", limit=0),
        lambda: coordinator.lexical_candidates(partition, "query", limit=True),
        lambda: coordinator.vector_candidates(partition, profile, [1.0], limit=1),
        lambda: coordinator.vector_candidates(partition, profile, ["x"] * DIMENSIONS, limit=1),
        lambda: coordinator.vector_candidates(partition, profile, [float("inf")] * DIMENSIONS, limit=1),
    ):
        with pytest.raises(MemoryStoreError) as caught:
            call()
        assert caught.value.reason_code == "MEMORY_SCHEMA_INVALID"


# --------------------------------------------------------------------------
# Real backends: PostgreSQL (metadata, content, full-text), Qdrant, OpenBao
# --------------------------------------------------------------------------


def _http(method: str, url: str, body: Any | None = None, *, headers: Mapping[str, str] | None = None, timeout: float = 5.0) -> tuple[int, Any]:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return exc.code, json.loads(raw) if raw else None
        except json.JSONDecodeError:
            return exc.code, None


def _docker(*args: str, timeout: int = 120) -> str:
    result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError(f"docker {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


class OpenBaoHarness:
    """Disposable pinned OpenBao dev server with a generated root token."""

    PREFIX = "ocor-test-0051-openbao-"

    def __init__(self, container: str, endpoint: str, token: str) -> None:
        self.container = container
        self.endpoint = endpoint
        self.token = token

    @classmethod
    def provision(cls) -> OpenBaoHarness:
        image = LOCKED_IMAGES["openbao"]
        container = cls.PREFIX + uuid.uuid4().hex[:12]
        token = secrets.token_hex(24)
        _docker(
            "run", "--detach", "--name", container, "--cap-add=IPC_LOCK",
            "--security-opt", "no-new-privileges:true",
            "--env", f"BAO_DEV_ROOT_TOKEN_ID={token}",
            "--publish", "127.0.0.1::8200",
            image, "server", "-dev", "-dev-listen-address=0.0.0.0:8200",
        )
        try:
            port = _docker("port", container, "8200/tcp").splitlines()[0].rsplit(":", 1)[1]
            harness = cls(container, f"http://127.0.0.1:{port}", token)
            deadline = time.monotonic() + 60
            while True:
                try:
                    status, _ = _http("GET", f"{harness.endpoint}/v1/sys/health")
                    if status == 200:
                        break
                except (urllib.error.URLError, ConnectionError, OSError):
                    pass
                if time.monotonic() > deadline:
                    raise RuntimeError("OpenBao did not become healthy")
                time.sleep(0.3)
            harness.call("POST", "/v1/sys/mounts/ocor-memory-transit", {"type": "transit"})
            harness.call("POST", "/v1/ocor-memory-transit/keys/memory-content", {"type": "aes256-gcm96", "derived": True})
            return harness
        except Exception:
            _docker("rm", "--force", "--volumes", container)
            raise

    def call(self, method: str, path: str, body: Any | None = None) -> Any:
        status, data = _http(method, f"{self.endpoint}{path}", body, headers={"X-Vault-Token": self.token})
        if status not in (200, 204):
            raise RuntimeError(f"OpenBao {method} {path} -> {status}")
        return data

    def destroy(self) -> None:
        assert self.container.startswith(self.PREFIX)
        _docker("rm", "--force", "--volumes", self.container)


class OpenBaoTransitCipher:
    """AES-256-GCM96 transit key derived per content address, AAD = canonical context."""

    def __init__(self, bao: OpenBaoHarness, key: str = "memory-content") -> None:
        self._bao = bao
        self._key = key

    @staticmethod
    def _params(context: Mapping[str, str]) -> dict[str, str]:
        encoded = canonical_bytes(dict(context))
        return {
            "context": base64.b64encode(hashlib.sha256(encoded).digest()).decode(),
            "associated_data": base64.b64encode(encoded).decode(),
        }

    def seal(self, *, context: Mapping[str, str], plaintext: bytes) -> SealedContent:
        data = self._bao.call(
            "POST",
            f"/v1/ocor-memory-transit/encrypt/{self._key}",
            {"plaintext": base64.b64encode(plaintext).decode(), **self._params(context)},
        )
        return SealedContent(f"urn:ocor:memory-key:transit:{self._key}", data["data"]["ciphertext"].encode())

    def open(self, *, context: Mapping[str, str], sealed: SealedContent) -> bytes:
        data = self._bao.call(
            "POST",
            f"/v1/ocor-memory-transit/decrypt/{self._key}",
            {"ciphertext": sealed.ciphertext.decode(), **self._params(context)},
        )
        return base64.b64decode(data["data"]["plaintext"])


def _layout_name(prefix: str, partition_digest: str, representation_version: str) -> str:
    return prefix + hashlib.sha256(f"{partition_digest}|{representation_version}".encode()).hexdigest()[:40]


class PostgresStores:
    """Metadata store, content store and full-text index on one PostgreSQL schema."""

    def __init__(self, dsn: str, schema: str) -> None:
        self.dsn = dsn
        self.schema = schema
        with psycopg.connect(dsn, autocommit=True) as conn:
            conn.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
            conn.execute(
                f'CREATE TABLE IF NOT EXISTS "{schema}".partitions (partition_digest text PRIMARY KEY, body text NOT NULL)'
            )
            conn.execute(
                f'CREATE TABLE IF NOT EXISTS "{schema}".versions ('
                "memory_item_id text NOT NULL, memory_version integer NOT NULL, "
                "partition_digest text NOT NULL REFERENCES "
                f'"{schema}".partitions(partition_digest), '
                "stage_digest text NOT NULL, body text NOT NULL, staged_at text NOT NULL, "
                "state text NOT NULL CHECK (state IN ('PENDING','COMMITTED')), committed_at text, "
                "PRIMARY KEY (memory_item_id, memory_version))"
            )
            conn.execute(
                f'CREATE TABLE IF NOT EXISTS "{schema}".pointers (store_ref text PRIMARY KEY, '
                "memory_item_id text NOT NULL, memory_version integer NOT NULL, body text NOT NULL, "
                "state text NOT NULL CHECK (state IN ('PENDING','COMMITTED')), "
                f'FOREIGN KEY (memory_item_id, memory_version) REFERENCES "{schema}".versions)'
            )
            conn.execute(
                f'CREATE TABLE IF NOT EXISTS "{schema}".heads (memory_item_id text PRIMARY KEY, head_version integer NOT NULL)'
            )
            conn.execute(
                f'CREATE TABLE IF NOT EXISTS "{schema}".content (object_ref text PRIMARY KEY, '
                "partition_digest text NOT NULL, key_ref text NOT NULL, ciphertext bytea NOT NULL)"
            )
            conn.execute(
                f'CREATE TABLE IF NOT EXISTS "{schema}".lexical_layouts (table_name text PRIMARY KEY, '
                "partition_digest text NOT NULL, representation_version text NOT NULL, configuration text NOT NULL)"
            )

    def connect(self) -> psycopg.Connection[Any]:
        return psycopg.connect(self.dsn)

    # -- MemoryMetadataStore -------------------------------------------------

    def _row(self, row: tuple[str, str, str, str | None]) -> StoredVersion:
        body, staged_at, state, committed_at = row
        return StoredVersion(StagedVersion.from_body(json.loads(body), staged_at), VersionState(state), committed_at)

    def stage(self, staged: StagedVersion) -> StoredVersion:
        s = self.schema
        with self.connect() as conn, conn.transaction():
            conn.execute(
                f'INSERT INTO "{s}".partitions VALUES (%s, %s) ON CONFLICT DO NOTHING',
                (staged.partition.digest, canonical_bytes(staged.partition.to_mapping()).decode()),
            )
            inserted = conn.execute(
                f'INSERT INTO "{s}".versions VALUES (%s, %s, %s, %s, %s, %s, %s, NULL) ON CONFLICT DO NOTHING RETURNING 1',
                (
                    staged.memory_item_id, staged.memory_version, staged.partition.digest, staged.stage_digest,
                    canonical_bytes(staged.body()).decode(), staged.staged_at, "PENDING",
                ),
            ).fetchone()
            if inserted is None:
                row = conn.execute(
                    f'SELECT stage_digest, body, staged_at, state, committed_at FROM "{s}".versions '
                    "WHERE memory_item_id = %s AND memory_version = %s FOR SHARE",
                    (staged.memory_item_id, staged.memory_version),
                ).fetchone()
                assert row is not None
                if row[0] != staged.stage_digest:
                    raise stage_conflict(staged.memory_version_ref)
                return self._row(row[1:])
            for pointer in staged.pointers:
                conn.execute(
                    f'INSERT INTO "{s}".pointers VALUES (%s, %s, %s, %s, %s)',
                    (pointer.store_ref, staged.memory_item_id, staged.memory_version,
                     canonical_bytes(pointer.to_mapping()).decode(), "PENDING"),
                )
        return StoredVersion(staged, VersionState.PENDING, None)

    def get(self, memory_item_id: str, memory_version: int) -> StoredVersion | None:
        with self.connect() as conn:
            row = conn.execute(
                f'SELECT body, staged_at, state, committed_at FROM "{self.schema}".versions '
                "WHERE memory_item_id = %s AND memory_version = %s",
                (memory_item_id, memory_version),
            ).fetchone()
        return None if row is None else self._row(row)

    def commit(self, memory_item_id: str, memory_version: int, *, stage_digest: str, committed_at: str) -> StoredVersion:
        s = self.schema
        with self.connect() as conn, conn.transaction():
            row = conn.execute(
                f'SELECT stage_digest, body, staged_at, state, committed_at FROM "{s}".versions '
                "WHERE memory_item_id = %s AND memory_version = %s FOR UPDATE",
                (memory_item_id, memory_version),
            ).fetchone()
            if row is None or row[0] != stage_digest:
                raise stage_conflict(memory_version_ref(memory_item_id, memory_version))
            if row[3] == "COMMITTED":
                return self._row(row[1:])
            conn.execute(f'INSERT INTO "{s}".heads VALUES (%s, 0) ON CONFLICT DO NOTHING', (memory_item_id,))
            head = conn.execute(
                f'SELECT head_version FROM "{s}".heads WHERE memory_item_id = %s FOR UPDATE', (memory_item_id,)
            ).fetchone()
            assert head is not None
            if head[0] != memory_version - 1:
                raise predecessor_not_committed(memory_version_ref(memory_item_id, memory_version))
            conn.execute(
                f'UPDATE "{s}".versions SET state = %s, committed_at = %s WHERE memory_item_id = %s AND memory_version = %s',
                ("COMMITTED", committed_at, memory_item_id, memory_version),
            )
            conn.execute(
                f'UPDATE "{s}".pointers SET state = %s WHERE memory_item_id = %s AND memory_version = %s',
                ("COMMITTED", memory_item_id, memory_version),
            )
            conn.execute(
                f'UPDATE "{s}".heads SET head_version = %s WHERE memory_item_id = %s', (memory_version, memory_item_id)
            )
            committed = conn.execute(
                f'SELECT body, staged_at, state, committed_at FROM "{s}".versions '
                "WHERE memory_item_id = %s AND memory_version = %s",
                (memory_item_id, memory_version),
            ).fetchone()
        assert committed is not None
        return self._row(committed)

    def head(self, memory_item_id: str) -> int:
        with self.connect() as conn:
            row = conn.execute(
                f'SELECT head_version FROM "{self.schema}".heads WHERE memory_item_id = %s', (memory_item_id,)
            ).fetchone()
        return 0 if row is None else int(row[0])

    def pointer(self, store_ref: str) -> tuple[RepresentationPointer, VersionState] | None:
        with self.connect() as conn:
            row = conn.execute(
                f'SELECT body, state FROM "{self.schema}".pointers WHERE store_ref = %s', (store_ref,)
            ).fetchone()
        if row is None:
            return None
        return RepresentationPointer.from_mapping(json.loads(row[0])), VersionState(row[1])

    def versions_in(self, partition_digest: str) -> tuple[StoredVersion, ...]:
        with self.connect() as conn:
            rows = conn.execute(
                f'SELECT body, staged_at, state, committed_at FROM "{self.schema}".versions '
                "WHERE partition_digest = %s ORDER BY memory_item_id, memory_version",
                (partition_digest,),
            ).fetchall()
        return tuple(self._row(row) for row in rows)

    def partitions(self) -> tuple[MemoryPartition, ...]:
        with self.connect() as conn:
            rows = conn.execute(f'SELECT body FROM "{self.schema}".partitions ORDER BY partition_digest').fetchall()
        return tuple(MemoryPartition.from_mapping(json.loads(row[0])) for row in rows)


class PostgresContentStore:
    def __init__(self, stores: PostgresStores) -> None:
        self._s = stores

    def put(self, object_ref: str, partition_digest: str, sealed: SealedContent) -> None:
        with self._s.connect() as conn:
            conn.execute(
                f'INSERT INTO "{self._s.schema}".content VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING',
                (object_ref, partition_digest, sealed.key_ref, sealed.ciphertext),
            )

    def get(self, object_ref: str) -> SealedContent | None:
        with self._s.connect() as conn:
            row = conn.execute(
                f'SELECT key_ref, ciphertext FROM "{self._s.schema}".content WHERE object_ref = %s', (object_ref,)
            ).fetchone()
        return None if row is None else SealedContent(row[0], bytes(row[1]))

    def delete(self, object_ref: str) -> None:
        with self._s.connect() as conn:
            conn.execute(f'DELETE FROM "{self._s.schema}".content WHERE object_ref = %s', (object_ref,))

    def refs(self, partition_digest: str) -> tuple[str, ...]:
        with self._s.connect() as conn:
            rows = conn.execute(
                f'SELECT object_ref FROM "{self._s.schema}".content WHERE partition_digest = %s ORDER BY object_ref',
                (partition_digest,),
            ).fetchall()
        return tuple(row[0] for row in rows)


class PostgresLexicalIndex:
    """One physical table per partition and lexical representation version."""

    def __init__(self, stores: PostgresStores) -> None:
        self._s = stores

    def table(self, partition: MemoryPartition, representation_version: str) -> str:
        return _layout_name("lex_", partition.digest, representation_version)

    def _layout(self, conn: psycopg.Connection[Any], table: str) -> str | None:
        row = conn.execute(
            f'SELECT configuration FROM "{self._s.schema}".lexical_layouts WHERE table_name = %s', (table,)
        ).fetchone()
        return None if row is None else str(row[0])

    def upsert(self, partition: MemoryPartition, profile: LexicalProfile, store_ref: str, payload: Mapping[str, object], document: str) -> None:
        s, table = self._s.schema, self.table(partition, profile.representation_version)
        with self._s.connect() as conn, conn.transaction():
            conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"{s}.{table}",))
            if self._layout(conn, table) is None:
                conn.execute(
                    f'CREATE TABLE "{s}"."{table}" (store_ref text PRIMARY KEY, payload text NOT NULL, '
                    "document text NOT NULL, tsv tsvector NOT NULL)"
                )
                conn.execute(f'CREATE INDEX "{table}_tsv" ON "{s}"."{table}" USING GIN (tsv)')
                conn.execute(
                    f'INSERT INTO "{s}".lexical_layouts VALUES (%s, %s, %s, %s)',
                    (table, partition.digest, profile.representation_version, profile.text_search_configuration),
                )
            conn.execute(
                f'INSERT INTO "{s}"."{table}" VALUES (%s, %s, %s, to_tsvector(%s::regconfig, %s)) '
                "ON CONFLICT (store_ref) DO NOTHING",
                (store_ref, canonical_bytes(dict(payload)).decode(), document,
                 profile.text_search_configuration, document),
            )

    def search(self, partition: MemoryPartition, representation_version: str, query: str, *, limit: int, offset: int) -> Sequence[IndexHit]:
        s, table = self._s.schema, self.table(partition, representation_version)
        with self._s.connect() as conn:
            config = self._layout(conn, table)
            if config is None:
                return []
            rows = conn.execute(
                f'SELECT store_ref, payload, ts_rank_cd(tsv, q) AS score FROM "{s}"."{table}", '
                "plainto_tsquery(%s::regconfig, %s) AS q WHERE tsv @@ q "
                "ORDER BY score DESC, store_ref ASC LIMIT %s OFFSET %s",
                (config, query, limit, offset),
            ).fetchall()
        return [IndexHit(row[0], json.loads(row[1]), float(row[2])) for row in rows]

    def get(self, partition: MemoryPartition, representation_version: str, store_ref: str) -> Mapping[str, object] | None:
        s, table = self._s.schema, self.table(partition, representation_version)
        with self._s.connect() as conn:
            if self._layout(conn, table) is None:
                return None
            row = conn.execute(f'SELECT payload FROM "{s}"."{table}" WHERE store_ref = %s', (store_ref,)).fetchone()
        return None if row is None else json.loads(row[0])

    def entries(self, partition: MemoryPartition, representation_version: str) -> Sequence[IndexHit]:
        s, table = self._s.schema, self.table(partition, representation_version)
        with self._s.connect() as conn:
            if self._layout(conn, table) is None:
                return []
            rows = conn.execute(f'SELECT store_ref, payload FROM "{s}"."{table}" ORDER BY store_ref').fetchall()
        return [IndexHit(row[0], json.loads(row[1]), 0.0) for row in rows]

    def remove(self, partition: MemoryPartition, representation_version: str, store_ref: str) -> None:
        s, table = self._s.schema, self.table(partition, representation_version)
        with self._s.connect() as conn:
            if self._layout(conn, table) is not None:
                conn.execute(f'DELETE FROM "{s}"."{table}" WHERE store_ref = %s', (store_ref,))


class QdrantVectorIndex:
    """One Qdrant collection per partition and vector representation version."""

    def __init__(self, endpoint: str, namespace: str) -> None:
        self.endpoint = endpoint
        self.namespace = namespace

    def collection(self, partition: MemoryPartition, representation_version: str) -> str:
        return _layout_name(f"ocor_{self.namespace}_", partition.digest, representation_version)

    @staticmethod
    def point_id(store_ref: str) -> str:
        return str(uuid.UUID(hashlib.sha256(store_ref.encode()).hexdigest()[:32]))

    def _call(self, method: str, path: str, body: Any | None = None) -> tuple[int, Any]:
        return _http(method, f"{self.endpoint}{path}", body, timeout=3.0)

    def _require(self, status: int, what: str) -> None:
        if status != 200:
            raise RuntimeError(f"Qdrant {what} -> {status}")

    def upsert(self, partition: MemoryPartition, profile: VectorProfile, store_ref: str, payload: Mapping[str, object], vector: Sequence[float]) -> None:
        name = self.collection(partition, profile.representation_version)
        status, _ = self._call("GET", f"/collections/{name}")
        if status == 404:
            status, _ = self._call(
                "PUT", f"/collections/{name}", {"vectors": {"size": profile.embedding_dimensions, "distance": "Cosine"}}
            )
            if status != 200:
                # A concurrent creator may have won the race; the collection must now exist.
                status, _ = self._call("GET", f"/collections/{name}")
                self._require(status, "create collection")
        else:
            self._require(status, "get collection")
        status, _ = self._call(
            "PUT",
            f"/collections/{name}/points?wait=true",
            {"points": [{"id": self.point_id(store_ref), "vector": list(vector), "payload": {"store_ref": store_ref, "pointer": dict(payload)}}]},
        )
        self._require(status, "upsert")

    UNBOUND_POINT = "urn:ocor:unbound-point:"

    def _hits(self, points: Sequence[Mapping[str, Any]]) -> list[IndexHit]:
        hits = []
        for point in points:
            payload = point.get("payload") or {}
            store_ref = payload.get("store_ref")
            # A point not stored under its own ref's id is addressed by raw id so
            # that reconciliation can still remove it.
            if not isinstance(store_ref, str) or self.point_id(store_ref) != str(point["id"]):
                store_ref = self.UNBOUND_POINT + str(point["id"])
            pointer = payload.get("pointer")
            hits.append(IndexHit(store_ref, pointer if isinstance(pointer, dict) else {}, float(point.get("score", 0.0))))
        return hits

    def search(self, partition: MemoryPartition, representation_version: str, vector: Sequence[float], *, limit: int, offset: int) -> Sequence[IndexHit]:
        name = self.collection(partition, representation_version)
        status, data = self._call(
            "POST", f"/collections/{name}/points/query",
            {"query": list(vector), "limit": limit, "offset": offset, "with_payload": True, "with_vector": False},
        )
        if status == 404:
            return []
        self._require(status, "query")
        return self._hits(data["result"]["points"])

    def get(self, partition: MemoryPartition, representation_version: str, store_ref: str) -> Mapping[str, object] | None:
        name = self.collection(partition, representation_version)
        status, data = self._call("GET", f"/collections/{name}/points/{self.point_id(store_ref)}")
        if status == 404:
            return None
        self._require(status, "get point")
        payload = data["result"]["payload"]
        return payload["pointer"] if payload.get("store_ref") == store_ref else None

    def entries(self, partition: MemoryPartition, representation_version: str) -> Sequence[IndexHit]:
        name = self.collection(partition, representation_version)
        status, data = self._call("POST", f"/collections/{name}/points/scroll", {"limit": 10000, "with_payload": True})
        if status == 404:
            return []
        self._require(status, "scroll")
        return self._hits(data["result"]["points"])

    def remove(self, partition: MemoryPartition, representation_version: str, store_ref: str) -> None:
        name = self.collection(partition, representation_version)
        point = store_ref.removeprefix(self.UNBOUND_POINT) if store_ref.startswith(self.UNBOUND_POINT) else self.point_id(store_ref)
        status, _ = self._call("POST", f"/collections/{name}/points/delete?wait=true", {"points": [point]})
        if status != 404:
            self._require(status, "delete")

    def count(self, partition: MemoryPartition, representation_version: str) -> int:
        name = self.collection(partition, representation_version)
        status, data = self._call("POST", f"/collections/{name}/points/count", {"exact": True})
        if status == 404:
            return 0
        self._require(status, "count")
        return int(data["result"]["count"])

    def collections(self) -> list[str]:
        status, data = self._call("GET", "/collections")
        self._require(status, "list collections")
        return sorted(c["name"] for c in data["result"]["collections"] if c["name"].startswith(f"ocor_{self.namespace}_"))


class OffsetClock:
    """Store-side boundary clock: the admission clock plus a test-controlled offset."""

    def __init__(self, base: InMemoryTrustedClock) -> None:
        self._base = base
        self.offset = timedelta(0)

    def now(self) -> datetime:
        return self._base.now() + self.offset


@dataclass
class Stack:
    postgres: PostgresStores
    content: PostgresContentStore
    lexical: PostgresLexicalIndex
    vector: QdrantVectorIndex
    cipher: OpenBaoTransitCipher
    qdrant: QdrantHarness
    bao: OpenBaoHarness
    admission: Admission = field(default_factory=Admission)
    clock: OffsetClock = field(init=False)

    def __post_init__(self) -> None:
        self.clock = OffsetClock(self.admission.clock)

    @contextlib.contextmanager
    def later(self, delta: timedelta) -> Iterator[None]:
        self.clock.offset = delta
        try:
            yield
        finally:
            self.clock.offset = timedelta(0)

    def coordinator(self, *, metadata: Any | None = None, **limits: Any) -> MemoryStoreCoordinator:
        return MemoryStoreCoordinator(
            ledger=self.admission.ledger,
            metadata=metadata if metadata is not None else self.postgres,
            content=self.content,
            cipher=self.cipher,
            lexical=self.lexical,
            vector=self.vector,
            clock=self.clock,
            limits=StoreLimits(**limits),
        )

    def fresh_coordinator(self) -> MemoryStoreCoordinator:
        """New adapter instances and connections over the same backends (new run)."""

        postgres = PostgresStores(self.postgres.dsn, self.postgres.schema)
        return MemoryStoreCoordinator(
            ledger=self.admission.ledger,
            metadata=postgres,
            content=PostgresContentStore(postgres),
            cipher=OpenBaoTransitCipher(self.bao),
            lexical=PostgresLexicalIndex(postgres),
            vector=QdrantVectorIndex(self.vector.endpoint, self.vector.namespace),
            clock=self.clock,
        )

    def sql(self, statement: str, params: Sequence[Any] = ()) -> list[tuple[Any, ...]]:
        with self.postgres.connect() as conn:
            cursor = conn.execute(statement.replace("{s}", f'"{self.postgres.schema}"'), params)
            return cursor.fetchall() if cursor.description else []

    def lexical_rows(self, partition: MemoryPartition) -> list[tuple[Any, ...]]:
        table = self.lexical.table(partition, LexicalProfile().representation_version)
        if not self.sql("SELECT 1 FROM {s}.lexical_layouts WHERE table_name = %s", (table,)):
            return []
        return self.sql(f'SELECT store_ref, payload FROM {{s}}."{table}" ORDER BY store_ref')


@pytest.fixture(scope="module")
def stack() -> Iterator[Stack]:
    dsn = os.environ.get("OCOR_LIVE_POSTGRES_DSN")
    if not dsn:
        pytest.fail("OCOR_LIVE_POSTGRES_DSN is mandatory qualifying evidence (real PostgreSQL)")
    schema = f"ocor_t0051_{uuid.uuid4().hex[:12]}"
    qdrant = QdrantHarness.provision()
    bao: OpenBaoHarness | None = None
    try:
        bao = OpenBaoHarness.provision()
        postgres = PostgresStores(dsn, schema)
        yield Stack(
            postgres=postgres,
            content=PostgresContentStore(postgres),
            lexical=PostgresLexicalIndex(postgres),
            vector=QdrantVectorIndex(qdrant.endpoint, schema),
            cipher=OpenBaoTransitCipher(bao),
            qdrant=qdrant,
            bao=bao,
        )
    finally:
        try:
            with psycopg.connect(dsn, autocommit=True) as conn:
                conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        finally:
            try:
                if bao is not None:
                    bao.destroy()
            finally:
                qdrant.destroy()


def assert_store_error(action: Any, reason: str, detail: str) -> MemoryStoreError:
    with pytest.raises(MemoryStoreError) as caught:
        action()
    assert (caught.value.reason_code, caught.value.detail_code) == (reason, detail), caught.value
    return caught.value


def counts(stack: Stack) -> dict[str, int]:
    tables = [row[0] for row in stack.sql("SELECT table_name FROM {s}.lexical_layouts")]
    lexical = sum(stack.sql(f'SELECT count(*) FROM {{s}}."{t}"')[0][0] for t in tables)
    vectors = 0
    for name in stack.vector.collections():
        status, data = _http("POST", f"{stack.vector.endpoint}/collections/{name}/points/count", {"exact": True})
        assert status == 200
        vectors += int(data["result"]["count"])
    return {
        "versions": stack.sql("SELECT count(*) FROM {s}.versions")[0][0],
        "pointers": stack.sql("SELECT count(*) FROM {s}.pointers")[0][0],
        "content": stack.sql("SELECT count(*) FROM {s}.content")[0][0],
        "lexical": lexical,
        "vector": vectors,
    }


def test_qualifying_backends_are_real_and_pinned(stack: Stack) -> None:
    assert QDRANT_IMAGE.endswith(LOCKED_IMAGES["qdrant"].split("@", 1)[1])
    assert _docker("inspect", stack.qdrant.container, "--format", "{{.Config.Image}}") == QDRANT_IMAGE
    assert _docker("inspect", stack.bao.container, "--format", "{{.Config.Image}}") == LOCKED_IMAGES["openbao"]
    status, data = _http("GET", f"{stack.bao.endpoint}/v1/sys/health")
    assert status == 200 and str(data["version"]).startswith("2.6.2")
    version = stack.sql("SHOW server_version")[0][0]
    assert version.startswith("16."), version


def test_commit_writes_metadata_content_lexical_and_vector_with_bound_pointers(stack: Stack) -> None:
    record, payload, vector = stack.admission.admit("mem-commit", "pump P-101 vibration exceeded threshold")
    receipt = stack.coordinator().commit(record, payload=payload, embedding=vector)
    partition = partition_of(record)
    assert receipt.state == "COMMITTED" and receipt.head_version == 1
    assert receipt.partition_ref == partition.ref
    # The receipt links to the admission audit event, which carries the correlation id.
    assert receipt.audit_ref == record.receipt.audit_ref
    assert record.audit_event["correlation_id"] == CORRELATION
    assert sorted(kind for kind, _, _ in receipt.representations) == ["FULL_TEXT", "STRUCTURED", "VECTOR"]
    assert all(ref.startswith("urn:ocor:memory-representation:") for _, _, ref in receipt.representations)

    # Metadata: the version and all three pointers are COMMITTED in one record set.
    rows = stack.sql(
        "SELECT state, partition_digest FROM {s}.versions WHERE memory_item_id = %s", ("mem-commit",)
    )
    assert rows == [("COMMITTED", partition.digest)]
    pointer_rows = stack.sql("SELECT store_ref, body, state FROM {s}.pointers WHERE memory_item_id = %s", ("mem-commit",))
    assert {row[2] for row in pointer_rows} == {"COMMITTED"} and len(pointer_rows) == 3
    pointers = {json.loads(row[1])["representation_kind"]: json.loads(row[1]) for row in pointer_rows}

    # Content: encrypted at rest, content-addressed inside the partition.
    obj = stack.sql("SELECT object_ref, partition_digest, ciphertext FROM {s}.content WHERE object_ref = %s", (receipt.content_object_ref,))
    assert len(obj) == 1 and obj[0][1] == partition.digest
    assert obj[0][0] == content_object_ref(partition, record.item.content_digest)
    ciphertext = bytes(obj[0][2])
    assert payload not in ciphertext and b"vibration" not in ciphertext and ciphertext.startswith(b"vault:v1:")

    # Every index entry carries the exact pointer (change-control §7 fields).
    required = {"memory_version_ref", "content_digest", "representation_digest", "classification_marking_ref",
                "policy_bundle_digest", "memory_scope", "deletion_epoch"}
    lexical = stack.lexical_rows(partition)
    assert [json.loads(row[1]) for row in lexical] == [pointers["FULL_TEXT"]]
    point = stack.vector.get(partition, pointers["VECTOR"]["representation_version"], RepresentationPointer.from_mapping(pointers["VECTOR"]).store_ref)
    assert point == pointers["VECTOR"]
    for pointer in pointers.values():
        assert required <= set(pointer)
        assert pointer["memory_version_ref"] == record.item.version_ref
        assert pointer["item_digest"] == record.item_digest
        assert pointer["partition_digest"] == partition.digest
    assert pointers["VECTOR"]["representation_digest"] == record.item.embedding_digest
    assert pointers["VECTOR"]["representation_version"] == VectorProfile.for_item(record.item).representation_version
    assert pointers["FULL_TEXT"]["representation_version"] == LexicalProfile().representation_version

    # Materialisation: exact item and payload; both indexes return the bound version.
    materialized = stack.coordinator().read_version(partition, "mem-commit", 1)
    assert materialized.payload == payload and materialized.item == record.item
    lexical_hits = stack.coordinator().lexical_candidates(partition, "vibration threshold", limit=5)
    assert [hit.memory_version_ref for hit in lexical_hits] == [record.item.version_ref]
    vector_hits = stack.coordinator().vector_candidates(partition, VectorProfile.for_item(record.item), vector or [], limit=5)
    assert [hit.memory_version_ref for hit in vector_hits] == [record.item.version_ref]
    assert vector_hits[0].score > 0.99
    # Backend identifiers never cross the port: no Qdrant point id or table name in results.
    exposed = json.dumps([dataclasses.asdict(hit) for hit in (*lexical_hits, *vector_hits)])
    assert QdrantVectorIndex.point_id(vector_hits[0].store_ref) not in exposed
    assert stack.lexical.table(partition, LexicalProfile().representation_version) not in exposed


def test_versions_advance_a_versioned_head_pointer_and_history_stays_exact(stack: Stack) -> None:
    coordinator = stack.coordinator()
    v1, p1, e1 = stack.admission.admit("mem-ver", "valve V-7 inspected and sealed")
    coordinator.commit(v1, payload=p1, embedding=e1)
    v2, p2, e2 = stack.admission.admit("mem-ver", "valve V-7 inspected; seal replaced", version=2)
    v3, p3, e3 = stack.admission.admit("mem-ver", "valve V-7 seal replaced and pressure tested", version=3)
    partition = partition_of(v1)

    # v3 cannot become visible before v2: the head pointer only advances by one.
    assert_store_error(lambda: coordinator.commit(v3, payload=p3, embedding=e3), "REPRESENTATION_NOT_READY", "PREDECESSOR_NOT_COMMITTED")
    assert stack.postgres.head("mem-ver") == 1
    assert_store_error(lambda: coordinator.read_version(partition, "mem-ver", 3), "REPRESENTATION_NOT_READY", "VERSION_NOT_COMMITTED")
    assert all("v3" not in hit.memory_version_ref for hit in coordinator.lexical_candidates(partition, "pressure tested", limit=5))

    r2 = coordinator.commit(v2, payload=p2, embedding=e2)
    r3 = coordinator.commit(v3, payload=p3, embedding=e3)
    assert (r2.head_version, r3.head_version) == (2, 3)
    assert coordinator.read_latest(partition, "mem-ver").item.memory_version == 3
    assert coordinator.read_version(partition, "mem-ver", 1).payload == p1
    assert coordinator.read_version(partition, "mem-ver", 2).item.supersedes_ref == v1.item.version_ref
    refs = [set(ref for _, _, ref in r.representations) for r in (r2, r3)]
    assert refs[0].isdisjoint(refs[1])
    assert stack.sql("SELECT memory_version, state FROM {s}.versions WHERE memory_item_id = %s ORDER BY 1", ("mem-ver",)) == [
        (1, "COMMITTED"), (2, "COMMITTED"), (3, "COMMITTED")]


def test_compartment_partitions_are_physically_and_logically_isolated(stack: Stack) -> None:
    coordinator = stack.coordinator()
    alpha, pa, ea = stack.admission.admit("mem-alpha", "convoy route Kilo blocked by flooding", compartment="golf")
    bravo, pb, eb = stack.admission.admit("mem-bravo", "convoy route Kilo blocked by flooding", compartment="hotel")
    coordinator.commit(alpha, payload=pa, embedding=ea)
    coordinator.commit(bravo, payload=pb, embedding=eb)
    part_a, part_b = partition_of(alpha), partition_of(bravo)
    assert part_a.digest != part_b.digest and part_a.compartments == ("golf",)

    # Physically separate content objects, lexical tables and vector collections.
    assert content_object_ref(part_a, alpha.item.content_digest) != content_object_ref(part_b, bravo.item.content_digest)
    version = LexicalProfile().representation_version
    assert stack.lexical.table(part_a, version) != stack.lexical.table(part_b, version)
    vector_version = VectorProfile.for_item(alpha.item).representation_version
    assert stack.vector.collection(part_a, vector_version) != stack.vector.collection(part_b, vector_version)
    assert stack.vector.count(part_a, vector_version) == 1 and stack.vector.count(part_b, vector_version) == 1

    # Identical text and identical vector: each partition sees only its own item.
    for part, item in ((part_a, alpha), (part_b, bravo)):
        lex = coordinator.lexical_candidates(part, "convoy flooding", limit=10)
        vec = coordinator.vector_candidates(part, VectorProfile.for_item(item.item), ea or [], limit=10)
        assert [h.memory_version_ref for h in lex] == [item.item.version_ref]
        assert [h.memory_version_ref for h in vec] == [item.item.version_ref]
    assert coordinator.committed_count(part_a) == 1

    # Out-of-partition reads are indistinguishable from absent versions.
    foreign = assert_store_error(lambda: coordinator.read_version(part_a, "mem-bravo", 1), "MEMORY_VERSION_NOT_FOUND", "VERSION_NOT_VISIBLE")
    absent = assert_store_error(lambda: coordinator.read_version(part_a, "mem-nonexistent", 1), "MEMORY_VERSION_NOT_FOUND", "VERSION_NOT_VISIBLE")
    assert foreign.to_problem() == absent.to_problem() and str(foreign) == str(absent)
    assert_store_error(lambda: coordinator.read_latest(part_a, "mem-bravo"), "MEMORY_VERSION_NOT_FOUND", "VERSION_NOT_VISIBLE")

    # A ciphertext moved into another partition's address does not open there.
    sealed = stack.content.get(content_object_ref(part_b, bravo.item.content_digest))
    assert sealed is not None
    context_a = {"content_object_ref": content_object_ref(part_a, alpha.item.content_digest),
                 "partition_digest": part_a.digest, "content_digest": alpha.item.content_digest}
    with pytest.raises(RuntimeError):
        stack.cipher.open(context=context_a, sealed=sealed)


def test_scope_owner_bindings_partition_otherwise_identical_items(stack: Stack) -> None:
    coordinator = stack.coordinator()
    one, p1, e1 = stack.admission.admit("mem-agent-1", "telemetry gap on relay R-4", vector=False, scope="AGENT", scope_fields={"agent_id": "agent-1"})
    two, p2, _ = stack.admission.admit("mem-agent-2", "telemetry gap on relay R-4", vector=False, scope="AGENT", scope_fields={"agent_id": "agent-2"})
    coordinator.commit(one, payload=p1)
    coordinator.commit(two, payload=p2)
    for record in (one, two):
        hits = coordinator.lexical_candidates(partition_of(record), "relay telemetry", limit=10)
        assert [h.memory_version_ref for h in hits] == [record.item.version_ref]
    assert e1 is None


def test_committed_versions_are_durable_across_fresh_adapters(stack: Stack) -> None:
    record, payload, vector = stack.admission.admit("mem-durable", "generator G-2 fuel at 40 percent")
    stack.coordinator().commit(record, payload=payload, embedding=vector)
    fresh = stack.fresh_coordinator()
    partition = partition_of(record)
    assert fresh.read_version(partition, "mem-durable", 1).payload == payload
    assert [h.memory_version_ref for h in fresh.lexical_candidates(partition, "generator fuel", limit=3)] == [record.item.version_ref]


def test_recommit_is_idempotent_and_concurrent_commits_converge(stack: Stack) -> None:
    record, payload, vector = stack.admission.admit("mem-idem", "bridge B-9 load limit reduced to 20 tonnes")
    results: list[Any] = []

    def worker() -> None:
        try:
            results.append(stack.fresh_coordinator().commit(record, payload=payload, embedding=vector))
        except Exception as exc:  # noqa: BLE001 -- the assertion below inspects every outcome
            results.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(60)
    receipts = [r for r in results if not isinstance(r, Exception)]
    assert len(receipts) == 4, results
    assert len({json.dumps(r.to_mapping(), sort_keys=True) for r in receipts}) == 1
    before = counts(stack)
    again = stack.coordinator().commit(record, payload=payload, embedding=vector)
    assert again == receipts[0]
    assert counts(stack) == before
    partition = partition_of(record)
    assert len(stack.sql("SELECT 1 FROM {s}.versions WHERE memory_item_id = %s", ("mem-idem",))) == 1
    assert len([row for row in stack.lexical_rows(partition) if "mem-idem" in row[1]]) == 1


def test_a_different_representation_for_a_committed_version_is_a_stage_conflict(stack: Stack) -> None:
    record, payload, vector = stack.admission.admit("mem-profile", "antenna mast A-3 realigned")
    stack.coordinator().commit(record, payload=payload, embedding=vector)
    before = counts(stack)
    upgraded = stack.coordinator(lexical_profile=LexicalProfile(version=2))
    assert_store_error(lambda: upgraded.commit(record, payload=payload, embedding=vector), "MEMORY_IDEMPOTENCY_CONFLICT", "STAGE_CONFLICT")
    assert counts(stack) == before


def test_rejected_commits_never_reach_any_real_backend(stack: Stack) -> None:
    record, payload, vector = stack.admission.admit("mem-reject", "water tank T-1 contamination check")
    before = counts(stack)
    assert vector is not None
    coordinator = stack.coordinator()
    assert_store_error(lambda: coordinator.commit(record, payload=payload + b" ", embedding=vector), "MEMORY_SCHEMA_INVALID", "CONTENT_DIGEST_MISMATCH")
    assert_store_error(lambda: coordinator.commit(record, payload=payload, embedding=[v * 0.5 for v in vector]), "MEMORY_SCHEMA_INVALID", "EMBEDDING_DIGEST_MISMATCH")
    assert_store_error(lambda: coordinator.commit(record, payload=payload), "MEMORY_SCHEMA_INVALID", "EMBEDDING_MISSING")
    assert counts(stack) == before


def test_vector_outage_leaves_a_pending_non_queryable_version_that_is_reconciled(stack: Stack) -> None:
    record, payload, vector = stack.admission.admit("mem-outage", "checkpoint Lima reports unidentified drone", compartment="juliet")
    partition = partition_of(record)
    coordinator = stack.coordinator(reconcile_grace=timedelta(minutes=5))
    baseline = coordinator.committed_count(partition)
    _docker("pause", stack.qdrant.container)
    try:
        assert_store_error(lambda: coordinator.commit(record, payload=payload, embedding=vector), "REPRESENTATION_NOT_READY", "STORE_COMMIT_INCOMPLETE")
    finally:
        _docker("unpause", stack.qdrant.container)

    # Partial store visibility: metadata PENDING, content and lexical entry physically present.
    assert stack.sql("SELECT state FROM {s}.versions WHERE memory_item_id = %s", ("mem-outage",)) == [("PENDING",)]
    staged = stack.postgres.get("mem-outage", 1)
    assert staged is not None
    assert stack.content.get(staged.staged.content_object_ref) is not None
    lexical_ref = next(p.store_ref for p in staged.staged.pointers if p.representation_kind.value == "FULL_TEXT")
    assert lexical_ref in [row[0] for row in stack.lexical_rows(partition)]
    # ...and nothing of it is queryable, countable or materialisable.
    assert coordinator.lexical_candidates(partition, "unidentified drone", limit=5) == ()
    assert coordinator.committed_count(partition) == baseline
    assert_store_error(lambda: coordinator.read_version(partition, "mem-outage", 1), "REPRESENTATION_NOT_READY", "VERSION_NOT_COMMITTED")
    assert_store_error(lambda: coordinator.read_latest(partition, "mem-outage"), "MEMORY_VERSION_NOT_FOUND", "VERSION_NOT_VISIBLE")

    # Inside the grace window an in-flight commit is protected from reconciliation.
    early = coordinator.reconcile()
    assert record.item.version_ref in early.deferred and lexical_ref not in early.unbound_removed
    with stack.later(timedelta(minutes=6)):
        report = coordinator.reconcile()
    assert record.item.version_ref in report.retracted
    assert staged.staged.content_object_ref in report.content_removed
    assert lexical_ref not in [row[0] for row in stack.lexical_rows(partition)]
    assert stack.content.get(staged.staged.content_object_ref) is None

    # A retried commit after recovery completes and becomes visible.
    receipt = coordinator.commit(record, payload=payload, embedding=vector)
    assert receipt.state == "COMMITTED"
    assert coordinator.read_version(partition, "mem-outage", 1).payload == payload
    assert [h.memory_version_ref for h in coordinator.lexical_candidates(partition, "unidentified drone", limit=5)] == [record.item.version_ref]


class CrashBeforeMetadataCommit:
    """Real PostgreSQL metadata store whose process 'dies' before the visibility switch."""

    def __init__(self, inner: PostgresStores) -> None:
        self._inner = inner

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)

    def commit(self, *args: Any, **kwargs: Any) -> StoredVersion:
        raise ConnectionResetError("process terminated before the metadata commit")


def test_crash_before_the_visibility_switch_is_rolled_forward_by_reconciliation(stack: Stack) -> None:
    record, payload, vector = stack.admission.admit("mem-crash", "fuel convoy delayed at bridge crossing Echo", compartment="india")
    partition = partition_of(record)
    crashing = stack.coordinator(metadata=CrashBeforeMetadataCommit(stack.postgres))
    error = assert_store_error(lambda: crashing.commit(record, payload=payload, embedding=vector), "REPRESENTATION_NOT_READY", "STORE_COMMIT_INCOMPLETE")
    assert isinstance(error.__cause__, ConnectionResetError)
    stored = stack.postgres.get("mem-crash", 1)
    assert stored is not None and stored.state is VersionState.PENDING
    # All projections exist, yet none is queryable before the metadata switch.
    profile = VectorProfile.for_item(record.item)
    vector_ref = next(p.store_ref for p in stored.staged.pointers if p.representation_kind.value == "VECTOR")
    assert stack.vector.get(partition, profile.representation_version, vector_ref) is not None
    survivor = stack.fresh_coordinator()
    assert survivor.vector_candidates(partition, profile, vector or [], limit=5) == ()
    assert survivor.lexical_candidates(partition, "convoy Echo", limit=5) == ()
    assert_store_error(lambda: survivor.read_version(partition, "mem-crash", 1), "REPRESENTATION_NOT_READY", "VERSION_NOT_COMMITTED")

    with stack.later(timedelta(minutes=6)):
        report = survivor.reconcile()
    assert record.item.version_ref in report.completed
    assert vector_ref not in report.unbound_removed
    assert survivor.read_version(partition, "mem-crash", 1).payload == payload
    assert [h.memory_version_ref for h in survivor.vector_candidates(partition, profile, vector or [], limit=5)] == [record.item.version_ref]


def test_unbound_index_entries_never_occupy_result_slots_and_are_reconciled(stack: Stack) -> None:
    coordinator = stack.coordinator()
    records = []
    for n, text in enumerate(("sensor S-1 offline near ridge", "sensor S-2 offline near ridge", "sensor S-3 offline near ridge")):
        rec, pay, vec = stack.admission.admit(f"mem-bound-{n}", text, compartment="charlie")
        coordinator.commit(rec, payload=pay, embedding=vec)
        records.append((rec, vec))
    foreign, fpay, fvec = stack.admission.admit("mem-foreign-delta", "sensor offline near ridge", compartment="delta")
    coordinator.commit(foreign, payload=fpay, embedding=fvec)
    pending, ppay, pvec = stack.admission.admit("mem-pending-charlie", "sensor offline near ridge pending", compartment="charlie")
    partition = partition_of(records[0][0])
    profile = VectorProfile.for_item(records[0][0].item)
    version = profile.representation_version
    query = embed("forged probe outranking every bound entry")

    foreign_stored = stack.postgres.get("mem-foreign-delta", 1)
    assert foreign_stored is not None
    foreign_vector = next(p for p in foreign_stored.staged.pointers if p.representation_kind.value == "VECTOR")
    committed = stack.postgres.get("mem-bound-0", 1)
    assert committed is not None
    committed_vector = next(p for p in committed.staged.pointers if p.representation_kind.value == "VECTOR")
    committed_lexical = next(p for p in committed.staged.pointers if p.representation_kind.value == "FULL_TEXT")
    downgraded = {**committed_vector.to_mapping(), "classification_marking_ref": M_UNCLASSIFIED}
    pending_pointer = {**committed_vector.to_mapping(), "memory_version_ref": pending.item.version_ref}

    forged = [
        ("urn:forged:fabricated", {"memory_version_ref": "urn:ocor:memory:ghost:v1"}),
        (foreign_vector.store_ref, foreign_vector.to_mapping()),  # wrong partition
        (RepresentationPointer.from_mapping(downgraded).store_ref, downgraded),  # marking downgrade
        (RepresentationPointer.from_mapping(pending_pointer).store_ref, pending_pointer),  # never staged
    ]
    for ref, payload in forged:
        # Forged entries use the exact query vector, so they outrank every bound one.
        status, _ = _http(
            "PUT", f"{stack.vector.endpoint}/collections/{stack.vector.collection(partition, version)}/points?wait=true",
            {"points": [{"id": QdrantVectorIndex.point_id(ref), "vector": query, "payload": {"store_ref": ref, "pointer": payload}}]},
        )
        assert status == 200
    table = stack.lexical.table(partition, LexicalProfile().representation_version)
    tampered_lexical = {**committed_lexical.to_mapping(), "policy_bundle_digest": d("policy-bundle:other")}
    stack.sql(
        f'INSERT INTO {{s}}."{table}" VALUES (%s, %s, %s, to_tsvector(%s::regconfig, %s))',
        (committed_lexical.store_ref + ":shadow", json.dumps(tampered_lexical), "sensor offline ridge ridge ridge", "simple", "sensor offline ridge ridge ridge"),
    )

    raw = stack.vector.search(partition, version, query, limit=8, offset=0)
    assert {hit.store_ref for hit in raw[:4]} == {ref for ref, _ in forged}
    hits = coordinator.vector_candidates(partition, profile, query, limit=3)
    assert sorted(h.memory_version_ref for h in hits) == sorted(r.item.version_ref for r, _ in records)
    lexical_hits = coordinator.lexical_candidates(partition, "sensor offline ridge", limit=3)
    assert sorted(h.memory_version_ref for h in lexical_hits) == sorted(r.item.version_ref for r, _ in records)
    assert all(h.classification_marking_ref == M_RESTRICTED for h in (*hits, *lexical_hits))

    report = coordinator.reconcile()
    removed = set(report.unbound_removed)
    assert {ref for ref, _ in forged} <= removed
    assert committed_lexical.store_ref + ":shadow" in removed
    remaining = {hit.store_ref for hit in stack.vector.entries(partition, version)}
    assert remaining == {next(p.store_ref for p in stack.postgres.get(r.item.memory_item_id, 1).staged.pointers  # type: ignore[union-attr]
                              if p.representation_kind.value == "VECTOR") for r, _ in records}
    assert committed_lexical.store_ref + ":shadow" not in [row[0] for row in stack.lexical_rows(partition)]
    assert pvec is not None and ppay


def test_tampered_metadata_or_content_fails_closed(stack: Stack) -> None:
    coordinator = stack.coordinator()
    first, p1, e1 = stack.admission.admit("mem-tamper-1", "medical kit M-4 restocked", compartment="echo")
    second, p2, e2 = stack.admission.admit("mem-tamper-2", "medical kit M-5 expired items removed", compartment="echo")
    coordinator.commit(first, payload=p1, embedding=e1)
    coordinator.commit(second, payload=p2, embedding=e2)
    partition = partition_of(first)

    # Content swapped between two addresses of the same partition does not open.
    ref_1 = content_object_ref(partition, first.item.content_digest)
    ref_2 = content_object_ref(partition, second.item.content_digest)
    original = stack.sql("SELECT ciphertext FROM {s}.content WHERE object_ref = %s", (ref_2,))[0][0]
    stack.sql("UPDATE {s}.content SET ciphertext = (SELECT ciphertext FROM {s}.content WHERE object_ref = %s) WHERE object_ref = %s", (ref_1, ref_2))
    try:
        assert_store_error(lambda: coordinator.read_version(partition, "mem-tamper-2", 1), "INTERNAL_ERROR", "CONTENT_UNSEALABLE")
    finally:
        stack.sql("UPDATE {s}.content SET ciphertext = %s WHERE object_ref = %s", (original, ref_2))
    assert coordinator.read_version(partition, "mem-tamper-2", 1).payload == p2

    # Metadata rewritten in place is detected on read.
    body = stack.sql("SELECT body FROM {s}.versions WHERE memory_item_id = %s", ("mem-tamper-1",))[0][0]
    forged = json.loads(body)
    forged["item"]["confidence"] = 0.99
    stack.sql("UPDATE {s}.versions SET body = %s WHERE memory_item_id = %s", (json.dumps(forged), "mem-tamper-1"))
    try:
        with pytest.raises(MemoryStoreCorrupted):
            coordinator.read_version(partition, "mem-tamper-1", 1)
    finally:
        stack.sql("UPDATE {s}.versions SET body = %s WHERE memory_item_id = %s", (body, "mem-tamper-1"))
    assert coordinator.read_version(partition, "mem-tamper-1", 1).item == first.item


class AcknowledgeWithoutWriting(PostgresLexicalIndex):
    """Real PostgreSQL index whose upsert is acknowledged but never persisted."""

    def upsert(self, *args: Any, **kwargs: Any) -> None:
        return None


class PersistAnotherPointer(PostgresLexicalIndex):
    """Real PostgreSQL index that persists a different (downgraded) pointer."""

    def upsert(self, partition: MemoryPartition, profile: LexicalProfile, store_ref: str, payload: Mapping[str, object], document: str) -> None:
        super().upsert(partition, profile, store_ref, {**payload, "classification_marking_ref": M_UNCLASSIFIED}, document)


@pytest.mark.parametrize("index_type", [AcknowledgeWithoutWriting, PersistAnotherPointer], ids=["lost-write", "wrong-pointer"])
def test_an_acknowledgement_is_never_trusted_without_read_back(stack: Stack, index_type: type[PostgresLexicalIndex]) -> None:
    item_id = f"mem-ack-{index_type.__name__.lower()}"
    record, payload, vector = stack.admission.admit(item_id, f"ammunition depot inventory {index_type.__name__}", compartment="kilo")
    coordinator = MemoryStoreCoordinator(
        ledger=stack.admission.ledger,
        metadata=stack.postgres,
        content=stack.content,
        cipher=stack.cipher,
        lexical=index_type(stack.postgres),
        vector=stack.vector,
        clock=stack.clock,
    )
    assert_store_error(lambda: coordinator.commit(record, payload=payload, embedding=vector), "REPRESENTATION_NOT_READY", "PROJECTION_UNVERIFIED")
    assert stack.sql("SELECT state FROM {s}.versions WHERE memory_item_id = %s", (item_id,)) == [("PENDING",)]
    assert stack.coordinator().lexical_candidates(partition_of(record), "ammunition depot inventory", limit=5) == ()


def test_content_that_opens_but_does_not_match_its_digest_is_rejected(stack: Stack) -> None:
    record, payload, vector = stack.admission.admit("mem-reseal", "fuel bladder F-3 leak sealed", compartment="lima")
    coordinator = stack.coordinator()
    coordinator.commit(record, payload=payload, embedding=vector)
    partition = partition_of(record)
    ref = content_object_ref(partition, record.item.content_digest)
    context = {"content_object_ref": ref, "partition_digest": partition.digest, "content_digest": record.item.content_digest}
    forged = stack.cipher.seal(context=context, plaintext=b"fuel bladder F-3 intact, no leak")
    original = stack.sql("SELECT ciphertext FROM {s}.content WHERE object_ref = %s", (ref,))[0][0]
    stack.sql("UPDATE {s}.content SET ciphertext = %s WHERE object_ref = %s", (forged.ciphertext, ref))
    try:
        assert_store_error(lambda: coordinator.read_version(partition, "mem-reseal", 1), "INTERNAL_ERROR", "CONTENT_DIGEST_MISMATCH")
    finally:
        stack.sql("UPDATE {s}.content SET ciphertext = %s WHERE object_ref = %s", (original, ref))
    assert coordinator.read_version(partition, "mem-reseal", 1).payload == payload


def test_projection_drift_on_a_committed_version_blocks_materialisation(stack: Stack) -> None:
    record, payload, vector = stack.admission.admit("mem-drift", "runway R-2 lights failing", compartment="foxtrot")
    coordinator = stack.coordinator()
    coordinator.commit(record, payload=payload, embedding=vector)
    partition = partition_of(record)
    stored = stack.postgres.get("mem-drift", 1)
    assert stored is not None
    vector_pointer = next(p for p in stored.staged.pointers if p.representation_kind.value == "VECTOR")
    stack.vector.remove(partition, vector_pointer.representation_version, vector_pointer.store_ref)
    assert_store_error(lambda: coordinator.read_version(partition, "mem-drift", 1), "REPRESENTATION_NOT_READY", "PROJECTION_DRIFT")
    # The pointer itself stays registered; the drift is not hidden by a re-commit.
    assert coordinator.commit(record, payload=payload, embedding=vector).state == "COMMITTED"
    assert_store_error(lambda: coordinator.read_version(partition, "mem-drift", 1), "REPRESENTATION_NOT_READY", "PROJECTION_DRIFT")

