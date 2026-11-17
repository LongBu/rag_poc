from functools import cache
import os
import re

from azure.identity import AzureCliCredential, ManagedIdentityCredential, get_bearer_token_provider
import httpx
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI

INSTRUCTION = "Answer concisely by default. Use the supplied conversation context."
UUID = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}")


class ModelConfigurationError(ValueError):
    pass


class ModelResponseError(ValueError):
    pass


def model_settings(settings):
    endpoint = settings.get("AZURE_OPENAI_ENDPOINT", "")
    deployment = settings.get("AZURE_OPENAI_DEPLOYMENT", "")
    version = settings.get("AZURE_OPENAI_API_VERSION", "")
    tenant = settings.get("AZURE_TENANT_ID", "")
    mode = settings.get("AZURE_AUTH_MODE", "")
    client = settings.get("AZURE_CLIENT_ID", "")
    if not (
        re.fullmatch(r"https://[a-z0-9][a-z0-9-]{1,62}\.openai\.azure\.com/?", endpoint)
        and re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}", deployment)
        and version == "2025-04-01-preview"
        and UUID.fullmatch(tenant)
        and mode in {"azure_cli", "managed_identity"}
    ):
        raise ModelConfigurationError("Required Azure model settings are missing or invalid")
    if mode == "managed_identity" and not UUID.fullmatch(client):
        raise ModelConfigurationError("User-assigned managed identity is required")
    if settings.get("CONTAINER_APP_NAME") and mode != "managed_identity":
        raise ModelConfigurationError("Hosted inference requires managed identity")
    if any(settings.get(key) for key in ("OPENAI_API_KEY", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_AD_TOKEN")):
        raise ModelConfigurationError("Use Entra credentials, not ambient keys or tokens")
    return endpoint, deployment, version, tenant, mode, client


def create_model(settings, completion_tokens=512):
    if completion_tokens not in (32, 512):
        raise ModelConfigurationError("Only the normal or synthetic probe cap is supported")
    endpoint, deployment, version, tenant, mode, client = model_settings(settings)
    credential = (
        ManagedIdentityCredential(client_id=client, retry_total=0, connection_timeout=2, read_timeout=5)
        if mode == "managed_identity" else AzureCliCredential(tenant_id=tenant, process_timeout=5)
    )
    return AzureChatOpenAI(
        azure_endpoint=endpoint, azure_deployment=deployment, api_version=version,
        azure_ad_token_provider=get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default"),
        api_key=None, azure_ad_token=None, model="gpt-5-mini", model_version="2025-08-07",
        max_completion_tokens=completion_tokens, reasoning_effort="minimal", verbosity="low",
        temperature=None, timeout=httpx.Timeout(15, connect=2), max_retries=0,
        streaming=False, use_responses_api=False,
    )


@cache
def model():
    return create_model(os.environ)


def invoke(client, prompt, history):
    messages = [SystemMessage(INSTRUCTION)]
    for pair in history:
        messages.extend([HumanMessage(pair["user"]), AIMessage(pair["assistant"])])
    messages.append(HumanMessage(prompt))
    response = client.invoke(messages)
    text = response.text
    usage = response.usage_metadata
    if (
        not isinstance(text, str) or not text.strip()
        or response.additional_kwargs.get("refusal") or response.tool_calls
        or not isinstance(usage, dict)
        or any(type(usage.get(key)) is not int or usage[key] < 0 for key in ("input_tokens", "output_tokens"))
        or usage["output_tokens"] > 512
    ):
        raise ModelResponseError("No usable text or valid token usage within the completion cap")
    return {"text": text, "usage": {key: usage[key] for key in ("input_tokens", "output_tokens")}}


def answer(prompt, history):
    return invoke(model(), prompt, history)
