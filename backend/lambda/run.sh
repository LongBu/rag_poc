#!/bin/sh
set -eu
cd "${LAMBDA_TASK_ROOT:-/var/task}"
exec python -m gunicorn --bind 127.0.0.1:8000 --workers 1 --timeout 22 \
  --error-logfile /dev/null 'bedrock_chat.app:create_app()'
