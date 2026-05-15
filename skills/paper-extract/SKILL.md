---
name: paper-extract
description: Ekstrak problem, metode, temuan, pentingnya, dan batasan dari paper arXiv
metadata: {"openclaw":{"emoji":"🔬","requires":{"bins":["python3"]}}}
---

# paper-extract

Ekstrak ringkasan terstruktur dari paper yang sudah di-fetch ke `data/<arxiv_id>/`.

## Prasyarat

Folder paper harus berisi minimal `metadata.json` dan `abstract.txt`. Idealnya juga `paper.txt` (dari PDF).

Jika belum ada, jalankan dulu **arxiv-fetch**.

## Langkah

1. Tentukan `arxiv_id` dan buka:
   - `data/<arxiv_id>/metadata.json` — title, authors, abstract
   - `data/<arxiv_id>/abstract.txt`
   - `data/<arxiv_id>/paper.txt` — isi utama (jika ada)

2. Baca title, abstract, dan teks PDF. Headless memakai **RAG ringan** (`scripts/agent/rag_context.py`) untuk memilih cuplikan `paper.txt` paling relevan. Sintesis field berikut **dalam Bahasa Indonesia**, ringkas tapi substantif:
   - `problem`
   - `method`
   - `main_findings`
   - `why_important`
   - `limitations`

3. Tulis hasil ke `data/<arxiv_id>/paper-summary.json` mengikuti schema di `schemas/paper-summary.schema.json`.

4. Panggil **paper-verify** sebelum dialog. Jika gagal, perbaiki field yang dilaporkan dan verifikasi lagi.

## Template output

```json
{
  "arxiv_id": "2301.07041",
  "title": "...",
  "authors": ["..."],
  "published": "2023-01-17",
  "categories": ["cs.LG"],
  "pdf_url": "https://arxiv.org/pdf/...",
  "abstract": "...",
  "problem": "...",
  "method": "...",
  "main_findings": "...",
  "why_important": "...",
  "limitations": "...",
  "sources": {
    "used_abstract": true,
    "used_pdf": true,
    "notes": ""
  }
}
```

## Kualitas

- Jangan fabrikasi eksperimen atau angka yang tidak ada di sumber.
- `limitations`: kombinasikan yang disebut penulis + batasan metodologis yang jelas dari teks.
- Jika hanya abstract tersedia, set `sources.used_pdf: false` dan jelaskan di `sources.notes`.
