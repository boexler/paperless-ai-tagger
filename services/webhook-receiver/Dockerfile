FROM ghcr.io/freeformz/paperless-ngx-mcp:0.0.12 AS paperless-mcp

FROM python:3.12-slim

WORKDIR /app

COPY --from=paperless-mcp /paperless-ngx-mcp /usr/local/bin/paperless-ngx-mcp

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY services/webhook-receiver/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/webhook-receiver/app ./app
COPY prompts ./prompts

ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/data

RUN mkdir -p /data

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
