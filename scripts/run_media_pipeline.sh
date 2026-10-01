#!/usr/bin/env bash
# Hourly job (invoked by cron): downloads any new WhatsApp attachments,
# renames them by content and uploads them to Google Drive, via a headless
# Claude Code run. See scripts/media_pipeline_prompt.txt for the actual
# instructions given to it.
set -euo pipefail

# cron runs with a minimal PATH that may not include where `claude` lives.
export PATH="/home/antonio/.local/bin:$PATH"

cd "$(dirname "$0")/.."

set -a
source .env
set +a

if [ -z "${GOOGLE_DRIVE_ROOT_FOLDER_ID:-}" ]; then
  echo "$(date -u +%FT%TZ) GOOGLE_DRIVE_ROOT_FOLDER_ID not set in .env, skipping run." >&2
  exit 0
fi

DATA_DIR="${WHATSAPP_DATA_DIR:-./data/whatsapp-store}"

prompt=$(sed \
  -e "s|{{REPO_ROOT}}|$(pwd)|g" \
  -e "s|{{DATA_DIR}}|$DATA_DIR|g" \
  -e "s|{{DRIVE_ROOT_FOLDER_ID}}|$GOOGLE_DRIVE_ROOT_FOLDER_ID|g" \
  scripts/media_pipeline_prompt.txt)

mkdir -p logs

echo "=== $(date -u +%FT%TZ) starting media pipeline run ===" >> logs/media_pipeline.log
claude -p "$prompt" \
  --permission-mode acceptEdits \
  --allowedTools "Bash,Read,mcp__claude_ai_Google_Drive__search_files,mcp__claude_ai_Google_Drive__create_file" \
  --output-format text \
  >> logs/media_pipeline.log 2>&1
echo "=== $(date -u +%FT%TZ) finished (exit $?) ===" >> logs/media_pipeline.log
