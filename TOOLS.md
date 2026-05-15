# Paper2Video — Tools

## CLI (repo root)

| Perintah | Fungsi |
|----------|--------|
| `python scripts/fetch_arxiv.py <id>` | Metadata + unduh PDF |
| `python scripts/extract_pdf_text.py data/<id>` | PDF → `paper.txt` |
| `python scripts/run_pipeline.py <id>` | Fetch + extract sekaligus |
| `python scripts/video/render.py data/<id>` | Render video berlapis + TTS |

## OpenClaw

```bash
openclaw agent --message "Ekstrak paper 2301.07041"
openclaw agent --message "Buat dialog dua orang untuk paper terakhir"
```

Workspace proyek ini harus mengarah ke root repo (`agents.defaults.workspace`).

## Artefak per paper

```
data/<arxiv_id>/
  metadata.json
  abstract.txt
  paper.pdf
  paper.txt
  paper-summary.json      # hasil ekstraksi agent
  dialog-script.json      # naskah dialog
  audio/                  # cache TTS per giliran
```

Output video: `output/<arxiv_id>.mp4`

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
