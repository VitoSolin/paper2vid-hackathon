# Aset Pak Nam & Zaba (WebP)

| File | Pemakaian |
|------|-----------|
| `bgpaknam.webp` | Background saat **Pak Nam** bicara |
| `bgzaba.webp` | Background saat **Zaba** bicara |
| `paknam_*_up.png` | Sprite Pak Nam (resolusi tinggi, dipakai render) |
| `zaba_*_up.png` | Sprite Zaba (resolusi tinggi, dipakai render) |
| `paknam_*.webp`, `zaba_*.webp` | Versi lama / cadangan |

**Zaba di video:** posisi di-mirror dari kanan → kiri + sprite di-flip horizontal (`mirror` + `mirror_position` di config).

Konversi PNG → WebP: `python scripts/convert_to_webp.py`

Mapping: `config/characters.paknam-zaba.json`
