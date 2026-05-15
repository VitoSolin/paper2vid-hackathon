---
name: dialog-script
description: Buat naskah dialog dua orang dari ringkasan paper untuk video
metadata: {"openclaw":{"emoji":"🎙️"}}
---

# dialog-script

Buat **naskah dialog** antara dua pembicara dari `paper-summary.json`. Setelah selesai, render video dengan skill **video-render**.

## Prasyarat

`data/<arxiv_id>/paper-summary.json` harus sudah ada (skill **paper-extract**).

## Persona

- **A (Host)** — penasaran, bertanya singkat, audiens umum.
- **B (Ahli)** — menjelaskan dengan analogi, tidak terlalu jargon.

## Langkah

1. Baca `paper-summary.json`.
2. Tulis dialog 8–14 giliran, Bahasa Indonesia, alur:
   - hook / judul paper
   - masalah (`problem`)
   - metode (`method`)
   - temuan (`main_findings`)
   - kenapa penting (`why_important`)
   - batasan (`limitations`) + penutup singkat
3. Simpan ke `data/<arxiv_id>/dialog-script.json`:

```json
{
  "arxiv_id": "...",
  "title": "...",
  "speakers": { "A": "Host", "B": "Ahli" },
  "turns": [
    { "speaker": "A", "text": "..." },
    { "speaker": "B", "text": "..." }
  ],
  "estimated_duration_sec": 180,
  "notes": "Siap untuk video-render"
}
```

## Batasan

- Jangan klaim video sudah dibuat.
- Usahakan kalimat pendek (mudah di-TTS nanti).
