from __future__ import annotations

from pathlib import Path

import pytest

from spikes.c6_fsm_fidelity.generator import (
    TRANSITION_TABLE_SHA256,
    Transition,
    TransitionFidelityError,
    generate_from_lld,
    mutated,
    transition_digest,
    validate_transition_set,
)

ROOT = Path(__file__).resolve().parents[3]
LLD = ROOT / "docs/OCOR_LLD_v1.1.md"


@pytest.fixture(scope="module")
def transitions() -> tuple[Transition, ...]:
    return generate_from_lld(LLD)


def test_generated_table_has_all_44_unique_lld_transition_ids(transitions):
    assert len(transitions) == 44
    assert len({item.transition_id for item in transitions}) == 44
    assert transitions[0].transition_id == "ACT-T01"
    assert transitions[-1].transition_id == "ACT-T31b"


def test_generated_sources_guards_effects_and_destinations_match_seal(transitions):
    assert transition_digest(transitions) == TRANSITION_TABLE_SHA256
    assert validate_transition_set(transitions) == transitions


def test_emission_fence_transitions_are_preserved_exactly(transitions):
    fenced = {
        item.transition_id: item
        for item in transitions
        if "EMISSION-FENCE" in item.guard or "EMISSION-FENCE" in item.durable_effect
    }
    assert set(fenced) == {"ACT-T12", "ACT-T14", "ACT-T19", "ACT-T21", "ACT-T29"}
    assert fenced["ACT-T12"].destination == "COMMAND_READY"
    assert fenced["ACT-T29"].destination == "CANONICAL_COMMIT_PENDING"


@pytest.mark.parametrize("mode", ["missing", "extra", "duplicate"])
def test_missing_extra_or_duplicate_transition_fails(mode, transitions):
    if mode == "missing":
        candidate = transitions[:-1]
    elif mode == "extra":
        candidate = transitions + (
            Transition("ACT-T99", "A", "guard", "effect", "B"),
        )
    else:
        candidate = transitions[:-1] + (transitions[0],)
    with pytest.raises(TransitionFidelityError):
        validate_transition_set(candidate)


def test_altered_durable_effect_fails_semantic_equality(transitions):
    changed = list(transitions)
    changed[11] = mutated(changed[11], durable_effect="command senza outbox")
    with pytest.raises(TransitionFidelityError, match="semantic digest mismatch"):
        validate_transition_set(changed)


def test_unsealed_or_modified_lld_is_rejected_before_generation(tmp_path, transitions):
    changed = tmp_path / "LLD.md"
    changed.write_text(LLD.read_text().replace("ACK correlato", "ACK non correlato"))
    with pytest.raises(TransitionFidelityError, match="LLD digest mismatch"):
        generate_from_lld(changed)
