---
name: video-render
description: Render video dialog berlapis (subtitle atas, 2 karakter, background) dengan TTS
metadata: {"openclaw":{"emoji":"🎬","requires":{"bins":["python3","ffmpeg","ffprobe"]}}}
---

# video-render

Buat video vertikal (format Shorts/Reels) dari `dialog-script.json`.

## Layer (dari belakang ke depan)

| z | Layer | Isi |
|---|--------|-----|
| 0 | Background | Gambar/video penuh (`assets/backgrounds/`) |
| 1 | Karakter | Dua PNG kiri/kanan; yang bicara **aktif** (lebih besar/terang) |
| 2 | Subtitle | Teks giliran saat ini di **bagian atas**, putih + outline hitam |

## Prasyarat

- `data/<arxiv_id>/dialog-script.json`
- `ffmpeg`, `ffprobe` terpasang
- `pip install -r requirements.txt` (termasuk `edge-tts`, `pillow`)

## Render

```bash
python scripts/video/render.py data/<arxiv_id>/dialog-script.json
```

Output: `output/<arxiv_id>.mp4`

## Kustomisasi aset

Ganti placeholder dengan gambar Anda (transparan PNG):

- `assets/backgrounds/default.png` — latar (contoh: lab, kantor)
- `assets/characters/speaker_a.png` — Host (kiri)
- `assets/characters/speaker_b.png` — Ahli (kanan)

Atau lewat flag:

```bash
python scripts/video/render.py data/1706.03762 \
  --background assets/backgrounds/my_lab.png \
  --char-a assets/characters/host.png \
  --char-b assets/characters/expert.png
```

Layout & font: `config/video.default.json`

## TTS

- Speaker **A** → `id-ID-GadisNeural` (default)
- Speaker **B** → `id-ID-ArdiNeural` (default)

Audio per giliran disimpan di `data/<arxiv_id>/audio/` (cache; hapus folder untuk regenerate).
