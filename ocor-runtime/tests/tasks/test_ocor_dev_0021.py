"""OCOR-DEV-0021: SPIKE identity-policy latency and failure semantics.

Proves that OPA, Keycloak and OpenBao timeouts remain bounded and deny
with correlated audit evidence: a real, live control that stops answering
is never silently treated as a permit. Every positive and fault-injection
test drives the real services in the ocor-bootstrap stack -- no mocks --
reusing ``ocor_runtime.security.ports`` (OCOR-DEV-0014, sealed) and
WS-12's sealed fault-injection helpers (``scripts/fault_inject_test_environment.py``)
completely unmodified.
"""

from __future__ import annotations

import importlib.util
import sys
import uuid
from pathlib import Path

import pytest
from ocor_runtime.security.ports import ControlName, ControlStatus, SecurityControlError

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))
SCRIPTS_DIR = REPOSITORY_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from spikes.control_plane_latency.probe import (  # noqa: E402 -- must follow sys.path.insert above
    HEALTH_URLS,
    bounded_probe,
    decide_with_fail_closed_default,
)

_SPEC = importlib.util.spec_from_file_location(
    "fault_inject_test_environment_0021", SCRIPTS_DIR / "fault_inject_test_environment.py"
)
assert _SPEC is not None and _SPEC.loader is not None
fault_inject = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = fault_inject
_SPEC.loader.exec_module(fault_inject)

BOUNDED_TIMEOUT_SECONDS = 2.0


@pytest.fixture(scope="session")
def stack_reachable() -> None:
    for control, url in HEALTH_URLS.items():
        if not fault_inject.http_reachable(url, timeout=5.0):
            pytest.fail(f"a real, live {control.value} service is mandatory qualifying evidence")


def new_ids() -> tuple[str, str]:
    return str(uuid.uuid4()), str(uuid.uuid4())


@pytest.mark.parametrize("control", [ControlName.POLICY, ControlName.IDENTITY, ControlName.SECRETS])
def test_bounded_probe_succeeds_within_deadline_when_healthy(stack_reachable: None, control: ControlName):
    correlation_id, causation_id = new_ids()
    status, audit = bounded_probe(
        control,
        HEALTH_URLS[control],
        timeout_seconds=BOUNDED_TIMEOUT_SECONDS,
        correlation_id=correlation_id,
        causation_id=causation_id,
    )
    assert status.is_available is True
    assert audit.outcome == "AVAILABLE"
    assert audit.correlation_id == correlation_id
    assert audit.causation_id == causation_id
    assert 0 <= audit.latency_ms < BOUNDED_TIMEOUT_SECONDS * 1000
    decide_with_fail_closed_default(status, control)  # must not raise


def test_require_available_never_permits_on_unavailable_status(stack_reachable: None):
    for control in (ControlName.POLICY, ControlName.IDENTITY, ControlName.SECRETS, ControlName.WORKLOAD_IDENTITY):
        import datetime

        status = ControlStatus.unavailable(
            control,
            reason_code="SIMULATED_OUTAGE",
            observed_at=datetime.datetime.now(datetime.UTC),
            source_digest="urn:sha256:" + "0" * 64,
        )
        with pytest.raises(SecurityControlError) as excinfo:
            decide_with_fail_closed_default(status, control)
        assert excinfo.value.reason_code == f"{control.value}_UNAVAILABLE"


def _run_pause_cycle(control: ControlName, service: str):
    url = HEALTH_URLS[control]
    assert fault_inject.http_reachable(url, timeout=5.0), f"{service} must start healthy for a clean fault drill"

    pause = fault_inject.run(fault_inject.fault_command(service, "pause"), cwd=REPOSITORY_ROOT, timeout=30)
    assert pause.returncode == 0, pause.stderr
    try:
        paused = fault_inject._poll(lambda: not fault_inject.http_reachable(url, timeout=1.0), timeout=10.0)
        assert paused, f"{service} was never observed unreachable after pause"

        correlation_id, causation_id = new_ids()
        status, audit = bounded_probe(
            control, url, timeout_seconds=BOUNDED_TIMEOUT_SECONDS, correlation_id=correlation_id, causation_id=causation_id
        )
        elapsed_seconds = audit.latency_ms / 1000
    finally:
        unpause = fault_inject.run(fault_inject.fault_command(service, "unpause"), cwd=REPOSITORY_ROOT, timeout=30)
        assert unpause.returncode == 0, unpause.stderr
        recovered = fault_inject._poll(lambda: fault_inject.http_reachable(url, timeout=2.0), timeout=15.0)
        assert recovered, f"{service} did not recover within the bounded window after unpause"

    assert status.is_available is False
    assert audit.outcome == "DENIED_TIMEOUT"
    assert audit.reason_code == "CONTROL_TIMEOUT"
    assert audit.correlation_id == correlation_id
    assert audit.causation_id == causation_id
    assert elapsed_seconds <= BOUNDED_TIMEOUT_SECONDS + 1.0, (
        f"the probe against a paused {service} took {elapsed_seconds:.2f}s, exceeding its declared "
        f"{BOUNDED_TIMEOUT_SECONDS:.2f}s bound plus tolerance -- a timeout must stay bounded, never hang"
    )
    with pytest.raises(SecurityControlError, match="POLICY_UNAVAILABLE|IDENTITY_UNAVAILABLE|SECRETS_UNAVAILABLE"):
        decide_with_fail_closed_default(status, control)

    # recovery: the same probe against the now-healthy service succeeds again
    correlation_id_2, causation_id_2 = new_ids()
    recovered_status, recovered_audit = bounded_probe(
        control, url, timeout_seconds=BOUNDED_TIMEOUT_SECONDS, correlation_id=correlation_id_2, causation_id=causation_id_2
    )
    assert recovered_status.is_available is True
    assert recovered_audit.outcome == "AVAILABLE"


def test_paused_opa_is_denied_within_the_bounded_timeout_with_audit_evidence(stack_reachable: None):
    _run_pause_cycle(ControlName.POLICY, "opa")


def test_paused_openbao_is_denied_within_the_bounded_timeout_with_audit_evidence(stack_reachable: None):
    _run_pause_cycle(ControlName.SECRETS, "openbao")


def test_audit_evidence_is_emitted_with_matching_correlation_on_success_and_failure(stack_reachable: None):
    correlation_id, causation_id = new_ids()
    _, success_audit = bounded_probe(
        ControlName.POLICY,
        HEALTH_URLS[ControlName.POLICY],
        timeout_seconds=BOUNDED_TIMEOUT_SECONDS,
        correlation_id=correlation_id,
        causation_id=causation_id,
    )
    _, failure_audit = bounded_probe(
        ControlName.POLICY,
        "http://127.0.0.1:1/unreachable-port",
        timeout_seconds=0.5,
        correlation_id=correlation_id,
        causation_id=causation_id,
    )
    assert success_audit.outcome == "AVAILABLE"
    assert failure_audit.outcome in ("DENIED_TIMEOUT", "DENIED_UNREACHABLE")
    assert success_audit.correlation_id == failure_audit.correlation_id == correlation_id
    assert success_audit.causation_id == failure_audit.causation_id == causation_id
    for event in (success_audit, failure_audit):
        mapping = event.to_mapping()
        assert set(mapping) == {
            "correlation_id",
            "causation_id",
            "control",
            "outcome",
            "latency_ms",
            "observed_at",
            "reason_code",
        }
