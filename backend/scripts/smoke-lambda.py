"""Exercise real Web Adapter HTTP API conversion locally; no AWS credentials."""
import base64
import json
from pathlib import Path
import subprocess
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

root = Path(__file__).resolve().parent.parent
container = subprocess.check_output([
    "docker", "run", "--rm", "--detach", "--platform", "linux/amd64",
    "--publish", "127.0.0.1::8080", "--env", "PYTHONPATH=/smoke:/var/task",
    "--env", "FRONTEND_ORIGIN=https://chat.example",
    "--volume", f"{root / 'tests/lambda_smoke'}:/smoke:ro",
    "private-bedrock-lambda:local",
], text=True).strip()
try:
    address = subprocess.check_output(["docker", "port", container, "8080/tcp"], text=True).strip()
    endpoint = f"http://{address}/2015-03-31/functions/function/invocations"

    def invoke(method="POST", path="/query", body='{"prompt":"hello"}', token="smoke-owner", encoded=False):
        event = {
            "version": "2.0", "routeKey": f"{method} {path}", "rawPath": path,
            "rawQueryString": "", "headers": {"content-type": "application/json",
                "authorization": f"Bearer {token}", "origin": "https://chat.example"},
            "requestContext": {"requestId": "synthetic", "stage": "$default",
                "http": {"method": method, "path": path, "protocol": "HTTP/1.1",
                         "sourceIp": "127.0.0.1", "userAgent": "smoke"}},
            "body": base64.b64encode(body.encode()).decode() if encoded else body,
            "isBase64Encoded": encoded,
        }
        with urlopen(Request(endpoint, data=json.dumps(event).encode(),
                             headers={"Content-Type": "application/json"}), timeout=45) as response:
            result = json.load(response)
        assert "statusCode" in result, result
        return result

    deadline = time.monotonic() + 45
    while True:
        try:
            response = invoke("GET", "/ready", "")
            break
        except (URLError, ConnectionError):
            assert time.monotonic() < deadline, "Local runtime did not become ready"
            time.sleep(0.5)
    assert response["statusCode"] == 200 and response["body"] == "ready"
    response = invoke(encoded=True)
    assert response["statusCode"] == 200, response
    assert json.loads(response["body"])["text"] == "answer: hello"
    assert response["headers"]["access-control-allow-origin"] == "https://chat.example"
    assert invoke(token="other")["statusCode"] == 401
    assert invoke(body='{"prompt":""}')["statusCode"] == 400
    assert invoke(body="{")["statusCode"] == 400
    assert invoke(body='{"prompt":"timeout"}')["statusCode"] == 504
    assert invoke(method="OPTIONS", body="")["statusCode"] == 204
    assert invoke(method="GET", path="/missing", body="")["statusCode"] == 404
    print("Adapter smoke checks passed: readiness, base64/JSON body, headers, success, auth, validation, errors, preflight, 404")
except Exception:
    subprocess.run(["docker", "logs", container], check=False)
    raise
finally:
    subprocess.run(["docker", "stop", container], check=True, stdout=subprocess.DEVNULL)
