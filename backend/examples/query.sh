#!/bin/sh
set -eu
# Entra token acquisition is performed by AzureCliCredential; no token is printed.
exec "${PYTHON:-python}" -m bedrock_chat.cli \
  --tenant "${AZURE_TENANT_ID:?Set AZURE_TENANT_ID to the selected Entra tenant}" "$@"
