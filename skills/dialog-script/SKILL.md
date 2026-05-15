---
name: dialog-script
description: Buat naskah dialog dua orang dari ringkasan paper untuk video
metadata: {"openclaw":{"emoji":"🎙️"}}
---

# dialog-script

Buat **naskah dialog** antara dua pembicara dari `paper-summary.json`. Setelah selesai, render video dengan skill **video-render**.

## Prasyarat

`data/<arxiv_id>/paper-summary.json` harus sudah ada (skill **paper-extract**).

## Persona (Pak Nam & Zaba)

- **zaba** — **pemula**: banyak bertanya, bingung di istilah baru, bahasa santai.
- **paknam** — **mentor**: menjelaskan dengan bahasa mudah, analogi sehari-hari, hindari jargon (atau langsung diterjemahkan).

Giliran ideal: Zaba tanya → Pak Nam jelaskan. Boleh Zaba tanya lanjutan ("jadi maksudnya…?").

Alias lama `A`/`B` masih diterima (A=paknam, B=zaba) — tetap ikuti persona di atas.

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
  "speakers": { "paknam": "Pak Nam", "zaba": "Zaba" },
  "turns": [
    { "speaker": "paknam", "text": "...", "expression": "neutral" },
    { "speaker": "zaba", "text": "...", "expression": "thinking" }
  ],
  "estimated_duration_sec": 180,
  "notes": "Siap untuk video-render"
}
```

## Batasan

- Jangan klaim video sudah dibuat.
- Usahakan kalimat pendek (mudah di-TTS nanti).
