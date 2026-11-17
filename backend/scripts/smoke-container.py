"""Real Gunicorn HTTP checks in a network-isolated Linux container; no cloud calls."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import time

IMAGE = "private-azure-chat:local"
ROOT = Path(__file__).resolve().parents[2]
ENV = {
    "AZURE_TENANT_ID": "00000000-0000-0000-0000-000000000001",
    "ENTRA_API_CLIENT_ID": "00000000-0000-0000-0000-000000000002",
    "ENTRA_SPA_CLIENT_ID": "00000000-0000-0000-0000-000000000003",
    "ENTRA_OWNER_OBJECT_ID": "00000000-0000-0000-0000-000000000004",
    "AZURE_CLIENT_ID": "00000000-0000-0000-0000-000000000005",
    "AZURE_OPENAI_ENDPOINT": "https://synthetic.openai.azure.com",
    "AZURE_OPENAI_DEPLOYMENT": "synthetic",
    "AZURE_OPENAI_API_VERSION": "2025-04-01-preview",
    "AZURE_AUTH_MODE": "managed_identity",
    "CONTAINER_APP_NAME": "synthetic",
    "FRONTEND_ORIGIN": "https://chat.example",
    "BUDGET_EMAIL": "synthetic-private@example.invalid",
}
HTTP = '''
import json,sys
from urllib.request import Request,urlopen
from urllib.error import HTTPError
args=json.load(sys.stdin)
body=args.pop('body')
request=Request('http://127.0.0.1:8000'+args.pop('path'),data=None if body is None else body.encode(),**args)
try: response=urlopen(request,timeout=15)
except HTTPError as error: response=error
with response:
 print(json.dumps({'status':response.status,'headers':dict(response.headers),'body':response.read().decode()}))
'''


def docker(*args, data=None):
    return subprocess.check_output(["docker", *args], input=data, text=True, stderr=subprocess.PIPE, timeout=90)


def execute(container, code):
    return docker("exec", container, "python", "-c", code).strip()


def http(container, path="/query", method="POST", body='{"prompt":"synthetic-prompt-marker"}', token="synthetic-smoke-owner"):
    args = {"path": path, "method": method, "body": body,
            "headers": {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}}
    return json.loads(docker("exec", "-i", container, "python", "-c", HTTP, data=json.dumps(args)))


def start(mocked):
    args = ["run", "--rm", "--detach", "--platform", "linux/amd64", "--network", "none",
            "--read-only", "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m,mode=1777",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true"]
    for key, value in ENV.items():
        args += ["--env", f"{key}={value}"]
    if mocked:
        args += ["--volume", f"{ROOT / 'backend/tests/container_smoke'}:/smoke:ro",
                 "--env", "PYTHONPATH=/smoke:/app"]
    args += [IMAGE]
    if mocked:
        args += ["python", "-m", "gunicorn", "--config", "/app/gunicorn.conf.py", "wsgi:app"]
    return docker(*args).strip()


def wait_ready(container):
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            response = http(container, "/ready", "GET", None)
            if response["status"] == 200:
                return
        except subprocess.CalledProcessError:
            pass
        time.sleep(.25)
    raise AssertionError("Container did not become ready")


def check_runtime(container, mocked):
    info = json.loads(docker("inspect", container))[0]
    assert info["HostConfig"]["ReadonlyRootfs"] and info["HostConfig"]["NetworkMode"] == "none"
    assert "/tmp" in info["HostConfig"]["Tmpfs"]
    assert [(m["Destination"], m["RW"]) for m in info["Mounts"]] == ([("/smoke", False)] if mocked else [])
    execute(container, '''
import errno,importlib.util,os,platform,sys,tempfile
from pathlib import Path
assert os.getuid()==10001 and platform.machine()=='x86_64'
assert sys.version_info[:3]==(3,14,8)
assert {p.name for p in Path('/app').iterdir()} == {'bedrock_chat','gunicorn.conf.py'}
assert {p.name for p in Path('/app/bedrock_chat').iterdir()} == {'__init__.py','admission.py','app.py','auth.py','cli.py','model.py','web.py','static'}
assert not Path('/app/bedrock_chat/static/config.json').exists()
assert not Path('/opt/extensions/lambda-adapter').exists()
for name in ['pytest','pipenv','boto3','botocore']:
 assert importlib.util.find_spec(name) is None,name
with tempfile.TemporaryFile() as file: file.write(b'temporary')
try: open('/app/forbidden','w')
except OSError as error: assert error.errno in (errno.EROFS,errno.EACCES)
else: raise AssertionError('Application directory is writable')
''')
    config = json.loads(execute(container, '''
import json,runpy
s=runpy.run_path('/app/gunicorn.conf.py')
print(json.dumps({k:s[k] for k in ['workers','threads','worker_class','bind','accesslog','errorlog','control_socket_disable']}))
'''))
    assert config == {"workers": 1, "threads": 4, "worker_class": "gthread", "bind": "0.0.0.0:8000",
                      "accesslog": None, "errorlog": "-", "control_socket_disable": True}


def check_public(container):
    response = http(container, "/?code=synthetic-callback-marker", "GET", None)
    assert response["status"] == 200 and response["headers"]["Cache-Control"] == "no-cache"
    assert "synthetic-callback-marker" not in response["body"]
    assert response["headers"]["Referrer-Policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in response["headers"]["Content-Security-Policy"]
    import re
    assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', response["body"])
    assert len(assets) >= 2
    for path in assets:
        asset = http(container, path, "GET", None)
        assert asset["status"] == 200 and "immutable" in asset["headers"]["Cache-Control"]
        assert ENV["BUDGET_EMAIL"] not in asset["body"]
    config = http(container, "/config.json", "GET", None)
    assert config["status"] == 200 and config["headers"]["Cache-Control"] == "no-store"
    assert set(json.loads(config["body"])) == {"apiUrl", "issuer", "tenantId", "spaClientId", "apiAudience", "apiScope", "ownerObjectId"}
    for value in [ENV["BUDGET_EMAIL"], ENV["AZURE_OPENAI_ENDPOINT"], ENV["AZURE_CLIENT_ID"]]:
        assert value not in config["body"]
    for path in ["/missing", "/api/missing", "/assets/%2e%2e/Pipfile", "/.env"]:
        assert http(container, path, "GET", None)["status"] == 404
    assert http(container, token="other")["status"] == 401
    assert http(container, method="OPTIONS", body=None)["status"] == 204


def check_mocked(container):
    assert http(container, body='{"prompt":""}')["status"] == 400
    assert http(container, body="{")["status"] == 400
    response = http(container)
    assert response["status"] == 200 and json.loads(response["body"]) == {
        "text": "answer: synthetic-prompt-marker", "usage": {"input_tokens": 10, "output_tokens": 2}}
    for prompt, status in [("synthetic-timeout", 504), ("synthetic-configuration", 503), ("synthetic-provider", 502)]:
        time.sleep(1.05)
        response = http(container, body=json.dumps({"prompt": prompt}))
        assert response["status"] == status and "synthetic-private-error" not in response["body"]
    time.sleep(2.05)
    before = int(execute(container, "from pathlib import Path; print(len(Path('/tmp/invocations').read_text().splitlines()))"))
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(http, container, body='{"prompt":"synthetic-block"}')
        try:
            for _ in range(30):
                if execute(container, "from pathlib import Path; print(Path('/tmp/smoke-entered').exists())") == "True":
                    break
                time.sleep(.1)
            else:
                raise AssertionError("Model did not enter blocking test")
            assert http(container)["status"] == 429
            assert http(container, "/ready", "GET", None)["status"] == 200
            calls = int(execute(container, "from pathlib import Path; print(len(Path('/tmp/invocations').read_text().splitlines()))"))
            assert calls == before + 1
        finally:
            execute(container, "from pathlib import Path; Path('/tmp/smoke-release').touch()")
        assert first.result(timeout=20)["status"] == 200
    assert http(container)["status"] == 200


def main():
    image = json.loads(docker("image", "inspect", IMAGE))[0]
    assert image["Os"] == "linux" and image["Architecture"] == "amd64"
    assert image["Config"]["User"] == "10001:10001"
    baked_keys = {entry.split("=", 1)[0] for entry in image["Config"]["Env"]}
    assert not baked_keys.intersection(ENV)
    assert not any(key.startswith("AWS_") for key in baked_keys)
    for mocked in [False, True]:
        container = start(mocked)
        try:
            wait_ready(container); check_runtime(container, mocked); check_public(container)
            if mocked:
                check_mocked(container)
            logs = subprocess.run(["docker", "logs", container], capture_output=True, text=True, check=True)
            assert logs.stdout == ""
            combined = logs.stdout + logs.stderr
            for marker in ["synthetic-callback-marker", "synthetic-prompt-marker", "synthetic-smoke-owner", "synthetic-private-error"]:
                assert marker not in combined, "Private marker appeared in logs"
            if mocked:
                for category in ["timeout", "credentials", "unexpected"]:
                    assert f"category={category}" in logs.stderr
        finally:
            subprocess.run(["docker", "stop", "--timeout", "5", container], check=True, stdout=subprocess.DEVNULL)
    print("Linux/amd64 container HTTP smoke passed: production and mocked targets, read-only/non-root, no network or credentials, assets/config/readiness/auth/validation/errors/concurrency, sanitized stderr.")


if __name__ == "__main__":
    main()
