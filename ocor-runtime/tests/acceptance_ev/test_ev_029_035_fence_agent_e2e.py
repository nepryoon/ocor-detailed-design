from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from ocor_runtime.c1_compiler import SemanticCompiler
from ocor_runtime.c2_identity import IdentityRecord, IdentityRegistry
from ocor_runtime.c3_store import AtomicOutboxStore
from ocor_runtime.c4_marking import MarkingEngine, MarkingSchemeDefinition, MarkingSet
from ocor_runtime.c5_actions import Action, ActionEvent, ActionFSM, ActionState
from ocor_runtime.c6_capabilities import CapabilityAuthority
from ocor_runtime.c7_emission import EmissionFence
from ocor_runtime.c8_agent import (
    AgentDecision,
    AgentKernel,
    AgentResponse,
    ModelResult,
    StrictSandbox,
    TokenBudget,
)
from ocor_runtime.errors import EmissionBlocked, SandboxViolation, TokenBudgetExceeded

pytestmark = pytest.mark.acceptance
SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"


def _events(fixed_now):
    store = AtomicOutboxStore()
    first = store.write(
        "aggregate-1",
        {"value": 1},
        expected_version=0,
        writer_id="ocor-core",
        event_type="created",
        idempotency_key="first",
        occurred_at=fixed_now,
    ).event
    second = store.write(
        "aggregate-1",
        {"value": 2},
        expected_version=1,
        writer_id="ocor-core",
        event_type="updated",
        idempotency_key="second",
        occurred_at=fixed_now + timedelta(seconds=1),
    ).event
    return store, first, second


def test_ev_029_emission_fence_blocks_uncommitted_or_integrity_broken_events(fixed_now):
    _, first, _ = _events(fixed_now)
    for invalid in (
        replace(first, committed=False),
        replace(first, payload={"value": "tampered"}),
    ):
        with pytest.raises(EmissionBlocked):
            EmissionFence().emit(invalid, lambda event: None, at=fixed_now)


def test_ev_030_emission_fence_orders_and_deduplicates_external_effects(fixed_now):
    store, first, second = _events(fixed_now)
    fence = EmissionFence(store=store)
    fence.register(first)
    fence.register(second)
    delivered = []
    with pytest.raises(EmissionBlocked):
        fence.emit(second, delivered.append, at=second.occurred_at)
    fence.emit(first, delivered.append, at=second.occurred_at)
    fence.emit(second, delivered.append, at=second.occurred_at)
    duplicate = fence.emit(second, delivered.append, at=second.occurred_at)
    assert [event.event_id for event in delivered] == [first.event_id, second.event_id]
    assert duplicate.deduplicated
    assert store.outbox() == ()


def test_ev_031_emission_requires_both_capability_and_marking_clearance(fixed_now):
    store, first, _ = _events(fixed_now)
    authority = CapabilityAuthority()
    lease = authority.issue(
        subject="emitter",
        capabilities=["emit"],
        resources=["aggregate-1"],
        issued_at=fixed_now,
        ttl=timedelta(minutes=1),
    )
    engine = MarkingEngine(
        [MarkingSchemeDefinition("classification", ["PUBLIC", "SECRET"])]
    )
    fence = EmissionFence(
        store=store,
        capability_authority=authority,
        require_capability=True,
        marking_engine=engine,
    )
    markings = MarkingSet({"classification": "SECRET"})
    with pytest.raises(EmissionBlocked):
        fence.emit(
            first,
            lambda event: None,
            at=fixed_now,
            lease=lease,
            subject="emitter",
            markings=markings,
            clearance=MarkingSet({"classification": "PUBLIC"}),
        )
    receipt = fence.emit(
        first,
        lambda event: "ack",
        at=fixed_now,
        lease=lease,
        subject="emitter",
        markings=markings,
        clearance=MarkingSet({"classification": "SECRET"}),
    )
    assert receipt.sink_result == "ack"


def test_ev_032_strict_sandbox_allows_pure_tools_and_blocks_escape_syntax():
    sandbox = StrictSandbox({"add": lambda left, right: left + right})
    assert sandbox.execute("add(value, 2) if value > 1 else 0", {"value": 3}) == 5
    forbidden = [
        "__import__('os')",
        "open('/etc/passwd')",
        "(1).__class__",
        "[item for item in [1, 2]]",
        "lambda: 1",
    ]
    for expression in forbidden:
        with pytest.raises(SandboxViolation):
            sandbox.execute(expression)


def test_ev_033_token_budget_preflights_and_enforces_actual_model_output():
    called = False

    def model(prompt, *, max_output_tokens):
        nonlocal called
        called = True
        return ModelResult(
            AgentResponse(AgentDecision.ABSTAIN, None, 0.0, "no evidence")
        )

    kernel = AgentKernel()
    tiny = TokenBudget(5)
    with pytest.raises(TokenBudgetExceeded):
        kernel.invoke(
            "one two",
            model,
            budget=tiny,
            max_output_tokens=4,
        )
    assert not called

    under_reserved = TokenBudget(100)
    with pytest.raises(TokenBudgetExceeded):
        kernel.invoke(
            "input",
            model,
            budget=under_reserved,
            max_output_tokens=1,
        )
    assert called
    assert under_reserved.reserved == 0


def test_ev_034_agent_kernel_identifies_only_uniquely_and_otherwise_abstains():
    registry = IdentityRegistry()
    registry.register(
        IdentityRecord("urn:ocor:identity:alice", aliases=frozenset({"alice"}))
    )
    registry.register(
        IdentityRecord("urn:ocor:identity:alicia", aliases=frozenset({"shared"}))
    )
    registry.add_alias("urn:ocor:identity:alice", "shared")
    kernel = AgentKernel(identity_registry=registry)
    identified = kernel.identify_or_abstain("alice", budget=TokenBudget(10))
    ambiguous = kernel.identify_or_abstain("shared", budget=TokenBudget(10))
    unknown = kernel.identify_or_abstain("unknown", budget=TokenBudget(10))
    assert identified.decision is AgentDecision.IDENTIFY
    assert identified.identity_id == "urn:ocor:identity:alice"
    assert ambiguous.decision is AgentDecision.ABSTAIN
    assert ambiguous.identity_id is None
    assert unknown.decision is AgentDecision.ABSTAIN


def test_ev_035_end_to_end_c1_through_c8_semantic_action_emission(fixed_now):
    # C2/C8: resolve the acting principal without guessing.
    registry = IdentityRegistry()
    registry.register(
        IdentityRecord("urn:ocor:identity:alice", aliases=frozenset({"alice"}))
    )
    kernel = AgentKernel(identity_registry=registry)
    principal = kernel.identify_or_abstain("alice", budget=TokenBudget(10))
    assert principal.decision is AgentDecision.IDENTIFY

    # C5: create a tamper-evident action transition.
    action = Action(
        "action-35",
        not_before=fixed_now,
        expires_at=fixed_now + timedelta(minutes=5),
    )
    action = ActionFSM().transition(
        action,
        ActionEvent.SUBMIT,
        occurred_at=fixed_now,
        actor=principal.identity_id,
    )
    assert action.state is ActionState.PROPOSED

    # C1/C4: validate and compile while keeping markings out of semantic identity.
    envelope = {
        "schemaVersion": "1.2",
        "kind": "Action",
        "objectId": action.action_id,
        "payload": {
            "actionId": action.action_id,
            "state": action.state.value,
            "version": action.version,
        },
        "markings": {"classification": "INTERNAL"},
    }
    compiler = SemanticCompiler.from_schema_file(SCHEMAS / "semantic-envelope.schema.json")
    artifact = compiler.compile(envelope)
    assert artifact.artifact_id.startswith("urn:ocor:sha256:")

    # C3: aggregate and event become visible in one transaction.
    store = AtomicOutboxStore()
    write = store.write(
        action.action_id,
        envelope,
        expected_version=0,
        writer_id="ocor-core",
        event_type="action.proposed",
        idempotency_key="EV-035",
        occurred_at=fixed_now,
    )
    assert store.verify_atomicity()

    # C6/C7: only a live, scoped lease and dominating clearance open the fence.
    authority = CapabilityAuthority()
    lease = authority.issue(
        subject=principal.identity_id,
        capabilities=["emit"],
        resources=[action.action_id],
        issued_at=fixed_now,
        ttl=timedelta(minutes=1),
    )
    marking_engine = MarkingEngine(
        [
            MarkingSchemeDefinition(
                "classification", ["PUBLIC", "INTERNAL", "SECRET"]
            )
        ]
    )

    class Sink:
        def __init__(self):
            self.deliveries = []

        def emit(self, event, *, idempotency_key):
            self.deliveries.append((event.event_id, idempotency_key))
            return "accepted"

    sink = Sink()
    receipt = EmissionFence(
        store=store,
        capability_authority=authority,
        require_capability=True,
        marking_engine=marking_engine,
    ).emit(
        write.event,
        sink,
        at=fixed_now,
        lease=lease,
        subject=principal.identity_id,
        markings=MarkingSet({"classification": "INTERNAL"}),
        clearance=MarkingSet({"classification": "SECRET"}),
    )
    assert receipt.sink_result == "accepted"
    assert sink.deliveries == [(write.event.event_id, "EV-035")]
    assert store.get_event(write.event.event_id).emitted_at == fixed_now

