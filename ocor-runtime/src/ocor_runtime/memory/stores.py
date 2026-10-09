"""C8 governed memory -- metadata, content, lexical and vector stores.

Implements the ``MemoryMetadataStore``, ``MemoryContentStore``,
``MemoryLexicalIndexPort`` and ``MemoryVectorIndexPort`` slice of the
``GovernedMemoryService`` (ADD v1.3 Part II §§2.5-2.8, 2.13; LLD v1.1
§§2.8.1-2.8.4; change-control §7):

* Every admitted version is stored under one ``MemoryPartition``: the full
  isolation tuple (tenant, organization, domain, compartments, marking,
  purpose, policy bundle, ontology release, memory scope and the scope owner
  bindings).  Content objects, lexical entries and vector entries live only in
  the physical partition derived from that digest; nothing is shared across
  partitions, so there is no cross-compartment dedupe, ANN graph or index.
* Each representation (``STRUCTURED``, ``FULL_TEXT``, ``VECTOR``) has a
  ``RepresentationPointer`` binding item/version, item digest, content digest,
  representation version and digest, partition, marking, policy bundle, scope
  and deletion epoch.  The index entry carries exactly that pointer, so every
  projection is rebuildable from metadata plus content and every hit can be
  checked against the metadata authority.  Pointer references are opaque URNs:
  backend identifiers never cross the ports.
* ``MemoryStoreCoordinator.commit`` stages metadata and pointers as
  ``PENDING``, writes the encrypted content-addressed payload and each
  projection, re-reads every write instead of trusting an acknowledgement, and
  only then flips the version and all its pointers to ``COMMITTED`` in a single
  metadata transaction that also advances the item's versioned head pointer.
  A version that is ``PENDING`` -- partial store visibility -- is never
  materialised (``REPRESENTATION_NOT_READY``), and an index hit whose pointer is
  not a committed metadata pointer -- an unbound representation -- never
  reaches a result, a rank slot or a count.
* ``MemoryStoreCoordinator.reconcile`` rolls complete pending versions forward,
  retracts the projections and content of incomplete ones, and removes every
  unbound index entry and unreferenced content object (fail closed).

The module is backend-free (``OCOR_LANGUAGE_POLICY.md`` row 8): stores, indexes
and the content cipher are ports.  Policy evaluation and the derivation of the
caller's authorized partition belong to retrieval (OCOR-DEV-0052); memory
metadata is authority for memory metadata only, never for canonical state.
"""

from __future__ import annotations

import hashlib
import hmac
import math
import struct
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import timedelta
from enum import StrEnum
from types import MappingProxyType
from typing import Protocol

from ..kernel.canonical import canonical_digest, format_utc_timestamp, parse_utc_timestamp
from ..kernel.governance import TrustedClock
from .model import (
    DIGEST,
    SCOPE_BINDINGS,
    AdmittedMemoryVersion,
    GovernedMemoryItem,
    MemoryAdmissionError,
    MemoryScope,
    MemoryVersionLedger,
    RepresentationKind,
    memory_version_ref,
)

PARTITION_PREFIX = "urn:ocor:memory-partition:"
REPRESENTATION_PREFIX = "urn:ocor:memory-representation:"
CONTENT_OBJECT_PREFIX = "urn:ocor:memory-content-object:"
VECTOR_ENCODING = b"ocor-memory-vector:f64be:"


class MemoryStoreError(MemoryAdmissionError):
    """Fail-closed store refusal carrying the closed memory Problem vocabulary."""


class MemoryStoreCorrupted(MemoryStoreError):
    """Persisted memory metadata, content or pointers failed verification."""

    def __init__(self, detail_code: str, message: str) -> None:
        super().__init__("INTERNAL_ERROR", detail_code, message)


def _hex(digest: str) -> str:
    return digest.removeprefix("urn:sha256:")


def _sha256(data: bytes) -> str:
    return "urn:sha256:" + hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------
# Partitions and representation profiles
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MemoryPartition:
    """The full isolation tuple of ADD v1.3 Part II §2.6 for one stored item.

    ``scope_bindings`` are the owner bindings of the item's scope (the schema
    ``allOf`` bindings: run, task, agent, team, project or federation policy),
    so two items share a partition only if every isolation attribute matches.
    """

    tenant_id: str
    organization_id: str
    domain_id: str
    compartments: tuple[str, ...]
    classification_marking_ref: str
    purpose: str
    policy_bundle_digest: str
    ontology_release_digest: str
    memory_scope: MemoryScope
    scope_bindings: tuple[tuple[str, str], ...]

    @classmethod
    def for_item(cls, item: GovernedMemoryItem) -> MemoryPartition:
        bindings: list[tuple[str, str]] = []
        for name in SCOPE_BINDINGS[item.memory_scope]:
            value = getattr(item, name)
            if not isinstance(value, str) or not value:
                raise MemoryStoreError(
                    "MEMORY_SCHEMA_INVALID",
                    "SCOPE_BINDING_MISSING",
                    f"{item.memory_scope.value} partition requires {name}",
                )
            bindings.append((name, value))
        return cls(
            tenant_id=item.tenant_id,
            organization_id=item.organization_id,
            domain_id=item.domain_id,
            compartments=tuple(sorted(item.compartments)),
            classification_marking_ref=item.classification_marking_ref,
            purpose=item.purpose,
            policy_bundle_digest=item.policy_bundle_digest,
            ontology_release_digest=item.ontology_release_digest,
            memory_scope=item.memory_scope,
            scope_bindings=tuple(bindings),
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id,
            "organization_id": self.organization_id,
            "domain_id": self.domain_id,
            "compartments": list(self.compartments),
            "classification_marking_ref": self.classification_marking_ref,
            "purpose": self.purpose,
            "policy_bundle_digest": self.policy_bundle_digest,
            "ontology_release_digest": self.ontology_release_digest,
            "memory_scope": self.memory_scope.value,
            "scope_bindings": [[name, value] for name, value in self.scope_bindings],
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> MemoryPartition:
        expected = {
            "tenant_id",
            "organization_id",
            "domain_id",
            "compartments",
            "classification_marking_ref",
            "purpose",
            "policy_bundle_digest",
            "ontology_release_digest",
            "memory_scope",
            "scope_bindings",
        }
        if not isinstance(value, Mapping) or set(value) != expected:
            raise MemoryStoreCorrupted("PARTITION_INVALID", "partition is not a closed record")
        raw_compartments = value["compartments"]
        raw_bindings = value["scope_bindings"]
        if not isinstance(raw_compartments, list) or not isinstance(raw_bindings, list):
            raise MemoryStoreCorrupted("PARTITION_INVALID", "partition members have invalid types")
        compartments: list[str] = []
        for compartment in raw_compartments:
            if not isinstance(compartment, str) or not compartment:
                raise MemoryStoreCorrupted("PARTITION_INVALID", "partition compartment is invalid")
            compartments.append(compartment)
        bindings: list[tuple[str, str]] = []
        for binding in raw_bindings:
            if (
                not isinstance(binding, list)
                or len(binding) != 2
                or not all(isinstance(part, str) and part for part in binding)
            ):
                raise MemoryStoreCorrupted("PARTITION_INVALID", "partition binding is invalid")
            bindings.append((str(binding[0]), str(binding[1])))
        strings: dict[str, str] = {}
        for name in expected - {"compartments", "scope_bindings", "memory_scope"}:
            raw = value[name]
            if not isinstance(raw, str) or not raw:
                raise MemoryStoreCorrupted("PARTITION_INVALID", f"partition {name} is invalid")
            strings[name] = raw
        try:
            scope = MemoryScope(str(value["memory_scope"]))
        except ValueError as exc:
            raise MemoryStoreCorrupted("PARTITION_INVALID", "partition scope is invalid") from exc
        partition = cls(
            tenant_id=strings["tenant_id"],
            organization_id=strings["organization_id"],
            domain_id=strings["domain_id"],
            compartments=tuple(compartments),
            classification_marking_ref=strings["classification_marking_ref"],
            purpose=strings["purpose"],
            policy_bundle_digest=strings["policy_bundle_digest"],
            ontology_release_digest=strings["ontology_release_digest"],
            memory_scope=scope,
            scope_bindings=tuple(bindings),
        )
        if list(partition.compartments) != sorted(partition.compartments):
            raise MemoryStoreCorrupted("PARTITION_INVALID", "partition is not canonical")
        return partition

    @property
    def digest(self) -> str:
        return canonical_digest(self.to_mapping())

    @property
    def ref(self) -> str:
        return PARTITION_PREFIX + _hex(self.digest)


@dataclass(frozen=True, slots=True)
class LexicalProfile:
    """Versioned full-text analyzer profile; a new version is a new representation."""

    profile_ref: str = "urn:ocor:memory-lexical:simple"
    version: int = 1
    text_search_configuration: str = "simple"

    @property
    def representation_version(self) -> str:
        return canonical_digest(
            {
                "representation_kind": RepresentationKind.FULL_TEXT.value,
                "profile_ref": self.profile_ref,
                "version": self.version,
                "text_search_configuration": self.text_search_configuration,
            }
        )


@dataclass(frozen=True, slots=True)
class VectorProfile:
    """Embedding representation version bound to the item's model pins (§2.8)."""

    embedding_model_ref: str
    embedding_model_digest: str
    embedding_dimensions: int
    embedding_normalization_profile: str

    @classmethod
    def for_item(cls, item: GovernedMemoryItem) -> VectorProfile:
        if (
            item.embedding_model_ref is None
            or item.embedding_model_digest is None
            or item.embedding_dimensions is None
            or item.embedding_normalization_profile is None
        ):
            raise MemoryStoreError(
                "MEMORY_SCHEMA_INVALID",
                "EMBEDDING_BINDING_MISSING",
                "VECTOR representation requires the embedding model binding",
            )
        return cls(
            embedding_model_ref=item.embedding_model_ref,
            embedding_model_digest=item.embedding_model_digest,
            embedding_dimensions=item.embedding_dimensions,
            embedding_normalization_profile=item.embedding_normalization_profile,
        )

    @property
    def representation_version(self) -> str:
        return canonical_digest(
            {
                "representation_kind": RepresentationKind.VECTOR.value,
                "embedding_model_ref": self.embedding_model_ref,
                "embedding_model_digest": self.embedding_model_digest,
                "embedding_dimensions": self.embedding_dimensions,
                "embedding_normalization_profile": self.embedding_normalization_profile,
            }
        )


def structured_representation_version(item: GovernedMemoryItem) -> str:
    return canonical_digest(
        {
            "representation_kind": RepresentationKind.STRUCTURED.value,
            "content_schema_ref": item.content_schema_ref,
        }
    )


def vector_digest(values: Sequence[float]) -> str:
    """Canonical digest of an embedding: IEEE-754 binary64 big-endian values."""

    return _sha256(VECTOR_ENCODING + struct.pack(f">{len(values)}d", *values))


def lexical_document(payload: bytes) -> str:
    """The full-text document is the strict UTF-8 payload, so it is rebuildable."""

    try:
        document = bytes(payload).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MemoryStoreError(
            "MEMORY_SCHEMA_INVALID",
            "LEXICAL_DOCUMENT_INVALID",
            "FULL_TEXT representation requires a UTF-8 payload",
        ) from exc
    if "\x00" in document or not document.strip():
        raise MemoryStoreError(
            "MEMORY_SCHEMA_INVALID",
            "LEXICAL_DOCUMENT_INVALID",
            "FULL_TEXT representation requires a non-empty document without NUL",
        )
    return document


def validate_embedding(item: GovernedMemoryItem, vector: Sequence[float]) -> tuple[float, ...]:
    """The supplied embedding must be exactly the one the item digests."""

    profile = VectorProfile.for_item(item)
    if isinstance(vector, (str, bytes)) or not isinstance(vector, Sequence):
        raise MemoryStoreError(
            "MEMORY_SCHEMA_INVALID", "EMBEDDING_INVALID", "embedding must be a sequence"
        )
    values: list[float] = []
    for value in vector:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise MemoryStoreError(
                "MEMORY_SCHEMA_INVALID", "EMBEDDING_INVALID", "embedding values must be numbers"
            )
        if not math.isfinite(value):
            raise MemoryStoreError(
                "MEMORY_SCHEMA_INVALID", "EMBEDDING_INVALID", "embedding values must be finite"
            )
        values.append(float(value))
    if len(values) != profile.embedding_dimensions:
        raise MemoryStoreError(
            "MEMORY_SCHEMA_INVALID",
            "EMBEDDING_DIMENSION_MISMATCH",
            "embedding length differs from embedding_dimensions",
        )
    if not any(values):
        raise MemoryStoreError(
            "MEMORY_SCHEMA_INVALID", "EMBEDDING_INVALID", "embedding must not be the zero vector"
        )
    if item.embedding_digest is None or not hmac.compare_digest(
        vector_digest(values), item.embedding_digest
    ):
        raise MemoryStoreError(
            "MEMORY_SCHEMA_INVALID",
            "EMBEDDING_DIGEST_MISMATCH",
            "embedding_digest does not bind the supplied embedding",
        )
    return tuple(values)


# --------------------------------------------------------------------------
# Versioned representation pointers
# --------------------------------------------------------------------------

POINTER_FIELDS = frozenset(
    {
        "memory_version_ref",
        "item_digest",
        "content_digest",
        "representation_kind",
        "representation_version",
        "representation_digest",
        "partition_digest",
        "classification_marking_ref",
        "policy_bundle_digest",
        "memory_scope",
        "deletion_epoch",
    }
)


@dataclass(frozen=True, slots=True)
class RepresentationPointer:
    """The binding carried by metadata and by every index entry (change-control §7)."""

    memory_version_ref: str
    item_digest: str
    content_digest: str
    representation_kind: RepresentationKind
    representation_version: str
    representation_digest: str
    partition_digest: str
    classification_marking_ref: str
    policy_bundle_digest: str
    memory_scope: MemoryScope
    deletion_epoch: int

    def to_mapping(self) -> dict[str, object]:
        return {
            "memory_version_ref": self.memory_version_ref,
            "item_digest": self.item_digest,
            "content_digest": self.content_digest,
            "representation_kind": self.representation_kind.value,
            "representation_version": self.representation_version,
            "representation_digest": self.representation_digest,
            "partition_digest": self.partition_digest,
            "classification_marking_ref": self.classification_marking_ref,
            "policy_bundle_digest": self.policy_bundle_digest,
            "memory_scope": self.memory_scope.value,
            "deletion_epoch": self.deletion_epoch,
        }

    @classmethod
    def from_mapping(cls, value: object) -> RepresentationPointer:
        """Parse a stored pointer strictly; anything else is not a pointer."""

        if not isinstance(value, Mapping) or set(value) != POINTER_FIELDS:
            raise MemoryStoreCorrupted("POINTER_INVALID", "pointer is not a closed record")
        epoch = value["deletion_epoch"]
        if isinstance(epoch, bool) or not isinstance(epoch, int) or epoch < 0:
            raise MemoryStoreCorrupted("POINTER_INVALID", "pointer deletion_epoch is invalid")
        strings: dict[str, str] = {}
        for name in POINTER_FIELDS - {"deletion_epoch"}:
            raw = value[name]
            if not isinstance(raw, str) or not raw:
                raise MemoryStoreCorrupted("POINTER_INVALID", f"pointer {name} is invalid")
            strings[name] = raw
        for name in (
            "item_digest",
            "content_digest",
            "representation_version",
            "representation_digest",
            "partition_digest",
            "classification_marking_ref",
            "policy_bundle_digest",
        ):
            if DIGEST.fullmatch(strings[name]) is None:
                raise MemoryStoreCorrupted("POINTER_INVALID", f"pointer {name} is not a digest")
        try:
            kind = RepresentationKind(strings["representation_kind"])
            scope = MemoryScope(strings["memory_scope"])
        except ValueError as exc:
            raise MemoryStoreCorrupted("POINTER_INVALID", "pointer enum is invalid") from exc
        return cls(
            memory_version_ref=strings["memory_version_ref"],
            item_digest=strings["item_digest"],
            content_digest=strings["content_digest"],
            representation_kind=kind,
            representation_version=strings["representation_version"],
            representation_digest=strings["representation_digest"],
            partition_digest=strings["partition_digest"],
            classification_marking_ref=strings["classification_marking_ref"],
            policy_bundle_digest=strings["policy_bundle_digest"],
            memory_scope=scope,
            deletion_epoch=epoch,
        )

    @property
    def digest(self) -> str:
        return canonical_digest(self.to_mapping())

    @property
    def store_ref(self) -> str:
        return REPRESENTATION_PREFIX + _hex(self.digest)


def stage_conflict(version_ref: str) -> MemoryStoreError:
    """Raised by metadata stores when a slot already holds a different stage."""

    return MemoryStoreError(
        "MEMORY_IDEMPOTENCY_CONFLICT",
        "STAGE_CONFLICT",
        f"{version_ref} is already staged with different metadata or pointers",
    )


def predecessor_not_committed(version_ref: str) -> MemoryStoreError:
    """Raised by metadata stores when the head pointer is not exactly ``n - 1``."""

    return MemoryStoreError(
        "REPRESENTATION_NOT_READY",
        "PREDECESSOR_NOT_COMMITTED",
        f"{version_ref} requires its predecessor version to be committed first",
    )


def content_object_ref(partition: MemoryPartition, content_digest: str) -> str:
    """Content address scoped to the partition: no cross-partition dedupe."""

    return CONTENT_OBJECT_PREFIX + _hex(
        canonical_digest({"partition_digest": partition.digest, "content_digest": content_digest})
    )


# --------------------------------------------------------------------------
# Ports
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SealedContent:
    """Ciphertext plus the opaque logical key reference that sealed it."""

    key_ref: str
    ciphertext: bytes


class ContentCipher(Protocol):
    """Authenticated encryption bound to ``context`` (partition and content address)."""

    def seal(self, *, context: Mapping[str, str], plaintext: bytes) -> SealedContent:
        """Encrypt ``plaintext`` so it opens only under the identical context."""

    def open(self, *, context: Mapping[str, str], sealed: SealedContent) -> bytes:
        """Decrypt, raising on any context, key or ciphertext mismatch."""


class MemoryContentStore(Protocol):
    """Encrypted, content-addressed payload store (no canonical-state authority)."""

    def put(self, object_ref: str, partition_digest: str, sealed: SealedContent) -> None:
        """Store once; an existing object is never overwritten."""

    def get(self, object_ref: str) -> SealedContent | None:
        """Return the sealed object, or ``None``."""

    def delete(self, object_ref: str) -> None:
        """Remove the object (reconciliation of unreferenced content)."""

    def refs(self, partition_digest: str) -> tuple[str, ...]:
        """Every object ref stored in one partition."""


class VersionState(StrEnum):
    PENDING = "PENDING"
    COMMITTED = "COMMITTED"


@dataclass(frozen=True, slots=True)
class StagedVersion:
    """Metadata of one version plus its pointers, as written before projections."""

    memory_item_id: str
    memory_version: int
    item: Mapping[str, object]
    item_digest: str
    audit_ref: str
    partition: MemoryPartition
    content_object_ref: str
    pointers: tuple[RepresentationPointer, ...]
    staged_at: str

    @property
    def memory_version_ref(self) -> str:
        return memory_version_ref(self.memory_item_id, self.memory_version)

    def body(self) -> dict[str, object]:
        """The idempotency-relevant body (everything except the staging time)."""

        return {
            "memory_item_id": self.memory_item_id,
            "memory_version": self.memory_version,
            "item": dict(self.item),
            "item_digest": self.item_digest,
            "audit_ref": self.audit_ref,
            "partition": self.partition.to_mapping(),
            "content_object_ref": self.content_object_ref,
            "pointers": [pointer.to_mapping() for pointer in self.pointers],
        }

    @property
    def stage_digest(self) -> str:
        return canonical_digest(self.body())

    @classmethod
    def from_body(cls, body: Mapping[str, object], staged_at: str) -> StagedVersion:
        """Rebuild a persisted stage strictly; adapters never trust stored bytes."""

        expected = {
            "memory_item_id",
            "memory_version",
            "item",
            "item_digest",
            "audit_ref",
            "partition",
            "content_object_ref",
            "pointers",
        }
        if not isinstance(body, Mapping) or set(body) != expected:
            raise MemoryStoreCorrupted("METADATA_INVALID", "stage is not a closed record")
        item = body["item"]
        partition = body["partition"]
        pointers = body["pointers"]
        version = body["memory_version"]
        strings = {
            name: body[name]
            for name in ("memory_item_id", "item_digest", "audit_ref", "content_object_ref")
        }
        if (
            not isinstance(item, Mapping)
            or not isinstance(partition, Mapping)
            or not isinstance(pointers, list)
            or isinstance(version, bool)
            or not isinstance(version, int)
            or not all(isinstance(value, str) and value for value in strings.values())
            or not isinstance(staged_at, str)
        ):
            raise MemoryStoreCorrupted("METADATA_INVALID", "stage members have invalid types")
        staged = cls(
            memory_item_id=str(strings["memory_item_id"]),
            memory_version=version,
            item=MappingProxyType(dict(item)),
            item_digest=str(strings["item_digest"]),
            audit_ref=str(strings["audit_ref"]),
            partition=MemoryPartition.from_mapping(partition),
            content_object_ref=str(strings["content_object_ref"]),
            pointers=tuple(RepresentationPointer.from_mapping(p) for p in pointers),
            staged_at=staged_at,
        )
        staged.verify()
        return staged

    def verify(self) -> GovernedMemoryItem:
        """Re-validate the stored item and every binding derived from it."""

        try:
            item = GovernedMemoryItem.from_mapping(self.item)
        except MemoryAdmissionError as exc:
            raise MemoryStoreCorrupted("METADATA_INVALID", f"stored item invalid: {exc}") from exc
        if not hmac.compare_digest(item.digest(), self.item_digest):
            raise MemoryStoreCorrupted("METADATA_DIGEST_MISMATCH", "item digest mismatch")
        if (item.memory_item_id, item.memory_version) != (
            self.memory_item_id,
            self.memory_version,
        ):
            raise MemoryStoreCorrupted("METADATA_INVALID", "stored version slot mismatch")
        if MemoryPartition.for_item(item) != self.partition:
            raise MemoryStoreCorrupted("METADATA_INVALID", "stored partition mismatch")
        if content_object_ref(self.partition, item.content_digest) != self.content_object_ref:
            raise MemoryStoreCorrupted("METADATA_INVALID", "stored content ref mismatch")
        kinds = sorted(pointer.representation_kind.value for pointer in self.pointers)
        if kinds != sorted(kind.value for kind in item.representation_kinds):
            raise MemoryStoreCorrupted("METADATA_INVALID", "stored pointers mismatch")
        for pointer in self.pointers:
            if (
                pointer.memory_version_ref != item.version_ref
                or pointer.item_digest != self.item_digest
                or pointer.content_digest != item.content_digest
                or pointer.partition_digest != self.partition.digest
            ):
                raise MemoryStoreCorrupted("METADATA_INVALID", "stored pointer binding mismatch")
        return item


@dataclass(frozen=True, slots=True)
class StoredVersion:
    staged: StagedVersion
    state: VersionState
    committed_at: str | None


class MemoryMetadataStore(Protocol):
    """Authority for memory metadata only: versions, pointers and head pointers."""

    def stage(self, staged: StagedVersion) -> StoredVersion:
        """Atomically insert the version and its pointers as ``PENDING``.

        An existing version with the same stage digest is returned unchanged;
        any other occupant of the slot raises ``MEMORY_IDEMPOTENCY_CONFLICT``.
        """

    def get(self, memory_item_id: str, memory_version: int) -> StoredVersion | None:
        """Return one exact version, whatever its state."""

    def commit(
        self, memory_item_id: str, memory_version: int, *, stage_digest: str, committed_at: str
    ) -> StoredVersion:
        """Atomically flip version and pointers to ``COMMITTED`` and advance the head.

        Refuses unless the slot holds ``stage_digest`` and, for a version
        ``n > 1``, the head pointer is exactly ``n - 1``.
        """

    def head(self, memory_item_id: str) -> int:
        """Highest committed version, or 0."""

    def pointer(self, store_ref: str) -> tuple[RepresentationPointer, VersionState] | None:
        """The pointer registered under ``store_ref`` and its version state."""

    def versions_in(self, partition_digest: str) -> tuple[StoredVersion, ...]:
        """Every staged or committed version of one partition."""

    def partitions(self) -> tuple[MemoryPartition, ...]:
        """Every partition that has ever received a staged version."""


@dataclass(frozen=True, slots=True)
class IndexHit:
    """One raw index answer: the opaque ref, the stored pointer payload, a score."""

    store_ref: str
    payload: Mapping[str, object]
    score: float


class MemoryLexicalIndexPort(Protocol):
    """Policy-partitioned full-text projection (rebuildable)."""

    def upsert(
        self,
        partition: MemoryPartition,
        profile: LexicalProfile,
        store_ref: str,
        payload: Mapping[str, object],
        document: str,
    ) -> None:
        """Write one entry into the physical partition of ``partition``/``profile``."""

    def search(
        self,
        partition: MemoryPartition,
        representation_version: str,
        query: str,
        *,
        limit: int,
        offset: int,
    ) -> Sequence[IndexHit]:
        """Ranked page of the partition only; deterministic order."""

    def get(
        self, partition: MemoryPartition, representation_version: str, store_ref: str
    ) -> Mapping[str, object] | None:
        """The stored payload of one entry, read from the backend."""

    def entries(
        self, partition: MemoryPartition, representation_version: str
    ) -> Sequence[IndexHit]:
        """Every entry of the physical partition (reconciliation)."""

    def remove(
        self, partition: MemoryPartition, representation_version: str, store_ref: str
    ) -> None:
        """Delete one entry."""


class MemoryVectorIndexPort(Protocol):
    """Policy-partitioned, representation-versioned embedding projection."""

    def upsert(
        self,
        partition: MemoryPartition,
        profile: VectorProfile,
        store_ref: str,
        payload: Mapping[str, object],
        vector: Sequence[float],
    ) -> None:
        """Write one entry into the physical partition of ``partition``/``profile``."""

    def search(
        self,
        partition: MemoryPartition,
        representation_version: str,
        vector: Sequence[float],
        *,
        limit: int,
        offset: int,
    ) -> Sequence[IndexHit]:
        """Ranked page of the partition only; deterministic order."""

    def get(
        self, partition: MemoryPartition, representation_version: str, store_ref: str
    ) -> Mapping[str, object] | None:
        """The stored payload of one entry, read from the backend."""

    def entries(
        self, partition: MemoryPartition, representation_version: str
    ) -> Sequence[IndexHit]:
        """Every entry of the physical partition (reconciliation)."""

    def remove(
        self, partition: MemoryPartition, representation_version: str, store_ref: str
    ) -> None:
        """Delete one entry."""


# --------------------------------------------------------------------------
# Coordinator
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StoreLimits:
    """Boundary configuration of the store coordinator."""

    lexical_profile: LexicalProfile = field(default_factory=LexicalProfile)
    page_size: int = 16
    max_scanned_hits: int = 256
    reconcile_grace: timedelta = timedelta(minutes=5)


@dataclass(frozen=True, slots=True)
class StoreCommitReceipt:
    memory_version_ref: str
    item_digest: str
    partition_ref: str
    content_object_ref: str
    representations: tuple[tuple[str, str, str], ...]
    state: str
    head_version: int
    audit_ref: str

    def to_mapping(self) -> dict[str, object]:
        return {
            "memory_version_ref": self.memory_version_ref,
            "item_digest": self.item_digest,
            "audit_ref": self.audit_ref,
            "partition_ref": self.partition_ref,
            "content_object_ref": self.content_object_ref,
            "representations": [list(entry) for entry in self.representations],
            "state": self.state,
            "head_version": self.head_version,
        }


@dataclass(frozen=True, slots=True)
class MaterializedVersion:
    item: GovernedMemoryItem
    payload: bytes
    pointers: tuple[RepresentationPointer, ...]
    partition_ref: str


@dataclass(frozen=True, slots=True)
class BoundHit:
    """A candidate whose index entry is a committed metadata pointer."""

    memory_version_ref: str
    item_digest: str
    content_digest: str
    store_ref: str
    representation_kind: str
    representation_version: str
    classification_marking_ref: str
    score: float


@dataclass(frozen=True, slots=True)
class ReconciliationReport:
    completed: tuple[str, ...]
    retracted: tuple[str, ...]
    deferred: tuple[str, ...]
    unbound_removed: tuple[str, ...]
    content_removed: tuple[str, ...]

    def to_mapping(self) -> dict[str, object]:
        return {
            "completed": list(self.completed),
            "retracted": list(self.retracted),
            "deferred": list(self.deferred),
            "unbound_removed": list(self.unbound_removed),
            "content_removed": list(self.content_removed),
        }


class _Outcome(StrEnum):
    COMPLETED = "COMPLETED"
    RETRACTED = "RETRACTED"
    DEFERRED = "DEFERRED"


def _not_visible() -> MemoryStoreError:
    # Absent and out-of-partition versions are indistinguishable (no existence leak).
    return MemoryStoreError(
        "MEMORY_VERSION_NOT_FOUND", "VERSION_NOT_VISIBLE", "memory version is not visible"
    )


def _not_ready(detail: str, message: str) -> MemoryStoreError:
    return MemoryStoreError("REPRESENTATION_NOT_READY", detail, message)


class MemoryStoreCoordinator:
    """Commits admitted versions across the four stores with one visibility switch."""

    def __init__(
        self,
        *,
        ledger: MemoryVersionLedger,
        metadata: MemoryMetadataStore,
        content: MemoryContentStore,
        cipher: ContentCipher,
        lexical: MemoryLexicalIndexPort,
        vector: MemoryVectorIndexPort,
        clock: TrustedClock,
        limits: StoreLimits | None = None,
    ) -> None:
        self._ledger = ledger
        self._metadata = metadata
        self._content = content
        self._cipher = cipher
        self._lexical = lexical
        self._vector = vector
        self._clock = clock
        self._limits = limits if limits is not None else StoreLimits()
        if self._limits.page_size < 1 or self._limits.max_scanned_hits < 1:
            raise ValueError("store limits must be positive")

    # -- commit -----------------------------------------------------------

    def commit(
        self,
        record: AdmittedMemoryVersion,
        *,
        payload: bytes,
        embedding: Sequence[float] | None = None,
    ) -> StoreCommitReceipt:
        """Store one admitted version; it becomes visible only when complete."""

        try:
            return self._commit(record, payload, embedding)
        except MemoryAdmissionError as exc:
            # Correlate every refusal with the admission that produced the record.
            if exc.correlation_id is None and isinstance(record, AdmittedMemoryVersion):
                correlation = record.audit_event.get("correlation_id")
                exc.correlation_id = correlation if isinstance(correlation, str) else None
            raise

    def _commit(
        self,
        record: AdmittedMemoryVersion,
        payload: bytes,
        embedding: Sequence[float] | None,
    ) -> StoreCommitReceipt:
        staged, document, vector = self._prepare(record, payload, embedding)
        stored = self._metadata.stage(staged)
        if stored.staged.stage_digest != staged.stage_digest:
            raise MemoryStoreCorrupted("METADATA_INVALID", "metadata returned another stage")
        if stored.state is VersionState.COMMITTED:
            self._verify_committed(stored)
            return self._receipt(stored)
        partition = staged.partition
        item = record.item
        try:
            self._write_content(staged, item.content_digest, payload)
            for pointer in staged.pointers:
                self._write_projection(partition, item, pointer, document, vector)
        except MemoryStoreError:
            raise
        except Exception as exc:  # noqa: BLE001 -- every backend failure fails closed
            raise _not_ready(
                "STORE_COMMIT_INCOMPLETE",
                f"{staged.memory_version_ref} stays PENDING: {type(exc).__name__}",
            ) from exc
        try:
            committed = self._metadata.commit(
                staged.memory_item_id,
                staged.memory_version,
                stage_digest=staged.stage_digest,
                committed_at=format_utc_timestamp(self._clock.now()),
            )
        except MemoryStoreError:
            raise
        except Exception as exc:  # noqa: BLE001 -- a lost metadata commit fails closed
            raise _not_ready(
                "STORE_COMMIT_INCOMPLETE",
                f"{staged.memory_version_ref} stays PENDING: {type(exc).__name__}",
            ) from exc
        if committed.state is not VersionState.COMMITTED:
            raise MemoryStoreCorrupted("METADATA_INVALID", "metadata commit was not applied")
        return self._receipt(committed)

    def _prepare(
        self,
        record: AdmittedMemoryVersion,
        payload: bytes,
        embedding: Sequence[float] | None,
    ) -> tuple[StagedVersion, str | None, tuple[float, ...] | None]:
        if not isinstance(record, AdmittedMemoryVersion):
            raise MemoryStoreError(
                "MEMORY_SCHEMA_INVALID", "RECORD_INVALID", "commit requires an admitted version"
            )
        try:
            record.verify()
        except MemoryAdmissionError as exc:
            raise MemoryStoreError(
                "MEMORY_SCHEMA_INVALID", "RECORD_INVALID", "admitted version does not verify"
            ) from exc
        item = record.item
        admitted = self._ledger.get(item.memory_item_id, item.memory_version)
        if (
            admitted is None
            or not hmac.compare_digest(admitted.item_digest, record.item_digest)
            or not hmac.compare_digest(admitted.receipt.audit_ref, record.receipt.audit_ref)
        ):
            raise MemoryStoreError(
                "MEMORY_VERSION_NOT_FOUND",
                "VERSION_NOT_ADMITTED",
                "only versions recorded by the admission ledger are stored",
            )
        if not isinstance(payload, (bytes, bytearray)) or not hmac.compare_digest(
            _sha256(bytes(payload)), item.content_digest
        ):
            raise MemoryStoreError(
                "MEMORY_SCHEMA_INVALID",
                "CONTENT_DIGEST_MISMATCH",
                "content_digest does not bind payload",
            )
        kinds = set(item.representation_kinds)
        document = (
            lexical_document(bytes(payload)) if RepresentationKind.FULL_TEXT in kinds else None
        )
        vector: tuple[float, ...] | None = None
        if RepresentationKind.VECTOR in kinds:
            if embedding is None:
                raise MemoryStoreError(
                    "MEMORY_SCHEMA_INVALID",
                    "EMBEDDING_MISSING",
                    "VECTOR representation requires its embedding",
                )
            vector = validate_embedding(item, embedding)
        elif embedding is not None:
            raise MemoryStoreError(
                "MEMORY_SCHEMA_INVALID",
                "UNBOUND_REPRESENTATION",
                "embedding supplied for an item without VECTOR representation",
            )
        partition = MemoryPartition.for_item(item)
        pointers = tuple(
            self._pointer(item, record.item_digest, partition, kind, document)
            for kind in sorted(kinds, key=lambda k: k.value)
        )
        staged = StagedVersion(
            memory_item_id=item.memory_item_id,
            memory_version=item.memory_version,
            item=MappingProxyType(item.to_mapping()),
            item_digest=record.item_digest,
            audit_ref=record.receipt.audit_ref,
            partition=partition,
            content_object_ref=content_object_ref(partition, item.content_digest),
            pointers=pointers,
            staged_at=format_utc_timestamp(self._clock.now()),
        )
        return staged, document, vector

    def _pointer(
        self,
        item: GovernedMemoryItem,
        item_digest: str,
        partition: MemoryPartition,
        kind: RepresentationKind,
        document: str | None,
    ) -> RepresentationPointer:
        if kind is RepresentationKind.FULL_TEXT:
            assert document is not None
            version = self._limits.lexical_profile.representation_version
            representation = canonical_digest(
                {"representation_version": version, "document_digest": _sha256(document.encode())}
            )
        elif kind is RepresentationKind.VECTOR:
            assert item.embedding_digest is not None
            version = VectorProfile.for_item(item).representation_version
            representation = item.embedding_digest
        else:
            version = structured_representation_version(item)
            representation = item_digest
        return RepresentationPointer(
            memory_version_ref=item.version_ref,
            item_digest=item_digest,
            content_digest=item.content_digest,
            representation_kind=kind,
            representation_version=version,
            representation_digest=representation,
            partition_digest=partition.digest,
            classification_marking_ref=item.classification_marking_ref,
            policy_bundle_digest=item.policy_bundle_digest,
            memory_scope=item.memory_scope,
            deletion_epoch=item.deletion_epoch if item.deletion_epoch is not None else 0,
        )

    @staticmethod
    def _cipher_context(staged: StagedVersion, content_digest: str) -> dict[str, str]:
        return {
            "content_object_ref": staged.content_object_ref,
            "partition_digest": staged.partition.digest,
            "content_digest": content_digest,
        }

    def _write_content(self, staged: StagedVersion, content_digest: str, payload: bytes) -> None:
        context = self._cipher_context(staged, content_digest)
        if self._content.get(staged.content_object_ref) is None:
            sealed = self._cipher.seal(context=context, plaintext=bytes(payload))
            # Plaintext surviving verbatim in the stored object means no encryption.
            if len(payload) >= 16 and bytes(payload) in sealed.ciphertext:
                raise MemoryStoreCorrupted("CONTENT_NOT_ENCRYPTED", "cipher returned plaintext")
            self._content.put(staged.content_object_ref, staged.partition.digest, sealed)
        self._read_content(staged, content_digest)

    def _read_content(self, staged: StagedVersion, content_digest: str) -> bytes:
        sealed = self._content.get(staged.content_object_ref)
        if sealed is None:
            raise _not_ready("CONTENT_UNAVAILABLE", "content object is not readable")
        try:
            plaintext = self._cipher.open(
                context=self._cipher_context(staged, content_digest), sealed=sealed
            )
        except Exception as exc:  # noqa: BLE001 -- any decrypt failure is corruption
            raise MemoryStoreCorrupted("CONTENT_UNSEALABLE", "content does not open") from exc
        if not hmac.compare_digest(_sha256(plaintext), content_digest):
            raise MemoryStoreCorrupted("CONTENT_DIGEST_MISMATCH", "content does not bind digest")
        return plaintext

    def _write_projection(
        self,
        partition: MemoryPartition,
        item: GovernedMemoryItem,
        pointer: RepresentationPointer,
        document: str | None,
        vector: tuple[float, ...] | None,
    ) -> None:
        payload = pointer.to_mapping()
        if pointer.representation_kind is RepresentationKind.FULL_TEXT:
            assert document is not None
            self._lexical.upsert(
                partition, self._limits.lexical_profile, pointer.store_ref, payload, document
            )
        elif pointer.representation_kind is RepresentationKind.VECTOR:
            assert vector is not None
            self._vector.upsert(
                partition, VectorProfile.for_item(item), pointer.store_ref, payload, vector
            )
        else:
            return  # STRUCTURED is the metadata record itself.
        if not self._projection_bound(partition, pointer):
            raise _not_ready("PROJECTION_UNVERIFIED", "projection read-back does not match")

    def _index(self, kind: RepresentationKind) -> MemoryLexicalIndexPort | MemoryVectorIndexPort:
        return self._lexical if kind is RepresentationKind.FULL_TEXT else self._vector

    def _projection_bound(self, partition: MemoryPartition, pointer: RepresentationPointer) -> bool:
        if pointer.representation_kind is RepresentationKind.STRUCTURED:
            return True
        stored = self._index(pointer.representation_kind).get(
            partition, pointer.representation_version, pointer.store_ref
        )
        return stored is not None and dict(stored) == pointer.to_mapping()

    def _receipt(self, stored: StoredVersion) -> StoreCommitReceipt:
        staged = stored.staged
        return StoreCommitReceipt(
            memory_version_ref=staged.memory_version_ref,
            item_digest=staged.item_digest,
            partition_ref=staged.partition.ref,
            content_object_ref=staged.content_object_ref,
            representations=tuple(
                (p.representation_kind.value, p.representation_version, p.store_ref)
                for p in staged.pointers
            ),
            state=stored.state.value,
            head_version=self._metadata.head(staged.memory_item_id),
            audit_ref=staged.audit_ref,
        )

    def _verify_committed(self, stored: StoredVersion) -> GovernedMemoryItem:
        item = stored.staged.verify()
        for pointer in stored.staged.pointers:
            registered = self._metadata.pointer(pointer.store_ref)
            if registered is None or registered != (pointer, VersionState.COMMITTED):
                raise MemoryStoreCorrupted("POINTER_UNBOUND", "committed pointer is not registered")
        return item

    # -- reads ------------------------------------------------------------

    def read_version(
        self, partition: MemoryPartition, memory_item_id: str, memory_version: int
    ) -> MaterializedVersion:
        """Materialise one exact committed version of the authorized partition."""

        stored = self._metadata.get(memory_item_id, memory_version)
        if stored is None or stored.staged.partition.digest != partition.digest:
            raise _not_visible()
        if stored.state is not VersionState.COMMITTED:
            raise _not_ready("VERSION_NOT_COMMITTED", "memory version is partially stored")
        item = self._verify_committed(stored)
        for pointer in stored.staged.pointers:
            if not self._projection_bound(partition, pointer):
                raise _not_ready("PROJECTION_DRIFT", "a committed projection is missing")
        payload = self._read_content(stored.staged, item.content_digest)
        return MaterializedVersion(
            item=item,
            payload=payload,
            pointers=stored.staged.pointers,
            partition_ref=partition.ref,
        )

    def read_latest(self, partition: MemoryPartition, memory_item_id: str) -> MaterializedVersion:
        """Follow the versioned head pointer to the latest committed version."""

        head = self._metadata.head(memory_item_id)
        if head < 1:
            raise _not_visible()
        return self.read_version(partition, memory_item_id, head)

    def lexical_candidates(
        self, partition: MemoryPartition, query: str, *, limit: int
    ) -> tuple[BoundHit, ...]:
        if not isinstance(query, str) or not query.strip():
            raise MemoryStoreError("MEMORY_SCHEMA_INVALID", "QUERY_INVALID", "query is empty")
        version = self._limits.lexical_profile.representation_version

        def page(offset: int) -> Sequence[IndexHit]:
            return self._lexical.search(
                partition, version, query, limit=self._limits.page_size, offset=offset
            )

        return self._bound_candidates(
            partition, RepresentationKind.FULL_TEXT, version, page, limit
        )

    def vector_candidates(
        self,
        partition: MemoryPartition,
        profile: VectorProfile,
        vector: Sequence[float],
        *,
        limit: int,
    ) -> tuple[BoundHit, ...]:
        try:
            values = [float(v) for v in vector if not isinstance(v, bool)]
        except (TypeError, ValueError) as exc:
            raise MemoryStoreError(
                "MEMORY_SCHEMA_INVALID", "QUERY_INVALID", "query vector must be numeric"
            ) from exc
        if len(values) != profile.embedding_dimensions or not all(map(math.isfinite, values)):
            raise MemoryStoreError(
                "MEMORY_SCHEMA_INVALID", "QUERY_INVALID", "query vector does not fit the profile"
            )
        version = profile.representation_version

        def page(offset: int) -> Sequence[IndexHit]:
            return self._vector.search(
                partition, version, values, limit=self._limits.page_size, offset=offset
            )

        return self._bound_candidates(partition, RepresentationKind.VECTOR, version, page, limit)

    def _bound_candidates(
        self,
        partition: MemoryPartition,
        kind: RepresentationKind,
        representation_version: str,
        page: Callable[[int], Sequence[IndexHit]],
        limit: int,
    ) -> tuple[BoundHit, ...]:
        """Only committed pointers occupy result slots; unbound hits are skipped.

        Pages are read until ``limit`` bound hits are found or the partition
        is exhausted, so unbound entries never displace a bound candidate.  A
        backlog of unbound entries beyond ``max_scanned_hits`` fails closed
        instead of silently returning a shorter result.
        """

        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise MemoryStoreError("MEMORY_SCHEMA_INVALID", "QUERY_INVALID", "limit must be >= 1")
        results: list[BoundHit] = []
        seen: set[str] = set()
        offset = 0
        while len(results) < limit:
            if offset >= self._limits.max_scanned_hits:
                raise _not_ready("UNBOUND_BACKLOG", "index requires reconciliation")
            hits = page(offset)
            for hit in hits:
                if hit.store_ref in seen:
                    continue
                seen.add(hit.store_ref)
                pointer = self._bound_pointer(partition, kind, representation_version, hit)
                if pointer is None:
                    continue
                results.append(
                    BoundHit(
                        memory_version_ref=pointer.memory_version_ref,
                        item_digest=pointer.item_digest,
                        content_digest=pointer.content_digest,
                        store_ref=pointer.store_ref,
                        representation_kind=pointer.representation_kind.value,
                        representation_version=pointer.representation_version,
                        classification_marking_ref=pointer.classification_marking_ref,
                        score=float(hit.score),
                    )
                )
                if len(results) == limit:
                    break
            if len(hits) < self._limits.page_size:
                break
            offset += len(hits)
        return tuple(results)

    def _bound_pointer(
        self,
        partition: MemoryPartition,
        kind: RepresentationKind,
        representation_version: str,
        hit: IndexHit,
    ) -> RepresentationPointer | None:
        try:
            pointer = RepresentationPointer.from_mapping(dict(hit.payload))
        except MemoryStoreError:
            return None
        if (
            pointer.store_ref != hit.store_ref
            or pointer.partition_digest != partition.digest
            or pointer.representation_kind is not kind
            or pointer.representation_version != representation_version
        ):
            return None
        registered = self._metadata.pointer(pointer.store_ref)
        if registered is None or registered != (pointer, VersionState.COMMITTED):
            return None
        return pointer

    def committed_count(self, partition: MemoryPartition) -> int:
        """Count of committed versions in the partition (pending ones never count)."""

        return sum(
            1
            for stored in self._metadata.versions_in(partition.digest)
            if stored.state is VersionState.COMMITTED
        )

    # -- reconciliation ---------------------------------------------------

    def reconcile(self) -> ReconciliationReport:
        """Roll complete pending versions forward and retract every partial or unbound one."""

        completed: list[str] = []
        retracted: list[str] = []
        deferred: list[str] = []
        unbound: list[str] = []
        removed_content: list[str] = []
        cutoff = self._clock.now() - self._limits.reconcile_grace
        for partition in self._metadata.partitions():
            versions = sorted(
                self._metadata.versions_in(partition.digest),
                key=lambda s: (s.staged.memory_item_id, s.staged.memory_version),
            )
            in_flight: set[str] = set()
            for stored in versions:
                if stored.state is VersionState.COMMITTED:
                    continue
                staged = stored.staged
                if parse_utc_timestamp(staged.staged_at) > cutoff:
                    in_flight.add(staged.memory_version_ref)
                    deferred.append(staged.memory_version_ref)
                    continue
                outcome = self._reconcile_pending(partition, staged)
                if outcome is _Outcome.COMPLETED:
                    completed.append(staged.memory_version_ref)
                elif outcome is _Outcome.RETRACTED:
                    retracted.append(staged.memory_version_ref)
                else:
                    # Complete but waiting for its predecessor: keep its projections.
                    deferred.append(staged.memory_version_ref)
                    in_flight.add(staged.memory_version_ref)
            refreshed = self._metadata.versions_in(partition.digest)
            unbound.extend(self._sweep_indexes(partition, refreshed, in_flight))
            removed_content.extend(self._sweep_content(partition, refreshed, in_flight))
        return ReconciliationReport(
            completed=tuple(completed),
            retracted=tuple(retracted),
            deferred=tuple(deferred),
            unbound_removed=tuple(unbound),
            content_removed=tuple(removed_content),
        )

    def _reconcile_pending(self, partition: MemoryPartition, staged: StagedVersion) -> _Outcome:
        item = staged.verify()
        try:
            self._read_content(staged, item.content_digest)
            complete = all(self._projection_bound(partition, p) for p in staged.pointers)
        except MemoryStoreError:
            complete = False
        if complete:
            head = self._metadata.head(staged.memory_item_id)
            if staged.memory_version != head + 1:
                return _Outcome.DEFERRED
            self._metadata.commit(
                staged.memory_item_id,
                staged.memory_version,
                stage_digest=staged.stage_digest,
                committed_at=format_utc_timestamp(self._clock.now()),
            )
            return _Outcome.COMPLETED
        # Not protected as in flight: the index and content sweeps that follow
        # remove every projection and content object this version left behind.
        return _Outcome.RETRACTED

    def _sweep_indexes(
        self,
        partition: MemoryPartition,
        versions: Sequence[StoredVersion],
        in_flight: set[str],
    ) -> list[str]:
        committed: dict[str, RepresentationPointer] = {}
        protected: dict[str, RepresentationPointer] = {}
        layouts: set[tuple[RepresentationKind, str]] = {
            (RepresentationKind.FULL_TEXT, self._limits.lexical_profile.representation_version)
        }
        for stored in versions:
            for pointer in stored.staged.pointers:
                if pointer.representation_kind is not RepresentationKind.STRUCTURED:
                    layouts.add((pointer.representation_kind, pointer.representation_version))
                if stored.state is VersionState.COMMITTED:
                    committed[pointer.store_ref] = pointer
                elif stored.staged.memory_version_ref in in_flight:
                    protected[pointer.store_ref] = pointer
        removed: list[str] = []
        for kind, version in sorted(layouts, key=lambda layout: (layout[0].value, layout[1])):
            index = self._index(kind)
            for hit in index.entries(partition, version):
                expected = committed.get(hit.store_ref) or protected.get(hit.store_ref)
                if expected is not None and dict(hit.payload) == expected.to_mapping():
                    continue
                index.remove(partition, version, hit.store_ref)
                removed.append(hit.store_ref)
        return removed

    def _sweep_content(
        self,
        partition: MemoryPartition,
        versions: Sequence[StoredVersion],
        in_flight: set[str],
    ) -> list[str]:
        keep = {
            stored.staged.content_object_ref
            for stored in versions
            if stored.state is VersionState.COMMITTED
            or stored.staged.memory_version_ref in in_flight
        }
        removed: list[str] = []
        for ref in self._content.refs(partition.digest):
            if ref not in keep:
                self._content.delete(ref)
                removed.append(ref)
        return removed


__all__ = [
    "BoundHit",
    "ContentCipher",
    "IndexHit",
    "LexicalProfile",
    "MaterializedVersion",
    "MemoryContentStore",
    "MemoryLexicalIndexPort",
    "MemoryMetadataStore",
    "MemoryPartition",
    "MemoryStoreCoordinator",
    "MemoryStoreCorrupted",
    "MemoryStoreError",
    "MemoryVectorIndexPort",
    "ReconciliationReport",
    "RepresentationPointer",
    "SealedContent",
    "StagedVersion",
    "StoreCommitReceipt",
    "StoreLimits",
    "StoredVersion",
    "VectorProfile",
    "VersionState",
    "content_object_ref",
    "lexical_document",
    "predecessor_not_committed",
    "stage_conflict",
    "structured_representation_version",
    "validate_embedding",
    "vector_digest",
]
