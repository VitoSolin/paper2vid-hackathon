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
import json
import os
import re
import sys
import time
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

# Baris log yang dikirim ke chat (progress live)
_PROGRESS_LINE = re.compile(
    r"(\[[A-F]/\d+\].*)|"  # langkah A–F
    r"(Discover via .+)|"
    r"(Memindai \d+ kandidat)|"
    r"(✓ Memilih .+)|"
    r"(⚠ Tidak ada paper baru)|"
    r"(Paper: .+)|"
    r"(  ✓ .+)|"
    r"(  ✗ .+)|"
    r"(  ⚠ .+)|"
    r"(  ↻ .+)|"
    r"(LLM \[.+→.+)|"
    r"(  \(OpenCode LLM)|"
    r"(SELESAI —)"
)


_PAPER_LINE = re.compile(r"^Paper:\s*(\S+)")
_PICKED_LINE = re.compile(r"✓ Memilih \d+ paper:\s*([^,\s]+)")


def _paper_data_dir(arxiv_id: str) -> Path:
    return ROOT / "data" / arxiv_id.replace("/", "_")


def _format_dialog_preview(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    parts: list[str] = []
    title = data.get("title") or data.get("arxiv_id", "")
    if title:
        parts.append(f"📄 {title}")
    speakers = data.get("speakers") or {}
    for i, turn in enumerate(data.get("turns") or [], 1):
        sp = (turn.get("speaker") or "?").lower()
        name = speakers.get(sp) or ("Pak Nam" if sp == "paknam" else "Zaba" if sp == "zaba" else sp)
        text = (turn.get("text") or "").strip()
        parts.append(f"{i}. {name}: {text}")
    est = data.get("estimated_duration_sec")
    if est:
        parts.append(f"\n⏱ ~{int(est)} detik")
    return "\n\n".join(parts)


async def _send_dialog_to_chat(bot, chat_id: int, arxiv_id: str) -> None:
    path = _paper_data_dir(arxiv_id) / "dialog-script.json"
    if not path.exists():
        return
    preview = _format_dialog_preview(path)
    header = f"📝 Naskah dialog — {arxiv_id}\n\n"
    if len(header) + len(preview) <= 4000:
        await bot.send_message(chat_id, header + preview)
    else:
        await bot.send_message(
            chat_id,
            f"📝 Naskah dialog — {arxiv_id} ({data_turns(path)} giliran). "
            "Pratinjau panjang; file JSON dilampirkan.",
        )
    with path.open("rb") as f:
        await bot.send_document(
            chat_id,
            document=f,
            filename=f"dialog-{arxiv_id.replace('/', '_')}.json",
            caption="dialog-script.json",
        )


def data_turns(path: Path) -> int:
    try:
        return len(json.loads(path.read_text(encoding="utf-8")).get("turns") or [])
    except Exception:
        return 0


async def _send_video_to_chat(bot, chat_id: int, arxiv_id: str) -> None:
    mp4 = ROOT / "output" / f"{arxiv_id.replace('/', '_')}.mp4"
    if not mp4.exists():
        await bot.send_message(
            chat_id, f"⚠ Video tidak ditemukan: `{mp4.name}`", parse_mode="Markdown"
        )
        return
    size_mb = mp4.stat().st_size / (1024 * 1024)
    if size_mb > 48:
        await bot.send_message(
            chat_id,
            f"🎬 Video selesai (`{mp4.name}`, {size_mb:.1f} MB) — "
            "terlalu besar untuk dikirim via Telegram. Ambil dari server/VPS.",
            parse_mode="Markdown",
        )
        return
    await bot.send_message(chat_id, f"🎬 Mengunggah video… ({size_mb:.1f} MB)")
    with mp4.open("rb") as f:
        await bot.send_video(
            chat_id,
            video=f,
            supports_streaming=True,
            caption=f"{arxiv_id} — paper2video",
            read_timeout=300,
            write_timeout=300,
        )


def _line_for_telegram(line: str) -> str | None:
    line = line.strip()
    if not line or line.startswith("→ python"):
        return None
    if _PROGRESS_LINE.search(line):
        return line[:500]
    if line.startswith("=" * 10):
        return None
    return None


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
        "• Saat selesai: naskah dialog + file video dikirim ke chat\n"
        "• `/status` — cuplikan log job (jalan atau selesai)\n"
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

    mode = []
    if latest:
        mode.append("RSS")
    if force_llm:
        mode.append("force-llm")
    if upload:
        mode.append(f"upload→{os.environ.get('YOUTUBE_PRIVACY_DEFAULT', 'public')}")
    mode_s = f" ({', '.join(mode)})" if mode else ""

    await bot.send_message(
        chat_id,
        f"▶️ Pipeline: {label}{mode_s}\n"
        "Progress + naskah dialog + video akan dikirim ke chat ini.",
    )

    resolved_aid: str | None = None if latest else arxiv_id
    dialog_sent = False

    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    last_push = 0.0
    try:
        with open(log_path, "w", encoding="utf-8") as logf:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(ROOT),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            assert proc.stdout is not None
            while True:
                raw = await proc.stdout.readline()
                if not raw:
                    break
                text = raw.decode("utf-8", errors="replace")
                logf.write(text)
                logf.flush()
                for line in text.splitlines():
                    m = _PAPER_LINE.match(line.strip())
                    if m:
                        resolved_aid = normalize_arxiv_id(m.group(1))
                    m = _PICKED_LINE.search(line)
                    if m and not resolved_aid:
                        resolved_aid = normalize_arxiv_id(m.group(1))

                    if (
                        not dialog_sent
                        and resolved_aid
                        and "dialog-script.json" in line
                        and "✓" in line
                    ):
                        dialog_sent = True
                        try:
                            await _send_dialog_to_chat(bot, chat_id, resolved_aid)
                        except Exception as e:
                            await bot.send_message(
                                chat_id, f"⚠ Gagal kirim naskah: {e}"
                            )

                    msg = _line_for_telegram(line)
                    if not msg:
                        continue
                    now = time.monotonic()
                    if now - last_push < 1.5 and not msg.startswith("["):
                        continue
                    last_push = now
                    try:
                        await bot.send_message(chat_id, f"▸ {label}\n{msg}")
                    except Exception:
                        pass
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

    # Fallback: cari paper ID dari log jika latest
    if not resolved_aid and log_path.exists():
        for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
            m = _PAPER_LINE.match(line.strip())
            if m:
                resolved_aid = normalize_arxiv_id(m.group(1))
                break
            m = _PICKED_LINE.search(line)
            if m:
                resolved_aid = normalize_arxiv_id(m.group(1))
                break

    final_aid = resolved_aid or label

    if code == 0:
        msg = f"✅ e2e selesai: `{final_aid}`"
        if resolved_aid and not dialog_sent:
            try:
                await _send_dialog_to_chat(bot, chat_id, resolved_aid)
            except Exception:
                pass
        pub = _paper_data_dir(final_aid) / "youtube-publish.json"
        if pub.exists():
            data = json.loads(pub.read_text(encoding="utf-8"))
            if data.get("url"):
                msg += f"\n📺 {data['url']}"
        try:
            await bot.send_message(chat_id, msg, parse_mode="Markdown")
        except Exception:
            await bot.send_message(chat_id, msg[:4000])
        if resolved_aid:
            try:
                await _send_video_to_chat(bot, chat_id, resolved_aid)
            except Exception as e:
                await bot.send_message(chat_id, f"⚠ Gagal kirim video: {e}")
    else:
        msg = f"❌ e2e gagal (exit {code}): `{final_aid}`"
        if tail:
            snippet = tail[-3000:]
            if len(msg) + len(snippet) < 4000:
                msg += f"\n\n{snippet}"
            else:
                msg += f"\n\n(log: {log_path.name})"
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

    flags = []
    if latest:
        flags.append("latest")
    if force_llm:
        flags.append("force")
    if upload:
        flags.append("upload")
    target = arxiv_id or "paper terbaru (RSS)"
    await update.effective_message.reply_text(
        f"✓ Perintah diterima: {target}"
        + (f" [{', '.join(flags)}]" if flags else "")
        + "\nJob dimulai…"
    )

    async def _job_wrapper() -> None:
        try:
            await _run_e2e_job(
                chat.id,
                context.bot,
                arxiv_id=arxiv_id,
                upload=upload,
                latest=latest,
                force_llm=force_llm,
            )
        except Exception as e:
            _running.discard(chat.id)
            try:
                await context.bot.send_message(
                    chat.id, f"❌ Error bot: {e}"
                )
            except Exception:
                pass
            raise

    _running.add(chat.id)
    asyncio.create_task(_job_wrapper())


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
