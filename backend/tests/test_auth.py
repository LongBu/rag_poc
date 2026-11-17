import base64
import io
import json
import time
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.error import URLError

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from bedrock_chat import auth as auth_module
from bedrock_chat.app import create_app
from bedrock_chat.auth import OwnerAuth

TENANT = "00000000-0000-0000-0000-000000000001"
API = "00000000-0000-0000-0000-000000000002"
SPA = "00000000-0000-0000-0000-000000000003"
OWNER = "00000000-0000-0000-0000-000000000004"
OTHER = "00000000-0000-0000-0000-000000000009"
ISSUER = f"https://login.microsoftonline.com/{TENANT}/v2.0"
DISCOVERY = f"{ISSUER}/.well-known/openid-configuration"
JWKS = f"https://login.microsoftonline.com/{TENANT}/discovery/v2.0/keys"
SETTINGS = {"AZURE_TENANT_ID": TENANT, "ENTRA_API_CLIENT_ID": API,
            "ENTRA_SPA_CLIENT_ID": SPA, "ENTRA_OWNER_OBJECT_ID": OWNER}


def jwk(key, kid="first", **extra):
    return {**jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key(), as_dict=True),
            "kid": kid, "use": "sig", "alg": "RS256", "issuer": ISSUER, **extra}


def key_response(keys):
    return io.BytesIO(json.dumps({"keys": keys}).encode())


def signed(key, claims, kid="first"):
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": kid})


@pytest.fixture(scope="module")
def signing_keys():
    return [rsa.generate_private_key(public_exponent=65537, key_size=2048) for _ in range(2)]


@pytest.fixture
def setup_auth(monkeypatch, signing_keys):
    first, second = signing_keys
    metadata = {"issuer": ISSUER, "jwks_uri": JWKS}
    discovery = Mock(return_value=httpx.Response(200, json=metadata, request=httpx.Request("GET", DISCOVERY)))
    monkeypatch.setattr(auth_module.httpx, "get", discovery)
    fetch = Mock(side_effect=lambda *args, **kwargs: key_response([jwk(first)]))
    monkeypatch.setattr(jwt.jwks_client.urllib.request, "build_opener", Mock(return_value=SimpleNamespace(open=fetch)))
    auth = OwnerAuth(TENANT, API, SPA, OWNER)
    model = Mock(return_value={"text": "answer", "usage": {"input_tokens": 2, "output_tokens": 1}})
    client = create_app(auth=auth, model_service=model, settings={}).test_client()
    now = int(time.time())
    claims = {"iss": ISSUER, "aud": API, "sub": "display-subject", "tid": TENANT,
              "oid": OWNER, "azp": SPA, "ver": "2.0", "scp": "openid query",
              "exp": now + 300, "iat": now - 1, "nbf": now - 1}
    return SimpleNamespace(auth=auth, model=model, client=client, claims=claims,
                           first=first, second=second, discovery=discovery, fetch=fetch)


def reject(s, token, caplog):
    response = s.client.post("/query", json={"prompt": "secret prompt"},
                             headers={"Authorization": "Bearer " + token,
                                      "X-MS-CLIENT-PRINCIPAL-ID": OWNER,
                                      "X-Amzn-Oidc-Identity": OWNER})
    assert response.status_code == 401
    s.model.assert_not_called()
    assert "secret" not in response.get_data(as_text=True) and "secret" not in caplog.text
    assert token not in response.get_data(as_text=True) and token not in caplog.text


@pytest.mark.parametrize("scheme", ["Bearer", "bearer", "BEARER"])
def test_owner_without_email_and_default_wiring(setup_auth, scheme):
    s = setup_auth
    claims = {**s.claims, "sub": "another-display-subject", "roles": ["optional-role"], "idtyp": "user"}
    s.client = create_app(model_service=s.model, settings=SETTINGS).test_client()
    response = s.client.post("/query", json={"prompt": "ok"}, headers={"Authorization": scheme + " " + signed(s.first, claims)})
    assert response.status_code == 200
    s.model.assert_called_once_with("ok", [])
    s.discovery.assert_called_once_with(DISCOVERY, timeout=2, follow_redirects=False)
    assert s.fetch.call_count == 1
    assert s.fetch.call_args.kwargs["timeout"] == 2
    assert s.fetch.call_args.args[0].full_url == JWKS


@pytest.mark.parametrize("field,value", [
    ("iss", "https://evil.example"), ("iss", f"https://sts.windows.net/{TENANT}/"),
    ("iss", "https://login.microsoftonline.com/common/v2.0"),
    ("aud", SPA), ("aud", OTHER), ("aud", "api://" + API), ("aud", [API]),
    ("aud", None), ("aud", True),
    ("tid", OTHER), ("tid", [TENANT]), ("oid", OTHER), ("oid", [OWNER]),
    ("azp", OTHER), ("azp", API), ("azp", [SPA]),
    ("ver", "1.0"), ("ver", 2.0),
    ("scp", "openid"), ("scp", "notquery"), ("scp", "Query"),
    ("scp", f"api://{API}/query"), ("scp", ["query"]), ("scp", {}),
    ("idtyp", "app"), ("idtyp", ["user"]), ("idtyp", "unknown"), ("exp", 1), ("exp", "invalid"),
    ("exp", str(int(time.time()) + 600)), ("nbf", int(time.time()) + 600),
    ("nbf", False), ("iat", int(time.time()) + 600), ("iat", False),
])
def test_rejected_claim_never_calls_model(setup_auth, field, value, caplog):
    s = setup_auth
    reject(s, signed(s.first, {**s.claims, field: value}), caplog)


@pytest.mark.parametrize("field", ["iss", "aud", "exp", "iat", "nbf", "ver", "tid", "scp", "azp", "oid"])
def test_missing_claim_never_calls_model(setup_auth, field, caplog):
    s = setup_auth
    claims = {k: v for k, v in s.claims.items() if k != field}
    reject(s, signed(s.first, claims), caplog)


def test_id_token_and_app_only_token(setup_auth, caplog):
    s = setup_auth
    id_token = {k: v for k, v in s.claims.items() if k != "scp"}
    reject(s, signed(s.first, {**id_token, "aud": SPA, "nonce": "nonce"}), caplog)
    reject(s, signed(s.first, {**id_token, "idtyp": "app", "roles": ["query"]}), caplog)


@pytest.mark.parametrize("kind", ["signature", "algorithm", "none", "truncated"])
def test_signature_algorithm_and_malformed_token(setup_auth, kind, caplog):
    s = setup_auth
    token = signed(s.second, s.claims)
    if kind == "algorithm":
        token = jwt.encode(s.claims, "x" * 64, algorithm="HS256", headers={"kid": "first"})
    elif kind == "none":
        token = jwt.encode(s.claims, None, algorithm="none", headers={"kid": "first"})
    elif kind == "truncated":
        token = "not.a.valid.token"
    reject(s, token, caplog)


@pytest.mark.parametrize("header", ["", "Basic secret", "Bearer", "Bearer ", "Bearer  secret", "Bearer secret "])
def test_invalid_header_and_forged_identity(setup_auth, header, caplog):
    s = setup_auth
    response = s.client.post("/query", json={"prompt": "secret"}, headers={
        "Authorization": header, "X-MS-CLIENT-PRINCIPAL-ID": OWNER,
        "X-MS-CLIENT-PRINCIPAL": base64.b64encode(json.dumps(s.claims).encode()).decode(),
        "X-MS-TOKEN-AAD-ACCESS-TOKEN": signed(s.first, s.claims), "X-Amzn-Oidc-Identity": OWNER})
    assert response.status_code == 401
    s.model.assert_not_called()
    s.discovery.assert_not_called()
    assert "secret" not in caplog.text


@pytest.mark.parametrize("header", [{"alg": "RS256"}, {"alg": "RS256", "kid": 1},
                                    {"alg": "RS256", "kid": ""}, {"alg": "RS256", "kid": "first", "crit": ["custom"]}])
def test_bad_signing_header_rejected_before_discovery(setup_auth, header, caplog):
    s = setup_auth
    parts = signed(s.first, s.claims).split(".")
    parts[0] = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    reject(s, ".".join(parts), caplog)
    s.discovery.assert_not_called()


@pytest.mark.parametrize("field", list(SETTINGS))
@pytest.mark.parametrize("value", ["", "invalid", None, 1])
def test_missing_or_malformed_configuration(setup_auth, field, value, caplog):
    s = setup_auth
    s.client = create_app(model_service=s.model, settings={**SETTINGS, field: value}).test_client()
    reject(s, signed(s.first, s.claims), caplog)
    s.discovery.assert_not_called()


def test_same_spa_api_and_legacy_configuration_fail_closed(setup_auth, caplog):
    s = setup_auth
    for config in [{**SETTINGS, "ENTRA_API_CLIENT_ID": SPA},
                   {"ISSUER": ISSUER, "CLIENT_ID": SPA, "OWNER_SUB": OWNER}]:
        s.client = create_app(model_service=s.model, settings=config).test_client()
        reject(s, signed(s.first, s.claims), caplog)
    s.discovery.assert_not_called()
    assert OwnerAuth(TENANT.upper(), API.upper(), SPA.upper(), OWNER.upper()).configured
    assert auth_module._identifier("ABCDEFAB-CDEF-ABCD-EFAB-CDEFABCDEFAB") == "abcdefab-cdef-abcd-efab-cdefabcdefab"


@pytest.mark.parametrize("metadata", [None, [], {}, {"issuer": "https://evil.example", "jwks_uri": JWKS},
    {"issuer": ISSUER}, {"issuer": ISSUER, "jwks_uri": None},
    *[{"issuer": ISSUER, "jwks_uri": uri} for uri in [
        "http://login.microsoftonline.com/common/discovery/v2.0/keys",
        "https://evil.example/keys", "https://login.microsoftonline.com.evil.example/keys",
        f"https://login.microsoftonline.com/{OTHER}/discovery/v2.0/keys",
        JWKS + "?appid=other", JWKS + "#fragment", "file:///private/secret"]],
])
def test_untrusted_or_malformed_discovery(setup_auth, metadata, caplog):
    s = setup_auth
    s.discovery.return_value = httpx.Response(200, json=metadata, request=httpx.Request("GET", DISCOVERY))
    reject(s, signed(s.first, s.claims), caplog)
    s.fetch.assert_not_called()


@pytest.mark.parametrize("failure", ["timeout", "http", "redirect", "json"])
def test_discovery_failure(setup_auth, failure, caplog):
    s = setup_auth
    if failure == "timeout":
        s.discovery.side_effect = httpx.ConnectTimeout("secret")
    else:
        s.discovery.return_value = httpx.Response(
            {"http": 503, "redirect": 302, "json": 200}[failure], content=b"secret",
            headers={"Location": "https://evil.example"}, request=httpx.Request("GET", DISCOVERY))
    reject(s, signed(s.first, s.claims), caplog)
    s.fetch.assert_not_called()


@pytest.mark.parametrize("issuer", [ISSUER, "https://login.microsoftonline.com/{tenantid}/v2.0"])
def test_key_issuer_and_common_discovered_endpoint(setup_auth, issuer):
    s = setup_auth
    uri = "https://login.microsoftonline.com/common/discovery/v2.0/keys"
    s.discovery.return_value = httpx.Response(200, json={"issuer": ISSUER, "jwks_uri": uri}, request=httpx.Request("GET", DISCOVERY))
    s.fetch.side_effect = lambda *a, **k: key_response([jwk(s.first, issuer=issuer)])
    s.auth("Bearer " + signed(s.first, s.claims))
    assert s.fetch.call_args.args[0].full_url == uri


@pytest.mark.parametrize("issuer", [None, "", "https://evil.example", f"https://login.microsoftonline.com/{OTHER}/v2.0", {}])
def test_disallowed_signing_key_issuer(setup_auth, issuer, caplog):
    s = setup_auth
    s.fetch.side_effect = lambda *a, **k: key_response([jwk(s.first, issuer=issuer)])
    reject(s, signed(s.first, s.claims), caplog)


def test_key_algorithm_and_attacker_header_urls(setup_auth, caplog):
    s = setup_auth
    s.fetch.side_effect = lambda *a, **k: key_response([jwk(s.first, alg="RS512")])
    reject(s, signed(s.first, s.claims), caplog)
    s.auth.keys = None
    s.fetch.side_effect = lambda *a, **k: key_response([jwk(s.first)])
    token = jwt.encode(s.claims, s.first, algorithm="RS256", headers={"kid": "first", "jku": "https://evil.example", "x5u": "https://evil.example"})
    s.auth("Bearer " + token)
    assert s.fetch.call_args.args[0].full_url == JWKS


@pytest.mark.parametrize("failure", ["timeout", "unavailable", "json", "shape", "empty", "malformed_key"])
def test_jwks_failure(setup_auth, failure, caplog):
    s = setup_auth
    data = {"json": b"secret", "shape": b"[]", "empty": b'{"keys":[]}',
            "malformed_key": b'{"keys":[{"kid":"first","kty":"RSA"}]}'}
    if failure in ["timeout", "unavailable"]:
        s.fetch.side_effect = TimeoutError("secret") if failure == "timeout" else URLError("secret")
    else:
        s.fetch.side_effect = lambda *a, **k: io.BytesIO(data[failure])
    reject(s, signed(s.first, s.claims), caplog)


def test_discovery_cache_expiry_failure_and_recovery(setup_auth, monkeypatch, caplog):
    s = setup_auth
    clock = Mock(return_value=0)
    monkeypatch.setattr(auth_module, "monotonic", clock)
    token = signed(s.first, s.claims)
    s.auth("Bearer " + token)
    s.auth("Bearer " + token)
    assert s.discovery.call_count == s.fetch.call_count == 1
    clock.return_value = 301
    s.discovery.side_effect = httpx.ReadTimeout("secret")
    reject(s, token, caplog)
    assert s.discovery.call_count == 2 and s.fetch.call_count == 1
    s.discovery.side_effect = None
    s.auth("Bearer " + token)
    assert s.discovery.call_count == 3 and s.fetch.call_count == 2


def test_jwks_cache_rotation_cooldown_and_failed_refresh(setup_auth, monkeypatch, caplog):
    s = setup_auth
    clock = Mock(return_value=0)
    monkeypatch.setattr(jwt.jwks_client.time, "monotonic", clock)
    s.fetch.side_effect = [key_response([jwk(s.first)]),
                           key_response([jwk(s.second, "second")]), URLError("secret"), URLError("secret")]
    first = signed(s.first, s.claims)
    second = signed(s.second, s.claims, "second")
    s.auth("Bearer " + first)
    s.auth("Bearer " + first)
    assert s.fetch.call_count == 1
    reject(s, second, caplog)
    assert s.fetch.call_count == 1
    clock.return_value = 31
    s.auth("Bearer " + second)
    assert s.fetch.call_count == 2
    clock.return_value = 62
    reject(s, signed(s.first, s.claims, "unknown"), caplog)
    assert s.fetch.call_count == 3
    s.auth("Bearer " + second)
    assert s.fetch.call_count == 3
    clock.return_value = 363
    reject(s, second, caplog)
