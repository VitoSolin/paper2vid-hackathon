---
name: orchestrate-paper
description: Orkestrasi autonomous penuh — fetch → extract → verify → dialog → video → YouTube
metadata: {"openclaw":{"emoji":"🎬","requires":{"bins":["python3","ffmpeg"]}}}
---

# orchestrate-paper

Satu perintah agent untuk **seluruh pipeline** paper2video (demo hackathon / juri).

## Peran multi-agent

| Agent | Skill / script | Output |
|-------|----------------|--------|
| Orchestrator | skill ini | mengawasi alur + `agent-run.jsonl` |
| Extractor | `paper-extract` | `paper-summary.json` (RAG dari `paper.txt`) |
| Verifier | `paper-verify` | QA + retry otomatis |
| Writer | `dialog-script` | `dialog-script.json` |
| Director | `video-render` | `output/<id>.mp4` |
| Publisher | `youtube-publish` | `youtube-publish.json` |

## Headless (VPS / demo cepat)

```bash
python scripts/run_e2e.py 1706.03762 --force-llm
python scripts/run_e2e.py 1706.03762 --upload
python scripts/run_e2e.py --latest upload
```

## OpenClaw (narasi untuk juri)

```
Orkestrasi paper 1706.03762 end-to-end:
1. arxiv-fetch
2. paper-extract (Agent Extractor, RAG)
3. paper-verify — jika gagal, extract ulang lalu verify lagi
4. dialog-script (Agent Writer, Pak Nam & Zaba)
5. video-render
6. youtube-publish unlisted (opsional)
Tunjukkan isi data/1706.03762/agent-run.jsonl sebagai bukti autonomous loop.
```

## Audit trail

Setiap langkah agent → `data/<arxiv_id>/agent-run.jsonl` (timestamp, agent, action, status, detail).
