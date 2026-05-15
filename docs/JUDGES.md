# Menjalankan demo

Panduan singkat kalau ingin mencoba repo ini dari nol.

## Setup

```bash
git clone https://github.com/VitoSolin/paper2vid-hackathon.git
cd paper2vid-hackathon
./setup.sh && source .venv/bin/activate
cp .env.example .env
# isi LLM_PROVIDER + API key, opsional ELEVENLABS_API_KEY
```

## Satu paper end-to-end

```bash
python scripts/run_e2e.py 1706.03762 --force-llm
```

Video: `output/1706.03762.mp4`  
Log agent: `data/1706.03762/agent-run.jsonl`

Dengan upload YouTube (butuh OAuth — lihat [YOUTUBE.md](YOUTUBE.md)):

```bash
python scripts/run_e2e.py 1706.03762 --upload
```

## OpenClaw

```bash
export PAPER2VIDEO_USE_OPENCLAW=1
openclaw config set agents.defaults.workspace "$(pwd)"
openclaw agent --message "Orkestrasi paper 1706.03762: fetch, extract, verify, dialog, render"
```

## Produksi (VPS / Telegram)

- Cron: [VPS.md](VPS.md)
- Bot: [TELEGRAM.md](TELEGRAM.md) — `/e2e latest`, `/e2e 1706.03762 upload`
