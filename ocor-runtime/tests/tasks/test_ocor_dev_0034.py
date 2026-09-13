"""OCOR-DEV-0034: Implement C2 named-query gateway and identity resolution.

Proves that only registered named queries execute, and only after
identity, purpose, marking and policy checks are all dispositive.
Composes the retained, real ``IdentityRegistry`` (``c2_identity``,
reused unmodified), a real Fuseki-backed marking join
(``spikes.jena_marking.adapter``, OCOR-DEV-0018, reused unmodified),
and a real TypeDB exact-at-commit projection
(``spikes.typedb_exact_commit.adapter``, OCOR-DEV-0017, reused
unmodified) behind the sealed C2 ``AuthorityResolutionPort``/
``PolicyDecisionPort``/``ProjectionReadPort`` (OCOR-DEV-0012). Every
qualifying test drives real backends -- no mocks.
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path

import pytest
from ocor_runtime.c2.gateway import (
    IdentityBackedAuthority,
    MarkingAuthorizationPort,
    NamedQueryGateway,
    RegisteredNamedQuery,
    RegistrationAndMarkingPolicy,
)
from ocor_runtime.c2.ports import (
    AuthorityResolutionPort,
    C2Error,
    ConsistencyMode,
    ConsistencyRequirement,
    NamedQueryPort,
    NamedQueryRequest,
    PolicyDecisionPort,
)
from ocor_runtime.c2_identity import IdentityRecord, IdentityRegistry
from ocor_runtime.c4_marking import MarkingEngine, MarkingSchemeDefinition, MarkingSet
from ocor_runtime.kernel.governed_context import GovernedContext, GovernedContextError

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from spikes.jena_marking.adapter import (  # noqa: E402 -- must follow sys.path.insert above
    JenaAdapterError,
    JenaMarkingProjectionAdapter,
)
from spikes.typedb_exact_commit.adapter import (  # noqa: E402 -- must follow sys.path.insert above
    TypeDBAdapterError,
    TypeDBExactCommitAdapter,
)

DIGEST_A = "urn:sha256:" + "a" * 64
DIGEST_B = "urn:sha256:" + "b" * 64
DIGEST_C = "urn:sha256:" + "c" * 64

CONTRACT_ID = "urn:ocor:contract:named-query:gateway-fixture"
RESOURCE_ID = "urn:ocor:resource:gateway-fixture"

CLASSIFICATION_SCHEME = MarkingSchemeDefinition(
    "classification", levels=("UNCLASSIFIED", "SECRET", "TOP_SECRET")
)


def clearance(level: str) -> MarkingSet:
    return MarkingSet({"classification": level})


@pytest.fixture(scope="session")
def backends_reachable() -> None:
    try:
        JenaMarkingProjectionAdapter(MarkingEngine([CLASSIFICATION_SCHEME])).reset()
    except (JenaAdapterError, OSError) as error:
        pytest.fail(f"a real, live Fuseki instance is mandatory qualifying evidence: {error}")
    try:
        TypeDBExactCommitAdapter().initialize()
    except (TypeDBAdapterError, OSError) as error:
        pytest.fail(f"a real, live TypeDB instance is mandatory qualifying evidence: {error}")


@pytest.fixture
def jena(backends_reachable: None) -> JenaMarkingProjectionAdapter:
    value = JenaMarkingProjectionAdapter(MarkingEngine([CLASSIFICATION_SCHEME]))
    value.reset()
    return value


@pytest.fixture
def typedb(backends_reachable: None) -> TypeDBExactCommitAdapter:
    value = TypeDBExactCommitAdapter()
    value.reset()
    value.ingest("fact-1", "commit-1", "V1")
    value.advance_watermark("commit-1")
    return value


@pytest.fixture
def identity_registry() -> IdentityRegistry:
    registry = IdentityRegistry()
    registry.register(IdentityRecord(canonical_id="urn:ocor:principal:analyst-1", aliases=frozenset({"analyst-1"})))
    return registry


def make_request(
    *,
    principal: str,
    marking_ref: str = DIGEST_A,
    resource_id: str | None = RESOURCE_ID,
    contract_id: str = CONTRACT_ID,
    contract_version: str = "1.0.0",
) -> NamedQueryRequest:
    context = GovernedContext.from_mapping(
        {
            "tenant_id": "urn:ocor:tenant:synthetic",
            "organization_id": "urn:ocor:org:synthetic",
            "domain_id": "urn:ocor:domain:logistics",
            "compartments": ["urn:ocor:compartment:alpha"],
            "classification_marking_ref": marking_ref,
            "purpose": "gateway-fixture",
            "effective_principal_id": principal,
            "actor_chain": ["urn:ocor:actor:synthetic", principal],
            "ontology_release_digest": DIGEST_B,
            "policy_bundle_digest": DIGEST_C,
            "correlation_id": "018f2f95-01b2-7cc3-8d4e-123456789abc",
        }
    )
    parameters: dict[str, object] = {"fact_id": "fact-1"}
    if resource_id is not None:
        parameters["resource_id"] = resource_id
    return NamedQueryRequest(
        request_id="018f2f95-01b2-7cc3-8d4e-123456789abc",
        contract_id=contract_id,
        contract_version=contract_version,
        contract_digest=DIGEST_A,
        parameters=parameters,
        governed_context=context,
        governed_context_digest=context.digest(),
        consistency=ConsistencyRequirement(mode=ConsistencyMode.EXACT_AT_COMMIT, required_commit="commit-1"),
    )


def make_gateway(
    *,
    identity_registry: IdentityRegistry,
    jena: JenaMarkingProjectionAdapter,
    typedb: TypeDBExactCommitAdapter,
    marking_ref_to_clearance_level: dict[str, str],
) -> NamedQueryGateway:
    engine = MarkingEngine([CLASSIFICATION_SCHEME])
    registry = {
        CONTRACT_ID: RegisteredNamedQuery(
            contract_id=CONTRACT_ID, versions=frozenset({"1.0.0"}), marking_scheme_id="classification"
        )
    }
    clearance_by_marking_ref = {ref: clearance(level) for ref, level in marking_ref_to_clearance_level.items()}
    policy = RegistrationAndMarkingPolicy(
        registry=registry,
        marking_engine=engine,
        marking_port=jena,
        clearance_by_marking_ref=clearance_by_marking_ref,
    )
    authority = IdentityBackedAuthority(identity_registry)
    return NamedQueryGateway(authority=authority, policy=policy, projection=typedb)


def test_identity_backed_authority_conforms_to_the_sealed_port(identity_registry: IdentityRegistry) -> None:
    assert isinstance(IdentityBackedAuthority(identity_registry), AuthorityResolutionPort)


def test_registration_and_marking_policy_conforms_to_the_sealed_port(jena: JenaMarkingProjectionAdapter) -> None:
    policy = RegistrationAndMarkingPolicy(
        registry={}, marking_engine=MarkingEngine([CLASSIFICATION_SCHEME]), marking_port=jena, clearance_by_marking_ref={}
    )
    assert isinstance(policy, PolicyDecisionPort)


def test_gateway_conforms_to_the_sealed_named_query_port(
    identity_registry: IdentityRegistry, jena: JenaMarkingProjectionAdapter, typedb: TypeDBExactCommitAdapter
) -> None:
    gateway = make_gateway(
        identity_registry=identity_registry, jena=jena, typedb=typedb, marking_ref_to_clearance_level={}
    )
    assert isinstance(gateway, NamedQueryPort)


def test_a_registered_query_executes_for_an_identified_and_authorized_principal(
    identity_registry: IdentityRegistry, jena: JenaMarkingProjectionAdapter, typedb: TypeDBExactCommitAdapter
) -> None:
    jena.ingest_marked(RESOURCE_ID, "fixture", "SECRET")
    gateway = make_gateway(
        identity_registry=identity_registry,
        jena=jena,
        typedb=typedb,
        marking_ref_to_clearance_level={DIGEST_A: "SECRET"},
    )
    request = make_request(principal="urn:ocor:principal:analyst-1")

    response = gateway.execute(request)

    assert response.served.canonical_commit == "commit-1"


def test_an_unregistered_contract_id_is_denied_without_any_response(
    identity_registry: IdentityRegistry, jena: JenaMarkingProjectionAdapter, typedb: TypeDBExactCommitAdapter
) -> None:
    jena.ingest_marked(RESOURCE_ID, "fixture", "SECRET")
    gateway = make_gateway(
        identity_registry=identity_registry,
        jena=jena,
        typedb=typedb,
        marking_ref_to_clearance_level={DIGEST_A: "SECRET"},
    )
    request = make_request(principal="urn:ocor:principal:analyst-1", contract_id="urn:ocor:contract:named-query:not-registered")

    result = None
    try:
        result = gateway.execute(request)
    except C2Error as error:
        assert error.reason_code == "ARBITRARY_QUERY_FORBIDDEN"
    assert result is None


def test_an_unregistered_version_is_denied_without_any_response(
    identity_registry: IdentityRegistry, jena: JenaMarkingProjectionAdapter, typedb: TypeDBExactCommitAdapter
) -> None:
    jena.ingest_marked(RESOURCE_ID, "fixture", "SECRET")
    gateway = make_gateway(
        identity_registry=identity_registry,
        jena=jena,
        typedb=typedb,
        marking_ref_to_clearance_level={DIGEST_A: "SECRET"},
    )
    request = make_request(principal="urn:ocor:principal:analyst-1", contract_version="9.9.9")

    result = None
    try:
        result = gateway.execute(request)
    except C2Error as error:
        assert error.reason_code == "ARBITRARY_QUERY_FORBIDDEN"
    assert result is None


def test_an_ambiguous_unregistered_identity_is_denied_without_any_response(
    identity_registry: IdentityRegistry, jena: JenaMarkingProjectionAdapter, typedb: TypeDBExactCommitAdapter
) -> None:
    jena.ingest_marked(RESOURCE_ID, "fixture", "SECRET")
    gateway = make_gateway(
        identity_registry=identity_registry,
        jena=jena,
        typedb=typedb,
        marking_ref_to_clearance_level={DIGEST_A: "SECRET"},
    )
    request = make_request(principal="urn:ocor:principal:never-registered")

    result = None
    try:
        result = gateway.execute(request)
    except C2Error as error:
        assert error.reason_code == "IDENTITY_AMBIGUOUS"
    assert result is None


def test_a_resource_outside_the_requesters_clearance_is_denied_before_projection_is_ever_read(
    identity_registry: IdentityRegistry, jena: JenaMarkingProjectionAdapter, typedb: TypeDBExactCommitAdapter
) -> None:
    jena.ingest_marked(RESOURCE_ID, "fixture", "TOP_SECRET")
    gateway = make_gateway(
        identity_registry=identity_registry,
        jena=jena,
        typedb=typedb,
        marking_ref_to_clearance_level={DIGEST_A: "UNCLASSIFIED"},
    )
    request = make_request(principal="urn:ocor:principal:analyst-1")

    result = None
    try:
        result = gateway.execute(request)
    except C2Error as error:
        # the same reason code as an unregistered contract: a caller must
        # not be able to distinguish "not registered" from "marking denied"
        # from the error alone.
        assert error.reason_code == "ARBITRARY_QUERY_FORBIDDEN"
    assert result is None


def test_a_resource_missing_its_marking_triple_is_denied_never_disclosed(
    identity_registry: IdentityRegistry, jena: JenaMarkingProjectionAdapter, typedb: TypeDBExactCommitAdapter
) -> None:
    jena.ingest_unmarked(RESOURCE_ID, "fixture")
    gateway = make_gateway(
        identity_registry=identity_registry,
        jena=jena,
        typedb=typedb,
        marking_ref_to_clearance_level={DIGEST_A: "TOP_SECRET"},
    )
    request = make_request(principal="urn:ocor:principal:analyst-1")

    result = None
    try:
        result = gateway.execute(request)
    except C2Error as error:
        assert error.reason_code == "ARBITRARY_QUERY_FORBIDDEN"
    assert result is None


def test_an_unresolvable_clearance_reference_is_denied_without_any_response(
    identity_registry: IdentityRegistry, jena: JenaMarkingProjectionAdapter, typedb: TypeDBExactCommitAdapter
) -> None:
    jena.ingest_marked(RESOURCE_ID, "fixture", "SECRET")
    gateway = make_gateway(
        identity_registry=identity_registry, jena=jena, typedb=typedb, marking_ref_to_clearance_level={}
    )
    request = make_request(principal="urn:ocor:principal:analyst-1")

    result = None
    try:
        result = gateway.execute(request)
    except C2Error as error:
        assert error.reason_code == "ARBITRARY_QUERY_FORBIDDEN"
    assert result is None


def test_a_registered_query_without_a_resource_parameter_skips_the_marking_join(
    identity_registry: IdentityRegistry, jena: JenaMarkingProjectionAdapter, typedb: TypeDBExactCommitAdapter
) -> None:
    gateway = make_gateway(
        identity_registry=identity_registry, jena=jena, typedb=typedb, marking_ref_to_clearance_level={}
    )
    request = make_request(principal="urn:ocor:principal:analyst-1", resource_id=None)

    response = gateway.execute(request)

    assert response.served.canonical_commit == "commit-1"


def test_missing_purpose_is_rejected_before_any_gateway_or_backend_call(identity_registry: IdentityRegistry) -> None:
    with pytest.raises(GovernedContextError) as excinfo:
        GovernedContext.from_mapping(
            {
                "tenant_id": "urn:ocor:tenant:synthetic",
                "organization_id": "urn:ocor:org:synthetic",
                "domain_id": "urn:ocor:domain:logistics",
                "compartments": ["urn:ocor:compartment:alpha"],
                "classification_marking_ref": DIGEST_A,
                "purpose": "",
                "effective_principal_id": "urn:ocor:principal:analyst-1",
                "actor_chain": ["urn:ocor:principal:analyst-1"],
                "ontology_release_digest": DIGEST_B,
                "policy_bundle_digest": DIGEST_C,
                "correlation_id": "018f2f95-01b2-7cc3-8d4e-123456789abc",
            }
        )
    assert excinfo.value.code == "GOVERNED_CONTEXT_INVALID"


def test_an_arbitrary_query_shape_is_rejected_before_any_gateway_or_backend_call() -> None:
    context = GovernedContext.from_mapping(
        {
            "tenant_id": "urn:ocor:tenant:synthetic",
            "organization_id": "urn:ocor:org:synthetic",
            "domain_id": "urn:ocor:domain:logistics",
            "compartments": ["urn:ocor:compartment:alpha"],
            "classification_marking_ref": DIGEST_A,
            "purpose": "gateway-fixture",
            "effective_principal_id": "urn:ocor:principal:analyst-1",
            "actor_chain": ["urn:ocor:principal:analyst-1"],
            "ontology_release_digest": DIGEST_B,
            "policy_bundle_digest": DIGEST_C,
            "correlation_id": "018f2f95-01b2-7cc3-8d4e-123456789abc",
        }
    )
    with pytest.raises(C2Error) as excinfo:
        NamedQueryRequest(
            request_id="018f2f95-01b2-7cc3-8d4e-123456789abc",
            contract_id="not-a-registered-contract-urn",
            contract_version="1.0.0",
            contract_digest=DIGEST_A,
            parameters={},
            governed_context=context,
            governed_context_digest=context.digest(),
            consistency=ConsistencyRequirement(mode=ConsistencyMode.BEST_AVAILABLE),
        )
    assert excinfo.value.reason_code == "ARBITRARY_QUERY_FORBIDDEN"


class _UnreachableMarkingPort:
    """A real ``MarkingAuthorizationPort`` implementation pointed at a
    genuinely closed local TCP port -- the same real, lower-blast-radius
    network fault used by OCOR-DEV-0026/0027, rather than pausing a
    shared, CI-provisioned backend container."""

    def exists_authorized(self, resource_id: str, clearance: MarkingSet) -> bool:
        with socket.create_connection(("127.0.0.1", 1), timeout=1.0):
            return True  # pragma: no cover -- unreachable, the connect above always raises


def test_a_real_marking_backend_failure_propagates_and_never_defaults_to_permit(
    identity_registry: IdentityRegistry, typedb: TypeDBExactCommitAdapter
) -> None:
    unreachable_port: MarkingAuthorizationPort = _UnreachableMarkingPort()
    policy = RegistrationAndMarkingPolicy(
        registry={
            CONTRACT_ID: RegisteredNamedQuery(
                contract_id=CONTRACT_ID, versions=frozenset({"1.0.0"}), marking_scheme_id="classification"
            )
        },
        marking_engine=MarkingEngine([CLASSIFICATION_SCHEME]),
        marking_port=unreachable_port,
        clearance_by_marking_ref={DIGEST_A: clearance("SECRET")},
    )
    gateway = NamedQueryGateway(
        authority=IdentityBackedAuthority(identity_registry), policy=policy, projection=typedb
    )
    request = make_request(principal="urn:ocor:principal:analyst-1")

    with pytest.raises(OSError):
        gateway.execute(request)
