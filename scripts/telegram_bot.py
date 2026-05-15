#!/usr/bin/env python3
"""
Bot Telegram — trigger pipeline e2e paper2video dari HP.

Env:
  TELEGRAM_BOT_TOKEN
  TELEGRAM_ALLOWED_CHAT_IDS=123456789,987654321  (kosong = tolak semua)

Jalankan:
  python scripts/telegram_bot.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
JOBS_DIR = ROOT / "data" / ".schedule" / "telegram_jobs"

sys.path.insert(0, str(ROOT / "scripts"))
from fetch_arxiv import normalize_arxiv_id  # noqa: E402

try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes
except ImportError as e:
    raise SystemExit(
        "Install: pip install python-telegram-bot\n" f"({e})"
    ) from e

_running: set[int] = set()


def load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def allowed_chat_ids() -> set[int]:
    raw = os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS", "").strip()
    if not raw:
        return set()
    out: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part:
            out.add(int(part))
    return out


def is_allowed(update: Update) -> bool:
    allowed = allowed_chat_ids()
    if not allowed:
        return False
    chat = update.effective_chat
    return chat is not None and chat.id in allowed


async def deny(update: Update) -> None:
    chat = update.effective_chat
    if not chat:
        return
    allowed = allowed_chat_ids()
    if not allowed:
        await update.effective_message.reply_text(
            "Bot belum dikonfigurasi. Set TELEGRAM_ALLOWED_CHAT_IDS di .env "
            "lalu kirim /whoami untuk dapat Chat ID Anda."
        )
    else:
        await update.effective_message.reply_text(
            f"Akses ditolak. Chat ID Anda: {chat.id}\n"
            "Tambahkan ke TELEGRAM_ALLOWED_CHAT_IDS di .env"
        )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        await deny(update)
        return
    await update.effective_message.reply_text(
        "🎬 *paper2video bot*\n\n"
        "Perintah:\n"
        "• `/e2e 1706.03762` — pipeline penuh (fetch→LLM→video)\n"
        "• `/e2e 1706.03762 upload` — + YouTube\n"
        "• `/e2e latest` — paper terbaru (RSS)\n"
        "• `/status` — job terakhir\n"
        "• `/whoami` — Chat ID Anda",
        parse_mode="Markdown",
    )


async def cmd_whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if not chat:
        return
    await update.effective_message.reply_text(
        f"Chat ID: `{chat.id}`\nUser: {update.effective_user.full_name if update.effective_user else '?'}",
        parse_mode="Markdown",
    )


def _parse_e2e_args(args: list[str]) -> tuple[str | None, bool, bool, bool]:
    """Return (arxiv_id|None, upload, latest, force_llm)."""
    upload = False
    latest = False
    force_llm = False
    arxiv_id = None
    for a in args:
        low = a.lower()
        if low in ("upload", "--upload"):
            upload = True
        elif low in ("latest", "--latest"):
            latest = True
        elif low in ("force", "--force-llm", "force-llm"):
            force_llm = True
        elif not a.startswith("-"):
            arxiv_id = normalize_arxiv_id(a)
    return arxiv_id, upload, latest, force_llm


async def _run_e2e_job(
    chat_id: int,
    bot,
    *,
    arxiv_id: str | None,
    upload: bool,
    latest: bool,
    force_llm: bool,
) -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    label = arxiv_id or "latest"
    log_path = LOGS / f"telegram_e2e_{label}_{ts}.log"

    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_e2e.py"),
    ]
    if latest:
        cmd.append("--latest")
    elif arxiv_id:
        cmd.append(arxiv_id)
    if upload:
        cmd.append("--upload")
        cmd.append("--privacy")
        cmd.append(os.environ.get("YOUTUBE_PRIVACY_DEFAULT", "public"))
    if force_llm:
        cmd.append("--force-llm")

    await bot.send_message(
        chat_id,
        f"▶️ Memulai e2e `{label}`\nLog: `{log_path.relative_to(ROOT)}`\n"
        "Proses bisa 15–40 menit. Saya kabari saat selesai.",
        parse_mode="Markdown",
    )

    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    try:
        with open(log_path, "w", encoding="utf-8") as logf:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(ROOT),
                env=env,
                stdout=logf,
                stderr=asyncio.subprocess.STDOUT,
            )
            code = await proc.wait()
    except Exception as e:
        await bot.send_message(chat_id, f"❌ Gagal menjalankan job: {e}")
        return
    finally:
        _running.discard(chat_id)

    tail = ""
    if log_path.exists():
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        tail = "\n".join(lines[-25:])

    if code == 0:
        msg = f"✅ e2e selesai: `{label}`"
        out = ROOT / "output" / f"{label.replace('/', '_')}.mp4"
        if latest and code == 0:
            msg += "\n(Cek folder output/ untuk file terbaru)"
        elif out.exists():
            msg += f"\n📁 `{out.relative_to(ROOT)}`"
        pub = ROOT / "data" / label.replace("/", "_") / "youtube-publish.json"
        if pub.exists():
            import json

            data = json.loads(pub.read_text(encoding="utf-8"))
            if data.get("url"):
                msg += f"\n📺 {data['url']}"
    else:
        msg = f"❌ e2e gagal (exit {code}): `{label}`"

    if tail:
        snippet = tail[-3000:]
        if len(msg) + len(snippet) < 4000:
            msg += f"\n\n{snippet}"
        else:
            msg += f"\n\n(log penuh: {log_path.name})"

    try:
        await bot.send_message(chat_id, msg, parse_mode="Markdown")
    except Exception:
        await bot.send_message(chat_id, msg[:4000])


async def cmd_e2e(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        await deny(update)
        return
    chat = update.effective_chat
    if not chat:
        return

    if chat.id in _running:
        await update.effective_message.reply_text(
            "Masih ada job berjalan. Tunggu selesai atau cek /status"
        )
        return

    args = context.args or []
    arxiv_id, upload, latest, force_llm = _parse_e2e_args(args)
    if not latest and not arxiv_id:
        await update.effective_message.reply_text(
            "Format: `/e2e 1706.03762` atau `/e2e latest` atau `/e2e 1706.03762 upload`",
            parse_mode="Markdown",
        )
        return

    _running.add(chat.id)
    asyncio.create_task(
        _run_e2e_job(
            chat.id,
            context.bot,
            arxiv_id=arxiv_id,
            upload=upload,
            latest=latest,
            force_llm=force_llm,
        )
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        await deny(update)
        return
    chat = update.effective_chat
    if not chat:
        return
    if chat.id in _running:
        await update.effective_message.reply_text("⏳ Job e2e sedang berjalan…")
        return
    logs = sorted(LOGS.glob("telegram_e2e_*.log"), key=lambda p: p.stat().st_mtime)
    if not logs:
        await update.effective_message.reply_text("Belum ada job dari Telegram.")
        return
    last = logs[-1]
    lines = last.read_text(encoding="utf-8", errors="replace").splitlines()
    tail = "\n".join(lines[-15:])
    await update.effective_message.reply_text(
        f"Log terakhir: `{last.name}`\n\n```\n{tail}\n```",
        parse_mode="Markdown",
    )


def main() -> None:
    load_dotenv()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN di .env")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))
    app.add_handler(CommandHandler("whoami", cmd_whoami))
    app.add_handler(CommandHandler("e2e", cmd_e2e))
    app.add_handler(CommandHandler("status", cmd_status))

    print("paper2video Telegram bot — polling…", flush=True)
    if not allowed_chat_ids():
        print(
            "PERINGATAN: TELEGRAM_ALLOWED_CHAT_IDS kosong — semua akses ditolak.",
            flush=True,
        )
    else:
        print(f"Allowed chats: {allowed_chat_ids()}", flush=True)

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
