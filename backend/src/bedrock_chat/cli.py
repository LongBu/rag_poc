import argparse
import json
import os
import sys

from .model import ModelResponseError, create_model, invoke


def main():
    parser = argparse.ArgumentParser(description="Ask Azure GPT-5 mini using explicit Azure CLI credentials")
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--probe", action="store_true", help="Billable synthetic Hello probe capped at 32 tokens")
    parser.add_argument("prompt", nargs="?")
    args = parser.parse_args()
    if args.probe:
        if args.prompt is not None:
            parser.error("the synthetic probe accepts no user prompt")
        prompt, cap = "Hello", 32
    else:
        prompt, cap = args.prompt, 512
        if not prompt or not prompt.strip() or len(prompt) > 4000:
            parser.error("prompt must contain 1-4000 code points")
    settings = {**os.environ, "AZURE_TENANT_ID": args.tenant, "AZURE_AUTH_MODE": "azure_cli"}
    try:
        client = create_model(settings, completion_tokens=cap)
        print(json.dumps(invoke(client, prompt, [])))
        return 0
    except ModelResponseError:
        print("No usable text/usage within the completion cap; reasoning may have exhausted it. No retry was made.", file=sys.stderr)
        return 1
    except Exception:
        # SDK exception strings may contain request bodies or credentials.
        print("Invocation failed: check tenant login, model settings, scoped access, quota and availability. No retry was made.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
