"""OCOR-DEV-0046: Implement C8 AgentRun Task Assignment Commitment
Handoff and Dissent.

Proves that agent/team state transitions (assignment, commitment,
handoff, dissent) all require a real, independently-issued capability
lease, are durably written through the sealed C3 canonical commit
path, and that none of the three negative claims can be bypassed: an
agent cannot self-grant a capability (a fabricated lease id, a
wrong-capability lease, a wrong-resource lease, and a revoked lease
are all refused identically to a real authority denial), cannot
mutate canonical state directly (the sealed AtomicOutboxStore's own
single-writer boundary refuses a write from any writer_id other than
the orchestrator itself), and cannot suppress a registered dissent
(there is no method to remove, retract or overwrite one). Pure,
in-memory, deterministic component (no external service needed, like
OCOR-DEV-0028/0030/0042/0043/0044/0045's own C1/C6/C7 slices).
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta

import pytest
from ocor_runtime.c3_store import AtomicOutboxStore
from ocor_runtime.c6_capabilities import CapabilityAuthority
from ocor_runtime.c8.orchestrator import AgentRunOrchestrator, Dissent, OrchestratorError
from ocor_runtime.errors import SingleWriterViolation

NOW = datetime(2026, 9, 14, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def authority() -> CapabilityAuthority:
    return CapabilityAuthority(issuer="ocor-c8-orchestrator-authority")


@pytest.fixture
def store() -> AtomicOutboxStore:
    return AtomicOutboxStore(authoritative_writer="ocor-c8-orchestrator")


@pytest.fixture
def orchestrator(authority: CapabilityAuthority, store: AtomicOutboxStore) -> AgentRunOrchestrator:
    return AgentRunOrchestrator(authority=authority, store=store)


def grant(authority: CapabilityAuthority, *, subject: str, capability: str, resource: str, ttl: timedelta = timedelta(hours=1)):
    return authority.issue(subject=subject, capabilities=[capability], resources=[resource], issued_at=NOW, ttl=ttl)


def test_the_full_assign_commit_dissent_lifecycle_writes_real_canonical_state(
    orchestrator: AgentRunOrchestrator, authority: CapabilityAuthority, store: AtomicOutboxStore
) -> None:
    assign_lease = grant(authority, subject="team-lead-1", capability="agent:assign", resource="agent-1")
    assignment = orchestrator.assign("task-1", "agent-1", capability="act:do-thing", lease=assign_lease, assigned_by="team-lead-1", at=NOW)
    assert assignment.agent_id == "agent-1"
    assert store.get("urn:ocor:agentrun:assignment:task-1") is not None

    commit_lease = grant(authority, subject="agent-1", capability="agent:commit", resource="agent-1")
    commitment = orchestrator.commit("task-1", lease=commit_lease, at=NOW)
    assert commitment.agent_id == "agent-1"
    assert store.get("urn:ocor:agentrun:commitment:task-1") is not None

    dissent_lease = grant(authority, subject="agent-1", capability="agent:dissent", resource="agent-1")
    dissent = orchestrator.register_dissent("task-1", "agent-1", reason="risk ceiling exceeded", lease=dissent_lease, at=NOW)
    assert dissent.reason == "risk ceiling exceeded"
    assert orchestrator.dissents == (dissent,)
    assert store.get("urn:ocor:agentrun:dissent:task-1:0") is not None


def test_handoff_transfers_the_commitment_to_a_new_agent(orchestrator: AgentRunOrchestrator, authority: CapabilityAuthority) -> None:
    assign_lease = grant(authority, subject="team-lead-1", capability="agent:assign", resource="agent-1")
    orchestrator.assign("task-2", "agent-1", capability="act:do-thing", lease=assign_lease, assigned_by="team-lead-1", at=NOW)
    commit_lease = grant(authority, subject="agent-1", capability="agent:commit", resource="agent-1")
    orchestrator.commit("task-2", lease=commit_lease, at=NOW)

    handoff_lease = grant(authority, subject="agent-2", capability="agent:handoff", resource="agent-2")
    record = orchestrator.handoff("task-2", to_agent_id="agent-2", reason="agent-1 is overloaded", lease=handoff_lease, at=NOW)

    assert record.from_agent_id == "agent-1"
    assert record.to_agent_id == "agent-2"
    assert orchestrator.handoffs == (record,)
    assert orchestrator.assignment("task-2").agent_id == "agent-2"
    assert orchestrator.commitment("task-2").agent_id == "agent-2"

    # the new agent can now commit again using its own real lease
    second_commit_lease = grant(authority, subject="agent-2", capability="agent:commit", resource="agent-2")
    recommitment = orchestrator.commit("task-2", lease=second_commit_lease, at=NOW)
    assert recommitment.agent_id == "agent-2"


def test_a_handoff_without_a_reason_is_refused(orchestrator: AgentRunOrchestrator, authority: CapabilityAuthority) -> None:
    assign_lease = grant(authority, subject="team-lead-1", capability="agent:assign", resource="agent-1")
    orchestrator.assign("task-3", "agent-1", capability="act:do-thing", lease=assign_lease, assigned_by="team-lead-1", at=NOW)
    commit_lease = grant(authority, subject="agent-1", capability="agent:commit", resource="agent-1")
    orchestrator.commit("task-3", lease=commit_lease, at=NOW)

    handoff_lease = grant(authority, subject="agent-2", capability="agent:handoff", resource="agent-2")
    with pytest.raises(OrchestratorError) as excinfo:
        orchestrator.handoff("task-3", to_agent_id="agent-2", reason="", lease=handoff_lease, at=NOW)
    assert excinfo.value.reason_code == "HANDOFF_REASON_REQUIRED"


def test_committing_or_handing_off_an_unassigned_task_is_refused(orchestrator: AgentRunOrchestrator, authority: CapabilityAuthority) -> None:
    commit_lease = grant(authority, subject="agent-1", capability="agent:commit", resource="agent-1")
    with pytest.raises(OrchestratorError) as excinfo:
        orchestrator.commit("never-assigned", lease=commit_lease, at=NOW)
    assert excinfo.value.reason_code == "UNKNOWN_TASK"

    handoff_lease = grant(authority, subject="agent-2", capability="agent:handoff", resource="agent-2")
    with pytest.raises(OrchestratorError) as excinfo:
        orchestrator.handoff("never-committed", to_agent_id="agent-2", reason="x", lease=handoff_lease, at=NOW)
    assert excinfo.value.reason_code == "UNKNOWN_TASK"


# --- an agent cannot self-grant a capability ---------------------------------


def test_a_fabricated_lease_id_never_issued_by_the_authority_is_refused(orchestrator: AgentRunOrchestrator) -> None:
    with pytest.raises(OrchestratorError) as excinfo:
        orchestrator.assign("task-4", "agent-1", capability="act:do-thing", lease="agent-1-made-this-up", assigned_by="agent-1", at=NOW)
    assert excinfo.value.reason_code == "CAPABILITY_DENIED"


def test_a_lease_for_a_different_capability_is_refused(orchestrator: AgentRunOrchestrator, authority: CapabilityAuthority) -> None:
    wrong_capability_lease = grant(authority, subject="agent-1", capability="agent:invoke", resource="agent-1")
    with pytest.raises(OrchestratorError) as excinfo:
        orchestrator.register_dissent("task-5", "agent-1", reason="x", lease=wrong_capability_lease, at=NOW)
    assert excinfo.value.reason_code == "CAPABILITY_DENIED"


def test_a_lease_scoped_to_a_different_resource_is_refused(orchestrator: AgentRunOrchestrator, authority: CapabilityAuthority) -> None:
    wrong_resource_lease = grant(authority, subject="agent-1", capability="agent:dissent", resource="agent-999")
    with pytest.raises(OrchestratorError) as excinfo:
        orchestrator.register_dissent("task-6", "agent-1", reason="x", lease=wrong_resource_lease, at=NOW)
    assert excinfo.value.reason_code == "CAPABILITY_DENIED"


def test_a_revoked_lease_is_refused_even_though_it_was_valid_when_issued(orchestrator: AgentRunOrchestrator, authority: CapabilityAuthority) -> None:
    lease = grant(authority, subject="agent-1", capability="agent:dissent", resource="agent-1")
    authority.revoke(lease.lease_id, at=NOW)
    with pytest.raises(OrchestratorError) as excinfo:
        orchestrator.register_dissent("task-7", "agent-1", reason="x", lease=lease, at=NOW)
    assert excinfo.value.reason_code == "CAPABILITY_DENIED"


# --- an agent cannot mutate canonical state directly -------------------------


def test_an_agent_cannot_write_canonical_state_directly_only_the_orchestrator_can(store: AtomicOutboxStore) -> None:
    """Real fault injection: the sealed AtomicOutboxStore's own
    single-writer boundary -- not anything this task adds -- refuses
    a write from any writer_id other than the orchestrator's own."""
    with pytest.raises(SingleWriterViolation):
        store.write(
            "urn:ocor:agentrun:assignment:tampered",
            {"task_id": "tampered", "agent_id": "agent-1"},
            expected_version=None,
            writer_id="agent-1",
            event_type="agentrun-task-assigned",
            idempotency_key="tampered",
            occurred_at=NOW,
        )


# --- dissent can never be suppressed -----------------------------------------


def test_dissent_is_append_only_and_the_class_exposes_no_removal_method(orchestrator: AgentRunOrchestrator, authority: CapabilityAuthority) -> None:
    lease_a = grant(authority, subject="agent-1", capability="agent:dissent", resource="agent-1")
    lease_b = grant(authority, subject="agent-1", capability="agent:dissent", resource="agent-1")
    first = orchestrator.register_dissent("task-8", "agent-1", reason="first objection", lease=lease_a, at=NOW)
    second = orchestrator.register_dissent("task-8", "agent-1", reason="second objection", lease=lease_b, at=NOW)

    assert orchestrator.dissents == (first, second)
    assert not any(name.startswith(("remove", "retract", "delete", "clear", "update")) for name in dir(orchestrator) if "dissent" in name.lower())


def test_a_dissent_record_itself_is_frozen_and_cannot_be_mutated() -> None:
    dissent = Dissent(task_id="task-9", agent_id="agent-1", reason="objection", registered_at=NOW)
    with pytest.raises(FrozenInstanceError):
        dissent.reason = "tampered"  # type: ignore[misc]


def test_a_dissent_without_a_reason_is_refused(orchestrator: AgentRunOrchestrator, authority: CapabilityAuthority) -> None:
    lease = grant(authority, subject="agent-1", capability="agent:dissent", resource="agent-1")
    with pytest.raises(OrchestratorError) as excinfo:
        orchestrator.register_dissent("task-10", "agent-1", reason="", lease=lease, at=NOW)
    assert excinfo.value.reason_code == "DISSENT_REASON_REQUIRED"
