"""Paired-fixture observational-equivalence assertion.

This is the one small new abstraction OCOR-DEV-0024 adds: a single place
to express "a low-clearance observation must be unaffected by
high-compartment population" once, reused across every axis (content,
existence, rank, count) and every backend this spike composes -- the Jena
marking-safe projection (OCOR-DEV-0018), the identity/policy control
plane (OCOR-DEV-0021) and the Qdrant vector-partition oracle
(OCOR-DEV-0023) -- all reused completely unmodified.
"""

from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


class NonInterferenceViolation(AssertionError):
    pass


def assert_observationally_equivalent(before: T, after: T, *, axis: str) -> None:
    """Raise with a precise, axis-labeled message if a paired observation
    diverges -- never silently pass on a mismatch, and never require the
    caller to hand-roll the comparison and its failure message."""
    if before != after:
        raise NonInterferenceViolation(
            f"non-interference violated on axis {axis!r}: a low-clearance observation changed "
            f"after high-compartment population -- before={before!r} after={after!r}"
        )
