import os

import jwt
from botocore.exceptions import (
    BotoCoreError, ClientError, ConnectTimeoutError, NoCredentialsError,
    PartialCredentialsError, ReadTimeoutError,
)
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from .auth import OwnerAuth
from .model import answer


def validate(data):
    if not isinstance(data, dict) or set(data) - {"prompt", "history"}:
        raise ValueError
    prompt = data.get("prompt")
    history = data.get("history", [])
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 4000:
        raise ValueError
    if not isinstance(history, list) or len(history) > 10:
        raise ValueError
    total = len(prompt)
    prompt.encode("utf-8")
    for pair in history:
        if not isinstance(pair, dict) or set(pair) != {"user", "assistant"}:
            raise ValueError
        for value in pair.values():
            if not isinstance(value, str) or not value.strip():
                raise ValueError
            value.encode("utf-8")
            total += len(value)
    if total > 32000:
        raise ValueError
    return prompt, history


def create_app(auth=None, model_service=answer, settings=None):
    config = os.environ if settings is None else settings
    app = Flask(__name__)
    app.config.update(MAX_CONTENT_LENGTH=256 * 1024, DEBUG=False)
    authenticate = auth if auth is not None else OwnerAuth(
        config.get("ISSUER", ""), config.get("CLIENT_ID", ""), config.get("OWNER_SUB", "")
    )
    origin = config.get("FRONTEND_ORIGIN", "")

    @app.after_request
    def cors(response):
        if origin and request.headers.get("Origin") == origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
            response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
            response.headers["Vary"] = "Origin"
        return response

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error="Request rejected"), error.code

    @app.get("/ready")
    def ready():
        return "ready"

    @app.route("/query", methods=["POST", "OPTIONS"])
    def query():
        if request.method == "OPTIONS":
            return "", 204
        try:
            authenticate(request.headers.get("Authorization", ""))
        except (jwt.PyJWTError, jwt.PyJWKClientError):
            return jsonify(error="Sign in as the configured owner"), 401
        try:
            prompt, history = validate(request.get_json())
        except (ValueError, UnicodeError):
            return jsonify(error="Invalid prompt or conversation limits exceeded"), 400
        try:
            return jsonify(model_service(prompt, history))
        except (NoCredentialsError, PartialCredentialsError):
            return jsonify(error="Model credentials unavailable"), 503
        except (ReadTimeoutError, ConnectTimeoutError, TimeoutError):
            return jsonify(error="Model request timed out"), 504
        except ClientError as error:
            code = error.response["Error"]["Code"]
            if code in {"ThrottlingException", "ServiceQuotaExceededException"}:
                return jsonify(error="Model quota exceeded; try again later"), 429
            if code in {"AccessDeniedException", "UnrecognizedClientException", "ExpiredTokenException"}:
                return jsonify(error="Model access unavailable"), 503
            return jsonify(error="Model request failed"), 502
        except BotoCoreError:
            return jsonify(error="Model service unavailable"), 503
        except Exception:
            # Provider exception strings can contain message bodies or credentials.
            return jsonify(error="Model request failed"), 502

    return app
