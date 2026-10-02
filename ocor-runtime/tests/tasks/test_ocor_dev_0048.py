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

import base64
import hashlib
import importlib.util
import json
import os
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ocor_runtime.kernel.governed_context import GovernedContext
from ocor_runtime.security.control_plane import (
    KeycloakIdentityProvider,
    OpaPolicyDecisionProvider,
    OpenBaoSecretProvider,
    SignedDelegation,
    SignedPolicyBundle,
    SpireWorkloadIdentityProvider,
    _b64_decode,
    _der_to_pem,
    _rsa_sign,
    _split_der_chain,
    verify_signed_delegation,
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

def _rego(principal_id: str) -> str:
    return (
        "package ocor.control_plane\n\n"
        "default allow := false\n\n"
        "allow if {\n"
        f'    input.principal_id == "{principal_id}"\n'
        '    input.action == "read"\n'
        '    input.resource == "urn:ocor:target:site-1"\n'
        "}\n"
    )

SERVICE_URLS = {
    "OPA": "http://127.0.0.1:8181/health",
    "Keycloak": "http://127.0.0.1:8080/realms/master/.well-known/openid-configuration",
    "OpenBao": "http://127.0.0.1:8200/v1/sys/health",
}

# Test-only policy-bundle signer (RSA-2048).  This key pair exists solely to
# prove the provider verifies a detached signature against a pinned public key;
# it is not a production credential and no private material is used elsewhere.
_SIGNER = "ocor-policy-signer-test"
_SIGNER_N = int(
    "00e1a86107dff3770af8b36aeed51e5f2c82aafc616fb3a365634f1ddcfdb1038"
    "e238da4600fa9f8b15223a1f4e9d63d60250ed5b323603d77a6659315e71ef71"
    "ae6982059fe31e6e98c8c12757863f7bcf2b8a83cd8ce0828f8e1b7a5e8128fc"
    "6a9779db09380fa5436ca701047def3fcec1416c36212bcf3d58b1af38678181"
    "d5ef740b6b4f0fbca559d4fd3be16aa3d39039e41cd918e4aad55c7c6785661a"
    "acd857fde6dec923ded1591e904d89024c4457e01984288e6cceb6b6cdafaaece"
    "ee2f568c245606e2ada66fa54ff4ca638729d1665d9e3a2c833be120f7a10a57"
    "df84e2dd099e49131291f0945c39ecc6c99be590655bb26460c8bd7d64c20717",
    16,
)
_SIGNER_E = 65537
_SIGNER_D = int(
    "0467d4a92232af26cc2f388dbc2471283dced7c991343922f01ae9d2d8331e06"
    "26e48b8a8293c772b2cf5648a14e18f9a90f8e958641c9416e42ba69e98ebdb5"
    "4d3e381779b280b71b92da83679bd008e4d63d169f06fabace0d1e18439d2528"
    "74438d1516f4242f03b8d512444cf28784166a515b3751701341b97f7aa71a95"
    "62d34fed0cc6d40a97eccc5dfb036d581bb72711fd1dd5f13ce69ce482f40231"
    "d3bd23a7da2d985862a2e7d33a01d3a261d9fccd2315290736ca7f46a7b61186"
    "6a39d6a8aa36ba26dbc7ae26a20942bb82d72a47dc877d9a1c17fa3665413c16"
    "b29d1f08cb29ba9050d41e4a66cb7e14d1f3f67da8707fce47ef20e7c65c8761",
    16,
)


def _sign_bundle(
    rego_source: str,
    *,
    policy_id: str = POLICY_ID,
    signer: str = _SIGNER,
    not_before: datetime | None = None,
    expires_at: datetime | None = None,
) -> SignedPolicyBundle:
    not_before = not_before or _now() - timedelta(minutes=5)
    expires_at = expires_at or _now() + timedelta(hours=1)
    unsigned = SignedPolicyBundle(
        policy_id=policy_id,
        rego_source=rego_source,
        signer=signer,
        not_before=not_before,
        expires_at=expires_at,
        signature="",
    )
    signature = base64.b64encode(
        _rsa_sign(unsigned.signing_payload(), _SIGNER_N, _SIGNER_D)
    ).decode()
    return replace(unsigned, signature=signature)


def _install_policy(
    provider: OpaPolicyDecisionProvider, rego_source: str
) -> str:
    return provider.install_policy(_sign_bundle(rego_source))


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


# --------------------------------------------------------------------------- #
# mTLS reverse proxy: a real TLS-terminating front that requires and verifies
# the caller's workload SVID and forwards plaintext to the local backend.  It
# exists solely to prove the providers carry the SVID on the transport, not
# merely fetch it in a separate (unused) probe.
# --------------------------------------------------------------------------- #


def _fetch_svid_json() -> dict[str, object]:
    completed = subprocess.run(
        [
            "docker",
            "exec",
            SPIRE_AGENT_CONTAINER,
            "/opt/spire/bin/spire-agent",
            "api",
            "fetch",
            "x509",
            "-socketPath",
            SPIRE_SOCKET,
            "-output",
            "json",
        ],
        capture_output=True,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        pytest.skip("spire-agent api fetch x509 failed; a real SVID is mandatory")
    svids = json.loads(completed.stdout.decode()).get("svids") or []
    assert svids, "no SVID returned by spire-agent"
    return svids[0]


def _server_tls_material() -> dict[str, str]:
    svid = _fetch_svid_json()
    chain = _split_der_chain(_b64_decode(str(svid["x509_svid"])))
    key_der = _b64_decode(str(svid["x509_svid_key"]))
    bundle_der = _b64_decode(str(svid["bundle"]))
    return {
        "cert_pem": "".join(_der_to_pem(der, "CERTIFICATE") for der in chain),
        "key_pem": _der_to_pem(key_der, "PRIVATE KEY"),
        "ca_pem": _der_to_pem(bundle_der, "CERTIFICATE"),
    }


def _read_http_head_and_body(sock: socket.socket) -> tuple[bytes, bytes]:
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(65536)
        if not chunk:
            break
        buf += chunk
    head, _, body = buf.partition(b"\r\n\r\n")
    content_length = 0
    for line in head.split(b"\r\n"):
        if line.lower().startswith(b"content-length:"):
            content_length = int(line.split(b":", 1)[1].strip())
    while len(body) < content_length:
        chunk = sock.recv(65536)
        if not chunk:
            break
        body += chunk
    return head, body


def _read_until_eof(sock: socket.socket) -> bytes:
    chunks: list[bytes] = []
    while True:
        chunk = sock.recv(65536)
        if not chunk:
            break
        chunks.append(chunk)
    return b"".join(chunks)


def _set_header(head: bytes, name: bytes, value: bytes) -> bytes:
    lines = head.split(b"\r\n")
    lowered = name.lower()
    updated = False
    for i, line in enumerate(lines):
        if b":" in line and line.split(b":", 1)[0].strip().lower() == lowered:
            lines[i] = name + b": " + value
            updated = True
    if not updated:
        lines.append(name + b": " + value)
    return b"\r\n".join(lines)


class _MtlsReverseProxy:
    """TLS-terminating loopback proxy with mandatory, verified client auth."""

    def __init__(
        self,
        backend_host: str,
        backend_port: int,
        server_cert_pem: str,
        server_key_pem: str,
        client_ca_pem: str,
    ) -> None:
        self._backend = (backend_host, backend_port)
        self._server_cert_pem = server_cert_pem
        self._server_key_pem = server_key_pem
        self._client_ca_pem = client_ca_pem
        self._lsock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._port = 0
        self._td: tempfile.TemporaryDirectory[str] | None = None

    def __enter__(self) -> "_MtlsReverseProxy":
        self._td = tempfile.TemporaryDirectory()
        cert_path = os.path.join(self._td.name, "server.pem")
        key_path = os.path.join(self._td.name, "server.key")
        with open(cert_path, "w") as handle:
            handle.write(self._server_cert_pem)
        with open(key_path, "w") as handle:
            handle.write(self._server_key_pem)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=cert_path, keyfile=key_path)
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_verify_locations(cadata=self._client_ca_pem)
        self._context = context
        self._lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._lsock.bind(("127.0.0.1", 0))
        self._lsock.listen(16)
        self._port = int(self._lsock.getsockname()[1])
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        return self

    def _serve(self) -> None:
        assert self._lsock is not None
        while not self._stop.is_set():
            try:
                self._lsock.settimeout(0.5)
                conn, _ = self._lsock.accept()
            except (socket.timeout, OSError):
                continue
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, conn: socket.socket) -> None:
        try:
            tls = self._context.wrap_socket(conn, server_side=True)
        except (ssl.SSLError, OSError):
            conn.close()
            return
        try:
            head, body = _read_http_head_and_body(tls)
            if not head:
                return
            head = _set_header(head, b"Connection", b"close")
            backend = socket.create_connection(self._backend, timeout=10)
            try:
                backend.sendall(head + b"\r\n\r\n" + body)
                backend.settimeout(30)
                response = _read_until_eof(backend)
            finally:
                backend.close()
            tls.sendall(response)
        except (ssl.SSLError, OSError):
            pass
        finally:
            tls.close()

    @property
    def url(self) -> str:
        return f"https://127.0.0.1:{self._port}"

    def __exit__(self, *exc: object) -> None:
        self._stop.set()
        if self._lsock is not None:
            try:
                self._lsock.close()
            except OSError:
                pass
        if self._thread is not None:
            self._thread.join(timeout=5)
        if self._td is not None:
            self._td.cleanup()


# --------------------------------------------------------------------------- #
# mTLS fixtures: a session-scoped client context carrying the real workload
# SVID plus three TLS-terminating reverse proxies that require and verify the
# caller's certificate before forwarding to the plaintext local backend.
# --------------------------------------------------------------------------- #


def _tls_handshake(url: str, context: ssl.SSLContext) -> dict[str, object]:
    host = "127.0.0.1"
    port = int(url.rsplit(":", 1)[1])
    with socket.create_connection((host, port), timeout=10) as raw:
        with context.wrap_socket(raw, server_hostname=host) as tls:
            tls.do_handshake()
            return tls.getpeercert() or {}


@pytest.fixture(scope="session")
def mtls(live_stack: None) -> dict[str, object]:
    if not fault_inject.container_healthy(SPIRE_AGENT_CONTAINER):
        pytest.skip("SPIRE agent container is unavailable; real mTLS is mandatory")
    provider = SpireWorkloadIdentityProvider(
        agent_container=SPIRE_AGENT_CONTAINER,
        socket_path=SPIRE_SOCKET,
        expected_spiffe_id=EXPECTED_SPIFFE_ID,
    )
    client_context = provider.mtls_context()
    material = _server_tls_material()
    proxies: list[_MtlsReverseProxy] = []
    for backend_port in (8181, 8080, 8200):
        proxy = _MtlsReverseProxy(
            "127.0.0.1",
            backend_port,
            material["cert_pem"],
            material["key_pem"],
            material["ca_pem"],
        )
        proxy.__enter__()
        proxies.append(proxy)
    try:
        yield {
            "ssl_context": client_context,
            "opa": proxies[0].url,
            "keycloak": proxies[1].url,
            "openbao": proxies[2].url,
        }
    finally:
        for proxy in proxies:
            proxy.__exit__(None, None, None)







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
def principal(principals: None, mtls: dict[str, object]) -> AuthenticatedPrincipal:
    provider = KeycloakIdentityProvider(
        str(mtls["keycloak"]),
        REALM,
        CLIENT_ID,
        password_resolver=lambda u: USER_PWD if u == USERNAME else "",
        ssl_context=mtls["ssl_context"],
    )
    return provider.authenticate(
        IdentityRequest(f"urn:ocor:credential-ref:{USERNAME}", "account", str(uuid.uuid4()))
    )


@pytest.fixture
def opa(
    principal: AuthenticatedPrincipal, mtls: dict[str, object]
) -> tuple[OpaPolicyDecisionProvider, str]:
    provider = OpaPolicyDecisionProvider(
        str(mtls["opa"]), POLICY_ID, signer_public_key=(_SIGNER_N, _SIGNER_E), ssl_context=mtls["ssl_context"]
    )
    digest = _install_policy(provider, _rego(principal.principal_id))
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


def test_split_der_chain_and_tlv_parse_synthetic_concatenation():
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
    # principal_id is the immutable Keycloak subject (sub), never the username
    assert principal.principal_id != USERNAME
    assert principal.principal_id == principal.actor_chain[-1]
    assert principal.assurance_level in ("LEVEL_1", "LEVEL_2")
    assert principal.session_id


def test_wrong_password_fails_closed(principals: None, mtls: dict[str, object]):
    provider = KeycloakIdentityProvider(
        str(mtls["keycloak"]),
        REALM,
        CLIENT_ID,
        password_resolver=lambda u: "wrong",
        ssl_context=mtls["ssl_context"],
    )
    with pytest.raises(SecurityControlError) as excinfo:
        provider.authenticate(
            IdentityRequest(f"urn:ocor:credential-ref:{USERNAME}", "account", str(uuid.uuid4()))
        )
    assert excinfo.value.reason_code == "IDENTITY_REJECTED"


def test_wrong_audience_fails_closed(principals: None, mtls: dict[str, object]):
    provider = KeycloakIdentityProvider(
        str(mtls["keycloak"]),
        REALM,
        CLIENT_ID,
        password_resolver=lambda u: USER_PWD,
        ssl_context=mtls["ssl_context"],
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


def test_policy_install_persists_and_returns_content_digest(
    principal: AuthenticatedPrincipal, opa: tuple[OpaPolicyDecisionProvider, str]
):
    provider, digest = opa
    source = _rego(principal.principal_id)
    assert digest == "urn:sha256:" + hashlib.sha256(source.encode()).hexdigest()
    assert provider._fetch_policy_source() == source


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


def test_policy_receives_all_governed_attributes(
    principal: AuthenticatedPrincipal, mtls: dict[str, object]
):
    provider = OpaPolicyDecisionProvider(
        str(mtls["opa"]),
        POLICY_ID,
        signer_public_key=(_SIGNER_N, _SIGNER_E),
        ssl_context=mtls["ssl_context"],
    )
    rego = (
        "package ocor.control_plane\n\n"
        "default allow := false\n\n"
        "allow if {\n"
        '    input.tenant_id == "tenant-a"\n'
        '    input.organization_id == "org-a"\n'
        '    input.domain_id == "domain-a"\n'
        '    input.compartments == ["compartment-a"]\n'
        '    input.classification_marking_ref == "urn:sha256:' + "0" * 64 + '"\n'
        "    input.effective_principal_id == input.principal_id\n"
        "    input.actor_chain[_] == input.principal_id\n"
        '    input.action == "read"\n'
        '    input.resource == "urn:ocor:target:site-1"\n'
        "}\n"
    )
    digest = _install_policy(provider, rego)
    request = _policy_request(principal, digest, action="read")
    decision = provider.evaluate(request)
    assert decision.effect is PolicyEffect.PERMIT


def test_policy_denies_when_tenant_is_not_forwarded(
    principal: AuthenticatedPrincipal, mtls: dict[str, object]
):
    provider = OpaPolicyDecisionProvider(
        str(mtls["opa"]),
        POLICY_ID,
        signer_public_key=(_SIGNER_N, _SIGNER_E),
        ssl_context=mtls["ssl_context"],
    )
    rego = (
        "package ocor.control_plane\n\n"
        "default allow := false\n\n"
        "allow if {\n"
        '    input.tenant_id == "tenant-b"\n'
        '    input.action == "read"\n'
        "}\n"
    )
    digest = _install_policy(provider, rego)
    # The governed context is tenant-a; if tenant_id were silently omitted the
    # comparison would be undefined, but it must be forwarded and denied here.
    request = _policy_request(principal, digest, action="read")
    decision = provider.evaluate(request)
    assert decision.effect is PolicyEffect.DENY


def test_stale_bundle_fails_closed(
    principal: AuthenticatedPrincipal, opa: tuple[OpaPolicyDecisionProvider, str]
):
    provider, digest = opa
    _http(
        "PUT",
        f"{OPA}/v1/policies/{POLICY_ID}",
        headers={"Content-Type": "text/plain"},
        body=_rego(principal.principal_id) + "# drift\n",
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
# mTLS transport: the providers present their workload SVID on the wire and
# verify the peer against the trust bundle; without either, they fail closed.
# --------------------------------------------------------------------------- #


def test_provider_requires_mtls_context():
    # Constructing a provider without a mutual-TLS context is an outright
    # refusal, not a silent downgrade to plaintext HTTP.
    with pytest.raises(SecurityControlError) as excinfo:
        OpaPolicyDecisionProvider(OPA, POLICY_ID, signer_public_key=(_SIGNER_N, _SIGNER_E))
    assert excinfo.value.reason_code == "MTLS_REQUIRED"


def test_mtls_transport_presents_and_verifies_workload_svid(mtls: dict[str, object]):
    # A successful handshake here means the provider-side context both presented
    # a client SVID that the proxy accepted and verified the proxy's SVID chain
    # against the SPIRE trust bundle (the context requires CERT_REQUIRED).
    peer = _tls_handshake(str(mtls["opa"]), mtls["ssl_context"])
    assert peer, "mutual-TLS handshake completed but no peer certificate was parsed"


def test_mtls_server_rejects_absent_client_certificate(mtls: dict[str, object]):
    # The reverse proxy requires and verifies a client certificate: a peer that
    # presents none is rejected, proving the "mutual" half of mTLS is enforced
    # by the server side, not merely claimed by the client.  With TLS 1.3 the
    # client may see its own Finished before the server's rejection lands, so
    # we drive a full request and require either a transport error or the
    # absence of any well-formed HTTP response.
    no_cert = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    no_cert.check_hostname = False
    no_cert.verify_mode = ssl.CERT_NONE
    host = "127.0.0.1"
    port = int(str(mtls["opa"]).rsplit(":", 1)[1])
    rejected = False
    with socket.create_connection((host, port), timeout=10) as raw:
        with no_cert.wrap_socket(raw, server_hostname=host) as tls:
            try:
                tls.do_handshake()
                tls.sendall(b"GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
                data = tls.recv(4096)
            except (ssl.SSLError, OSError):
                rejected = True
            else:
                rejected = not data.startswith(b"HTTP/")
    assert rejected, "server accepted an anonymous peer without a client certificate"



# --------------------------------------------------------------------------- #
# OpenBao: secret isolation, opaque handle, fail-closed
# --------------------------------------------------------------------------- #


def _seed_secret(
    env: dict[str, str], principal_id: str, secret_name: str, data: dict[str, str]
) -> None:
    status, body = _http(
        "POST",
        f"{OB}/v1/ocor/data/{principal_id}/{secret_name}",
        headers={
            "X-Vault-Token": env["OCOR_LOCAL_OPENBAO_TOKEN"],
            "Content-Type": "application/json",
        },
        body=json.dumps({"data": data}),
    )
    assert status in (200, 204), f"seed secret: HTTP {status} {body}"


def test_secret_lease_returns_opaque_handle(
    principal: AuthenticatedPrincipal,
    env: dict[str, str],
    opa: tuple[OpaPolicyDecisionProvider, str],
    mtls: dict[str, object],
):
    _, policy_digest = opa
    _seed_secret(
        env, principal.principal_id, "control-plane-db",
        {"dsn": "postgres://ocor:secret@control-plane-db/ocor"},
    )
    provider = OpenBaoSecretProvider(
        str(mtls["openbao"]), env["OCOR_LOCAL_OPENBAO_TOKEN"], mount="ocor", ssl_context=mtls["ssl_context"]
    )
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
    principal: AuthenticatedPrincipal,
    opa: tuple[OpaPolicyDecisionProvider, str],
    mtls: dict[str, object],
):
    _, policy_digest = opa
    provider = OpenBaoSecretProvider(
        str(mtls["openbao"]), "wrong-token", mount="ocor", ssl_context=mtls["ssl_context"]
    )
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


def test_paused_opa_fails_closed_within_bounded_timeout(
    principal: AuthenticatedPrincipal, mtls: dict[str, object]
):
    provider = OpaPolicyDecisionProvider(
        str(mtls["opa"]),
        POLICY_ID,
        signer_public_key=(_SIGNER_N, _SIGNER_E),
        timeout_seconds=2.0,
        ssl_context=mtls["ssl_context"],
    )
    digest = _install_policy(provider, _rego(principal.principal_id))
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
        # the denial is correlated to the exact request that caused it
        assert request.governed_context.correlation_id in str(excinfo.value)
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


# --------------------------------------------------------------------------- #
# Bundle integrity: digest pin, signature, validity window, non-boolean result
# --------------------------------------------------------------------------- #


def test_policy_pin_mismatch_fails_closed(
    principal: AuthenticatedPrincipal, opa: tuple[OpaPolicyDecisionProvider, str]
):
    provider, _ = opa
    wrong_digest = "urn:sha256:" + "f" * 64
    request = _policy_request(principal, wrong_digest, action="read")
    with pytest.raises(SecurityControlError) as excinfo:
        provider.evaluate(request)
    assert excinfo.value.reason_code == "STALE_BUNDLE"


def test_unsigned_bundle_fails_closed(mtls: dict[str, object]):
    provider = OpaPolicyDecisionProvider(
        str(mtls["opa"]),
        POLICY_ID,
        signer_public_key=(_SIGNER_N, _SIGNER_E),
        ssl_context=mtls["ssl_context"],
    )
    unsigned = SignedPolicyBundle(
        policy_id=POLICY_ID,
        rego_source=_rego("placeholder"),
        signer=_SIGNER,
        not_before=_now() - timedelta(minutes=5),
        expires_at=_now() + timedelta(hours=1),
        signature="",
    )
    with pytest.raises(SecurityControlError) as excinfo:
        provider.install_policy(unsigned)
    assert excinfo.value.reason_code == "POLICY_BUNDLE_SIGNATURE_INVALID"


def test_forged_bundle_signature_fails_closed(mtls: dict[str, object]):
    provider = OpaPolicyDecisionProvider(
        str(mtls["opa"]),
        POLICY_ID,
        signer_public_key=(_SIGNER_N, _SIGNER_E),
        ssl_context=mtls["ssl_context"],
    )
    valid = _sign_bundle(_rego("placeholder"))
    tampered = replace(valid, rego_source=_rego("placeholder") + "# tampered\n")
    with pytest.raises(SecurityControlError) as excinfo:
        provider.install_policy(tampered)
    assert excinfo.value.reason_code == "POLICY_BUNDLE_SIGNATURE_INVALID"


def test_expired_bundle_fails_closed(mtls: dict[str, object]):
    provider = OpaPolicyDecisionProvider(
        str(mtls["opa"]),
        POLICY_ID,
        signer_public_key=(_SIGNER_N, _SIGNER_E),
        ssl_context=mtls["ssl_context"],
    )
    bundle = _sign_bundle(
        _rego("placeholder"),
        not_before=_now() - timedelta(minutes=10),
        expires_at=_now() - timedelta(minutes=1),
    )
    with pytest.raises(SecurityControlError) as excinfo:
        provider.install_policy(bundle)
    assert excinfo.value.reason_code == "POLICY_BUNDLE_WINDOW_INVALID"


def test_non_boolean_policy_result_fails_closed(
    principal: AuthenticatedPrincipal, opa: tuple[OpaPolicyDecisionProvider, str]
):
    provider, _ = opa
    digest = provider.install_policy(
        _sign_bundle('package ocor.control_plane\n\nallow := {"permit": true}\n')
    )
    request = _policy_request(principal, digest, action="read")
    with pytest.raises(SecurityControlError) as excinfo:
        provider.evaluate(request)
    assert excinfo.value.reason_code == "POLICY_DECISION_INVALID"


# --------------------------------------------------------------------------- #
# Delegation binding: a forged actor chain never elevates privilege
# --------------------------------------------------------------------------- #


def test_forged_delegation_chain_fails_closed(
    principal: AuthenticatedPrincipal, opa: tuple[OpaPolicyDecisionProvider, str]
):
    provider, digest = opa
    gcs = GovernedContext(
        tenant_id="tenant-a",
        organization_id="org-a",
        domain_id="domain-a",
        compartments=("compartment-a",),
        classification_marking_ref="urn:sha256:" + "0" * 64,
        purpose="read-site-1",
        effective_principal_id=principal.principal_id,
        actor_chain=("forged-delegator",),
        ontology_release_digest="urn:sha256:" + "1" * 64,
        policy_bundle_digest=digest,
        correlation_id=str(uuid.uuid4()),
    )
    request = PolicyRequest(
        principal=principal,
        action="read",
        resource="urn:ocor:target:site-1",
        governed_context=gcs,
        governed_context_digest=gcs.digest(),
        at=_now(),
    )
    with pytest.raises(SecurityControlError) as excinfo:
        provider.evaluate(request)
    assert excinfo.value.reason_code == "IDENTITY_BINDING_MISMATCH"


def _sign_delegation(
    *,
    delegatee_id: str,
    delegator_id: str = "delegator-1",
    resource_scopes: tuple[str, ...] = ("urn:ocor:target:site-1",),
    permitted_purposes: tuple[str, ...] = ("read-site-1",),
    not_before: datetime | None = None,
    expires_at: datetime | None = None,
) -> SignedDelegation:
    unsigned = SignedDelegation(
        delegation_id="urn:ocor:delegation:test",
        delegator_id=delegator_id,
        delegatee_id=delegatee_id,
        resource_scopes=resource_scopes,
        permitted_purposes=permitted_purposes,
        not_before=not_before or _now() - timedelta(minutes=5),
        expires_at=expires_at or _now() + timedelta(hours=1),
        signature="",
    )
    signature = base64.b64encode(
        _rsa_sign(unsigned.signing_payload(), _SIGNER_N, _SIGNER_D)
    ).decode("ascii")
    return replace(unsigned, signature=signature)


# --------------------------------------------------------------------------- #
# Signed delegation: real crypto, bounded scope, revocation and window fences
# --------------------------------------------------------------------------- #


def test_valid_signed_delegation_grants_within_bounds(principal: AuthenticatedPrincipal):
    delegation = _sign_delegation(delegatee_id=principal.principal_id)
    verify_signed_delegation(
        delegation,
        (_SIGNER_N, _SIGNER_E),
        resource_scope="urn:ocor:target:site-1",
        purpose="read-site-1",
        delegator_id="delegator-1",
        delegatee_id=principal.principal_id,
        at=_now(),
    )


def test_delegation_over_scope_fails_closed(principal: AuthenticatedPrincipal):
    delegation = _sign_delegation(delegatee_id=principal.principal_id)
    with pytest.raises(SecurityControlError) as excinfo:
        verify_signed_delegation(
            delegation,
            (_SIGNER_N, _SIGNER_E),
            resource_scope="urn:ocor:target:other-site",
            purpose="read-site-1",
            delegator_id="delegator-1",
            delegatee_id=principal.principal_id,
            at=_now(),
        )
    assert excinfo.value.reason_code == "DELEGATION_SCOPE_MISMATCH"


def test_delegation_purpose_mismatch_fails_closed(principal: AuthenticatedPrincipal):
    delegation = _sign_delegation(delegatee_id=principal.principal_id)
    with pytest.raises(SecurityControlError) as excinfo:
        verify_signed_delegation(
            delegation,
            (_SIGNER_N, _SIGNER_E),
            resource_scope="urn:ocor:target:site-1",
            purpose="write-site-1",
            delegator_id="delegator-1",
            delegatee_id=principal.principal_id,
            at=_now(),
        )
    assert excinfo.value.reason_code == "DELEGATION_PURPOSE_MISMATCH"


def test_delegation_binding_mismatch_fails_closed(principal: AuthenticatedPrincipal):
    delegation = _sign_delegation(delegatee_id=principal.principal_id)
    with pytest.raises(SecurityControlError) as excinfo:
        verify_signed_delegation(
            delegation,
            (_SIGNER_N, _SIGNER_E),
            resource_scope="urn:ocor:target:site-1",
            purpose="read-site-1",
            delegator_id="delegator-1",
            delegatee_id="someone-else",
            at=_now(),
        )
    assert excinfo.value.reason_code == "DELEGATION_BINDING_MISMATCH"


def test_altered_delegation_fails_closed(principal: AuthenticatedPrincipal):
    delegation = _sign_delegation(delegatee_id=principal.principal_id)
    tampered = replace(
        delegation,
        resource_scopes=("urn:ocor:target:site-1", "urn:ocor:target:other-site"),
    )
    with pytest.raises(SecurityControlError) as excinfo:
        verify_signed_delegation(
            tampered,
            (_SIGNER_N, _SIGNER_E),
            resource_scope="urn:ocor:target:other-site",
            purpose="read-site-1",
            delegator_id="delegator-1",
            delegatee_id=principal.principal_id,
            at=_now(),
        )
    assert excinfo.value.reason_code == "DELEGATION_SIGNATURE_INVALID"


def test_revoked_delegation_fails_closed(principal: AuthenticatedPrincipal):
    delegation = _sign_delegation(delegatee_id=principal.principal_id)
    with pytest.raises(SecurityControlError) as excinfo:
        verify_signed_delegation(
            delegation,
            (_SIGNER_N, _SIGNER_E),
            resource_scope="urn:ocor:target:site-1",
            purpose="read-site-1",
            delegator_id="delegator-1",
            delegatee_id=principal.principal_id,
            at=_now(),
            revoked=True,
        )
    assert excinfo.value.reason_code == "DELEGATION_REVOKED"


def test_expired_delegation_fails_closed(principal: AuthenticatedPrincipal):
    delegation = _sign_delegation(
        delegatee_id=principal.principal_id,
        not_before=_now() - timedelta(minutes=10),
        expires_at=_now() - timedelta(minutes=1),
    )
    with pytest.raises(SecurityControlError) as excinfo:
        verify_signed_delegation(
            delegation,
            (_SIGNER_N, _SIGNER_E),
            resource_scope="urn:ocor:target:site-1",
            purpose="read-site-1",
            delegator_id="delegator-1",
            delegatee_id=principal.principal_id,
            at=_now(),
        )
    assert excinfo.value.reason_code == "DELEGATION_EXPIRED"


# --------------------------------------------------------------------------- #
# Secret isolation: an absent reference is an outright denial, never a write
# --------------------------------------------------------------------------- #


def test_absent_secret_ref_fails_closed_without_overwrite(
    principal: AuthenticatedPrincipal,
    env: dict[str, str],
    opa: tuple[OpaPolicyDecisionProvider, str],
    mtls: dict[str, object],
):
    _, policy_digest = opa
    provider = OpenBaoSecretProvider(
        str(mtls["openbao"]), env["OCOR_LOCAL_OPENBAO_TOKEN"], mount="ocor", ssl_context=mtls["ssl_context"]
    )
    gcs = _gcs(principal, policy_digest)
    request = SecretRequest(
        secret_ref="urn:ocor:secret-ref:absent-secret",
        principal_id=principal.principal_id,
        purpose="read-site-1",
        governed_context_digest=gcs.digest(),
        requested_at=_now(),
    )
    with pytest.raises(SecurityControlError) as excinfo:
        provider.lease(request)
    assert excinfo.value.reason_code == "SECRET_REFERENCE_UNRESOLVED"
    # no-overwrite: the lease attempt must not have provisioned the secret
    status, _ = _http(
        "GET",
        f"{OB}/v1/ocor/data/{principal.principal_id}/absent-secret",
        headers={"X-Vault-Token": env["OCOR_LOCAL_OPENBAO_TOKEN"]},
    )
    assert status == 404
