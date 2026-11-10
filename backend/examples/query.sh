#!/bin/sh
set -eu
# Use an AssumeRole profile backed by temporary SSO credentials, never static keys.
aws bedrock-runtime converse \
  --profile "${AWS_PROFILE:?Set AWS_PROFILE to the configured temporary-role profile}" \
  --region us-east-1 \
  --model-id amazon.nova-micro-v1:0 \
  --messages '[{"role":"user","content":[{"text":"Why is the sky blue?"}]}]' \
  --inference-config '{"maxTokens":512}' \
  --query '{answer:output.message.content,usage:usage}' \
  --no-cli-pager
