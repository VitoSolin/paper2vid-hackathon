# Setup ElevenLabs untuk Pak Nam & Zaba

## Yang perlu Anda siapkan

### 1. Akun ElevenLabs
Daftar di [elevenlabs.io](https://elevenlabs.io) (ada free tier dengan kuota karakter/bulan).

### 2. API key
1. Buka [API Keys](https://elevenlabs.io/app/settings/api-keys)
2. **Create API key** → salin (hanya muncul sekali)

### 3. Voice di akun Anda
Voice dari link Voice Library harus bisa dipakai API:

| Karakter | Voice ID | Link |
|----------|----------|------|
| Pak Nam | `aK834gEOxQEtviMPgurT` | [Voice Library](https://elevenlabs.io/app/voice-library?voiceId=aK834gEOxQEtviMPgurT) |
| Zaba | `JaUVfDrFcfwGIsv8X2kN` | [Voice Library](https://elevenlabs.io/app/voice-library?voiceId=JaUVfDrFcfwGIsv8X2kN) |

Di halaman masing-masing voice, klik **Add to My Voices** (jika belum ada di akun Anda). Tanpa ini API bisa error 404.

### 4. File `.env` di root proyek

```bash
cp .env.example .env
```

Edit `.env`:

```env
ELEVENLABS_API_KEY=sk_...
TTS_PROVIDER=elevenlabs
```

### 5. Regenerate audio & video

```bash
rm -rf data/1706.03762/audio
python scripts/video/render.py data/1706.03762
```

## Model yang dipakai

Default: `eleven_multilingual_v2` — bagus untuk Bahasa Indonesia.

Alternatif di `.env` atau `config/characters.paknam-zaba.json`:

| Model | Kapan dipakai |
|-------|----------------|
| `eleven_multilingual_v2` | Stabil, multilingual (default) |
| `eleven_turbo_v2_5` | Lebih cepat, sedikit lebih murah |
| `eleven_v3` | Ekspresif/dramatis (coba jika dialog terasa datar) |

## Kembali ke edge-tts (gratis)

```env
TTS_PROVIDER=edge
```

## Perkiraan biaya

ElevenLabs menagih per **karakter** teks. Satu video ~12 giliran × ~100 karakter ≈ 1.200 karakter. Cek kuota di dashboard.

## Troubleshooting

| Error | Solusi |
|-------|--------|
| `401` | API key salah / expired |
| `404` voice | Add voice ke **My Voices** |
| Quota exceeded | Upgrade plan atau tunggu reset bulanan |
| Masih robot | Coba `eleven_v3` atau naikkan `style` di config |
