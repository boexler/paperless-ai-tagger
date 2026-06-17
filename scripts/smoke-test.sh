#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8081}"
SECRET="${WEBHOOK_SECRET:-change-me-to-a-long-random-string}"

echo "Health check..."
curl -fsS "${BASE_URL}/health"
echo

echo "Webhook test (sync)..."
curl -fsS -X POST "${BASE_URL}/webhook/sync?secret=${SECRET}" \
  -H "Content-Type: application/json" \
  -d '{
    "doc_url": "https://paperless.example.com/documents/42/",
    "doc_title": "Test Rechnung",
    "correspondent": "Acme GmbH",
    "document_type": "Rechnung"
  }'
echo
