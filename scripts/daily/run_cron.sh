#!/usr/bin/env bash
# Wrapper cron — log + timezone + venv
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

export TZ="${PAPER2VIDEO_TZ:-Asia/Jakarta}"
mkdir -p logs

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source <(grep -v '^\s*#' "$ROOT/.env" | grep -v '^\s*$' | sed 's/^/export /')
  set +a
fi

if [[ -f "$ROOT/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
fi

PY="${PYTHON:-python3}"
JOB="$1"
LOG="$ROOT/logs/${JOB}-$(date +%Y%m%d).log"

echo "=== $(date -Iseconds) $JOB ===" >>"$LOG"
case "$JOB" in
  morning)
    "$PY" "$ROOT/scripts/daily/morning_job.py" >>"$LOG" 2>&1
    ;;
  upload)
    "$PY" "$ROOT/scripts/daily/upload_job.py" >>"$LOG" 2>&1
    ;;
  *)
    echo "Usage: run_cron.sh {morning|upload}" >&2
    exit 1
    ;;
esac
