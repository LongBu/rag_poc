import json
from unittest.mock import Mock

import jwt
import pytest
import httpx
from azure.core.exceptions import ClientAuthenticationError
from azure.identity import CredentialUnavailableError
from openai import APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, BadRequestError, PermissionDeniedError, RateLimitError
from bedrock_chat.model import ModelConfigurationError
from test_model import SETTINGS

from bedrock_chat.app import create_app, validate


@pytest.fixture
def services():
    auth = Mock()
    model = Mock(return_value={"text": "answer", "usage": {"input_tokens": 2, "output_tokens": 1}})
    client = create_app(auth, model, {"FRONTEND_ORIGIN": "https://chat.example"}).test_client()
    return client, auth, model


def test_query_same_origin(services):
    client, auth, model = services
    pair = {"user": "earlier", "assistant": "previous answer"}
    response = client.post("/query", json={"prompt": "next", "history": [pair]},
                           headers={"Authorization": "Bearer abc", "Origin": "https://chat.example"})
    assert response.status_code == 200
    assert response.json == model.return_value
    auth.assert_called_once_with("Bearer abc")
    model.assert_called_once_with("next", [pair])
    assert "Access-Control-Allow-Origin" not in response.headers


def test_ready_preflight_and_other_origin(services):
    client, auth, model = services
    assert client.get("/ready").data == b"ready"
    assert client.options("/query").status_code == 204
    assert "Access-Control-Allow-Origin" not in client.options(
        "/query", headers={"Origin": "https://other.example"}).headers
    auth.assert_not_called()
    model.assert_not_called()
    assert create_app(settings={}).test_client().get("/ready").status_code == 503
    assert create_app(settings={}).test_client().post("/query", json={"prompt": "ok"}).status_code == 401
    assert create_app(auth=auth).test_client().get("/ready").status_code == 503
    assert create_app(settings=SETTINGS).test_client().get("/ready").status_code == 200


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


def test_exact_boundaries(services, monkeypatch):
    from time import monotonic
    start = monotonic()
    ticks = iter([start, start + 1, start + 2])
    monkeypatch.setattr("bedrock_chat.admission.monotonic", lambda: next(ticks))
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


def provider_error(kind, status, request_id="request-123"):
    request = httpx.Request("POST", "https://chat.openai.azure.com/")
    response = httpx.Response(status, request=request, headers={"x-request-id":request_id})
    return kind("secret prompt token exception text", response=response, body={"secret":"answer"})


@pytest.mark.parametrize(("error", "status", "category"), [
    (CredentialUnavailableError("secret"),503,"credentials"),
    (ClientAuthenticationError("secret"),503,"credentials"),
    (ModelConfigurationError("secret"),503,"credentials"),
    (TimeoutError("secret"),504,"timeout"),
    (APITimeoutError(request=httpx.Request("POST","https://secret.example")),504,"timeout"),
    (provider_error(RateLimitError,429),429,"quota"),
    (provider_error(AuthenticationError,401),503,"access"),
    (provider_error(PermissionDeniedError,403),503,"access"),
    (provider_error(BadRequestError,400),502,"provider"),
    (provider_error(APIStatusError,500),502,"provider"),
    (APIConnectionError(request=httpx.Request("POST","https://secret.example")),502,"provider"),
    (RuntimeError("secret"),502,"unexpected"),
])
def test_safe_provider_errors(services,error,status,category,caplog):
    client,_,model=services;model.side_effect=error
    response=client.post("/query",json={"prompt":"secret"},headers={"Authorization":"Bearer secret"})
    assert response.status_code==status
    assert b"secret" not in response.data and "secret" not in caplog.text
    assert f"category={category} status={status}" in caplog.text
    model.assert_called_once()
    model.side_effect = None
    assert client.post("/query", json={"prompt": "after failure"}).status_code == 200
    assert model.call_count == 2


@pytest.mark.parametrize("request_id",["safe-request:123", "secret\nheader", "", "x"*129])
def test_request_id_sanitizing(services,request_id,caplog):
    client,_,model=services;model.side_effect=provider_error(BadRequestError,400,request_id)
    assert client.post("/query",json={"prompt":"secret"}).status_code==502
    assert "secret" not in caplog.text
    assert ("request_id="+request_id if request_id=="safe-request:123" else "request_id=unavailable") in caplog.text


@pytest.mark.parametrize("provider_status", [400, None, "secret", True, -1, 1000])
def test_provider_status_sanitizing(services, provider_status, caplog):
    client, _, model = services
    error = provider_error(BadRequestError, 400)
    error.status_code = provider_status
    model.side_effect = error
    assert client.post("/query", json={"prompt":"secret"}).status_code == 502
    expected = 400 if type(provider_status) is int and provider_status == 400 else 0
    assert f"provider_status={expected}" in caplog.text
    assert "secret" not in caplog.text
