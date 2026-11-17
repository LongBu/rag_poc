import os
from pathlib import Path

import jwt
import re

from azure.core.exceptions import ClientAuthenticationError
from azure.identity import CredentialUnavailableError
from openai import APIError, APITimeoutError, AuthenticationError, PermissionDeniedError, RateLimitError
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from .admission import AdmissionRejected, InferenceAdmission
from .auth import OwnerAuth
from .web import register_web
from .model import ModelConfigurationError, answer, model_settings


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


def create_app(auth=None, model_service=answer, settings=None, frontend_dir=None):
    config = os.environ if settings is None else settings
    app = Flask(__name__, static_folder=None)
    app.config.update(MAX_CONTENT_LENGTH=256 * 1024, DEBUG=False)
    identity = OwnerAuth(
        config.get("AZURE_TENANT_ID", ""), config.get("ENTRA_API_CLIENT_ID", ""),
        config.get("ENTRA_SPA_CLIENT_ID", ""), config.get("ENTRA_OWNER_OBJECT_ID", "")
    )
    admission = InferenceAdmission()
    authenticate = auth if auth is not None else identity
    register_web(app, config, identity, frontend_dir if frontend_dir is not None else Path(__file__).parent / "static")

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error="Request rejected"), error.code

    @app.get("/ready")
    def ready():
        if model_service is answer:
            try:
                model_settings(config)
            except ModelConfigurationError:
                return jsonify(error="Model configuration unavailable"), 503
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
            with admission.slot():
                return jsonify(model_service(prompt, history))
        except AdmissionRejected:
            return jsonify(error="Inference busy or rate limit reached; retry deliberately later"), 429
        except (ClientAuthenticationError, CredentialUnavailableError, ModelConfigurationError):
            app.logger.warning("model_failure category=credentials status=503")
            return jsonify(error="Model credentials or configuration unavailable"), 503
        except (APITimeoutError, TimeoutError):
            app.logger.warning("model_failure category=timeout status=504")
            return jsonify(error="Model request timed out"), 504
        except APIError as error:
            status, category = 502, "provider"
            if isinstance(error, RateLimitError):
                status, category = 429, "quota"
            elif isinstance(error, (AuthenticationError, PermissionDeniedError)):
                status, category = 503, "access"
            request_id = getattr(error, "request_id", None)
            if not isinstance(request_id, str) or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", request_id):
                request_id = "unavailable"
            provider_status = getattr(error, "status_code", 0)
            if type(provider_status) is not int or not 100 <= provider_status <= 599:
                provider_status = 0
            app.logger.warning("model_failure category=%s status=%s provider_status=%s request_id=%s", category, status, provider_status, request_id)
            return jsonify(error="Model request failed; check access and service availability"), status
        except Exception:
            # Provider exception strings can contain message bodies or credentials.
            app.logger.warning("model_failure category=unexpected status=502")
            return jsonify(error="Model request failed"), 502

    return app
