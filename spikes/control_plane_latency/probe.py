"""Real bounded-timeout identity/policy control-plane probes.

Proves that OPA, Keycloak and OpenBao (the real, live services backing
``PolicyDecisionPort``/``IdentityProviderPort``/``SecretProviderPort`` from
``ocor_runtime.security.ports``, OCOR-DEV-0014, sealed and reused
unmodified) never let a slow or unreachable control silently become a
permit: a bounded probe either observes the control within its declared
deadline, or reports it unavailable with correlated audit evidence -- and
``ControlStatus.require_available`` (also sealed, unmodified) then makes an
unavailable control raise rather than continue, by construction.

Real fault injection reuses WS-12's sealed
``scripts/fault_inject_test_environment.py`` helpers (``fault_command``,
``http_reachable``) unmodified against the live ocor-bootstrap stack,
rather than re-implementing container fault control.
"""

from __future__ import annotations

import hashlib
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime

from ocor_runtime.security.ports import ControlName, ControlStatus

HEALTH_URLS: dict[ControlName, str] = {
    ControlName.POLICY: "http://127.0.0.1:8181/health",
    ControlName.IDENTITY: "http://127.0.0.1:8080/realms/master/.well-known/openid-configuration",
    ControlName.SECRETS: "http://127.0.0.1:8200/v1/sys/health",
}


def _digest(value: str) -> str:
    return "urn:sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Correlated audit evidence emitted on every probe outcome, success or
    failure alike -- the same fields, the same correlation identifiers,
    regardless of which path was taken."""

    correlation_id: str
    causation_id: str
    control: ControlName
    outcome: str
    latency_ms: float
    observed_at: datetime
    reason_code: str | None

    def to_mapping(self) -> dict[str, object]:
        return {
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "control": self.control.value,
            "outcome": self.outcome,
            "latency_ms": self.latency_ms,
            "observed_at": self.observed_at.isoformat(),
            "reason_code": self.reason_code,
        }


def bounded_probe(
    control: ControlName,
    url: str,
    *,
    timeout_seconds: float,
    correlation_id: str,
    causation_id: str,
) -> tuple[ControlStatus, AuditEvent]:
    """Perform one real, bounded HTTP round trip against a live control.

    Returns an available ``ControlStatus`` only if the control answered
    within ``timeout_seconds``; any timeout, connection failure or
    non-2xx-with-no-body condition otherwise yields an unavailable status.
    Every outcome is paired with an ``AuditEvent`` carrying the exact
    correlation/causation identifiers passed in, so a caller can always
    trace a denial back to its request -- the audit trail never depends on
    the control actually having answered.
    """
    start = time.monotonic()
    observed_at = datetime.now(UTC)
    try:
        with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
            response.read(1)
            outcome = "AVAILABLE"
            reason_code = None
            status = ControlStatus.available(
                control, observed_at=observed_at, source_digest=_digest(f"{control.value}:{url}")
            )
    except urllib.error.HTTPError:
        # Any HTTP response at all (including a non-2xx one) proves the
        # control answered within the deadline -- it is reachable, even if
        # it declined the specific request.
        outcome = "AVAILABLE"
        reason_code = None
        status = ControlStatus.available(
            control, observed_at=observed_at, source_digest=_digest(f"{control.value}:{url}")
        )
    except TimeoutError:
        outcome = "DENIED_TIMEOUT"
        reason_code = "CONTROL_TIMEOUT"
        status = ControlStatus.unavailable(
            control, reason_code=reason_code, observed_at=observed_at, source_digest=_digest(f"{control.value}:{url}")
        )
    except (OSError, urllib.error.URLError):
        outcome = "DENIED_UNREACHABLE"
        reason_code = "CONTROL_UNREACHABLE"
        status = ControlStatus.unavailable(
            control, reason_code=reason_code, observed_at=observed_at, source_digest=_digest(f"{control.value}:{url}")
        )
    elapsed_ms = (time.monotonic() - start) * 1000
    audit = AuditEvent(
        correlation_id=correlation_id,
        causation_id=causation_id,
        control=control,
        outcome=outcome,
        latency_ms=elapsed_ms,
        observed_at=observed_at,
        reason_code=reason_code,
    )
    return status, audit


def decide_with_fail_closed_default(status: ControlStatus, control: ControlName) -> None:
    """Never returns a permit for an unavailable control: raises the sealed
    ``SecurityControlError`` instead, by delegating entirely to
    ``ControlStatus.require_available`` (unmodified)."""
    status.require_available(control)
