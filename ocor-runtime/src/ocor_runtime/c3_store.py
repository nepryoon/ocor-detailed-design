"""C3 — single-writer aggregate store with an atomic transactional outbox."""

from __future__ import annotations

import copy
import hashlib
import threading
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any, Callable

from .canonical import canonical_sha256, canonicalize
from .errors import (
    ConcurrencyConflict,
    CrashInjected,
    SingleWriterViolation,
    TemporalGuardViolation,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def require_aware(instant: datetime, *, field: str = "instant") -> datetime:
    if not isinstance(instant, datetime) or instant.tzinfo is None:
        raise TemporalGuardViolation(f"{field} must be timezone-aware")
    if instant.utcoffset() is None:
        raise TemporalGuardViolation(f"{field} must have a defined UTC offset")
    return instant


def freeze_json(value: Any) -> Any:
    """Recursively freeze already-canonicalizable JSON without changing meaning."""

    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("JSON object keys must be strings")
        return MappingProxyType({key: freeze_json(item) for key, item in value.items()})
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(freeze_json(item) for item in value)
    return copy.deepcopy(value)


class CrashWindow(str, Enum):
    """The five durability boundaries required by BA-01."""

    BEFORE_TRANSACTION = "before-transaction"
    AFTER_TRANSACTION_BEGIN = "after-transaction-begin"
    AFTER_AGGREGATE_STAGE = "after-aggregate-stage"
    AFTER_OUTBOX_STAGE = "after-outbox-stage"
    AFTER_COMMIT_BEFORE_ACK = "after-commit-before-ack"


@dataclass(frozen=True, slots=True)
class StoredDocument:
    aggregate_id: str
    document: Mapping[str, Any]
    version: int
    writer_id: str
    transaction_id: str
    semantic_digest: str
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class OutboxEvent:
    event_id: str
    aggregate_id: str
    aggregate_version: int
    event_type: str
    payload: Mapping[str, Any]
    payload_digest: str
    request_digest: str
    idempotency_key: str
    transaction_id: str
    occurred_at: datetime
    committed: bool = True
    emitted_at: datetime | None = None

    def verify_integrity(self) -> bool:
        return canonical_sha256(self.payload) == self.payload_digest


@dataclass(frozen=True, slots=True)
class WriteResult:
    document: StoredDocument
    event: OutboxEvent
    replayed: bool = False


class AtomicOutboxStore:
    """In-memory reference implementation of the C3 transaction contract.

    The implementation stages the aggregate and event privately, publishes both
    under one lock, and retains idempotency state in the same commit.  The crash
    injection points make the contract executable without relying on process
    timing or nondeterministic fault injection.
    """

    def __init__(self, *, authoritative_writer: str = "ocor-core") -> None:
        if not authoritative_writer:
            raise ValueError("authoritative_writer must be non-empty")
        self.authoritative_writer = authoritative_writer
        self._documents: dict[str, StoredDocument] = {}
        self._events: dict[str, OutboxEvent] = {}
        self._idempotency: dict[str, str] = {}
        self._lock = threading.RLock()

    @property
    def supports_atomic_multi_document_writes(self) -> bool:
        return True

    def _authorize_writer(self, writer_id: str) -> None:
        if writer_id != self.authoritative_writer:
            raise SingleWriterViolation(
                f"writer {writer_id!r} is outside the {self.authoritative_writer!r} boundary"
            )

    @staticmethod
    def _raise_if(window: CrashWindow | str | None, target: CrashWindow, *, committed: bool) -> None:
        if window is None:
            return
        try:
            selected = CrashWindow(window)
        except ValueError as exc:
            raise ValueError(f"unknown crash window: {window!r}") from exc
        if selected is target:
            raise CrashInjected(target.value, committed=committed)

    def write(
        self,
        aggregate_id: str,
        document: Mapping[str, Any],
        *,
        expected_version: int | None,
        writer_id: str,
        event_type: str,
        event_payload: Mapping[str, Any] | None = None,
        idempotency_key: str,
        occurred_at: datetime | None = None,
        crash_window: CrashWindow | str | None = None,
    ) -> WriteResult:
        if not aggregate_id or not event_type or not idempotency_key:
            raise ValueError("aggregate_id, event_type and idempotency_key are required")
        if expected_version is not None and expected_version < 0:
            raise ValueError("expected_version cannot be negative")
        self._authorize_writer(writer_id)
        instant = require_aware(occurred_at or _utc_now(), field="occurred_at")
        stable_document = freeze_json(document)
        stable_payload = freeze_json(event_payload if event_payload is not None else document)
        request_digest = canonical_sha256(
            {
                "aggregateId": aggregate_id,
                "document": stable_document,
                "eventType": event_type,
                "payload": stable_payload,
            }
        )

        self._raise_if(crash_window, CrashWindow.BEFORE_TRANSACTION, committed=False)
        with self._lock:
            replay_event_id = self._idempotency.get(idempotency_key)
            if replay_event_id is not None:
                event = self._events[replay_event_id]
                if event.request_digest != request_digest:
                    raise ConcurrencyConflict(
                        "idempotency key was reused for a different write request"
                    )
                return WriteResult(self._documents[event.aggregate_id], event, replayed=True)

            current = self._documents.get(aggregate_id)
            current_version = current.version if current is not None else 0
            if expected_version is not None and expected_version != current_version:
                raise ConcurrencyConflict(
                    f"expected aggregate version {expected_version}, found {current_version}"
                )
            if current is not None and instant < current.updated_at:
                raise TemporalGuardViolation("aggregate time cannot move backwards")

            self._raise_if(
                crash_window,
                CrashWindow.AFTER_TRANSACTION_BEGIN,
                committed=False,
            )
            version = current_version + 1
            transaction_id = str(uuid.uuid4())
            event_seed = canonicalize(
                {
                    "aggregateId": aggregate_id,
                    "idempotencyKey": idempotency_key,
                    "requestDigest": request_digest,
                }
            )
            event_id = "urn:ocor:event:sha256:" + hashlib.sha256(event_seed).hexdigest()
            staged_document = StoredDocument(
                aggregate_id=aggregate_id,
                document=stable_document,
                version=version,
                writer_id=writer_id,
                transaction_id=transaction_id,
                semantic_digest=canonical_sha256(stable_document),
                updated_at=instant,
            )

            self._raise_if(
                crash_window,
                CrashWindow.AFTER_AGGREGATE_STAGE,
                committed=False,
            )
            staged_event = OutboxEvent(
                event_id=event_id,
                aggregate_id=aggregate_id,
                aggregate_version=version,
                event_type=event_type,
                payload=stable_payload,
                payload_digest=canonical_sha256(stable_payload),
                request_digest=request_digest,
                idempotency_key=idempotency_key,
                transaction_id=transaction_id,
                occurred_at=instant,
            )
            self._raise_if(
                crash_window,
                CrashWindow.AFTER_OUTBOX_STAGE,
                committed=False,
            )

            # Copy-on-commit means readers can observe the old snapshot or the
            # complete new snapshot, never an aggregate/outbox half-state.
            documents = dict(self._documents)
            events = dict(self._events)
            idempotency = dict(self._idempotency)
            documents[aggregate_id] = staged_document
            events[event_id] = staged_event
            idempotency[idempotency_key] = event_id
            self._documents, self._events, self._idempotency = (
                documents,
                events,
                idempotency,
            )

            self._raise_if(
                crash_window,
                CrashWindow.AFTER_COMMIT_BEFORE_ACK,
                committed=True,
            )
            return WriteResult(staged_document, staged_event)

    transactional_write = write

    def get(self, aggregate_id: str) -> StoredDocument | None:
        with self._lock:
            return self._documents.get(aggregate_id)

    def get_event(self, event_id: str) -> OutboxEvent | None:
        with self._lock:
            return self._events.get(event_id)

    def outbox(self, *, include_emitted: bool = False) -> tuple[OutboxEvent, ...]:
        with self._lock:
            events = (
                event
                for event in self._events.values()
                if include_emitted or event.emitted_at is None
            )
            return tuple(
                sorted(
                    events,
                    key=lambda event: (
                        event.occurred_at,
                        event.aggregate_id,
                        event.aggregate_version,
                        event.event_id,
                    ),
                )
            )

    def mark_emitted(self, event_id: str, emitted_at: datetime) -> OutboxEvent:
        instant = require_aware(emitted_at, field="emitted_at")
        with self._lock:
            event = self._events[event_id]
            if instant < event.occurred_at:
                raise TemporalGuardViolation("event cannot be emitted before it occurred")
            if event.emitted_at is not None:
                return event
            emitted = replace(event, emitted_at=instant)
            events = dict(self._events)
            events[event_id] = emitted
            self._events = events
            return emitted

    def snapshot_counts(self) -> tuple[int, int]:
        with self._lock:
            return len(self._documents), len(self._events)

    def verify_atomicity(self) -> bool:
        """Confirm every durable aggregate transaction has exactly one event."""

        with self._lock:
            transactions = {event.transaction_id for event in self._events.values()}
            return all(
                document.transaction_id in transactions
                for document in self._documents.values()
            ) and all(
                event.aggregate_id in self._documents
                and self._documents[event.aggregate_id].version >= event.aggregate_version
                for event in self._events.values()
            )


DocumentStore = AtomicOutboxStore
