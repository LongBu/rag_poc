#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
docker build --platform linux/amd64 -f lambda/Dockerfile -t private-bedrock-lambda:local .
mkdir -p artifacts
docker run --rm --platform linux/amd64 --entrypoint python --env PYTHONPATH=/var/task \
  -v "$PWD/artifacts:/out" private-bedrock-lambda:local /package.py
