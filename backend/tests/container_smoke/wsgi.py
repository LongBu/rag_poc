"""Explicit Docker-smoke WSGI target; never included in the production image."""
from pathlib import Path
from threading import Event

import jwt

from bedrock_chat.app import create_app
from bedrock_chat.model import ModelConfigurationError

ENTERED = Path("/tmp/smoke-entered")
RELEASE = Path("/tmp/smoke-release")


def authenticate(header):
    if header != "Bearer synthetic-smoke-owner":
        raise jwt.InvalidTokenError("Synthetic owner required")


def model(prompt, history):
    with Path("/tmp/invocations").open("a") as calls:
        calls.write("invoked\n")
    if prompt == "synthetic-block":
        ENTERED.touch()
        gate = Event()
        for _ in range(100):
            if RELEASE.exists():
                break
            gate.wait(.1)
        else:
            raise TimeoutError("synthetic-private-error")
    if prompt == "synthetic-timeout":
        raise TimeoutError("synthetic-private-error")
    if prompt == "synthetic-configuration":
        raise ModelConfigurationError("synthetic-private-error")
    if prompt == "synthetic-provider":
        raise RuntimeError("synthetic-private-error")
    return {"text": "answer: " + prompt, "usage": {"input_tokens": 10, "output_tokens": 2}}


app = create_app(auth=authenticate, model_service=model)
