---
name: paper-verify
description: QA autonomous — verifikasi paper-summary.json sebelum dialog (retry jika gagal)
metadata: {"openclaw":{"emoji":"✅","requires":{"bins":["python3"]}}}
---

# paper-verify

**Agent Verifier** — memastikan ringkasan paper layak sebelum Agent Writer membuat dialog.

## Kapan dipanggil

Setelah `paper-extract` / `generate_paper_summary`, **sebelum** `dialog-script`.

## Jalankan

```bash
python scripts/agent/verify_summary.py <ARXIV_ID>
```

Exit `0` = lulus QA; `1` = ada issues (lihat JSON stdout).

## Kriteria

- Field wajib (`problem`, `method`, `main_findings`, `why_important`, `limitations`) minimal ~40 karakter
- `main_findings` selaras dengan `abstract.txt` (overlap istilah kunci)
- `sources.used_abstract` / `used_pdf` konsisten dengan file di folder paper

## Autonomous loop

Jika gagal, **Extractor** regenerate dengan daftar issues dari Verifier (maks. 2 retry di `scripts/daily/llm.py`). Setiap langkah tercatat di `data/<id>/agent-run.jsonl`.

## OpenClaw

```
Verifikasi paper-summary untuk 1706.03762. Jika gagal, minta paper-extract perbaiki lalu verifikasi lagi.
```
