FROM public.ecr.aws/awsguru/aws-lambda-adapter:1.1.0@sha256:17cfd08eff1dfea3f6a9a1e9c65fdac80aa4919b6085e746615530f43f57d2f1 AS adapter
FROM public.ecr.aws/lambda/python:3.14@sha256:cf4c3a72d1cd34b7ae289fef868bac0777afeef9895c5d0a3d83d7dcb4da9a29
COPY --from=adapter /lambda-adapter /opt/extensions/lambda-adapter
COPY lambda/bootstrap /opt/bootstrap
COPY Pipfile Pipfile.lock /tmp/dependencies/
RUN python -m venv /tmp/pipenv \
    && /tmp/pipenv/bin/pip install --no-cache-dir pipenv==2026.10.6 \
    && cd /tmp/dependencies \
    && /tmp/pipenv/bin/pipenv verify \
    && /tmp/pipenv/bin/pipenv requirements --hash > /tmp/locked-dependencies.txt \
    && python -m pip install --no-cache-dir --require-hashes --only-binary=:all: -r /tmp/locked-dependencies.txt --target /var/task
COPY src/bedrock_chat /var/task/bedrock_chat
COPY lambda/run.sh /var/task/run.sh
COPY lambda/package.py /package.py
RUN chmod 755 /opt/bootstrap /var/task/run.sh
ENV AWS_LAMBDA_EXEC_WRAPPER=/opt/bootstrap \
    AWS_LWA_PORT=8000 \
    AWS_LWA_READINESS_CHECK_PATH=/ready \
    AWS_LWA_READINESS_CHECK_HEALTHY_STATUS=200 \
    AWS_LWA_INVOKE_MODE=buffered \
    LANGSMITH_TRACING=false \
    LANGCHAIN_TRACING_V2=false
CMD ["run.sh"]
