#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "==> paper2video setup"

if ! command -v python3 >/dev/null; then
  echo "python3 diperlukan." >&2
  exit 1
fi

if python3 -m venv .venv 2>/dev/null; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install -q -U pip
  pip install -q -r requirements.txt
  echo "==> Python OK (.venv)"
else
  echo "==> venv gagal (pasang python3-venv); pakai pip --user"
  pip3 install --user -q -r requirements.txt
  echo "==> Python OK (user site-packages)"
fi

if command -v openclaw >/dev/null 2>&1; then
  echo "==> OpenClaw sudah terpasang: $(openclaw --version 2>/dev/null || echo ok)"
else
  echo "==> Pasang OpenClaw secara manual:"
  echo "    curl -fsSL https://openclaw.ai/install.sh | bash"
  echo "    # atau: npm install -g openclaw@latest"
fi

WORKSPACE="$ROOT"
echo ""
echo "Langkah berikutnya:"
echo "  1. openclaw onboard          # API key + model (sekali)"
echo "  2. openclaw config set agents.defaults.workspace \"$WORKSPACE\""
echo "  3. openclaw gateway          # atau: openclaw gateway --port 18789"
echo ""
echo "Uji pipeline:"
echo "  source .venv/bin/activate"
echo "  python scripts/run_pipeline.py 2301.07041"
echo "  openclaw agent --message \"Ekstrak paper 2301.07041\""
echo ""
echo "Contoh config: config/openclaw.example.json"
