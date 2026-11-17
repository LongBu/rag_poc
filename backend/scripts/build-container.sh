#!/bin/sh
set -eu
cd "$(dirname "$0")/../.."
docker build --platform linux/amd64 --tag private-azure-chat:local .
