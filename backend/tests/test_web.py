from unittest.mock import Mock

import jwt
import pytest

from bedrock_chat.app import create_app


PUBLIC = {
    "AZURE_TENANT_ID": "00000000-0000-0000-0000-000000000001",
    "ENTRA_API_CLIENT_ID": "00000000-0000-0000-0000-000000000002",
    "ENTRA_SPA_CLIENT_ID": "00000000-0000-0000-0000-000000000003",
    "ENTRA_OWNER_OBJECT_ID": "00000000-0000-0000-0000-000000000004",
    "FRONTEND_ORIGIN": "https://chat.example",
}
SECRET = "private-runtime-value-not-for-browser"


@pytest.fixture
def web(tmp_path):
    root = tmp_path / "build"
    root.mkdir()
    (root / "assets").mkdir()
    (root / "index.html").write_text('<div id="root"></div><script type="module" src="/assets/index-abcdefgh.js"></script>')
    (root / "assets/index-abcdefgh.js").write_text('document.title = "Chat";')
    (root / "assets/index-abcdefgh.css").write_text('body {color: black}')
    (root / "assets/private.json").write_text(SECRET)
    (tmp_path / "private.txt").write_text(SECRET)
    auth = Mock(side_effect=jwt.InvalidTokenError())
    model = Mock(return_value={"text": "<img src=x onerror=alert(1)>", "usage": {"input_tokens": 1, "output_tokens": 1}})
    settings = {**PUBLIC, "AZURE_CLIENT_SECRET": SECRET, "AZURE_OPENAI_API_KEY": SECRET,
                "AZURE_OPENAI_ENDPOINT": "https://private.example", "BUDGET_EMAIL": "private@example.com"}
    app = create_app(auth, model, settings, frontend_dir=root)
    return app.test_client(), root, auth, model


def test_shell_assets_and_cache(web):
    client, _, auth, model = web
    html = client.get("/?code=private-callback&state=private-callback")
    assert html.status_code == 200 and html.mimetype == "text/html"
    assert html.headers["Cache-Control"] == "no-cache"
    assert b"private-callback" not in html.data
    for name, mime in [("index-abcdefgh.js", "text/javascript"), ("index-abcdefgh.css", "text/css")]:
        response = client.get("/assets/" + name)
        assert response.status_code == 200 and response.mimetype == mime
        assert response.headers["Cache-Control"] == "public, max-age=31536000, immutable"
        cached = client.get("/assets/" + name, headers={"If-None-Match": response.headers["ETag"]})
        assert cached.status_code == 304
        assert cached.headers["Cache-Control"] == response.headers["Cache-Control"]
        assert client.head("/assets/" + name).data == b""
        assert SECRET.encode() not in response.data
    assert client.get("/", headers={"If-None-Match": html.headers["ETag"]}).status_code == 304
    auth.assert_not_called(); model.assert_not_called()


def test_public_configuration_is_allowlisted_and_host_independent(web):
    client, _, auth, model = web
    response = client.get("/config.json", headers={"Host": "evil.example", "X-Forwarded-Host": "evil.example", "X-Forwarded-Proto": "http"})
    assert response.status_code == 200
    assert response.json == {
        "apiUrl": PUBLIC["FRONTEND_ORIGIN"], "issuer": f'https://login.microsoftonline.com/{PUBLIC["AZURE_TENANT_ID"]}/v2.0',
        "tenantId": PUBLIC["AZURE_TENANT_ID"], "spaClientId": PUBLIC["ENTRA_SPA_CLIENT_ID"],
        "apiAudience": PUBLIC["ENTRA_API_CLIENT_ID"], "apiScope": f'api://{PUBLIC["ENTRA_API_CLIENT_ID"]}/query',
        "ownerObjectId": PUBLIC["ENTRA_OWNER_OBJECT_ID"],
    }
    assert response.headers["Cache-Control"] == "no-store"
    assert "ETag" not in response.headers
    for value in [SECRET, "private.example", "private@example.com", "evil.example"]:
        assert value.encode() not in response.data
    auth.assert_not_called(); model.assert_not_called()


@pytest.mark.parametrize("changes", [
    {"AZURE_TENANT_ID": "private\r\nheader"}, {"ENTRA_OWNER_OBJECT_ID": ""},
    {"ENTRA_API_CLIENT_ID": PUBLIC["ENTRA_SPA_CLIENT_ID"]},
    *[{"FRONTEND_ORIGIN": value} for value in [None, "", "http://chat.example", "https://chat.example/", "https://chat.example/path", "https://user:secret@chat.example", "https://chat.example?secret", "https://chat.example#secret", "https://chat.example:99999", "https://chat.example\r\nheader"]],
])
def test_bad_config_fails_closed(changes, tmp_path):
    model = Mock()
    client = create_app(model_service=model, settings={**PUBLIC, **changes}, frontend_dir=tmp_path).test_client()
    response = client.get("/config.json")
    assert response.status_code == 503
    assert response.json == {"error": "Application configuration unavailable"}
    assert response.headers["Cache-Control"] == "no-store"
    assert client.post("/query", json={"prompt": "ok"}).status_code == 401
    model.assert_not_called()


@pytest.mark.parametrize("path", [
    "/api/unknown", "/query/unknown", "/ready/unknown", "/anything", "/index.html", "/static/index.html",
    "/assets/private.json", "/assets/index.js", "/assets/index-abcdefgh.js.map", "/assets/missing-abcdefgh.js",
    "/assets/../private.txt", "/assets/%2e%2e/private.txt", "/assets/%2e%2e%2fprivate.txt",
    "/assets/%252e%252e%252fprivate.txt", "/assets/..%5cprivate.txt", "/assets/%00.js",
    "/assets/sub/index-abcdefgh.js", "/assets/.env", "/.env", "/Pipfile", "/config.json/extra",
])
def test_unknown_and_unsafe_paths_are_json_errors(web, path):
    client, _, auth, model = web
    response = client.get(path)
    assert response.status_code == 404
    assert response.json == {"error": "Request rejected"}
    assert SECRET.encode() not in response.data
    assert response.headers["Cache-Control"] == "no-store"
    auth.assert_not_called(); model.assert_not_called()


@pytest.mark.parametrize("name", ["index.html", "assets/index-abcdefgh.js"])
def test_symlink_escape_is_rejected(web, name):
    client, root, _, _ = web
    path = root / name
    path.unlink(); path.symlink_to(root.parent / "private.txt")
    assert client.get("/" if name == "index.html" else "/" + name).status_code == 404


def test_missing_build_has_safe_404(tmp_path):
    client = create_app(settings=PUBLIC, frontend_dir=tmp_path / "absent").test_client()
    assert client.get("/").status_code == 404


def test_canonical_identifiers_and_https_port(tmp_path):
    settings = {**PUBLIC, "AZURE_TENANT_ID": "ABCDEFAB-0000-0000-0000-000000000001", "FRONTEND_ORIGIN": "https://localhost:8443"}
    response = create_app(settings=settings, frontend_dir=tmp_path).test_client().get("/config.json")
    assert response.status_code == 200
    assert response.json["tenantId"] == settings["AZURE_TENANT_ID"].lower()
    assert response.json["apiUrl"] == "https://localhost:8443"


@pytest.mark.parametrize(("method", "path", "status"), [
    ("get", "/", 200), ("get", "/config.json", 200), ("get", "/ready", 200),
    ("get", "/assets/index-abcdefgh.js", 200), ("get", "/unknown", 404),
    ("get", "/query", 405), ("post", "/query", 401), ("options", "/query", 204),
])
def test_security_headers_on_success_and_errors(web, method, path, status):
    client, _, _, model = web
    response = getattr(client, method)(path)
    assert response.status_code == status
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000"
    policy = response.headers["Content-Security-Policy"]
    assert "Content-Security-Policy-Report-Only" not in response.headers
    directives = dict(part.strip().split(" ", 1) if " " in part.strip() else (part.strip(), "") for part in policy.split(";"))
    assert directives["default-src"] == "'none'"
    assert directives["script-src"] == directives["style-src"] == "'self'"
    assert directives["connect-src"].split() == [
        "'self'", f'https://login.microsoftonline.com/{PUBLIC["AZURE_TENANT_ID"]}/v2.0/.well-known/openid-configuration',
        f'https://login.microsoftonline.com/{PUBLIC["AZURE_TENANT_ID"]}/oauth2/v2.0/token',
    ]
    for name in ["base-uri", "frame-ancestors", "object-src", "form-action"]:
        assert directives[name] == "'none'"
    assert "upgrade-insecure-requests" in directives
    for forbidden in ["unsafe-inline", "unsafe-eval", "*", "private"]:
        assert forbidden not in policy
    model.assert_not_called()


def test_json_messages_are_not_rendered_as_html(web):
    client, _, auth, model = web; auth.side_effect = None
    response = client.post("/query", json={"prompt": "<script>private</script>"})
    assert response.status_code == 200 and response.mimetype == "application/json"
    assert response.json == model.return_value
    assert response.headers["Cache-Control"] == "no-store"
    assert b"<script>private" not in client.get("/").data
