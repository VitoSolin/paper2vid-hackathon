# Paper2Video — Tools

## CLI (repo root)

| Perintah | Fungsi |
|----------|--------|
| `python scripts/fetch_arxiv.py <id>` | Metadata + unduh PDF |
| `python scripts/extract_pdf_text.py data/<id>` | PDF → `paper.txt` |
| `python scripts/run_pipeline.py <id>` | Fetch + extract sekaligus |
| `python scripts/run_e2e.py <id>` | E2E showcase A→F (fetch→LLM→verify→video→YouTube) |
| `python scripts/agent/verify_summary.py <id>` | QA Agent Verifier pada `paper-summary.json` |
| `python scripts/video/render.py data/<id>` | Render video berlapis + TTS |
| `python scripts/youtube/auth.py` | Login OAuth YouTube (sekali) |
| `python scripts/youtube/upload.py data/<id>` | Upload ke YouTube |
| `./scripts/daily/run_cron.sh morning` | Otomasi: 3 paper baru + render |
| `./scripts/daily/run_cron.sh upload` | Otomasi: upload 1 dari antrian |
| `python scripts/telegram_bot.py` | Bot Telegram → `/e2e <arxiv_id>` |

## OpenClaw

```bash
openclaw agent --message "Orkestrasi paper 1706.03762: fetch, extract, verify, dialog, render"
openclaw agent --message "Verifikasi paper-summary 2301.07041"
```

Workspace proyek ini harus mengarah ke root repo (`agents.defaults.workspace`).

## Artefak per paper

```
data/<arxiv_id>/
  metadata.json
  abstract.txt
  paper.pdf
  paper.txt
  paper-summary.json      # hasil Agent Extractor (RAG)
  agent-run.jsonl         # audit multi-agent (extractor → verifier → writer)
  dialog-script.json      # naskah Agent Writer
  audio/                  # cache TTS per giliran
```

Output video: `output/<arxiv_id>.mp4`

Setelah upload: `data/<arxiv_id>/youtube-publish.json` (`url`, `video_id`). Setup: `docs/YOUTUBE.md`.

## Layer video

```
┌─────────────────────────┐
│  SUBTITLE (atas)        │  ← teks giliran aktif
│                         │
│    [A]          [B]     │  ← karakter; yang bicara lebih menonjol
│                         │
│  ░░░ BACKGROUND ░░░░░   │  ← gambar latar penuh
└─────────────────────────┘
```
