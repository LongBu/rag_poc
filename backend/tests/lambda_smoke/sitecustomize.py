"""Offline dependencies injected only into the local adapter smoke container."""
import jwt
from langchain_core.messages import AIMessage
from bedrock_chat import app, model


def authenticate(header):
    if header != "Bearer smoke-owner":
        raise jwt.InvalidTokenError("Synthetic owner required")


class FakeModel:
    def invoke(self, messages):
        if messages[-1].content == "timeout":
            raise TimeoutError("private provider detail")
        return AIMessage(content="answer: " + messages[-1].content,
                         usage_metadata={"input_tokens": 10, "output_tokens": 2, "total_tokens": 12})


app.OwnerAuth = lambda *_: authenticate
model.model = FakeModel
