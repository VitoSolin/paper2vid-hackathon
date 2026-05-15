# arXiv rate limit

## Masalah

API `export.arxiv.org` membatasi frekuensi request. Terlalu cepat → HTTP **429** / **503**, script terasa “hang”.

## Solusi di paper2video

### 1. RSS untuk daftar paper baru (tanpa API query)

Cron pagi memakai **RSS** dulu (`config/schedule.json`):

```json
"arxiv": {
  "discover": "rss",
  "rss_categories": ["cs.LG", "cs.CL", "cs.AI", "stat.ML"]
}
```

Feed: `https://rss.arxiv.org/rss/cs.LG` dll. — hanya untuk **menemukan ID**, bukan metadata lengkap.

### 2. Jeda global antar request API

Semua panggilan API (fetch metadata per paper) memakai file lock + tunggu:

```bash
# .env — minimal 2 detik, disarankan 3 (aturan arXiv)
ARXIV_REQUEST_INTERVAL=3
```

State: `data/.schedule/arxiv_rate.json`

### 3. Skip fetch jika sudah ada

`fetch_arxiv.py` tidak memanggil API jika `metadata.json` + `paper.pdf` sudah ada.

### 4. Antar paper di job pagi

3 paper = minimal ~6–9 detik jeda API (selain waktu render/LLM).

## Alur pagi (VPS)

```
07:00  RSS → 3 ID baru
       → fetch paper 1 (API + jeda 3s)
       → fetch paper 2 (API + jeda 3s)
       → fetch paper 3 (API + jeda 3s)
       → LLM + render masing-masing
```

## Fallback API query

Jika RSS gagal atau butuh query kompleks, set `"discover": "api"` di `schedule.json`.

## Uji

```bash
# Daftar baru via RSS (cepat)
python scripts/daily/fetch_latest.py -n 3

# Satu paper
python scripts/fetch_arxiv.py 1706.03762
```
