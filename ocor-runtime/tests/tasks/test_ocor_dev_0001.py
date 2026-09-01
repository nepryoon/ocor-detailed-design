"""OCOR-DEV-0001 delivery-control and autonomous-runner tests."""

from __future__ import annotations

import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]


def load_module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


delivery = load_module("ocor_autonomous_delivery", "scripts/ocor_autonomous_delivery.py")
scope = load_module("validate_ocor_change_scope", "scripts/validate_ocor_change_scope.py")


@pytest.fixture(scope="module")
def plan():
    loaded = delivery.Plan.load(ROOT)
    assert loaded.validate() == []
    return loaded


def test_backlog_schema_context_and_dag_parse(plan):
    assert len(plan.tasks) == 69
    assert len(plan.dag_nodes) == 69
    assert plan.context_for("OCOR-DEV-0001")["max_input_tokens"] == 28000


def test_dependency_ready_selection_starts_with_task_0001(plan):
    state = delivery.new_state(plan)
    assert [task["id"] for task in delivery.ready_tasks(plan, state)] == ["OCOR-DEV-0001"]


def test_hard_dependency_blocks_and_acceptance_unblocks_task_0002(plan):
    state = delivery.new_state(plan)
    assert "OCOR-DEV-0002" not in {task["id"] for task in delivery.ready_tasks(plan, state)}
    state["tasks"]["OCOR-DEV-0001"]["status"] = "ACCEPTED"
    ready = {task["id"] for task in delivery.ready_tasks(plan, state)}
    assert {"OCOR-DEV-0002", "OCOR-DEV-0004"} <= ready


def test_delivery_gate_blocks_later_gate_until_prior_gate_closes(plan):
    state = delivery.new_state(plan)
    for task_id in plan.backlog["gates"]["G0"]["required_tasks"]:
        state["tasks"][task_id]["status"] = "ACCEPTED"
    assert any(task["delivery_gate"] == "G1" for task in delivery.ready_tasks(plan, state))
    state["tasks"]["OCOR-DEV-0006"]["status"] = "PENDING"
    assert all(task["delivery_gate"] == "G0" for task in delivery.ready_tasks(plan, state))


def test_cycle_detection_fails_closed():
    tasks = {
        "OCOR-DEV-0001": {"hard_dependencies": ["OCOR-DEV-0002"], "soft_dependencies": []},
        "OCOR-DEV-0002": {"hard_dependencies": ["OCOR-DEV-0001"], "soft_dependencies": []},
    }
    with pytest.raises(delivery.DeliveryError, match="cycle"):
        delivery.topological_order(tasks)


def test_retry_exhaustion_is_invalid(plan):
    state = delivery.new_state(plan)
    state["tasks"]["OCOR-DEV-0001"]["retries"] = plan.config["max_retries"] + 1
    assert any("retry budget exceeded" in error for error in delivery.validate_state(plan, state))


def test_state_recovery_releases_interrupted_ownership(plan):
    state = delivery.new_state(plan)
    state["tasks"]["OCOR-DEV-0001"]["status"] = "RUNNING"
    state["ownership_locks"]["OCOR-DEV-0001"] = [".github/CODEOWNERS"]
    assert delivery.recover_interrupted(state) == ["OCOR-DEV-0001"]
    assert state["tasks"]["OCOR-DEV-0001"]["status"] == "PENDING"
    assert not state["ownership_locks"]


def test_bounded_retry_recovery_stops_at_budget(plan):
    state = delivery.new_state(plan)
    task = state["tasks"]["OCOR-DEV-0001"]
    task.update(status="FAILED_IMPLEMENTATION", retries=1)
    assert delivery.recover_interrupted(state, max_retries=2) == ["OCOR-DEV-0001"]
    task.update(status="FAILED_IMPLEMENTATION", retries=2)
    assert delivery.recover_interrupted(state, max_retries=2) == []


def test_file_ownership_collision_is_rejected(plan):
    state = delivery.new_state(plan)
    state["ownership_locks"]["other"] = [".github"]
    with pytest.raises(delivery.DeliveryError, match="collision"):
        delivery.acquire_ownership(plan, state, "OCOR-DEV-0001")


def test_dry_run_does_not_create_state(plan, tmp_path, capsys):
    state_path = tmp_path / "state.json"
    assert delivery.main(["--repo", str(ROOT), "--state", str(state_path), "--dry-run"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["mutated"] is False
    assert output["selected"] == ["OCOR-DEV-0001"]
    assert not state_path.exists()


def test_red_ci_and_absent_required_context_block_promotion():
    green, reason = delivery.ci_is_green(
        [{"name": "validation-closure", "status": "COMPLETED", "conclusion": "FAILURE"}],
        ["validation-closure"],
    )
    assert green is False and "red" in reason
    green, reason = delivery.ci_is_green([], ["validation-closure"])
    assert green is False and "absent" in reason


@pytest.mark.parametrize("status", ["SKIPPED", "UNAVAILABLE", "NOT_EXECUTED", "XFAIL"])
def test_nonexecuted_results_cannot_be_promoted(plan, status):
    state = delivery.new_state(plan)
    state["tasks"]["OCOR-DEV-0001"]["status"] = status
    assert delivery.validate_state(plan, state)
    assert delivery.status_is_qualifying(status) is False


def test_stop_after_task_and_gate_are_deterministic():
    task = {"delivery_gate": "G0"}
    assert delivery.should_stop_after(task, Namespace(stop_after_task=True, stop_after_gate=None))
    assert delivery.should_stop_after(task, Namespace(stop_after_task=False, stop_after_gate="G0"))
    assert not delivery.should_stop_after(task, Namespace(stop_after_task=False, stop_after_gate="G1"))


def test_immutable_path_guard_rejects_negative_fixture():
    assert scope.is_immutable("inputs/normative/fixture.md")
    assert scope.main(["--repo", str(ROOT), "--path", "inputs/normative/fixture.md"]) == 1


def test_scope_validator_accepts_delivery_control_fixture():
    assert scope.main(["--repo", str(ROOT), "--path", ".github/CODEOWNERS"]) == 0


def test_bounded_prompt_contains_one_task_and_prohibited_claims(plan):
    prompt = delivery.bounded_prompt(plan, plan.tasks["OCOR-DEV-0001"])
    assert "OCOR-DEV-0001" in prompt
    assert "OCOR-DEV-0002" not in prompt
    assert "Production readiness" in prompt


def test_content_addressed_evidence_includes_matching_raw_log(plan):
    qualifying, commit = delivery.evidence_qualifies(ROOT, plan.tasks["OCOR-DEV-0001"])
    assert qualifying is True
    assert len(commit) == 40
