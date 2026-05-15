# Upload otomatis ke YouTube

Pipeline paper2video bisa mengunggah `output/<arxiv_id>.mp4` ke channel YouTube Anda via **YouTube Data API v3**.

## 1. Google Cloud Console

1. Buka [Google Cloud Console](https://console.cloud.google.com/)
2. Buat proyek (atau pilih yang ada)
3. **APIs & Services → Enable APIs** → aktifkan **YouTube Data API v3**
4. **Credentials → Create Credentials → OAuth client ID**
   - Application type: **Desktop app**
5. Unduh JSON → simpan sebagai:

   ```
   config/youtube/client_secret.json
   ```

   (Jangan commit file ini — sudah di `.gitignore`.)

## 2. OAuth consent screen

- **User type**: External (atau Internal jika Google Workspace)
- Tambahkan scope: `.../auth/youtube.upload`
- Tambahkan email Anda sebagai **Test user** (selama app masih "Testing")

Tanpa test user, login OAuth akan gagal dengan error access_denied.

## 3. Instal dependensi & login

```bash
pip install -r requirements.txt
python scripts/youtube/auth.py
```

Browser terbuka → pilih akun Google channel YouTube → izinkan upload.  
Token disimpan di `config/youtube/token.json`.

Login ulang:

```bash
python scripts/youtube/auth.py --reauth
```

## 4. Upload video

Pastikan video sudah di-render:

```bash
python scripts/video/render.py data/1706.03762
```

Upload:

```bash
# Default: unlisted (aman untuk uji)
python scripts/youtube/upload.py data/1706.03762

# Publik
python scripts/youtube/upload.py data/1706.03762 --privacy public

# Cek metadata tanpa upload
python scripts/youtube/upload.py data/1706.03762 --dry-run
```

Hasil: `data/<arxiv_id>/youtube-publish.json` berisi `video_id` dan `url`.

## 5. Variabel lingkungan (`.env`)

```bash
YOUTUBE_PRIVACY_DEFAULT=unlisted   # public | unlisted | private
YOUTUBE_CATEGORY_ID=28             # 28 = Science & Technology
```

## 6. OpenClaw agent

```bash
openclaw agent --message "Publish video paper 1706.03762 ke YouTube unlisted"
```

Agent memakai skill `youtube-publish` → menjalankan `upload.py`.

## Metadata otomatis

Judul & deskripsi dibuat dari:

- `data/<id>/metadata.json` (judul, abstract, kategori)
- `data/<id>/paper-summary.json` (jika ada — problem, metode, temuan)

Contoh judul: *Attention Is All You Need — Pak Nam & Zaba*

Deskripsi berisi link arXiv, ringkasan, dan tag `#Shorts`.

## Kuota API

Upload video memakai kuota harian YouTube API (~1.600 unit per upload).  
Untuk channel pribadi biasanya cukup; pantau di Cloud Console jika error `quotaExceeded`.

## Troubleshooting

| Error | Solusi |
|-------|--------|
| `client_secret.json` tidak ada | Ikuti langkah 1 |
| `access_denied` | Tambahkan akun sebagai Test user di OAuth consent |
| `invalid_grant` | `python scripts/youtube/auth.py --reauth` |
| Video tidak ditemukan | Render dulu dengan `video/render.py` |
| `youtubeSignupRequired` | Channel YouTube belum dibuat untuk akun Google tersebut |
