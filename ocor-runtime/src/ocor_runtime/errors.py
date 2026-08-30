"""Typed, fail-closed exceptions used at OCOR trust boundaries."""

from __future__ import annotations


class OCORError(Exception):
    """Base class for deterministic runtime failures."""


class CanonicalizationError(OCORError, ValueError):
    """A value cannot be represented by RFC 8785 JSON canonicalization."""


class SchemaValidationError(OCORError, ValueError):
    """A semantic document does not conform to its normative schema."""


class IdentityConflictError(OCORError):
    """An immutable identity would be overwritten or aliased incorrectly."""


class SingleWriterViolation(OCORError, PermissionError):
    """A caller attempted to mutate an aggregate outside its writer boundary."""


class ConcurrencyConflict(OCORError):
    """An optimistic version precondition did not match durable state."""


class CrashInjected(OCORError):
    """A deterministic crash used by the atomicity verification harness."""

    def __init__(self, window: str, *, committed: bool) -> None:
        self.window = window
        self.committed = committed
        super().__init__(
            f"crash injected at {window}; transaction "
            f"{'committed' if committed else 'rolled back'}"
        )


class MarkingError(OCORError, ValueError):
    """A marking definition or lattice operation is invalid."""


class InvalidTransition(OCORError):
    """An action event is not defined for the current FSM state."""


class TemporalGuardViolation(OCORError):
    """An operation is outside its authoritative temporal window."""


class AuthorizationError(OCORError, PermissionError):
    """A capability is absent, expired, revoked, or out of scope."""


class EmissionBlocked(OCORError):
    """The emission fence rejected an externally observable effect."""


class SandboxViolation(OCORError, PermissionError):
    """Agent-supplied code attempted an operation outside the sandbox."""


class TokenBudgetExceeded(OCORError):
    """An agent invocation attempted to exceed its deterministic token budget."""

