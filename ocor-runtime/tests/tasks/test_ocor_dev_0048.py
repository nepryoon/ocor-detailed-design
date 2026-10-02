"""OCOR-DEV-0048: real control-plane boundary providers (WS-11).

Least privilege (OPA), workload identity and mTLS trust (SPIFFE/SPIRE), policy
bundles (OPA), delegation (Keycloak) and secret isolation (OpenBao) are
enforced by the real services in the ``ocor-bootstrap`` stack -- never mocks.
Every positive case drives a live backend; every negative case proves a
fail-closed rejection for the right reason; every fault-injection case proves
an unreachable or stale control stops answering as a denial, not a permit.

The SPIKE counterpart (OCOR-DEV-0021) proved bounded-timeout latency and
failure semantics for the control-plane *probe*; this task proves the same
semantics on the *provider* boundary itself, reusing the sealed ports
(OCOR-DEV-0014) and the sealed fault-injection helpers (WS-12) unmodified.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ocor_runtime.kernel.governed_context import GovernedContext
from ocor_runtime.security.control_plane import (
    KeycloakIdentityProvider,
    OpaPolicyDecisionProvider,
    OpenBaoSecretProvider,
    SpireWorkloadIdentityProvider,
)
from ocor_runtime.security.ports import (
    AuthenticatedPrincipal,
    IdentityRequest,
    PolicyEffect,
    PolicyRequest,
    SecretRequest,
    SecurityControlError,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))
SCRIPTS_DIR = REPOSITORY_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

_SPEC = importlib.util.spec_from_file_location(
    "fault_inject_test_environment_0048", SCRIPTS_DIR / "fault_inject_test_environment.py"
)
assert _SPEC is not None and _SPEC.loader is not None
fault_inject = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = fault_inject
_SPEC.loader.exec_module(fault_inject)

KC = "http://127.0.0.1:8080"
OPA = "http://127.0.0.1:8181"
OB = "http://127.0.0.1:8200"
REALM = "ocor"
CLIENT_ID = "ocor-control-plane"
USERNAME = "analyst-1"
USER_PWD = "analyst-pass-123"
POLICY_ID = "ocor-control-plane"
SPIRE_AGENT_CONTAINER = "ocor-bootstrap-spire-agent-1"
SPIRE_SOCKET = "/run/spire/sockets/agent.sock"
EXPECTED_SPIFFE_ID = "spiffe://ocor.test/ocor/control-plane"

REGO = (
    "package ocor.control_plane\n\n"
    "default allow := false\n\n"
    "allow if {\n"
    '    input.principal_id == "analyst-1"\n'
    '    input.action == "read"\n'
    '    input.resource == "urn:ocor:target:site-1"\n'
    "}\n"
)

SERVICE_URLS = {
    "OPA": "http://127.0.0.1:8181/health",
    "Keycloak": "http://127.0.0.1:8080/realms/master/.well-known/openid-configuration",
    "OpenBao": "http://127.0.0.1:8200/v1/sys/health",
}


def _env_file() -> Path | None:
    if os.environ.get("OCOR_BOOTSTRAP_ENV"):
        candidate = Path(os.environ["OCOR_BOOTSTRAP_ENV"])
        if candidate.exists():
            return candidate
    for candidate in (
        Path.home() / ".ocor-bootstrap-secrets" / "ocor-bootstrap.env",
        REPOSITORY_ROOT / ".ocor" / "bootstrap.env",
    ):
        if candidate.exists():
            return candidate
    for parent in Path(__file__).resolve().parents:
        candidate = parent / ".ocor" / "bootstrap.env"
        if candidate.exists():
            return candidate
    return None


def _load_env() -> dict[str, str]:
    path = _env_file()
    if path is None:
        pytest.skip(
            "ocor-bootstrap env file not found; real credentials are mandatory qualifying evidence"
        )
    env: dict[str, str] = {}
    for line in path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, _, value = line.partition("=")
            env[key] = value
    return env


def _http(method: str, url: str, *, headers: dict[str, str] | None = None, body: str | None = None):
    import urllib.error
    import urllib.request

    data = body.encode() if isinstance(body, str) else body
    req = urllib.request.Request(url, method=method, data=data)
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def _now() -> datetime:
    return datetime.now(UTC)


@pytest.fixture(scope="session")
def env() -> dict[str, str]:
    return _load_env()


@pytest.fixture(scope="session")
def live_stack(env: dict[str, str]) -> None:
    for label, url in SERVICE_URLS.items():
        if not fault_inject.http_reachable(url, timeout=5.0):
            pytest.skip(f"{label} is unreachable; real services are mandatory qualifying evidence")


@pytest.fixture(scope="session")
def admin_token(live_stack: None, env: dict[str, str]) -> str:
    import json
    import urllib.parse

    status, body = _http(
        "POST",
        f"{KC}/realms/master/protocol/openid-connect/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        body=(
            "client_id=admin-cli"
            f"&username=ocor-admin&password={urllib.parse.quote(env['OCOR_LOCAL_KEYCLOAK_PASSWORD'])}"
            "&grant_type=password"
        ),
    )
    assert status == 200, f"Keycloak admin token: HTTP {status} {body}"
    return json.loads(body)["access_token"]


@pytest.fixture(scope="session")
def principals(admin_token: str) -> None:
    import json

    headers = {"Authorization": f"Bearer {admin_token}"}
    status, body = _http(
        "GET", f"{KC}/admin/realms/{REALM}/clients?clientId={CLIENT_ID}", headers=headers
    )
    assert status == 200, f"client lookup: HTTP {status} {body}"
    clients = json.loads(body)
    if not clients:
        payload = json.dumps(
            {
                "clientId": CLIENT_ID,
                "enabled": True,
                "publicClient": True,
                "directAccessGrantsEnabled": True,
                "standardFlowEnabled": False,
                "protocol": "openid-connect",
                "redirectUris": ["http://127.0.0.1:8080/*"],
            }
        )
        status, body = _http(
            "POST",
            f"{KC}/admin/realms/{REALM}/clients",
            headers={**headers, "Content-Type": "application/json"},
            body=payload,
        )
        assert status in (200, 201), f"create client: HTTP {status} {body}"

    status, body = _http(
        "GET", f"{KC}/admin/realms/{REALM}/users?username={USERNAME}", headers=headers
    )
    assert status == 200, f"user lookup: HTTP {status} {body}"
    users = json.loads(body)
    if not users:
        payload = json.dumps(
            {
                "username": USERNAME,
                "enabled": True,
                "firstName": "Analyst",
                "lastName": "One",
                "emailVerified": True,
            }
        )
        status, body = _http(
            "POST",
            f"{KC}/admin/realms/{REALM}/users",
            headers={**headers, "Content-Type": "application/json"},
            body=payload,
        )
        assert status in (200, 201), f"create user: HTTP {status} {body}"
        status, body = _http(
            "GET", f"{KC}/admin/realms/{REALM}/users?username={USERNAME}", headers=headers
        )
        users = json.loads(body)
    uid = users[0]["id"]
    payload = json.dumps({"type": "password", "value": USER_PWD, "temporary": False})
    status, body = _http(
        "PUT",
        f"{KC}/admin/realms/{REALM}/users/{uid}/reset-password",
        headers={**headers, "Content-Type": "application/json"},
        body=payload,
    )
    assert status == 204, f"reset password: HTTP {status} {body}"


@pytest.fixture
def principal(principals: None) -> AuthenticatedPrincipal:
    provider = KeycloakIdentityProvider(
        KC, REALM, CLIENT_ID, password_resolver=lambda u: USER_PWD if u == USERNAME else ""
    )
    return provider.authenticate(
        IdentityRequest(f"urn:ocor:credential-ref:{USERNAME}", "account", str(uuid.uuid4()))
    )


@pytest.fixture
def opa() -> tuple[OpaPolicyDecisionProvider, str]:
    provider = OpaPolicyDecisionProvider(OPA, POLICY_ID)
    digest = provider.install_policy(REGO)
    return provider, digest


def _gcs(principal: AuthenticatedPrincipal, policy_digest: str) -> GovernedContext:
    return GovernedContext(
        tenant_id="tenant-a",
        organization_id="org-a",
        domain_id="domain-a",
        compartments=("compartment-a",),
        classification_marking_ref="urn:sha256:" + "0" * 64,
        purpose="read-site-1",
        effective_principal_id=principal.principal_id,
        actor_chain=(principal.principal_id,),
        ontology_release_digest="urn:sha256:" + "1" * 64,
        policy_bundle_digest=policy_digest,
        correlation_id=str(uuid.uuid4()),
    )


def _policy_request(
    principal: AuthenticatedPrincipal, policy_digest: str, action: str = "read"
) -> PolicyRequest:
    gcs = _gcs(principal, policy_digest)
    return PolicyRequest(
        principal=principal,
        action=action,
        resource="urn:ocor:target:site-1",
        governed_context=gcs,
        governed_context_digest=gcs.digest(),
        at=_now(),
    )


# --------------------------------------------------------------------------- #
# Unit: pure fail-closed parsing helpers (no live backend, no mock)
# --------------------------------------------------------------------------- #


def test_sha256_urn_and_b64_decode_are_deterministic():
    from ocor_runtime.security.control_plane import _b64_decode, _b64url_decode, _sha256_urn

    payload = b"ocor"
    digest = _sha256_urn(payload)
    assert digest == "urn:sha256:" + hashlib.sha256(payload).hexdigest()
    assert _sha256_urn(payload) == digest

    import base64

    assert _b64_decode(base64.b64encode(payload).decode()) == payload
    assert _b64url_decode(base64.urlsafe_b64encode(payload).decode()) == payload


def test_split_der_chain_and_tlv_parse_real_concatenation():
    from ocor_runtime.security.control_plane import _split_der_chain, _tlv

    # a SEQUENCE of 3 content bytes parses to (tag=0x30, len=3, start=2, end=5)
    assert _tlv(b"\x30\x03\x01\x02\x03", 0) == (0x30, 3, 2, 5)
    # two concatenated single-byte certs split into exactly two entries
    assert _split_der_chain(b"\x30\x01\x00" + b"\x30\x01\x00") == [b"\x30\x01\x00", b"\x30\x01\x00"]
    # an empty blob yields no certs; the provider's own len(chain) < 2 fence rejects it
    assert _split_der_chain(b"") == []


# --------------------------------------------------------------------------- #
# Keycloak: delegation chain and least-privilege identity, fail-closed
# --------------------------------------------------------------------------- #


def test_authenticate_real_keycloak_principal(principal: AuthenticatedPrincipal):
    assert principal.principal_id == USERNAME
    assert USERNAME in principal.actor_chain
    assert principal.assurance_level in ("LEVEL_1", "LEVEL_2")
    assert principal.session_id


def test_wrong_password_fails_closed(principals: None):
    provider = KeycloakIdentityProvider(KC, REALM, CLIENT_ID, password_resolver=lambda u: "wrong")
    with pytest.raises(SecurityControlError) as excinfo:
        provider.authenticate(
            IdentityRequest(f"urn:ocor:credential-ref:{USERNAME}", "account", str(uuid.uuid4()))
        )
    assert excinfo.value.reason_code == "IDENTITY_REJECTED"


def test_wrong_audience_fails_closed(principals: None):
    provider = KeycloakIdentityProvider(
        KC, REALM, CLIENT_ID, password_resolver=lambda u: USER_PWD
    )
    with pytest.raises(SecurityControlError) as excinfo:
        provider.authenticate(
            IdentityRequest(
                f"urn:ocor:credential-ref:{USERNAME}", "urn:ocor:audience:gateway", str(uuid.uuid4())
            )
        )
    assert excinfo.value.reason_code == "IDENTITY_REJECTED"


# --------------------------------------------------------------------------- #
# OPA: least privilege, signed policy bundle, stale-bundle fence
# --------------------------------------------------------------------------- #


def test_policy_install_persists_and_returns_content_digest(opa: tuple[OpaPolicyDecisionProvider, str]):
    provider, digest = opa
    assert digest == "urn:sha256:" + hashlib.sha256(REGO.encode()).hexdigest()
    assert provider._fetch_policy_source() == REGO


def test_policy_permit_for_matching_governed_input(
    principal: AuthenticatedPrincipal, opa: tuple[OpaPolicyDecisionProvider, str]
):
    provider, digest = opa
    request = _policy_request(principal, digest, action="read")
    decision = provider.evaluate(request)
    assert decision.effect is PolicyEffect.PERMIT
    decision.verify(request, at=_now())


def test_policy_deny_for_non_matching_action(
    principal: AuthenticatedPrincipal, opa: tuple[OpaPolicyDecisionProvider, str]
):
    provider, digest = opa
    decision = provider.evaluate(_policy_request(principal, digest, action="delete"))
    assert decision.effect is PolicyEffect.DENY


def test_stale_bundle_fails_closed(
    principal: AuthenticatedPrincipal, opa: tuple[OpaPolicyDecisionProvider, str]
):
    provider, digest = opa
    _http(
        "PUT",
        f"{OPA}/v1/policies/{POLICY_ID}",
        headers={"Content-Type": "text/plain"},
        body=REGO + "# drift\n",
    )
    with pytest.raises(SecurityControlError) as excinfo:
        provider.evaluate(_policy_request(principal, digest, action="read"))
    assert excinfo.value.reason_code == "STALE_BUNDLE"


# --------------------------------------------------------------------------- #
# SPIFFE/SPIRE: workload identity and mTLS trust verification
# --------------------------------------------------------------------------- #


@pytest.fixture
def spire(env: dict[str, str]) -> SpireWorkloadIdentityProvider:
    if not fault_inject.container_healthy(SPIRE_AGENT_CONTAINER):
        pytest.skip("SPIRE agent container is unavailable; a real workload identity is mandatory")
    return SpireWorkloadIdentityProvider(
        agent_container=SPIRE_AGENT_CONTAINER,
        socket_path=SPIRE_SOCKET,
        expected_spiffe_id=EXPECTED_SPIFFE_ID,
    )


def test_workload_identity_is_fetched_and_verified(spire: SpireWorkloadIdentityProvider):
    identity = spire.current()
    assert identity.spiffe_id == EXPECTED_SPIFFE_ID
    assert identity.attested is True
    assert identity.svid_ref.startswith("urn:sha256:")
    identity.require_valid(at=_now())


def test_unexpected_spiffe_id_fails_closed(env: dict[str, str]):
    if not fault_inject.container_healthy(SPIRE_AGENT_CONTAINER):
        pytest.skip("SPIRE agent container is unavailable; a real workload identity is mandatory")
    provider = SpireWorkloadIdentityProvider(
        agent_container=SPIRE_AGENT_CONTAINER,
        socket_path=SPIRE_SOCKET,
        expected_spiffe_id="spiffe://ocor.test/ocor/wrong",
    )
    with pytest.raises(SecurityControlError) as excinfo:
        provider.current()
    assert excinfo.value.reason_code == "WORKLOAD_IDENTITY_UNAVAILABLE"


# --------------------------------------------------------------------------- #
# OpenBao: secret isolation, opaque handle, fail-closed
# --------------------------------------------------------------------------- #


def test_secret_lease_returns_opaque_handle(
    principal: AuthenticatedPrincipal, env: dict[str, str], opa: tuple[OpaPolicyDecisionProvider, str]
):
    _, policy_digest = opa
    provider = OpenBaoSecretProvider(OB, env["OCOR_LOCAL_OPENBAO_TOKEN"], mount="ocor")
    gcs = _gcs(principal, policy_digest)
    request = SecretRequest(
        secret_ref="urn:ocor:secret-ref:control-plane-db",
        principal_id=principal.principal_id,
        purpose="read-site-1",
        governed_context_digest=gcs.digest(),
        requested_at=_now(),
    )
    lease = provider.lease(request)
    assert lease.handle_ref.startswith("urn:ocor:secret-handle:")
    assert lease.secret_ref == request.secret_ref
    lease.verify(request, at=_now())


def test_wrong_openbao_token_fails_closed(
    principal: AuthenticatedPrincipal, opa: tuple[OpaPolicyDecisionProvider, str]
):
    _, policy_digest = opa
    provider = OpenBaoSecretProvider(OB, "wrong-token", mount="ocor")
    gcs = _gcs(principal, policy_digest)
    request = SecretRequest(
        secret_ref="urn:ocor:secret-ref:control-plane-db",
        principal_id=principal.principal_id,
        purpose="read-site-1",
        governed_context_digest=gcs.digest(),
        requested_at=_now(),
    )
    with pytest.raises(SecurityControlError) as excinfo:
        provider.lease(request)
    assert excinfo.value.reason_code == "SECRETS_UNAVAILABLE"


# --------------------------------------------------------------------------- #
# Fault injection: a paused control plane stops answering as a denial
# --------------------------------------------------------------------------- #


def test_paused_opa_fails_closed_within_bounded_timeout(principal: AuthenticatedPrincipal):
    provider = OpaPolicyDecisionProvider(OPA, POLICY_ID, timeout_seconds=2.0)
    digest = provider.install_policy(REGO)
    request = _policy_request(principal, digest, action="read")
    provider.evaluate(request)

    pause = fault_inject.run(
        fault_inject.fault_command("opa", "pause"), cwd=REPOSITORY_ROOT, timeout=30
    )
    assert pause.returncode == 0, pause.stderr
    try:
        detected = fault_inject._poll(
            lambda: not fault_inject.http_reachable(SERVICE_URLS["OPA"], timeout=1.0), timeout=10.0
        )
        assert detected, "OPA was never observed unreachable after pause"
        start = time.monotonic()
        with pytest.raises(SecurityControlError) as excinfo:
            provider.evaluate(request)
        elapsed = time.monotonic() - start
        assert excinfo.value.reason_code in ("SERVICE_UNAVAILABLE", "POLICY_UNAVAILABLE")
        assert elapsed <= 2.0 + 1.0, f"fail-closed took {elapsed:.2f}s, exceeding its bound"
    finally:
        unpause = fault_inject.run(
            fault_inject.fault_command("opa", "unpause"), cwd=REPOSITORY_ROOT, timeout=30
        )
        assert unpause.returncode == 0, unpause.stderr
        recovered = fault_inject._poll(
            lambda: fault_inject.http_reachable(SERVICE_URLS["OPA"], timeout=2.0), timeout=15.0
        )
        assert recovered, "OPA did not recover within the bounded window after unpause"

    provider.evaluate(_policy_request(principal, digest, action="read"))
