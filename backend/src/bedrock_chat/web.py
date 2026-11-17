"""Same-origin browser shell and public configuration; no runtime secrets."""
import re
from pathlib import Path
from urllib.parse import urlsplit

from flask import abort, jsonify, send_file


def register_web(app, config, identity, frontend_dir):
    root = Path(frontend_dir).resolve()
    origin = config.get("FRONTEND_ORIGIN", "")
    origin_valid = isinstance(origin, str) and re.fullmatch(
        r"https://[a-z0-9]+(?:[.-][a-z0-9]+)*(?::[0-9]{1,5})?", origin
    ) is not None
    if origin_valid:
        try:
            urlsplit(origin).port
        except ValueError:
            origin_valid = False
    connections = "'self'"
    if identity.configured:
        connections += (
            f" {identity.issuer}/.well-known/openid-configuration"
            f" https://login.microsoftonline.com/{identity.tenant_id}/oauth2/v2.0/token"
        )
    policy = (
        "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; "
        "font-src 'self'; connect-src " + connections + "; base-uri 'none'; "
        "object-src 'none'; frame-ancestors 'none'; form-action 'none'; upgrade-insecure-requests"
    )

    @app.after_request
    def security_headers(response):
        response.headers["Content-Security-Policy"] = policy
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
        response.headers.setdefault("Cache-Control", "no-store")
        return response

    def built_file(name, cache):
        path = (root / name).resolve()
        # Resolving first also rejects symlinks escaping the build directory.
        if not path.is_relative_to(root) or not path.is_file():
            abort(404)
        response = send_file(path, conditional=True)
        response.headers["Cache-Control"] = cache
        return response

    @app.get("/")
    def index():
        return built_file("index.html", "no-cache")

    @app.get("/assets/<path:name>")
    def asset(name):
        if not re.fullmatch(r"[A-Za-z0-9_-]+-[A-Za-z0-9_-]{8,}\.[A-Za-z0-9]+", name):
            abort(404)
        return built_file(f"assets/{name}", "public, max-age=31536000, immutable")

    @app.get("/config.json")
    def public_config():
        if not identity.configured or not origin_valid:
            return jsonify(error="Application configuration unavailable"), 503
        return jsonify(
            apiUrl=origin, issuer=identity.issuer, tenantId=identity.tenant_id,
            spaClientId=identity.spa_client_id, apiAudience=identity.api_client_id,
            apiScope=f"api://{identity.api_client_id}/query", ownerObjectId=identity.owner_object_id,
        )
