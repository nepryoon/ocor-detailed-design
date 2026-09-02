"""Generate and seal the complete C6 transition table from the approved LLD."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass, replace
from pathlib import Path

LLD_SHA256 = "bd464bfef50dc5a5e1b7ffac389fdf12be57a3b545225a92cf1564dc6a01d219"
TRANSITION_TABLE_SHA256 = "de1a242107f29c9e5106a3b4894fbb15dec8a77e52a62eb8d373b28931bb6eee"


class TransitionFidelityError(RuntimeError):
    """The executable table is not identical to the approved LLD table."""


@dataclass(frozen=True, slots=True)
class Transition:
    transition_id: str
    source: str
    guard: str
    durable_effect: str
    destination: str


def _clean(cell: str) -> str:
    return cell.strip().replace("`", "")


def generate_from_lld(path: Path) -> tuple[Transition, ...]:
    """Parse only the closed five-column table under LLD section 3.2."""

    content = path.read_bytes()
    actual_lld_digest = hashlib.sha256(content).hexdigest()
    if actual_lld_digest != LLD_SHA256:
        raise TransitionFidelityError(
            f"approved LLD digest mismatch: {actual_lld_digest}"
        )
    text = content.decode("utf-8")
    marker = "### 3.2 Tabella completa delle 44 transizioni"
    try:
        table = text.split(marker, 1)[1].lstrip().split("\n\n", 1)[0]
    except IndexError as exc:
        raise TransitionFidelityError("LLD section 3.2 transition table not found") from exc

    transitions: list[Transition] = []
    for line in table.splitlines():
        if not line.startswith("| `ACT-"):
            continue
        cells = [_clean(cell) for cell in line.strip().strip("|").split("|")]
        if len(cells) != 5:
            raise TransitionFidelityError(
                f"transition row must have exactly five cells: {line}"
            )
        transitions.append(Transition(*cells))
    validate_transition_set(transitions, verify_seal=False)
    return tuple(transitions)


def canonical_bytes(transitions: Iterable[Transition]) -> bytes:
    body = [asdict(item) for item in transitions]
    return json.dumps(
        body, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def transition_digest(transitions: Iterable[Transition]) -> str:
    return hashlib.sha256(canonical_bytes(transitions)).hexdigest()


def validate_transition_set(
    transitions: Iterable[Transition], *, verify_seal: bool = True
) -> tuple[Transition, ...]:
    """Fail on missing, extra, duplicate or altered transition semantics."""

    generated = tuple(transitions)
    ids = [item.transition_id for item in generated]
    if len(generated) != 44:
        raise TransitionFidelityError(
            f"expected exactly 44 transitions, found {len(generated)}"
        )
    if len(set(ids)) != len(ids):
        raise TransitionFidelityError("duplicate transition id")
    if not all(
        item.transition_id.startswith("ACT-T")
        and item.source
        and item.guard
        and item.durable_effect
        and item.destination
        for item in generated
    ):
        raise TransitionFidelityError("empty or malformed transition field")
    if verify_seal:
        digest = transition_digest(generated)
        if digest != TRANSITION_TABLE_SHA256:
            raise TransitionFidelityError(
                f"transition table semantic digest mismatch: {digest}"
            )
    return generated


def mutated(
    transition: Transition, *, durable_effect: str | None = None
) -> Transition:
    """Test helper that preserves type and changes an explicit semantic field."""

    return replace(
        transition,
        durable_effect=durable_effect
        if durable_effect is not None
        else transition.durable_effect,
    )
