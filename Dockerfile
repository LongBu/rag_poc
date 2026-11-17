FROM node:24.22.3-bookworm-slim@sha256:0e2646ab57e77b7a384a0cb59b6815b182c77e1f9c3ba36bd8435bd9c4e6680e AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/src ./src
COPY frontend/index.html frontend/tsconfig.json frontend/vite.config.ts ./
RUN npm run build

FROM python:3.14.8-slim-trixie@sha256:9b629e83e1a517e01eaf7a36362563c0c7f620d3e4747f7dcf79564e290b7b48 AS dependencies
WORKDIR /build/backend
COPY backend/Pipfile backend/Pipfile.lock ./
RUN python -m venv /tools \
    && /tools/bin/pip install --no-cache-dir pipenv==2026.10.6 \
    && /tools/bin/pipenv verify \
    && /tools/bin/pipenv requirements --hash > /build/requirements.txt \
    && python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --require-hashes --only-binary=:all: -r /build/requirements.txt \
    && /opt/venv/bin/pip check

FROM python:3.14.8-slim-trixie@sha256:9b629e83e1a517e01eaf7a36362563c0c7f620d3e4747f7dcf79564e290b7b48
ENV PATH=/opt/venv/bin:$PATH \
    HOME=/tmp TMPDIR=/tmp \
    PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false
WORKDIR /app
COPY --from=dependencies /opt/venv /opt/venv
COPY backend/src/bedrock_chat ./bedrock_chat
COPY backend/gunicorn.conf.py ./gunicorn.conf.py
COPY --from=frontend /build/frontend/dist ./bedrock_chat/static
USER 10001:10001
EXPOSE 8000
CMD ["python", "-m", "gunicorn", "--config", "/app/gunicorn.conf.py", "bedrock_chat.app:create_app()"]
