"""C7 — EMISSION-FENCE for durable, ordered and authorized effects."""

from __future__ import annotations

import threading
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any, Callable, Protocol

from .c3_store import AtomicOutboxStore, OutboxEvent, require_aware
from .c4_marking import MarkingEngine, MarkingSet
from .c6_capabilities import CapabilityAuthority, CapabilityLease
from .errors import EmissionBlocked


class EventSink(Protocol):
    def emit(self, event: OutboxEvent, *, idempotency_key: str) -> Any: ...


@dataclass(frozen=True, slots=True)
class EmissionReceipt:
    event_id: str
    aggregate_id: str
    aggregate_version: int
    emitted_at: datetime
    sink_result: Any = None
    deduplicated: bool = False


class EmissionFence:
    """Release only committed outbox events across the external boundary.

    The event idempotency key is always supplied to object sinks.  A sink failure
    produces no receipt and leaves the durable event pending for safe retry.
    """

    def __init__(
        self,
        *,
        store: AtomicOutboxStore | None = None,
        capability_authority: CapabilityAuthority | None = None,
        require_capability: bool = False,
        marking_engine: MarkingEngine | None = None,
    ) -> None:
        if require_capability and capability_authority is None:
            raise ValueError("a capability authority is required by this fence")
        self._store = store
        self._capability_authority = capability_authority
        self._require_capability = require_capability
        self._marking_engine = marking_engine
        self._registered: dict[str, OutboxEvent] = {}
        self._receipts: dict[str, EmissionReceipt] = {}
        self._last_version: dict[str, int] = {}
        self._lock = threading.RLock()

    def register(self, event: OutboxEvent) -> OutboxEvent:
        if self._store is not None:
            durable = self._store.get_event(event.event_id)
            if durable is None:
                raise EmissionBlocked("event is not present in the durable outbox")
            if replace(event, emitted_at=durable.emitted_at) != durable:
                raise EmissionBlocked("event does not match its durable outbox record")
            event = durable
        if not event.committed:
            raise EmissionBlocked("EMISSION-FENCE rejected an uncommitted event")
        if not event.verify_integrity():
            raise EmissionBlocked("EMISSION-FENCE rejected a payload digest mismatch")
        with self._lock:
            existing = self._registered.get(event.event_id)
            if existing is not None and existing != event:
                raise EmissionBlocked("event id collision at EMISSION-FENCE")
            self._registered[event.event_id] = event
            if event.emitted_at is not None and event.event_id not in self._receipts:
                receipt = EmissionReceipt(
                    event.event_id,
                    event.aggregate_id,
                    event.aggregate_version,
                    event.emitted_at,
                    deduplicated=True,
                )
                self._receipts[event.event_id] = receipt
                self._last_version[event.aggregate_id] = max(
                    event.aggregate_version,
                    self._last_version.get(event.aggregate_id, 0),
                )
            return event

    def _check_order(self, event: OutboxEvent) -> None:
        last = self._last_version.get(event.aggregate_id, 0)
        if event.aggregate_version <= last:
            raise EmissionBlocked("aggregate version was already passed by the fence")
        candidates = list(self._registered.values())
        if self._store is not None:
            candidates.extend(self._store.outbox(include_emitted=True))
        earlier_pending = [
            candidate
            for candidate in candidates
            if candidate.aggregate_id == event.aggregate_id
            and candidate.aggregate_version < event.aggregate_version
            and candidate.emitted_at is None
            and candidate.event_id not in self._receipts
        ]
        if earlier_pending:
            raise EmissionBlocked("an earlier aggregate event is still pending")

    @staticmethod
    def _call_sink(sink: EventSink | Callable[[OutboxEvent], Any], event: OutboxEvent) -> Any:
        emit_method = getattr(sink, "emit", None)
        if callable(emit_method):
            return emit_method(event, idempotency_key=event.idempotency_key)
        if callable(sink):
            return sink(event)
        raise TypeError("sink must be callable or provide emit(event, idempotency_key=...)")

    def emit(
        self,
        event: OutboxEvent,
        sink: EventSink | Callable[[OutboxEvent], Any],
        *,
        at: datetime,
        lease: CapabilityLease | str | None = None,
        subject: str | None = None,
        markings: MarkingSet | None = None,
        clearance: MarkingSet | None = None,
    ) -> EmissionReceipt:
        instant = require_aware(at, field="at")
        with self._lock:
            existing_receipt = self._receipts.get(event.event_id)
            if existing_receipt is not None:
                return EmissionReceipt(
                    existing_receipt.event_id,
                    existing_receipt.aggregate_id,
                    existing_receipt.aggregate_version,
                    existing_receipt.emitted_at,
                    existing_receipt.sink_result,
                    deduplicated=True,
                )
            event = self.register(event)
            if instant < event.occurred_at:
                raise EmissionBlocked("event cannot cross the fence before it occurred")
            self._check_order(event)

            if self._marking_engine is not None:
                if markings is None or clearance is None:
                    raise EmissionBlocked("marking and clearance are required for disclosure")
                if not self._marking_engine.is_authorized(markings, clearance):
                    raise EmissionBlocked("clearance does not dominate event markings")

            if self._require_capability:
                if lease is None or self._capability_authority is None:
                    raise EmissionBlocked("an emission capability lease is required")
                try:
                    self._capability_authority.authorize(
                        lease,
                        "emit",
                        event.aggregate_id,
                        at=instant,
                        subject=subject,
                        consume=True,
                    )
                except Exception as exc:
                    raise EmissionBlocked(f"emission capability rejected: {exc}") from exc

            # No state is advanced until the sink acknowledges.  The lock makes
            # duplicate in-process delivery impossible; the durable idempotency
            # key covers retry after a process crash.
            sink_result = self._call_sink(sink, event)
            receipt = EmissionReceipt(
                event.event_id,
                event.aggregate_id,
                event.aggregate_version,
                instant,
                sink_result,
            )
            if self._store is not None:
                self._store.mark_emitted(event.event_id, instant)
            self._receipts[event.event_id] = receipt
            self._last_version[event.aggregate_id] = event.aggregate_version
            return receipt

    def drain(
        self,
        sink: EventSink | Callable[[OutboxEvent], Any],
        *,
        at: datetime,
        lease: CapabilityLease | str | None = None,
        subject: str | None = None,
        markings: MarkingSet | None = None,
        clearance: MarkingSet | None = None,
    ) -> tuple[EmissionReceipt, ...]:
        if self._store is None:
            raise RuntimeError("drain requires a store-bound EMISSION-FENCE")
        events = self._store.outbox()
        for event in events:
            self.register(event)
        receipts = []
        for event in events:
            receipts.append(
                self.emit(
                    event,
                    sink,
                    at=at,
                    lease=lease,
                    subject=subject,
                    markings=markings,
                    clearance=clearance,
                )
            )
        return tuple(receipts)

    def receipt(self, event_id: str) -> EmissionReceipt | None:
        with self._lock:
            return self._receipts.get(event_id)


EMISSION_FENCE = EmissionFence
