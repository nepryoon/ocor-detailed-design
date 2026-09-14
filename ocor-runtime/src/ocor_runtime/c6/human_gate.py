"""C6 -- Human Gate decision approval with dual control.

Supplies the real quorum/separation-of-duties/signature/scope/TTL
logic the Human Gate transitions OCOR-DEV-0042's sealed
``ocor_runtime.c6.fsm`` table declares (``ACT-T06``/``ACT-T07``/
``ACT-T08``/``ACT-T09a``/``ACT-T09b``, "Human Gate richiesto" /
"approvato" / "non approvato") actually need, and produces the exact
same sealed ``ocor_runtime.c6.engine.Approval`` record
(OCOR-DEV-0030, reused unmodified through its own public constructor)
``GovernedActionEngine.execute`` already accepts -- no change to
either sealed file.

``HumanGateCoordinator.validate`` is a pure function of the signature
set and the current time: calling it once when a Human Gate is first
resolved and again, unmodified, immediately before dispatch is what
gives "dual control" its real meaning here -- a signature that was
still within its TTL at resolution time can have expired by dispatch
time, and the second call denies exactly as the first would have,
never trusting a stale resolution. Composes the sealed
``ocor_runtime.c2_identity.IdentityRegistry`` (reused unmodified) to
refuse an unresolved signatory, and accepts an optional real
control-plane check (``ocor_runtime.security.ports.ControlStatus``,
OCOR-DEV-0014/0021's sealed fail-closed pattern) so a caller can wire
a live availability probe without this module depending on any one
concrete backend.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..c2_identity import IdentityRegistry
from ..c3_store import require_aware
from ..errors import OCORError
from ..kernel.canonical import canonical_digest
from .engine import Approval


class HumanGateError(OCORError):
    """A Human Gate resolution or revalidation was refused.
    ``reason_code`` identifies why (QUORUM_NOT_MET,
    MISSING_REQUIRED_ROLE), mirroring the reason-code pattern already
    established by the other retained C1-C8 components this session.
    Deliberately generic: it never discloses which individual
    signature was excluded (expired, scope-mismatched, unresolved,
    excluded, or shadowed by separation of duties), the same
    anti-disclosure posture OCOR-DEV-0034's marking gate already
    established."""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {message}")


@dataclass(frozen=True, slots=True)
class ApprovalPolicy:
    """The dual-control policy a risk-bearing action's Human Gate must
    satisfy: at least ``minimum_signatories`` distinct real humans
    total, with every one of ``required_roles`` covered by its own
    distinct human -- no single human ever credited toward two
    different required roles (separation of duties) -- and the
    action's own proposer (and any other explicitly excluded
    principal) never counted at all."""

    required_roles: frozenset[str]
    minimum_signatories: int
    ttl: timedelta
    excluded_principal_id: str | None = None

    def __post_init__(self) -> None:
        if self.minimum_signatories < 1:
            raise ValueError("minimum_signatories must be at least one")
        if self.ttl <= timedelta(0):
            raise ValueError("ttl must be a positive duration")


@dataclass(frozen=True, slots=True)
class GateSignature:
    """One real signatory's act of signing, bound to the exact action,
    role and scope it was given for. ``integrity_digest`` is a
    content-addressed binding of every semantic field via the shared,
    sealed RFC 8785 kernel canonicalizer -- an honest, tamper-evident
    commitment, not a real asymmetric cryptographic signature (no PKI
    exists in this delivery's scope, the same honesty already
    established by OCOR-DEV-0028's unsigned ``signature_envelope_ref``
    placeholder)."""

    action_id: str
    principal_id: str
    role: str
    scope: str
    signed_at: datetime

    def __post_init__(self) -> None:
        require_aware(self.signed_at, field="signed_at")
        if not self.action_id:
            raise ValueError("a GateSignature requires an action_id")
        if not self.principal_id:
            raise ValueError("a GateSignature requires a principal_id")
        if not self.role:
            raise ValueError("a GateSignature requires a role")
        if not self.scope:
            raise ValueError("a GateSignature requires a scope")

    @property
    def integrity_digest(self) -> str:
        return canonical_digest(
            {
                "action_id": self.action_id,
                "principal_id": self.principal_id,
                "role": self.role,
                "scope": self.scope,
                "signed_at": self.signed_at.isoformat(),
            }
        )


class HumanGateCoordinator:
    def __init__(self, *, identities: IdentityRegistry) -> None:
        self._identities = identities

    def validate(
        self,
        *,
        action_id: str,
        proposer_id: str,
        policy: ApprovalPolicy,
        signatures: Iterable[GateSignature],
        scope: str,
        at: datetime,
        control_check: Callable[[], None] | None = None,
    ) -> Approval:
        instant = require_aware(at, field="at")
        excluded = {proposer_id}
        if policy.excluded_principal_id:
            excluded.add(policy.excluded_principal_id)

        valid_principals: set[str] = set()
        role_covered_by: dict[str, str] = {}

        for signature in signatures:
            principal = signature.principal_id
            if signature.action_id != action_id:
                continue
            if principal in excluded:
                continue
            if self._identities.get(principal) is None:
                continue
            if signature.scope != scope:
                continue
            if instant - signature.signed_at > policy.ttl:
                continue

            valid_principals.add(principal)

            if signature.role in policy.required_roles and signature.role not in role_covered_by:
                already_covers_a_different_role = any(
                    other_principal == principal for other_role, other_principal in role_covered_by.items() if other_role != signature.role
                )
                if not already_covers_a_different_role:
                    role_covered_by[signature.role] = principal

        if len(valid_principals) < policy.minimum_signatories:
            raise HumanGateError(
                "QUORUM_NOT_MET",
                f"{len(valid_principals)} distinct valid signatory(ies), {policy.minimum_signatories} required",
            )
        missing_roles = policy.required_roles - role_covered_by.keys()
        if missing_roles:
            raise HumanGateError("MISSING_REQUIRED_ROLE", f"no distinct valid signatory for: {sorted(missing_roles)}")

        if control_check is not None:
            control_check()

        approver = ",".join(sorted(valid_principals))
        return Approval(action_id=action_id, approver=approver, approved=True, approved_at=instant)
