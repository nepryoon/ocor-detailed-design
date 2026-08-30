"""OCOR executable core semantic runtime (C1–C8)."""

from .canonical import canonical_sha256, canonicalize, canonicalize_json, load_i_json
from .c1_compiler import CompiledArtifact, SemanticCompiler
from .c2_identity import (
    IdentityRecord,
    IdentityRegistry,
    ResolutionOutcome,
    ResolutionStatus,
)
from .c3_store import AtomicOutboxStore, CrashWindow, OutboxEvent, StoredDocument
from .c4_marking import MarkingEngine, MarkingSchemeDefinition, MarkingSet
from .c5_actions import Action, ActionEvent, ActionFSM, ActionState
from .c6_capabilities import CapabilityAuthority, CapabilityLease
from .c7_emission import EmissionFence, EmissionReceipt
from .c8_agent import AgentDecision, AgentKernel, AgentResponse, StrictSandbox, TokenBudget

__all__ = [
    "CompiledArtifact",
    "SemanticCompiler",
    "IdentityRecord",
    "IdentityRegistry",
    "ResolutionOutcome",
    "ResolutionStatus",
    "AtomicOutboxStore",
    "CrashWindow",
    "OutboxEvent",
    "StoredDocument",
    "MarkingEngine",
    "MarkingSchemeDefinition",
    "MarkingSet",
    "Action",
    "ActionEvent",
    "ActionFSM",
    "ActionState",
    "CapabilityAuthority",
    "CapabilityLease",
    "EmissionFence",
    "EmissionReceipt",
    "AgentDecision",
    "AgentKernel",
    "AgentResponse",
    "StrictSandbox",
    "TokenBudget",
    "canonical_sha256",
    "canonicalize",
    "canonicalize_json",
    "load_i_json",
]

__version__ = "0.1.0"
