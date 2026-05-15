---
name: telegram-trigger
description: Trigger pipeline e2e paper2video via bot Telegram
metadata: {"openclaw":{"emoji":"📱","requires":{"bins":["python3"]}}}
---

# telegram-trigger

Jalankan bot yang mendengarkan perintah Telegram untuk memicu `run_e2e.py`.

## Setup

Lihat `docs/TELEGRAM.md`:

1. Token dari [@BotFather](https://t.me/BotFather) → `TELEGRAM_BOT_TOKEN`
2. `/whoami` → `TELEGRAM_ALLOWED_CHAT_IDS`
3. `python scripts/telegram_bot.py`

## Perintah user

- `/e2e <ARXIV_ID>` — pipeline penuh
- `/e2e <ARXIV_ID> upload` — + YouTube
- `/e2e latest` — paper terbaru

Bot berjalan terpisah dari OpenClaw gateway (proses polling sendiri).
