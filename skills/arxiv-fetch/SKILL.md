---
name: arxiv-fetch
description: Ambil paper dari arXiv (metadata, abstract, PDF) ke folder data/
metadata: {"openclaw":{"emoji":"📄","requires":{"bins":["python3"]}}}
---

# arxiv-fetch

Gunakan skill ini saat user meminta mengambil / mendownload paper dari arXiv.

## Langkah

1. Normalisasi ID dari input user (URL `arxiv.org/abs/...`, `pdf`, atau ID mentah seperti `2301.07041`).
2. Dari root workspace (`{baseDir}` parent = repo root), jalankan:

```bash
python scripts/run_pipeline.py <ARXIV_ID>
```

Atau hanya metadata tanpa PDF:

```bash
python scripts/fetch_arxiv.py <ARXIV_ID> --no-pdf
```

3. Konfirmasi folder output: `data/<arxiv_id>/` berisi `metadata.json` dan `abstract.txt` (plus `paper.pdf` / `paper.txt` jika pipeline penuh).

## Setelah fetch

Jika user minta ringkasan/ekstraksi, lanjut ke skill **paper-extract** (baca file di folder tersebut).

## Catatan

- Butuh virtualenv dengan `pip install -r requirements.txt` jika belum.
- Jangan commit file di `data/` ke git (sudah di `.gitignore`).
