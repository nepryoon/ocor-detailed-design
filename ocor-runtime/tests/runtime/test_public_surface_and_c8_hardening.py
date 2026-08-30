from __future__ import annotations

import importlib
from datetime import timedelta

import pytest

from ocor_runtime.c8_agent import (
    AgentDecision,
    AgentKernel,
    AgentResponse,
    ModelResult,
    StrictSandbox,
    TokenBudget,
    deterministic_token_count,
)
from ocor_runtime.c6_capabilities import CapabilityAuthority
from ocor_runtime.errors import AuthorizationError, SandboxViolation, TokenBudgetExceeded


def test_c1_through_c8_compatibility_modules_are_importable():
    for module in (
        "c1_compiler",
        "c2_identity",
        "c3_store",
        "c4_marking",
        "c5_actions",
        "c6_capabilities",
        "c7_emission",
        "c8_agent",
    ):
        assert importlib.import_module(module)


def test_token_budget_reservation_lifecycle_is_accounted_exactly():
    budget = TokenBudget(10)
    assert deterministic_token_count("one, two") == 3
    budget.consume_text("one two", category="input")
    reservation = budget.reserve(5, category="output")
    assert budget.used == 2
    assert budget.reserved == 5
    assert budget.remaining == 3
    budget.commit(reservation, used=3)
    assert budget.used == 5
    assert budget.reserved == 0
    assert budget.charges[-1].category == "output"
    cancelled = budget.reserve(4, category="cancelled")
    budget.cancel(cancelled)
    assert budget.remaining == 5
    with pytest.raises(TokenBudgetExceeded):
        budget.consume(6, category="overflow")


def test_sandbox_interpreter_supports_only_bounded_pure_expression_constructs():
    sandbox = StrictSandbox({"double": lambda value: value * 2})
    expression = """{
      "arithmetic": [1 + 2, 7 - 3, 3 * 2, 8 / 2, 9 // 2, 9 % 4, 2 ** 3],
      "logic": [not False, True and 4, False or 5],
      "comparison": 1 < 2 <= 2,
      "conditional": "yes" if flag else "no",
      "slice": values[1:3],
      "lookup": record["name"],
      "tool": double(4)
    }"""
    result = sandbox.execute(
        expression,
        {"flag": True, "values": [0, 1, 2, 3], "record": {"name": "Alice"}},
    )
    assert result == {
        "arithmetic": [3, 4, 6, 4.0, 4, 1, 8],
        "logic": [True, 4, 5],
        "comparison": True,
        "conditional": "yes",
        "slice": [1, 2],
        "lookup": "Alice",
        "tool": 8,
    }


@pytest.mark.parametrize(
    "expression",
    [
        "unknown_name",
        "~1",
        "2 @ 3",
        "2 ** 17",
        "1 is 1",
        "missing()",
        "sum(*[1, 2])",
        "sum(**{'x': 1})",
        "{1: 'non-string-key'}",
        "{'duplicate': 1, 'duplicate': 2}",
        "values[99]",
    ],
)
def test_sandbox_rejects_unsupported_or_unsafe_expression_forms(expression):
    sandbox = StrictSandbox({"sum": lambda *values, **named: sum(values) + sum(named.values())})
    with pytest.raises(SandboxViolation):
        sandbox.execute(expression, {"values": [1]})


def test_sandbox_rejects_unsafe_registration_bindings_limits_and_tool_results():
    with pytest.raises(SandboxViolation):
        StrictSandbox({"open": lambda: None})
    sandbox = StrictSandbox({"explode": lambda: (_ for _ in ()).throw(RuntimeError("boom"))})
    with pytest.raises(SandboxViolation):
        sandbox.register_tool("explode", lambda: None)
    with pytest.raises(SandboxViolation):
        sandbox.execute("1", {"_private": 1})
    with pytest.raises(SandboxViolation):
        sandbox.execute("explode()")
    non_json = StrictSandbox({"bad": lambda: object()})
    with pytest.raises(SandboxViolation):
        non_json.execute("bad()")
    tiny_source = StrictSandbox(max_source_characters=3)
    with pytest.raises(SandboxViolation):
        tiny_source.execute("1 + 2")
    tiny_ast = StrictSandbox(max_ast_nodes=2)
    with pytest.raises(SandboxViolation):
        tiny_ast.execute("1 + 2")
    tiny_result = StrictSandbox(max_result_characters=3)
    with pytest.raises(SandboxViolation):
        tiny_result.execute("'long'")


def test_agent_kernel_successfully_accounts_structured_mapping_response():
    kernel = AgentKernel()
    budget = TokenBudget(200)

    def model(prompt, *, max_output_tokens):
        assert max_output_tokens == 100
        return {
            "decision": "ABSTAIN",
            "identityId": None,
            "confidence": 0.25,
            "reason": "insufficient evidence",
            "content": {"prompt": prompt},
        }

    response = kernel.invoke(
        "Who is this?",
        model,
        budget=budget,
        max_output_tokens=100,
    )
    assert response.decision is AgentDecision.ABSTAIN
    assert response.content == {"prompt": "Who is this?"}
    assert budget.used > deterministic_token_count("Who is this?")
    assert budget.reserved == 0


def test_agent_kernel_capability_protects_model_and_sandbox_invocations(fixed_now):
    authority = CapabilityAuthority()
    lease = authority.issue(
        subject="agent-1",
        capabilities=["agent:invoke", "agent:sandbox"],
        resources=["agent-1"],
        issued_at=fixed_now,
        ttl=timedelta(minutes=1),
    )
    kernel = AgentKernel(
        sandbox=StrictSandbox({"double": lambda value: value * 2}),
        capability_authority=authority,
        subject="agent-1",
    )
    assert kernel.execute_sandboxed(
        "double(2)", lease=lease, at=fixed_now
    ) == 4
    response = kernel.invoke(
        "unknown",
        lambda prompt, *, max_output_tokens: ModelResult(
            AgentResponse(AgentDecision.ABSTAIN, None, 0.0, "unknown"),
            output_tokens=50,
        ),
        budget=TokenBudget(100),
        max_output_tokens=50,
        lease=lease,
        at=fixed_now,
    )
    assert response.decision is AgentDecision.ABSTAIN
    with pytest.raises(AuthorizationError):
        kernel.execute_sandboxed("double(2)")


def test_agent_token_preflight_does_not_consume_a_limited_capability(fixed_now):
    authority = CapabilityAuthority()
    lease = authority.issue(
        subject="agent-1",
        capabilities=["agent:invoke"],
        resources=["agent-1"],
        issued_at=fixed_now,
        ttl=timedelta(minutes=1),
        max_uses=1,
    )
    kernel = AgentKernel(capability_authority=authority, subject="agent-1")
    called = False

    def model(prompt, *, max_output_tokens):
        nonlocal called
        called = True
        return AgentResponse(AgentDecision.ABSTAIN, None, 0.0, "unknown")

    with pytest.raises(TokenBudgetExceeded):
        kernel.invoke(
            "two tokens",
            model,
            budget=TokenBudget(3),
            max_output_tokens=2,
            lease=lease,
            at=fixed_now,
        )
    assert not called
    assert authority.usage(lease.lease_id) == 0


def test_agent_response_and_model_contracts_fail_closed():
    with pytest.raises(ValueError):
        AgentResponse(AgentDecision.IDENTIFY, None, 0.9, "missing identity")
    with pytest.raises(ValueError):
        AgentResponse(AgentDecision.ABSTAIN, "invented", 0.1, "contradiction")
    with pytest.raises(ValueError):
        AgentResponse(AgentDecision.ABSTAIN, None, 1.1, "bad confidence")
    kernel = AgentKernel()
    with pytest.raises(SandboxViolation):
        kernel.invoke(
            "prompt",
            lambda prompt, *, max_output_tokens: "unstructured",
            budget=TokenBudget(100),
            max_output_tokens=50,
        )
