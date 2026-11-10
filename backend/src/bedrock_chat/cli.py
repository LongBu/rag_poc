import argparse
import json
import sys

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError


def main():
    parser = argparse.ArgumentParser(description="Ask Nova Micro using a temporary AWS role profile")
    parser.add_argument("--profile", required=True)
    parser.add_argument("prompt")
    args = parser.parse_args()
    if not args.prompt.strip() or len(args.prompt) > 4000:
        parser.error("prompt must contain 1-4000 code points")
    try:
        client = boto3.Session(profile_name=args.profile).client(
            "bedrock-runtime", region_name="us-east-1",
            config=Config(connect_timeout=2, read_timeout=15, retries={"total_max_attempts": 1}),
        )
        response = client.converse(
            modelId="amazon.nova-micro-v1:0",
            messages=[{"role": "user", "content": [{"text": args.prompt}]}],
            inferenceConfig={"maxTokens": 512},
        )
        print(json.dumps({
            "text": "".join(block.get("text", "") for block in response["output"]["message"]["content"]),
            "usage": response["usage"],
        }))
        return 0
    except (BotoCoreError, ClientError):
        print("Invocation failed: check temporary profile credentials, role access, model availability, and quota.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
