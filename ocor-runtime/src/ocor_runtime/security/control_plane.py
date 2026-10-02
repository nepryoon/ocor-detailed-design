"""Real service-backed control-plane boundary providers.

OCOR-DEV-0048 (G4, WS-11) wires the four approved control-plane ports to the
local ``ocor-bootstrap`` services so that least privilege (OPA), workload
identity and mTLS trust (SPIFFE/SPIRE), policy bundles (OPA), delegation
(Keycloak) and secret isolation (OpenBao) are enforced by real backends.

Every provider fails closed: an unreachable service, a stale policy bundle, an
unverifiable signature or an unredeemable lease raises a correlated
:class:`SecurityControlError` instead of returning a usable record.  No secret
material ever crosses a port -- only opaque handles and digests do.
"""

from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta, timezone
from typing import cast

from .ports import (
    AuthenticatedPrincipal,
    ControlName,
    ControlStatus,
    IdentityRequest,
    PolicyDecision,
    PolicyEffect,
    PolicyRequest,
    SecretLease,
    SecretRequest,
    SecurityControlError,
    WorkloadIdentity,
)

_RFC3339 = "%Y-%m-%dT%H:%M:%SZ"
_DIGEST_INFO: dict[str, bytes] = {
    "sha256": bytes.fromhex("3031300d060960864801650304020105000420"),
    "sha384": bytes.fromhex("3041300d060960864801650304020205000430"),
    "sha512": bytes.fromhex("3051300d060960864801650304020305000440"),
}

# signatureAlgorithm OIDs -> (key kind, digest name)
_SIGALG: dict[bytes, tuple[str, str]] = {
    bytes.fromhex("2a8648ce3d040302"): ("ecdsa", "sha256"),
    bytes.fromhex("2a8648ce3d040303"): ("ecdsa", "sha384"),
    bytes.fromhex("2a8648ce3d040304"): ("ecdsa", "sha512"),
    bytes.fromhex("2a864886f70d01010b"): ("rsa", "sha256"),
    bytes.fromhex("2a864886f70d01010c"): ("rsa", "sha384"),
    bytes.fromhex("2a864886f70d01010d"): ("rsa", "sha512"),
}
_OID_EC_PUBLIC = bytes.fromhex("2a8648ce3d0201")  # id-ecPublicKey
_OID_RSA = bytes.fromhex("2a864886f70d010101")  # rsaEncryption
_OID_P256 = bytes.fromhex("2a8648ce3d030107")  # secp256r1
_OID_SAN = bytes.fromhex("551d11")  # subjectAltName 2.5.29.17

# NIST P-256 domain parameters
_P = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF
_A = _P - 3
_B = 0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B
_GX = 0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296
_GY = 0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5
_N = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _sha256_urn(data: bytes) -> str:
    return "urn:sha256:" + hashlib.sha256(data).hexdigest()


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _b64_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.b64decode(value + padding)


def _request(
    method: str,
    url: str,
    *,
    data: bytes | None = None,
    headers: Mapping[str, str] | None = None,
    timeout: float = 3.0,
) -> tuple[int, bytes]:
    req = urllib.request.Request(url, method=method, data=data)
    if headers:
        for key, value in headers.items():
            req.add_header(key, value)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except urllib.error.URLError as exc:
        raise SecurityControlError("SERVICE_UNAVAILABLE", str(exc.reason)) from exc
    except TimeoutError as exc:
        raise SecurityControlError("SERVICE_UNAVAILABLE", "request timed out") from exc


# --------------------------------------------------------------------------- #
# Minimal DER / X.509 parsing (stdlib only; no third-party cryptography).
# --------------------------------------------------------------------------- #


def _tlv(data: bytes, off: int) -> tuple[int, int, int, int]:
    """Return ``(tag, length, content_start, content_end)`` for the TLV at ``off``."""
    tag = data[off]
    off += 1
    length = data[off]
    off += 1
    if length & 0x80:
        count = length & 0x7F
        length = int.from_bytes(data[off : off + count], "big")
        off += count
    return tag, length, off, off + length


def _first_oid(content: bytes) -> bytes:
    _, _, oid_start, oid_end = _tlv(content, 0)
    return content[oid_start:oid_end]


def _parse_time(raw: bytes) -> int:
    text = raw.decode("ascii")
    if len(text) == 13 and text.endswith("Z"):  # UTCTime
        yy = int(text[0:2])
        year = 1900 + yy if yy >= 50 else 2000 + yy
        when = datetime(
            year, int(text[2:4]), int(text[4:6]), int(text[6:8]),
            int(text[8:10]), int(text[10:12]), tzinfo=timezone.utc,
        )
    elif len(text) == 15 and text.endswith("Z"):  # GeneralizedTime
        when = datetime(
            int(text[0:4]), int(text[4:6]), int(text[6:8]), int(text[8:10]),
            int(text[10:12]), int(text[12:14]), tzinfo=timezone.utc,
        )
    else:
        raise SecurityControlError("SVID_CHAIN_INVALID", "unparseable certificate time")
    return int(when.timestamp())


def _parse_validity(content: bytes) -> tuple[int, int]:
    _, _, nb_start, nb_end = _tlv(content, 0)
    _, _, na_start, na_end = _tlv(content, nb_end)
    return _parse_time(content[nb_start:nb_end]), _parse_time(content[na_start:na_end])


def _parse_spki(content: bytes) -> dict[str, bytes]:
    _, _, ai_start, ai_end = _tlv(content, 0)
    oid = _first_oid(content[ai_start:ai_end])
    _, _, pk_start, pk_end = _tlv(content, ai_end)
    key_der = content[pk_start + 1 : pk_end]  # strip the BIT STRING unused-bits byte
    return {"oid": oid, "key_der": key_der}


def _parse_uri_sans(extensions_content: bytes) -> list[str]:
    uris: list[str] = []
    tag, _, seq_start, seq_end = _tlv(extensions_content, 0)
    if tag != 0x30:  # extensions SEQUENCE wrapper
        return uris
    off = seq_start
    while off < seq_end:
        _, _, ext_start, ext_end = _tlv(extensions_content, off)
        ext = extensions_content[ext_start:ext_end]
        _, _, oid_start, oid_end = _tlv(ext, 0)
        oid = ext[oid_start:oid_end]
        pos = oid_end
        if pos < len(ext) and ext[pos] == 0x01:  # optional critical BOOLEAN
            _, _, _, pos = _tlv(ext, pos)
        _, _, value_start, value_end = _tlv(ext, pos)
        if oid == _OID_SAN:
            names_content = ext[value_start:value_end]
            n_tag, _, n_start, n_end = _tlv(names_content, 0)
            if n_tag == 0x30:  # GeneralNames SEQUENCE wrapper
                n_off = n_start
                while n_off < n_end:
                    g_tag = names_content[n_off]
                    _, _, g_start, g_end = _tlv(names_content, n_off)
                    if g_tag == 0x86:  # uniformResourceIdentifier [6]
                        uris.append(names_content[g_start:g_end].decode("ascii"))
                    n_off = g_end
        off = ext_end
    return uris


def _parse_certificate(der: bytes) -> dict[str, object]:
    tag, _, content_start, _ = _tlv(der, 0)
    if tag != 0x30:
        raise SecurityControlError("SVID_CHAIN_INVALID", "certificate is not a SEQUENCE")
    # tbsCertificate
    tbs_tag, _, _, tbs_end = _tlv(der, content_start)
    if tbs_tag != 0x30:
        raise SecurityControlError("SVID_CHAIN_INVALID", "tbsCertificate is not a SEQUENCE")
    tbs_der = der[content_start:tbs_end]
    # signatureAlgorithm
    _, _, sa_start, sa_end = _tlv(der, tbs_end)
    sigalg_oid = _first_oid(der[sa_start:sa_end])
    # signatureValue BIT STRING
    _, _, sig_start, sig_end = _tlv(der, sa_end)
    signature = der[sig_start + 1 : sig_end]

    # walk tbs content: version?, serial, sig, issuer, validity, subject, spki, ext?
    tbs_start = content_start + 2
    _, tbs_len, tbs_body_start, _ = _tlv(der, content_start)
    del tbs_len
    off = tbs_body_start
    if der[off] == 0xA0:  # [0] EXPLICIT version
        _, _, _, off = _tlv(der, off)
    _, _, _, off = _tlv(der, off)  # serialNumber
    _, _, _, off = _tlv(der, off)  # signature (inner)
    _, _, _, off = _tlv(der, off)  # issuer
    _, _, validity_start, validity_end = _tlv(der, off)  # validity
    not_before, not_after = _parse_validity(der[validity_start:validity_end])
    off = validity_end
    _, _, _, off = _tlv(der, off)  # subject
    _, _, spki_start, spki_end = _tlv(der, off)  # subjectPublicKeyInfo
    spki = _parse_spki(der[spki_start:spki_end])
    off = spki_end
    uri_sans: list[str] = []
    if off < tbs_end and der[off] == 0xA3:  # [3] EXPLICIT extensions
        _, _, ext_start, ext_end = _tlv(der, off)
        uri_sans = _parse_uri_sans(der[ext_start:ext_end])

    del tbs_start
    return {
        "tbs_der": tbs_der,
        "sigalg_oid": sigalg_oid,
        "signature": signature,
        "not_before": not_before,
        "not_after": not_after,
        "spki_oid": spki["oid"],
        "key_der": spki["key_der"],
        "uri_sans": uri_sans,
    }


def _parse_rsa_public_key(key_der: bytes) -> tuple[int, int]:
    tag, _, content_start, content_end = _tlv(key_der, 0)
    if tag != 0x30:
        raise SecurityControlError("SVID_CHAIN_INVALID", "RSAPublicKey is not a SEQUENCE")
    _, _, mod_start, mod_end = _tlv(key_der, content_start)
    _, _, exp_start, exp_end = _tlv(key_der, mod_end)
    modulus = int.from_bytes(key_der[mod_start:mod_end], "big")
    exponent = int.from_bytes(key_der[exp_start:exp_end], "big")
    del content_end
    return modulus, exponent


def _parse_ec_point(key_der: bytes) -> tuple[int, int]:
    if not key_der or key_der[0] != 0x04:
        raise SecurityControlError("SVID_CHAIN_INVALID", "EC point is not uncompressed")
    half = (len(key_der) - 1) // 2
    x = int.from_bytes(key_der[1 : 1 + half], "big")
    y = int.from_bytes(key_der[1 + half :], "big")
    return x, y


def _rsa_verify(message: bytes, signature: bytes, n: int, e: int, digest: str) -> bool:
    k = (n.bit_length() + 7) // 8
    if len(signature) != k:
        return False
    em = pow(int.from_bytes(signature, "big"), e, n).to_bytes(k, "big")
    digest_info = _DIGEST_INFO[digest]
    digest_value = hashlib.new(digest, message).digest()
    padding_len = k - 3 - len(digest_info) - len(digest_value)
    if padding_len < 8:
        return False
    expected = b"\x00\x01" + b"\xff" * padding_len + b"\x00" + digest_info + digest_value
    return em == expected


def _ec_point_add(
    p1: tuple[int, int] | None, p2: tuple[int, int] | None
) -> tuple[int, int] | None:
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    x1, y1 = p1
    x2, y2 = p2
    if x1 == x2 and (y1 + y2) % _P == 0:
        return None
    if p1 == p2:
        slope = (3 * x1 * x1 + _A) * pow(2 * y1, -1, _P) % _P
    else:
        slope = (y2 - y1) * pow(x2 - x1, -1, _P) % _P
    x3 = (slope * slope - x1 - x2) % _P
    y3 = (slope * (x1 - x3) - y1) % _P
    return x3, y3


def _ec_scalar_mult(k: int, point: tuple[int, int]) -> tuple[int, int] | None:
    result: tuple[int, int] | None = None
    addend: tuple[int, int] | None = point
    while k:
        if k & 1:
            result = _ec_point_add(result, addend)
        addend = _ec_point_add(addend, addend)
        k >>= 1
    return result


def _ecdsa_verify(
    message: bytes, signature_der: bytes, qx: int, qy: int, digest: str
) -> bool:
    tag, _, content_start, content_end = _tlv(signature_der, 0)
    if tag != 0x30:
        return False
    _, _, r_start, r_end = _tlv(signature_der, content_start)
    _, _, s_start, s_end = _tlv(signature_der, r_end)
    if s_end != content_end:
        return False
    r = int.from_bytes(signature_der[r_start:r_end], "big")
    s = int.from_bytes(signature_der[s_start:s_end], "big")
    if not (1 <= r < _N and 1 <= s < _N):
        return False
    digest_value = hashlib.new(digest, message).digest()
    z = int.from_bytes(digest_value, "big")
    z >>= len(digest_value) * 8 - _N.bit_length()
    w = pow(s, -1, _N)
    u1 = (z * w) % _N
    u2 = (r * w) % _N
    point = _ec_point_add(
        _ec_scalar_mult(u1, (_GX, _GY)), _ec_scalar_mult(u2, (qx, qy))
    )
    if point is None:
        return False
    return point[0] % _N == r


def _verify_certificate_signature(
    cert: Mapping[str, object], issuer: Mapping[str, object]
) -> None:
    sigalg_oid = cert["sigalg_oid"]
    if not isinstance(sigalg_oid, bytes) or sigalg_oid not in _SIGALG:
        raise SecurityControlError("SVID_CHAIN_INVALID", "unsupported signature algorithm")
    kind, digest = _SIGALG[sigalg_oid]
    tbs_der = cert["tbs_der"]
    signature = cert["signature"]
    issuer_oid = issuer["spki_oid"]
    issuer_key = issuer["key_der"]
    assert isinstance(tbs_der, bytes)
    assert isinstance(signature, bytes)
    assert isinstance(issuer_key, bytes)
    if kind == "ecdsa":
        if issuer_oid != _OID_EC_PUBLIC:
            raise SecurityControlError(
                "SVID_CHAIN_INVALID", "ECDSA signature but non-EC issuer key"
            )
        qx, qy = _parse_ec_point(issuer_key)
        if not _ecdsa_verify(tbs_der, signature, qx, qy, digest):
            raise SecurityControlError("SVID_CHAIN_INVALID", "ECDSA signature check failed")
    else:
        if issuer_oid != _OID_RSA:
            raise SecurityControlError(
                "SVID_CHAIN_INVALID", "RSA signature but non-RSA issuer key"
            )
        modulus, exponent = _parse_rsa_public_key(issuer_key)
        if not _rsa_verify(tbs_der, signature, modulus, exponent, digest):
            raise SecurityControlError("SVID_CHAIN_INVALID", "RSA signature check failed")


def _split_der_chain(blob: bytes) -> list[bytes]:
    certs: list[bytes] = []
    off = 0
    while off < len(blob):
        _, _, _, end = _tlv(blob, off)
        certs.append(blob[off:end])
        off = end
    return certs


# --------------------------------------------------------------------------- #
# Providers
# --------------------------------------------------------------------------- #


class KeycloakIdentityProvider:
    """Authenticates a principal and its delegation chain against real Keycloak."""

    def __init__(
        self,
        base_url: str,
        realm: str,
        client_id: str,
        *,
        password_resolver: Callable[[str], str],
        timeout_seconds: float = 5.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._realm = realm
        self._client_id = client_id
        self._password_resolver = password_resolver
        self._timeout = timeout_seconds

    def _oidc_configuration(self) -> dict[str, object]:
        url = f"{self._base_url}/realms/{self._realm}/.well-known/openid-configuration"
        status, body = _request("GET", url, timeout=self._timeout)
        if status != 200:
            raise SecurityControlError("IDENTITY_UNAVAILABLE", f"OIDC discovery HTTP {status}")
        return cast(dict[str, object], json.loads(body.decode()))

    def _jwks(self, jwks_uri: str) -> dict[str, tuple[int, int]]:
        status, body = _request("GET", jwks_uri, timeout=self._timeout)
        if status != 200:
            raise SecurityControlError("IDENTITY_UNAVAILABLE", f"JWKS HTTP {status}")
        keys = json.loads(body.decode()).get("keys", [])
        result: dict[str, tuple[int, int]] = {}
        for key in keys:
            if key.get("kty") != "RSA":
                continue
            n = int.from_bytes(_b64url_decode(str(key["n"])), "big")
            e = int.from_bytes(_b64url_decode(str(key["e"])), "big")
            result[str(key["kid"])] = (n, e)
        return result

    def _password_grant(self, token_endpoint: str, username: str, password: str) -> str:
        form = urllib.parse.urlencode(
            {
                "client_id": self._client_id,
                "username": username,
                "password": password,
                "grant_type": "password",
            }
        ).encode()
        status, body = _request(
            "POST",
            token_endpoint,
            data=form,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=self._timeout,
        )
        if status != 200:
            raise SecurityControlError("IDENTITY_REJECTED", f"token grant HTTP {status}")
        return cast(str, json.loads(body.decode())["access_token"])

    def _verify_access_token(
        self,
        token: str,
        jwks: dict[str, tuple[int, int]],
        issuer: str,
        audience: str,
    ) -> dict[str, object]:
        try:
            header_b64, payload_b64, signature_b64 = token.split(".")
        except ValueError as exc:
            raise SecurityControlError("IDENTITY_REJECTED", "malformed JWT") from exc
        header = json.loads(_b64url_decode(header_b64))
        payload = json.loads(_b64url_decode(payload_b64))
        signature = _b64url_decode(signature_b64)
        if header.get("alg") != "RS256":
            raise SecurityControlError("IDENTITY_REJECTED", "unsupported JWT algorithm")
        key = jwks.get(str(header.get("kid")))
        if key is None:
            raise SecurityControlError("IDENTITY_REJECTED", "unknown signing key")
        signing_input = f"{header_b64}.{payload_b64}".encode()
        if not _rsa_verify(signing_input, signature, key[0], key[1], "sha256"):
            raise SecurityControlError("IDENTITY_REJECTED", "JWT signature check failed")
        if payload.get("iss") != issuer:
            raise SecurityControlError("IDENTITY_REJECTED", "issuer mismatch")
        audience_list = payload.get("aud", [])
        if isinstance(audience_list, str):
            audience_list = [audience_list]
        if audience not in audience_list:
            raise SecurityControlError("IDENTITY_REJECTED", "audience mismatch")
        now = int(_now().timestamp())
        if int(payload["exp"]) <= now:
            raise SecurityControlError("IDENTITY_REJECTED", "access token is expired")
        return cast(dict[str, object], payload)

    def authenticate(self, request: IdentityRequest) -> AuthenticatedPrincipal:
        prefix = "urn:ocor:credential-ref:"
        if not request.credential_ref.startswith(prefix):
            raise SecurityControlError("IDENTITY_REJECTED", "unknown credential reference")
        username = request.credential_ref[len(prefix) :]
        if not username:
            raise SecurityControlError("IDENTITY_REJECTED", "empty credential reference")
        password = self._password_resolver(username)

        configuration = self._oidc_configuration()
        issuer = str(configuration["issuer"])
        token_endpoint = str(configuration["token_endpoint"])
        jwks_uri = str(configuration["jwks_uri"])
        jwks = self._jwks(jwks_uri)
        token = self._password_grant(token_endpoint, username, password)
        claims = self._verify_access_token(
            token, jwks, issuer, request.expected_audience
        )

        subject = str(claims["sub"])
        principal_id = str(claims.get("preferred_username", subject))
        actor_chain = [principal_id]
        authorized_party = claims.get("azp")
        if isinstance(authorized_party, str) and authorized_party not in actor_chain:
            actor_chain.append(authorized_party)
        actor = claims.get("act")
        if isinstance(actor, dict) and isinstance(actor.get("sub"), str):
            if actor["sub"] not in actor_chain:
                actor_chain.insert(0, str(actor["sub"]))
        session_id = str(
            claims.get("session_state")
            or claims.get("sid")
            or claims.get("jti")
            or ""
        )
        if not session_id:
            raise SecurityControlError("IDENTITY_REJECTED", "missing session identifier")
        authenticated_at = datetime.fromtimestamp(
            cast(int, claims["iat"]), tz=timezone.utc
        )
        expires_at = datetime.fromtimestamp(
            cast(int, claims["exp"]), tz=timezone.utc
        )

        jwks_material = b"".join(
            f"{kid}:{key[0]}:{key[1]}".encode() for kid, key in sorted(jwks.items())
        )
        status = ControlStatus.available(
            ControlName.IDENTITY,
            observed_at=_now(),
            source_digest=_sha256_urn(jwks_material),
        )
        return AuthenticatedPrincipal(
            principal_id=principal_id,
            actor_chain=tuple(actor_chain),
            session_id=session_id,
            assurance_level="LEVEL_2",
            authenticated_at=authenticated_at,
            expires_at=expires_at,
            status=status,
        )


class OpaPolicyDecisionProvider:
    """Installs a signed policy bundle and evaluates it with real OPA."""

    _ALLOW_PATH = "/v1/data/ocor/control_plane/allow"

    def __init__(self, base_url: str, policy_id: str, *, timeout_seconds: float = 5.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._policy_id = policy_id
        self._timeout = timeout_seconds
        self._bundle_digest: str | None = None

    def install_policy(self, rego_source: str) -> str:
        digest = _sha256_urn(rego_source.encode())
        status, _ = _request(
            "PUT",
            f"{self._base_url}/v1/policies/{self._policy_id}",
            data=rego_source.encode(),
            headers={"Content-Type": "text/plain"},
            timeout=self._timeout,
        )
        if status != 200:
            raise SecurityControlError("POLICY_UNAVAILABLE", f"policy install HTTP {status}")
        current = self._fetch_policy_source()
        if current != rego_source:
            raise SecurityControlError("POLICY_UNAVAILABLE", "installed policy did not persist")
        self._bundle_digest = digest
        return digest

    def _fetch_policy_source(self) -> str:
        status, body = _request(
            "GET", f"{self._base_url}/v1/policies/{self._policy_id}", timeout=self._timeout
        )
        if status != 200:
            raise SecurityControlError("POLICY_UNAVAILABLE", f"policy fetch HTTP {status}")
        try:
            raw = json.loads(body.decode()).get("result", {}).get("raw", "")
        except (ValueError, json.JSONDecodeError):
            raw = body.decode()
        if not isinstance(raw, str):
            raise SecurityControlError("POLICY_UNAVAILABLE", "policy source is not textual")
        return raw

    def _require_fresh_bundle(self, correlation_id: str) -> None:
        current = _sha256_urn(self._fetch_policy_source().encode())
        if current != self._bundle_digest:
            raise SecurityControlError(
                "STALE_BUNDLE",
                f"correlation_id={correlation_id} live policy digest drifted",
            )

    def evaluate(self, request: PolicyRequest) -> PolicyDecision:
        self._require_fresh_bundle(request.governed_context.correlation_id)
        policy_input = {
            "principal_id": request.principal.principal_id,
            "action": request.action,
            "resource": request.resource,
            "purpose": request.governed_context.purpose,
        }
        status, body = _request(
            "POST",
            f"{self._base_url}{self._ALLOW_PATH}",
            data=json.dumps({"input": policy_input}).encode(),
            headers={"Content-Type": "application/json"},
            timeout=self._timeout,
        )
        if status != 200:
            raise SecurityControlError("POLICY_UNAVAILABLE", f"policy eval HTTP {status}")
        try:
            allowed = bool(json.loads(body.decode()).get("result", False))
        except (ValueError, json.JSONDecodeError) as exc:
            raise SecurityControlError("POLICY_UNAVAILABLE", "malformed policy response") from exc
        effect = PolicyEffect.PERMIT if allowed else PolicyEffect.DENY
        valid_until = _now() + timedelta(seconds=300)
        status_record = ControlStatus.available(
            ControlName.POLICY,
            observed_at=request.at,
            source_digest=request.governed_context.policy_bundle_digest,
        )
        decision_id = _sha256_urn(
            f"{request.principal.principal_id}:{request.action}:"
            f"{request.resource}:{request.at.isoformat()}".encode()
        )
        return PolicyDecision.from_request(
            request,
            effect=effect,
            decision_id=decision_id,
            valid_until=valid_until,
            obligations=(),
            status=status_record,
        )


class SpireWorkloadIdentityProvider:
    """Fetches and cryptographically verifies the control-plane SVID from SPIRE."""

    def __init__(
        self,
        *,
        agent_container: str,
        socket_path: str,
        expected_spiffe_id: str,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._agent_container = agent_container
        self._socket_path = socket_path
        self._expected_spiffe_id = expected_spiffe_id
        self._timeout = timeout_seconds

    def _fetch_svid(self) -> dict[str, object]:
        command = [
            "docker",
            "exec",
            self._agent_container,
            "/opt/spire/bin/spire-agent",
            "api",
            "fetch",
            "x509",
            "-socketPath",
            self._socket_path,
            "-output",
            "json",
        ]
        try:
            completed = subprocess.run(
                command, capture_output=True, timeout=self._timeout, check=False
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise SecurityControlError("WORKLOAD_IDENTITY_UNAVAILABLE", str(exc)) from exc
        if completed.returncode != 0:
            raise SecurityControlError(
                "WORKLOAD_IDENTITY_UNAVAILABLE", "spire-agent api fetch failed"
            )
        data = json.loads(completed.stdout.decode())
        svids = data.get("svids")
        if not isinstance(svids, list) or not svids:
            raise SecurityControlError("WORKLOAD_IDENTITY_UNAVAILABLE", "no SVID returned")
        return cast(dict[str, object], svids[0])

    def current(self) -> WorkloadIdentity:
        svid = self._fetch_svid()
        spiffe_id = str(svid.get("spiffe_id", ""))
        if spiffe_id != self._expected_spiffe_id:
            raise SecurityControlError(
                "WORKLOAD_IDENTITY_UNAVAILABLE",
                f"unexpected SPIFFE ID {spiffe_id!r}",
            )
        try:
            chain = _split_der_chain(_b64_decode(str(svid["x509_svid"])))
            bundle = _b64_decode(str(svid["bundle"]))
        except (KeyError, ValueError) as exc:
            raise SecurityControlError("WORKLOAD_IDENTITY_UNAVAILABLE", "malformed SVID") from exc
        if len(chain) < 2:
            raise SecurityControlError("WORKLOAD_IDENTITY_UNAVAILABLE", "incomplete SVID chain")
        leaf_der, intermediate_der = chain[0], chain[1]
        root_der = bundle

        leaf = _parse_certificate(leaf_der)
        intermediate = _parse_certificate(intermediate_der)
        root = _parse_certificate(root_der)
        _verify_certificate_signature(leaf, intermediate)
        _verify_certificate_signature(intermediate, root)

        uri_sans = leaf["uri_sans"]
        assert isinstance(uri_sans, list)
        if spiffe_id not in uri_sans:
            raise SecurityControlError(
                "WORKLOAD_IDENTITY_UNAVAILABLE", "SVID SAN does not carry the SPIFFE ID"
            )
        not_before = datetime.fromtimestamp(
            cast(int, leaf["not_before"]), tz=timezone.utc
        )
        expires_at = datetime.fromtimestamp(
            cast(int, leaf["not_after"]), tz=timezone.utc
        )
        trust_bundle_digest = _sha256_urn(root_der)
        svid_ref = _sha256_urn(leaf_der)
        status = ControlStatus.available(
            ControlName.WORKLOAD_IDENTITY,
            observed_at=_now(),
            source_digest=trust_bundle_digest,
        )
        return WorkloadIdentity(
            spiffe_id=spiffe_id,
            svid_ref=svid_ref,
            trust_bundle_digest=trust_bundle_digest,
            attested=True,
            not_before=not_before,
            expires_at=expires_at,
            status=status,
        )


class OpenBaoSecretProvider:
    """Leases principal-scoped secrets from a real OpenBao kv-v2 engine."""

    def __init__(
        self,
        base_url: str,
        token: str,
        mount: str = "ocor",
        *,
        timeout_seconds: float = 5.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._mount = mount
        self._timeout = timeout_seconds
        self._mount_digest: str | None = None

    def _headers(self) -> dict[str, str]:
        return {"X-Vault-Token": self._token}

    def _ensure_mount(self) -> str:
        status, body = _request(
            "GET", f"{self._base_url}/v1/sys/mounts", headers=self._headers(), timeout=self._timeout
        )
        if status != 200:
            raise SecurityControlError("SECRETS_UNAVAILABLE", f"mount list HTTP {status}")
        mounts = json.loads(body.decode()).get("data", {})
        mount_key = f"{self._mount}/"
        accessor = mounts.get(mount_key, {}).get("accessor") if isinstance(mounts, dict) else None
        if accessor is None:
            status, body = _request(
                "POST",
                f"{self._base_url}/v1/sys/mounts/{self._mount}",
                data=json.dumps({"type": "kv", "options": {"version": "2"}}).encode(),
                headers={**self._headers(), "Content-Type": "application/json"},
                timeout=self._timeout,
            )
            if status not in (200, 204):
                raise SecurityControlError("SECRETS_UNAVAILABLE", f"mount enable HTTP {status}")
            status, body = _request(
                "GET", f"{self._base_url}/v1/sys/mounts", headers=self._headers(), timeout=self._timeout
            )
            mounts = json.loads(body.decode()).get("data", {})
            accessor = mounts.get(mount_key, {}).get("accessor") if isinstance(mounts, dict) else None
        if accessor is None:
            raise SecurityControlError("SECRETS_UNAVAILABLE", "mount accessor not found")
        self._mount_digest = _sha256_urn(str(accessor).encode())
        return self._mount_digest

    def lease(self, request: SecretRequest) -> SecretLease:
        mount_digest = self._mount_digest or self._ensure_mount()
        secret_name = request.secret_ref[len("urn:ocor:secret-ref:") :]
        if not secret_name:
            raise SecurityControlError("SECRET_REFERENCE_INVALID", "empty secret reference")
        path = f"{self._mount}/data/{request.principal_id}/{secret_name}"
        material = hashlib.sha256(
            f"{request.principal_id}:{secret_name}:{request.purpose}:{_now().isoformat()}".encode()
        ).hexdigest()
        write_body = json.dumps(
            {
                "data": {
                    "purpose": request.purpose,
                    "correlation_id": request.governed_context_digest,
                    "material": material,
                }
            }
        ).encode()
        status, body = _request(
            "POST",
            f"{self._base_url}/v1/{path}",
            data=write_body,
            headers={**self._headers(), "Content-Type": "application/json"},
            timeout=self._timeout,
        )
        if status not in (200, 204):
            raise SecurityControlError("SECRETS_UNAVAILABLE", f"secret write HTTP {status}")
        version = "1"
        if body:
            version = str(json.loads(body.decode()).get("data", {}).get("version", "1"))
        handle = _sha256_urn(
            f"{request.principal_id}:{secret_name}:{request.purpose}:{version}".encode()
        )
        handle_ref = "urn:ocor:secret-handle:" + handle[len("urn:sha256:") :]
        expires_at = request.requested_at + timedelta(seconds=300)
        status_record = ControlStatus.available(
            ControlName.SECRETS,
            observed_at=_now(),
            source_digest=mount_digest,
        )
        return SecretLease.from_request(
            request,
            handle_ref=handle_ref,
            version=version,
            expires_at=expires_at,
            status=status_record,
        )
