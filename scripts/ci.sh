#!/usr/bin/env bash
# Runs the full CI suite using only Docker, so it works even without
# Go/Python/uv installed on the host.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> Building images"
docker compose --profile mcp build

echo "==> Running Go tests (whatsapp-bridge)"
docker run --rm -v "$(pwd)/whatsapp-bridge:/src" -w /src golang:1.25-bookworm go test ./...

echo "==> Running Python tests (whatsapp-mcp-server)"
docker run --rm -v "$(pwd)/whatsapp-mcp-server:/src" -w /src python:3.11-slim \
  bash -c "pip install --quiet uv && uv sync --frozen && uv run pytest"

echo "==> CI OK"
