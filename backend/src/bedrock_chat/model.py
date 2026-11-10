from functools import cache

import boto3
from botocore.config import Config
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import AIMessage, HumanMessage


@cache
def model():
    client = boto3.client(
        "bedrock-runtime", region_name="us-east-1",
        config=Config(connect_timeout=2, read_timeout=15, retries={"total_max_attempts": 1}),
    )
    return ChatBedrockConverse(
        client=client, model_id="amazon.nova-micro-v1:0", max_tokens=512,
        region_name="us-east-1",
    )


def answer(prompt, history):
    messages = []
    for pair in history:
        messages.extend([HumanMessage(pair["user"]), AIMessage(pair["assistant"])])
    messages.append(HumanMessage(prompt))
    response = model().invoke(messages)
    return {"text": response.text, "usage": response.usage_metadata}
