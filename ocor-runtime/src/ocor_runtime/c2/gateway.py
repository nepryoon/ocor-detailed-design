"""C2 -- named-query gateway: identity, purpose, marking and policy
checks before any registered named query executes.

Implements the smallest contract-compliant slice of LLD v1.1 section
2.2's Unified Semantic Gateway algorithm (steps 1, 2, 3, 5, 6 of 8;
steps 4/7/8 are already the responsibility of the injected, already
sealed ``ProjectionReadPort`` -- e.g. the real TypeDB exact-at-commit
adapter, OCOR-DEV-0017): purpose is already fail-closed inside the
sealed ``NamedQueryRequest`` constructor (OCOR-DEV-0012, reused
unmodified); this gateway adds name/version registration, identity
resolution (``ocor_runtime.c2_identity.IdentityRegistry``, retained,
reused unmodified), and marking-join authorization against an injected
port matching ``JenaMarkingProjectionAdapter``'s real shape
(OCOR-DEV-0018) before ever delegating to the projection read.
``AuthorityResolutionPort`` and ``PolicyDecisionPort`` (OCOR-DEV-0012,
``ocor_runtime.c2.ports``, sealed Protocols reused unmodified) get
their first real implementations here.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ..c2_identity import IdentityRegistry, ResolutionStatus
from ..c4_marking import MarkingEngine, MarkingSet
from .ports import (
    AuthorityResolutionPort,
    C2Error,
    NamedQueryRequest,
    NamedQueryResponse,
    PolicyDecisionPort,
    ProjectionReadPort,
)

PERMIT = "PERMIT"
DENY = "DENY"


@runtime_checkable
class MarkingAuthorizationPort(Protocol):
    """Structural shape of a real marking-safe existence check, matching
    ``JenaMarkingProjectionAdapter.exists_authorized`` (OCOR-DEV-0018)
    without importing the ``spikes`` package from retained runtime
    code."""

    def exists_authorized(self, resource_id: str, clearance: MarkingSet) -> bool: ...


@dataclass(frozen=True, slots=True)
class RegisteredNamedQuery:
    """One allow-listed named-query contract: an explicit name/version
    pair plus the marking scheme its resource-bearing parameter is
    checked against."""

    contract_id: str
    versions: frozenset[str]
    marking_scheme_id: str


class IdentityBackedAuthority:
    """``AuthorityResolutionPort``: resolves the requester's identity
    through the retained, real ``IdentityRegistry``. Returns the
    resolved canonical id when identity is unambiguous, or the literal
    ``ResolutionStatus.ABSTAIN`` value otherwise -- never a partial or
    best-guess identity."""

    def __init__(self, identity_registry: IdentityRegistry) -> None:
        self._identity_registry = identity_registry

    def resolve(self, request: NamedQueryRequest) -> str:
        outcome = self._identity_registry.resolve(request.governed_context.effective_principal_id)
        if outcome.status is not ResolutionStatus.IDENTIFIED or outcome.canonical_id is None:
            return ResolutionStatus.ABSTAIN.value
        return outcome.canonical_id


class RegistrationAndMarkingPolicy:
    """``PolicyDecisionPort``: PERMIT only when the named-query contract
    is explicitly registered for its declared version AND -- when the
    request names a resource -- that resource is authorized for the
    requester's clearance under the real marking join (OCOR-DEV-0018).
    Any other outcome is DENY; this port never distinguishes an
    unregistered contract from a marking denial in its return value,
    so a caller cannot use it to probe which barrier was crossed."""

    def __init__(
        self,
        *,
        registry: Mapping[str, RegisteredNamedQuery],
        marking_engine: MarkingEngine,
        marking_port: MarkingAuthorizationPort,
        clearance_by_marking_ref: Mapping[str, MarkingSet],
    ) -> None:
        self._registry = dict(registry)
        self._marking_engine = marking_engine
        self._marking_port = marking_port
        self._clearance_by_marking_ref = dict(clearance_by_marking_ref)

    def decide(self, request: NamedQueryRequest) -> str:
        registered = self._registry.get(request.contract_id)
        if registered is None or request.contract_version not in registered.versions:
            return DENY
        resource_id = request.parameters.get("resource_id")
        if not isinstance(resource_id, str) or not resource_id:
            return PERMIT
        clearance = self._clearance_by_marking_ref.get(request.governed_context.classification_marking_ref)
        if clearance is None:
            return DENY
        self._marking_engine.validate(clearance)
        if not self._marking_port.exists_authorized(resource_id, clearance):
            return DENY
        return PERMIT


class NamedQueryGateway:
    """``NamedQueryPort``: only registered named queries execute, and
    only after identity, purpose, marking and policy checks are all
    dispositive. Purpose is already enforced by the sealed
    ``NamedQueryRequest`` constructor before an instance can even
    exist; this gateway enforces the remaining three at ``execute``
    time, in the LLD's own order (authority/identity before policy,
    both before the projection read), and never returns any response
    -- partial or otherwise -- for a request that fails any of them."""

    def __init__(
        self,
        *,
        authority: AuthorityResolutionPort,
        policy: PolicyDecisionPort,
        projection: ProjectionReadPort,
    ) -> None:
        self._authority = authority
        self._policy = policy
        self._projection = projection

    def execute(self, request: NamedQueryRequest) -> NamedQueryResponse:
        resolved_identity = self._authority.resolve(request)
        if resolved_identity == ResolutionStatus.ABSTAIN.value:
            raise C2Error("IDENTITY_AMBIGUOUS", "requester identity could not be uniquely resolved")

        decision = self._policy.decide(request)
        if decision != PERMIT:
            raise C2Error("ARBITRARY_QUERY_FORBIDDEN", "named query is not a registered, authorized contract")

        return self._projection.read(request)
