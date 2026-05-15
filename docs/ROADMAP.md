# Roadmap & status tugas

## Ringkasan alur

```
arXiv → ringkasan paper → dialog Pak Nam ↔ Zaba → TTS per giliran → video 9:16 (ffmpeg)
```

## Status per tahap

| # | Tugas | Status | Catatan |
|---|--------|--------|---------|
| 1 | Fetch paper arXiv | ✅ Selesai | `scripts/fetch_arxiv.py` |
| 2 | Baca title, abstract, PDF | ✅ Selesai | `paper.txt` via PyMuPDF |
| 3 | Ekstrak problem, metode, temuan, pentingnya, batasan | ✅ Selesai | Skill OpenClaw `paper-extract` |
| 4 | Dialog Pak Nam & Zaba | ✅ Mudah / selesai | Skill `dialog-script`; speaker: `paknam` / `zaba` |
| 5 | TTS terpisah per pembicara | ✅ Selesai | `data/<id>/audio/turn_XX_paknam.mp3` dll. |
| 6 | Video maker custom 9:16 | ✅ Dasar selesai | `scripts/video/render.py` + ffmpeg |
| 7 | Polish video | 🔜 Opsional | animasi mulut, timing subtitle kata-per-kata, musik |

## Layer video (9:16 = 1080×1920)

```
┌─────────────────────────┐
│  SUBTITLE               │  z=2 — teks giliran aktif
│                         │
│  [Pak Nam]    [Zaba]    │  z=1 — ekspresi; yang bicara menonjol
│                         │
│  ░░ background ░░░░░░░    │  z=0 — bgpaknam / bgzaba saat giliran
└─────────────────────────┘
```

**Ya, ffmpeg** dipakai untuk:
- menggabungkan frame + audio per giliran (durasi = panjang TTS),
- meng-concat semua segmen jadi satu MP4.

Komposit visual (posisi karakter, subtitle, ganti background) dilakukan dengan **Pillow**; ffmpeg hanya encode/mux.

## Dialog — format

```json
{
  "speakers": { "paknam": "Pak Nam", "zaba": "Zaba" },
  "turns": [
    { "speaker": "paknam", "text": "...", "expression": "neutral" },
    { "speaker": "zaba", "text": "...", "expression": "thinking" }
  ]
}
```

Ekspresi: `neutral`, `laugh`, `thinking` (Pak Nam); `neutral`, `laugh`, `thinking`, `confused` (Zaba).

## Perintah

```bash
# 1–3: paper
python scripts/run_pipeline.py <ARXIV_ID>
openclaw agent --message "Ekstrak paper <ARXIV_ID>"

# 4: dialog
openclaw agent --message "Buat dialog Pak Nam dan Zaba untuk paper <ARXIV_ID>"

# 5–6: TTS + video (otomatis)
python scripts/video/render.py data/<ARXIV_ID> --config config/characters.paknam-zaba.json
```

Aset: folder `personA/` (background + sprite per ekspresi).
