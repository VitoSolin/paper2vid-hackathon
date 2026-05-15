# Aset Pak Nam & Zaba (WebP)

| File | Pemakaian |
|------|-----------|
| `bgpaknam.webp` | Background saat **Pak Nam** bicara |
| `bgzaba.webp` | Background saat **Zaba** bicara |
| `paknam_*.webp` | Sprite Pak Nam (neutral, laugh, thinking) |
| `zaba_*.webp` | Sprite Zaba (neutral, laugh, thinking, confused) |

**Zaba di video:** posisi di-mirror dari kanan → kiri + sprite di-flip horizontal (`mirror` + `mirror_position` di config).

Konversi PNG → WebP: `python scripts/convert_to_webp.py`

Mapping: `config/characters.paknam-zaba.json`
