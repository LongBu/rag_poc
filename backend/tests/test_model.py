from types import SimpleNamespace
from unittest.mock import Mock

import httpx
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
import pytest

from bedrock_chat import model

SETTINGS = {
    "AZURE_OPENAI_ENDPOINT": "https://private-chat.openai.azure.com/",
    "AZURE_OPENAI_DEPLOYMENT": "gpt-5-mini",
    "AZURE_OPENAI_API_VERSION": "2025-04-01-preview",
    "AZURE_TENANT_ID": "00000000-0000-0000-0000-000000000002",
    "AZURE_AUTH_MODE": "azure_cli",
    "AZURE_CLIENT_ID": "00000000-0000-0000-0000-000000000003",
}


@pytest.mark.parametrize("mode", ["azure_cli", "managed_identity"])
def test_model_parameters_and_credentials(monkeypatch, mode):
    cli, managed, provider, constructor = Mock(), Mock(), Mock(), Mock()
    for name, value in [("AzureCliCredential", cli), ("ManagedIdentityCredential", managed),
                        ("get_bearer_token_provider", provider), ("AzureChatOpenAI", constructor)]:
        monkeypatch.setattr(model, name, value)
    config = {**SETTINGS, "AZURE_AUTH_MODE": mode}
    assert model.create_model(config) is constructor.return_value
    args = constructor.call_args.kwargs
    assert args["max_completion_tokens"] == 512
    assert args["reasoning_effort"] == "minimal" and args["verbosity"] == "low"
    assert args["temperature"] is None and args["max_retries"] == 0
    assert args["model"] == "gpt-5-mini" and args["model_version"] == "2025-08-07"
    assert not args["streaming"] and not args["use_responses_api"]
    assert args["api_key"] is None and args["azure_ad_token"] is None
    assert args["azure_ad_token_provider"] is provider.return_value
    assert args["azure_endpoint"] == SETTINGS["AZURE_OPENAI_ENDPOINT"]
    assert args["azure_deployment"] == SETTINGS["AZURE_OPENAI_DEPLOYMENT"]
    assert args["api_version"] == SETTINGS["AZURE_OPENAI_API_VERSION"]
    assert args["timeout"].connect == 2 and args["timeout"].read == 15
    if mode == "managed_identity":
        managed.assert_called_once_with(client_id=SETTINGS["AZURE_CLIENT_ID"], retry_total=0, connection_timeout=2, read_timeout=5)
        cli.assert_not_called()
        credential = managed.return_value
    else:
        cli.assert_called_once_with(tenant_id=SETTINGS["AZURE_TENANT_ID"], process_timeout=5)
        managed.assert_not_called()
        credential = cli.return_value
    provider.assert_called_once_with(credential, "https://cognitiveservices.azure.com/.default")


@pytest.mark.parametrize("field,value", [
    ("AZURE_OPENAI_ENDPOINT", ""), ("AZURE_OPENAI_ENDPOINT", "http://private-chat.openai.azure.com"),
    ("AZURE_OPENAI_ENDPOINT", "https://evil.example"), ("AZURE_OPENAI_ENDPOINT", "https://chat.openai.azure.com/path"),
    ("AZURE_OPENAI_DEPLOYMENT", ""), ("AZURE_OPENAI_DEPLOYMENT", "../../other"),
    ("AZURE_OPENAI_API_VERSION", "future"), ("AZURE_TENANT_ID", "invalid"),
    ("AZURE_AUTH_MODE", "default_chain"), ("CONTAINER_APP_NAME", "hosted"),
    ("OPENAI_API_KEY", "secret"), ("AZURE_OPENAI_API_KEY", "secret"), ("AZURE_OPENAI_AD_TOKEN", "secret"),
])
def test_configuration_failures(monkeypatch, field, value):
    constructor = Mock()
    monkeypatch.setattr(model, "AzureChatOpenAI", constructor)
    with pytest.raises(model.ModelConfigurationError):
        model.create_model({**SETTINGS, field: value})
    constructor.assert_not_called()


def test_missing_settings_managed_identity_and_invalid_cap():
    with pytest.raises(model.ModelConfigurationError):
        model.model_settings({})
    with pytest.raises(model.ModelConfigurationError):
        model.model_settings({**SETTINGS, "AZURE_AUTH_MODE": "managed_identity", "AZURE_CLIENT_ID": ""})
    with pytest.raises(model.ModelConfigurationError):
        model.create_model(SETTINGS, 1024)


def test_history_usage_and_cache(monkeypatch):
    client = Mock()
    client.invoke.return_value = AIMessage(content="answer", usage_metadata={"input_tokens":10,"output_tokens":2,"total_tokens":12})
    factory = Mock(return_value=client)
    monkeypatch.setattr(model, "create_model", factory)
    model.model.cache_clear()
    result = model.answer("latest", [{"user":"first","assistant":"earlier"}])
    assert result == {"text":"answer","usage":{"input_tokens":10,"output_tokens":2}}
    client.invoke.assert_called_once_with([SystemMessage(model.INSTRUCTION),HumanMessage("first"),AIMessage("earlier"),HumanMessage("latest")])
    assert model.model() is client
    factory.assert_called_once()
    model.model.cache_clear()


@pytest.mark.parametrize("change", [
    {"text":""}, {"text":"  "}, {"text":None},
    {"additional_kwargs":{"refusal":"no"}}, {"tool_calls":[{"name":"tool"}]},
    {"usage_metadata":None}, {"usage_metadata":{}},
    {"usage_metadata":{"input_tokens":True,"output_tokens":1}},
    {"usage_metadata":{"input_tokens":1,"output_tokens":-1}},
    {"usage_metadata":{"input_tokens":1,"output_tokens":1.5}},
    {"usage_metadata":{"input_tokens":1,"output_tokens":513}},
])
def test_invalid_or_reasoning_only_response(change):
    response = SimpleNamespace(text="answer", usage_metadata={"input_tokens":1,"output_tokens":1},additional_kwargs={},tool_calls=[])
    for key,value in change.items():setattr(response,key,value)
    client = Mock();client.invoke.return_value=response
    with pytest.raises(model.ModelResponseError):model.invoke(client,"hello",[])
    client.invoke.assert_called_once()


@pytest.mark.parametrize("cap", [32, 512])
def test_wire_payload_uses_supported_parameters(monkeypatch, cap):
    for key in ["AZURE_OPENAI_API_KEY","OPENAI_API_KEY","AZURE_OPENAI_AD_TOKEN"]:monkeypatch.delenv(key,raising=False)
    client = model.create_model(SETTINGS, cap)
    payload = client._get_request_payload([SystemMessage(model.INSTRUCTION),HumanMessage("Hello")])
    assert payload["max_completion_tokens"] == cap
    assert payload["verbosity"] == "low" and payload["reasoning_effort"] == "minimal"
    assert "temperature" not in payload and "max_tokens" not in payload
    assert client.root_client.max_retries == 0
    assert client.root_client.timeout == httpx.Timeout(15,connect=2)


def test_sdk_wire_response_without_network(monkeypatch):
    import json
    for key in ["AZURE_OPENAI_API_KEY", "OPENAI_API_KEY", "AZURE_OPENAI_AD_TOKEN"]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(model, "get_bearer_token_provider", Mock(return_value=lambda: "test-token"))
    client = model.create_model(SETTINGS)
    requests = []
    def handle(request):
        requests.append(request)
        assert request.headers["Authorization"] == "Bearer test-token"
        assert "api-key" not in request.headers
        assert request.url.params["api-version"] == "2025-04-01-preview"
        assert request.url.path == "/openai/deployments/gpt-5-mini/chat/completions"
        payload = json.loads(request.content)
        assert payload["max_completion_tokens"] == 512
        assert payload["reasoning_effort"] == "minimal" and payload["verbosity"] == "low"
        return httpx.Response(200, json={"id":"chat-test", "object":"chat.completion", "created":1, "model":"gpt-5-mini", "choices":[{"index":0,"finish_reason":"stop","message":{"role":"assistant","content":"Hello"}}], "usage":{"prompt_tokens":10,"completion_tokens":2,"total_tokens":12}})
    client.root_client._client = httpx.Client(transport=httpx.MockTransport(handle))
    assert model.invoke(client, "Hi", []) == {"text":"Hello","usage":{"input_tokens":10,"output_tokens":2}}
    assert len(requests) == 1
