"""Exercise live authentication without valid model input or persisted tokens."""
import base64
import json
from pathlib import Path
import subprocess
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]


def encoded(value):
    return base64.urlsafe_b64encode(json.dumps(value).encode()).rstrip(b"=").decode()


def decoded(part):
    return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))


def main():
    state = json.loads((ROOT / "infra/azure/app/terraform.tfstate").read_text())
    settings = json.loads((ROOT / "infra/azure/app/private.tfvars.json").read_text())
    url = state["outputs"]["app_url"]["value"]
    api = state["outputs"]["api_client_id"]["value"]
    result = subprocess.run([
        "az", "account", "get-access-token", "--tenant", settings["tenant_id"],
        "--resource", "https://cognitiveservices.azure.com/", "--output", "json",
    ], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError("Azure CLI could not obtain the existing developer inference token")
    token = json.loads(result.stdout)["accessToken"]
    header, payload, _ = token.split(".")
    claims = decoded(payload)
    assert claims["aud"] != api, "Never submit an authorized API token in this rejection test"
    assert claims["tid"].lower() == settings["tenant_id"].lower()
    now = int(time.time())
    fake_claims = {"iss": f"https://login.microsoftonline.com/{settings['tenant_id']}/v2.0",
                   "aud": api, "tid": settings["tenant_id"], "ver": "2.0", "scp": "query",
                   "azp": state["outputs"]["spa_client_id"]["value"], "oid": settings["owner_object_id"],
                   "exp": now + 300, "iat": now, "nbf": now}
    kid = decoded(header).get("kid", "synthetic-key")
    cases = [
        ("missing bearer", {}),
        ("malformed bearer", {"Authorization": "Bearer invalid"}),
        ("forged identity headers without bearer", {"X-MS-CLIENT-PRINCIPAL": encoded(fake_claims), "X-MS-CLIENT-PRINCIPAL-ID": settings["owner_object_id"]}),
        ("unsigned alg=none", {"Authorization": "Bearer " + encoded({"alg": "none", "kid": kid}) + "." + encoded(fake_claims) + "."}),
        ("disallowed HS256", {"Authorization": "Bearer " + encoded({"alg": "HS256", "kid": kid}) + "." + encoded(fake_claims) + ".aW52YWxpZA"}),
        ("RS256 with missing kid", {"Authorization": "Bearer " + encoded({"alg": "RS256"}) + "." + encoded(fake_claims) + ".aW52YWxpZA"}),
        ("RS256 invalid signature with Microsoft kid", {"Authorization": "Bearer " + encoded({"alg": "RS256", "kid": kid}) + "." + encoded(fake_claims) + ".aW52YWxpZA"}),
        ("Microsoft-issued developer token for Cognitive Services, not this API/client", {"Authorization": "Bearer " + token}),
    ]
    for label, headers in cases:
        # Invalid prompt makes inference impossible even if authentication unexpectedly accepts.
        request = Request(url + "/query", data=b'{"prompt":""}', headers={"Content-Type": "application/json", **headers})
        try:
            response = urlopen(request, timeout=45)
        except HTTPError as error:
            response = error
        with response:
            assert response.status == 401, f"Authentication test failed: {label}; HTTP {response.status}"
            print(f"PASS HTTP 401: {label}")
    print("No tokens persisted or printed; invalid prompts prevented model inference.")
    print("Unverified live: isolated expiry/nbf, ID token, missing scope, other tenant/client/owner, app-only API token.")


if __name__ == "__main__":
    main()
