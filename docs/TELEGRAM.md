# Bot Telegram — trigger e2e

Jalankan pipeline **dari Telegram** (HP / desktop).

## 1. Buat bot (BotFather)

1. Buka [@BotFather](https://t.me/BotFather) di Telegram
2. `/newbot` → nama + username bot
3. Salin **token** → `.env`:

```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdef...
```

## 2. Dapatkan Chat ID

```bash
# Isi token dulu, allowed kosongkan sementara
python scripts/telegram_bot.py
```

Di Telegram, kirim ke bot Anda: `/whoami`  
Salin angka Chat ID → `.env`:

```bash
TELEGRAM_ALLOWED_CHAT_IDS=123456789
```

Beberapa user: pisah koma `111,222`

## 3. Jalankan bot

Lokal:

```bash
source .venv/bin/activate
pip install python-telegram-bot
python scripts/telegram_bot.py
```

VPS (background):

```bash
nohup python scripts/telegram_bot.py >> logs/telegram-bot.log 2>&1 &
```

Atau pakai systemd: `deploy/vps/paper2video-telegram.service`

## Perintah bot

| Perintah | Fungsi |
|----------|--------|
| `/start` | Bantuan |
| `/whoami` | Tampilkan Chat ID |
| `/e2e 1706.03762` | Pipeline penuh A→E |
| `/e2e 1706.03762 upload` | + upload YouTube |
| `/e2e latest` | Paper terbaru (RSS) |
| `/e2e 1706.03762 force` | Regenerate LLM |
| `/status` | Log job terakhir |

Satu job per chat pada satu waktu. Durasi ~15–40 menit.

## Keamanan

- Hanya `TELEGRAM_ALLOWED_CHAT_IDS` yang bisa memicu job
- Jangan commit token ke Git (sudah di `.gitignore` via `.env`)

## VPS + cron

Bot Telegram dan cron pagi bisa jalan bersamaan. Hindari `/e2e` saat jam 07:00–08:00 jika cron morning job aktif (beban berat).
