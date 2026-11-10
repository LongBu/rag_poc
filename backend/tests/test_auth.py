import time
from types import SimpleNamespace
from unittest.mock import Mock

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from bedrock_chat.auth import OwnerAuth


@pytest.fixture
def setup_auth():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    auth = OwnerAuth("https://issuer.example", "client", "owner")
    auth.keys = Mock()
    auth.keys.get_signing_key_from_jwt.return_value = SimpleNamespace(key=key.public_key())
    claims = {"iss": "https://issuer.example", "sub": "owner", "client_id": "client",
              "exp": int(time.time())+300, "iat": int(time.time()),
              "token_use": "access", "scope": "openid chat/query"}
    return auth, key, claims


def test_valid_owner(setup_auth):
    auth, key, claims = setup_auth
    auth("Bearer " + jwt.encode(claims, key, algorithm="RS256"))
    auth.keys.get_signing_key_from_jwt.assert_called_once()


@pytest.mark.parametrize(("field", "value"), [
    ("iss", "wrong"), ("sub", "other"), ("client_id", "other"),
    ("exp", 1), ("iat", 9999999999), ("token_use", "id"),
    ("scope", "openid"), ("scope", ["chat/query"]),
])
def test_rejected_claim(setup_auth, field, value):
    auth, key, claims = setup_auth
    claims[field] = value
    with pytest.raises(jwt.InvalidTokenError):
        auth("Bearer " + jwt.encode(claims, key, algorithm="RS256"))


@pytest.mark.parametrize("field", ["iss", "sub", "client_id", "exp", "iat", "token_use", "scope"])
def test_required_claim(setup_auth, field):
    auth, key, claims = setup_auth
    del claims[field]
    with pytest.raises(jwt.InvalidTokenError):
        auth("Bearer " + jwt.encode(claims, key, algorithm="RS256"))


def test_wrong_signature_and_algorithm(setup_auth):
    auth, _, claims = setup_auth
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(jwt.InvalidSignatureError):
        auth("Bearer " + jwt.encode(claims, other, algorithm="RS256"))
    with pytest.raises(jwt.InvalidAlgorithmError):
        auth("Bearer " + jwt.encode(claims, "x"*64, algorithm="HS256"))


@pytest.mark.parametrize("header", ["", "Bearer ", "Basic token"])
def test_invalid_header(setup_auth, header):
    auth, _, _ = setup_auth
    with pytest.raises(jwt.InvalidTokenError):
        auth(header)
    auth.keys.get_signing_key_from_jwt.assert_not_called()


@pytest.mark.parametrize("field", ["issuer", "client_id", "owner_sub"])
def test_missing_config(setup_auth, field):
    auth, _, _ = setup_auth
    setattr(auth, field, "")
    with pytest.raises(jwt.InvalidTokenError):
        auth("Bearer token")
    auth.keys.get_signing_key_from_jwt.assert_not_called()


def test_jwks_failure(setup_auth):
    auth, _, _ = setup_auth
    auth.keys.get_signing_key_from_jwt.side_effect = jwt.PyJWKClientError("unavailable")
    with pytest.raises(jwt.PyJWKClientError):
        auth("Bearer token")


def test_jwks_cache_rotation_and_refresh_failure(setup_auth):
    _, first, claims = setup_auth
    second = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    auth = OwnerAuth("https://issuer.example", "client", "owner")
    def jwk(key, kid):
        return {**jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key(), as_dict=True),
                "kid": kid, "use": "sig"}
    auth.keys.fetch_data = Mock(side_effect=[
        {"keys": [jwk(first, "first")]}, {"keys": [jwk(second, "second")]},
        jwt.PyJWKClientError("refresh unavailable"),
    ])
    token = jwt.encode(claims, first, algorithm="RS256", headers={"kid": "first"})
    auth("Bearer " + token)
    auth("Bearer " + token)
    assert auth.keys.fetch_data.call_count == 1
    auth("Bearer " + jwt.encode(claims, second, algorithm="RS256", headers={"kid": "second"}))
    assert auth.keys.fetch_data.call_count == 2
    with pytest.raises(jwt.PyJWKClientError):
        auth("Bearer " + jwt.encode(claims, first, algorithm="RS256", headers={"kid": "unknown"}))
