"""C6 -- complete 44-transition FSM table and effect-persistence runtime.

OCOR-DEV-0030 built retained, executable code for the single
representative path a risk-bearing action takes through LLD v1.1
section 3.2's normative C6 workflow (Authority -> Human Gate ->
Decision -> EMISSION-FENCE). This task builds the complementary,
complete piece OCOR-DEV-0030 deliberately left out of its own smallest
slice: a runtime transition table covering all 44 approved
transitions, and a generic mechanism that durably persists a record of
whichever transition's declared effect actually fires.

The table is parsed directly from the approved LLD document with the
same closed, five-column format OCOR-DEV-0020's sealed
``spikes.c6_fsm_fidelity.generator`` already proved fidelity for
(reimplemented here rather than imported, since ``spikes/`` lies
outside ``ocor-runtime``'s own pythonpath in production, the same
precedent OCOR-DEV-0028/0037/0040 already established) and validated
against the identical sealed digests at import time: any missing,
extra, duplicate or semantically altered transition -- a wrong source,
event/guard, durable effect or destination -- raises
``FSMTableIntegrityError`` before this module can even finish
importing, failing both local startup and CI.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any, Protocol

from ..c3_store import require_aware
from ..errors import OCORError

LLD_SHA256 = "bd464bfef50dc5a5e1b7ffac389fdf12be57a3b545225a92cf1564dc6a01d219"
TRANSITION_TABLE_SHA256 = "de1a242107f29c9e5106a3b4894fbb15dec8a77e52a62eb8d373b28931bb6eee"
TRANSITION_TABLE_MARKER = "### 3.2 Tabella completa delle 44 transizioni"
DEFAULT_LLD_PATH = Path(__file__).resolve().parents[4] / "docs" / "OCOR_LLD_v1.1.md"


class FSMTableIntegrityError(OCORError):
    """The runtime transition table is not identical to the approved LLD table."""


class FSMTransitionError(OCORError):
    """An FSM operation was refused. ``reason_code`` identifies why
    (UNKNOWN_TRANSITION), mirroring the reason-code pattern already
    established by the other retained C1-C8 components this session."""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {message}")


@dataclass(frozen=True, slots=True)
class Transition:
    transition_id: str
    source: str
    guard: str
    durable_effect: str
    destination: str


def _clean(cell: str) -> str:
    return cell.strip().replace("`", "")


def parse_transition_table(lld_path: Path) -> tuple[Transition, ...]:
    """Parse only the closed five-column table under LLD section 3.2,
    refusing to proceed at all unless the document is byte-identical
    to the approved, sealed baseline."""

    content = lld_path.read_bytes()
    actual_lld_digest = hashlib.sha256(content).hexdigest()
    if actual_lld_digest != LLD_SHA256:
        raise FSMTableIntegrityError(f"approved LLD digest mismatch: {actual_lld_digest}")
    text = content.decode("utf-8")
    try:
        table = text.split(TRANSITION_TABLE_MARKER, 1)[1].lstrip().split("\n\n", 1)[0]
    except IndexError as exc:
        raise FSMTableIntegrityError("LLD section 3.2 transition table not found") from exc

    transitions: list[Transition] = []
    for line in table.splitlines():
        if not line.startswith("| `ACT-"):
            continue
        cells = [_clean(cell) for cell in line.strip().strip("|").split("|")]
        if len(cells) != 5:
            raise FSMTableIntegrityError(f"transition row must have exactly five cells: {line}")
        transitions.append(Transition(*cells))
    return tuple(transitions)


def canonical_bytes(transitions: Iterable[Transition]) -> bytes:
    body = [asdict(item) for item in transitions]
    return json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def transition_digest(transitions: Iterable[Transition]) -> str:
    return hashlib.sha256(canonical_bytes(transitions)).hexdigest()


def validate_transition_set(transitions: Iterable[Transition]) -> tuple[Transition, ...]:
    """Fail on missing, extra, duplicate or altered transition semantics."""

    candidate = tuple(transitions)
    ids = [item.transition_id for item in candidate]
    if len(candidate) != 44:
        raise FSMTableIntegrityError(f"expected exactly 44 transitions, found {len(candidate)}")
    if len(set(ids)) != len(ids):
        raise FSMTableIntegrityError("duplicate transition id")
    if not all(
        item.transition_id.startswith("ACT-T") and item.source and item.guard and item.durable_effect and item.destination
        for item in candidate
    ):
        raise FSMTableIntegrityError("empty or malformed transition field")
    digest = transition_digest(candidate)
    if digest != TRANSITION_TABLE_SHA256:
        raise FSMTableIntegrityError(f"transition table semantic digest mismatch: {digest}")
    return candidate


def load_transitions(lld_path: Path = DEFAULT_LLD_PATH) -> tuple[Transition, ...]:
    return validate_transition_set(parse_transition_table(lld_path))


TRANSITIONS: tuple[Transition, ...] = load_transitions()


@dataclass(frozen=True, slots=True)
class PersistedEffect:
    """An immutable, durable record that a declared transition effect
    actually fired -- never mutated once persisted."""

    transition_id: str
    source: str
    destination: str
    durable_effect: str
    occurred_at: datetime
    correlation_id: str
    context: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_aware(self.occurred_at, field="occurred_at")
        if not self.correlation_id:
            raise ValueError("a PersistedEffect requires a correlation_id")
        object.__setattr__(self, "context", MappingProxyType(dict(self.context)))


class EffectSink(Protocol):
    def persist_effect(self, record: PersistedEffect) -> None: ...


class GovernedActionFSM:
    """The complete, approved 44-transition C6 table, executable as a
    generic lookup-and-persist runtime: applying a transition always
    durably records its declared effect via an injected sink before
    returning, whether or not any caller also implements that
    transition's substantive domain semantics elsewhere (as
    OCOR-DEV-0030's engine does for the four gates on the
    representative path)."""

    def __init__(self, transitions: tuple[Transition, ...] = TRANSITIONS) -> None:
        self._by_id = {item.transition_id: item for item in transitions}

    @property
    def transitions(self) -> tuple[Transition, ...]:
        return tuple(self._by_id.values())

    def transition(self, transition_id: str) -> Transition:
        try:
            return self._by_id[transition_id]
        except KeyError:
            raise FSMTransitionError("UNKNOWN_TRANSITION", f"no such C6 transition: {transition_id!r}") from None

    def apply(
        self,
        transition_id: str,
        *,
        sink: EffectSink | Callable[[PersistedEffect], Any],
        at: datetime,
        correlation_id: str,
        context: Mapping[str, Any] | None = None,
    ) -> PersistedEffect:
        transition = self.transition(transition_id)
        record = PersistedEffect(
            transition_id=transition.transition_id,
            source=transition.source,
            destination=transition.destination,
            durable_effect=transition.durable_effect,
            occurred_at=require_aware(at, field="at"),
            correlation_id=correlation_id,
            context=context or {},
        )
        if hasattr(sink, "persist_effect"):
            sink.persist_effect(record)
        else:
            sink(record)
        return record
