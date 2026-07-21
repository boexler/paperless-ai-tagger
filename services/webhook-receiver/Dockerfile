FROM ghcr.io/freeformz/paperless-ngx-mcp:0.0.12 AS paperless-mcp

FROM python:3.12-slim-bookworm

ARG GIT_SHA=unknown

WORKDIR /app

COPY --from=paperless-mcp /paperless-ngx-mcp /usr/local/bin/paperless-ngx-mcp

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl nano nodejs npm \
    && npm install -g @openai/codex \
    && rm -rf /var/lib/apt/lists/*

COPY services/webhook-receiver/requirements.txt .

# cursor-sdk ships large platform wheels (~60 MB); upgrade pip and allow longer downloads.
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir --default-timeout=300 --only-binary=cursor-sdk -r requirements.txt

COPY services/webhook-receiver/app ./app
COPY prompts ./prompts

ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/data
ENV CODEX_HOME=/data/codex
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_ROOT_USER_ACTION=ignore
ENV GIT_SHA=${GIT_SHA}

RUN mkdir -p /data /data/codex

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
