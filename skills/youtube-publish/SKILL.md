---
name: youtube-publish
description: Upload video paper ke YouTube (judul, deskripsi, tag otomatis dari metadata arXiv)
metadata: {"openclaw":{"emoji":"📺","requires":{"bins":["python3"]}}}
---

# youtube-publish

Unggah `output/<arxiv_id>.mp4` ke YouTube setelah render selesai.

## Prasyarat

1. Video ada: `output/<arxiv_id>.mp4` (skill `video-render`)
2. OAuth YouTube sudah di-setup — lihat `docs/YOUTUBE.md`
3. `config/youtube/client_secret.json` + token (`python scripts/youtube/auth.py`)
4. `pip install -r requirements.txt` (paket `google-api-python-client`, dll.)

## Upload

```bash
# Unlisted (default, aman untuk uji)
python scripts/youtube/upload.py data/<arxiv_id>

# Publik
python scripts/youtube/upload.py data/<arxiv_id> --privacy public

# Preview metadata saja
python scripts/youtube/upload.py data/<arxiv_id> --dry-run
```

## Output

- Video di YouTube → URL di stdout
- `data/<arxiv_id>/youtube-publish.json` — `video_id`, `url`, `privacy`

## Metadata

Otomatis dari `metadata.json` + `paper-summary.json` (jika ada):

- **Judul**: `{judul paper} — Pak Nam & Zaba`
- **Deskripsi**: link arXiv, ringkasan problem/metode/temuan, `#Shorts`
- **Tag**: arXiv, machine learning, kategori paper, dll.

Env opsional: `YOUTUBE_PRIVACY_DEFAULT`, `YOUTUBE_CATEGORY_ID` (default `28` = Science & Technology).

## Alur lengkap dengan agent

1. `arxiv-fetch` + `paper-extract`
2. `dialog-script`
3. `video-render`
4. **youtube-publish** ← langkah ini

Contoh perintah user:

> Publish video paper 1706.03762 ke YouTube unlisted

Jalankan upload; laporkan URL YouTube ke user.
