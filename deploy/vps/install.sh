#!/usr/bin/env bash
# Setup awal di VPS Ubuntu (jalankan sebagai user deploy, mis. ubuntu)
set -euo pipefail

REPO="${1:-$HOME/paper2video}"
cd "$REPO"

echo "==> paper2video VPS install @ $REPO"

sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip python3-venv ffmpeg git

if ! python3 -m venv .venv 2>/dev/null; then
  echo "Pasang python3-venv: sudo apt install python3-venv"
  exit 1
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -U pip
pip install -q -r requirements.txt

chmod +x scripts/daily/run_cron.sh

mkdir -p logs data/.schedule config/youtube

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo ""
  echo "EDIT .env: ELEVENLABS_API_KEY, ANTHROPIC_API_KEY, YOUTUBE_PRIVACY_DEFAULT"
fi

if [[ ! -f config/youtube/client_secret.json ]]; then
  echo "Salin client_secret.json ke config/youtube/ lalu: python scripts/youtube/auth.py"
fi

echo ""
echo "Selesai. Langkah manual:"
echo "  1. nano .env"
echo "  2. python scripts/youtube/auth.py   # sekali, butuh browser atau SSH -L"
echo "  3. crontab -e  # salin dari deploy/vps/crontab.example (sesuaikan path)"
echo "  4. Uji: ./scripts/daily/run_cron.sh morning"
