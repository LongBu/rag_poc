import json
from unittest.mock import Mock

import jwt
import pytest
from botocore.exceptions import (
    BotoCoreError, ClientError, ConnectTimeoutError, NoCredentialsError,
    PartialCredentialsError, ReadTimeoutError,
)

from bedrock_chat.app import create_app, validate


@pytest.fixture
def services():
    auth = Mock()
    model = Mock(return_value={"text": "answer", "usage": {"input_tokens": 2, "output_tokens": 1}})
    client = create_app(auth, model, {"FRONTEND_ORIGIN": "https://chat.example"}).test_client()
    return client, auth, model


def test_query_and_cors(services):
    client, auth, model = services
    pair = {"user": "earlier", "assistant": "previous answer"}
    response = client.post("/query", json={"prompt": "next", "history": [pair]},
                           headers={"Authorization": "Bearer abc", "Origin": "https://chat.example"})
    assert response.status_code == 200
    assert response.json == model.return_value
    auth.assert_called_once_with("Bearer abc")
    model.assert_called_once_with("next", [pair])
    assert response.headers["Access-Control-Allow-Origin"] == "https://chat.example"
    assert response.headers["Vary"] == "Origin"


def test_ready_preflight_and_other_origin(services):
    client, auth, model = services
    assert client.get("/ready").data == b"ready"
    assert client.options("/query").status_code == 204
    assert "Access-Control-Allow-Origin" not in client.options(
        "/query", headers={"Origin": "https://other.example"}).headers
    auth.assert_not_called()
    model.assert_not_called()
    assert create_app(settings={}).test_client().get("/ready").status_code == 200
    assert create_app(settings={}).test_client().post("/query", json={"prompt": "ok"}).status_code == 401
    assert create_app(auth=auth).test_client().get("/ready").status_code == 200


@pytest.mark.parametrize("error", [jwt.InvalidTokenError(), jwt.PyJWKClientError("secret")])
def test_unauthorized(services, error):
    client, auth, model = services
    auth.side_effect = error
    response = client.post("/query", json={"prompt": "secret"},
                           headers={"X-Amzn-Oidc-Identity": "owner"})
    assert response.status_code == 401
    model.assert_not_called()
    assert b"secret" not in response.data


@pytest.mark.parametrize("data", [
    None, [], {"prompt": "a", "max_tokens": 1000}, {}, {"prompt": None},
    {"prompt": 1}, {"prompt": " "}, {"prompt": "x"*4001},
    {"prompt": "ok", "history": None}, {"prompt": "ok", "history": {}},
    {"prompt": "ok", "history": [{"user": "a", "assistant": "b"}]*11},
    {"prompt": "ok", "history": ["invalid"]},
    {"prompt": "ok", "history": [{"user": "a"}]},
    {"prompt": "ok", "history": [{"user": "a", "assistant": 1}]},
    {"prompt": "ok", "history": [{"user": "a", "assistant": " "}]},
    {"prompt": "ok", "history": [{"user": "x"*32000, "assistant": "b"}]},
    {"prompt": "\ud800"},
    {"prompt": "ok", "history": [{"user": "\ud800", "assistant": "b"}]},
])
def test_invalid_payload(services, data):
    client, _, model = services
    response = client.post("/query", data=json.dumps(data), content_type="application/json")
    assert response.status_code == 400
    model.assert_not_called()


def test_exact_boundaries(services):
    client, _, model = services
    pairs = [{"user": "a"*1399, "assistant": "b"*1401} for _ in range(10)]
    prompt = "😀"*4000
    assert validate({"prompt": prompt, "history": pairs}) == (prompt, pairs)
    assert client.post("/query", json={"prompt": prompt, "history": pairs}).status_code == 200
    assert client.post("/query", json={"prompt": "ok"}).status_code == 200
    assert model.call_count == 2
    body = json.dumps({"prompt": "ok"})
    exact = body + " "*(256*1024-len(body))
    assert client.post("/query", data=exact, content_type="application/json").status_code == 200
    assert client.post("/query", data=exact+" ", content_type="application/json").status_code == 413


def test_http_errors(services):
    client, _, model = services
    assert client.post("/query", data="{", content_type="application/json").status_code == 400
    assert client.post("/query", data="text").status_code == 415
    assert client.get("/unknown").status_code == 404
    assert client.get("/query").status_code == 405
    model.assert_not_called()


@pytest.mark.parametrize(("error", "status"), [
    (NoCredentialsError(), 503),
    (PartialCredentialsError(provider="test", cred_var="secret"), 503),
    (ReadTimeoutError(endpoint_url="secret"), 504),
    (ConnectTimeoutError(endpoint_url="secret"), 504),
    (TimeoutError("secret"), 504), (BotoCoreError(), 503), (RuntimeError("secret"), 502),
    *[(ClientError({"Error": {"Code": code, "Message": "secret"}}, "Converse"), status)
      for code, status in [("ThrottlingException", 429), ("ServiceQuotaExceededException", 429),
                           ("AccessDeniedException", 503), ("UnrecognizedClientException", 503),
                           ("ExpiredTokenException", 503), ("Unknown", 502)]],
])
def test_safe_provider_errors(services, error, status, caplog):
    client, _, model = services
    model.side_effect = error
    response = client.post("/query", json={"prompt": "secret"})
    assert response.status_code == status
    assert b"secret" not in response.data
    assert "secret" not in caplog.text
    model.assert_called_once()
