#!/usr/bin/env python3
"""
Pipeline end-to-end satu paper dengan progress jelas (showcase / demo).

Langkah:
  A — Preflight (ffmpeg, API key, OAuth)
  B — Fetch arXiv + ekstrak PDF
  C — Ringkasan paper (LLM)
  D — Naskah dialog Pak Nam & Zaba (LLM)
  E — Render video 9:16 + TTS
  F — Upload YouTube (opsional)
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "daily"))
sys.path.insert(0, str(ROOT / "scripts" / "youtube"))

from llm import (  # noqa: E402
    generate_dialog_script,
    generate_paper_summary,
    llm_configured,
    load_dotenv,
    resolve_llm_config,
)
from fetch_arxiv import normalize_arxiv_id, paper_dir  # noqa: E402


def _step(label: str, letter: str, total: int, idx: int) -> None:
    print(f"\n{'=' * 60}", flush=True)
    print(f"  [{letter}/{total}] {label}", flush=True)
    print(f"{'=' * 60}\n", flush=True)


def _ok(msg: str) -> None:
    print(f"  ✓ {msg}", flush=True)


def _warn(msg: str) -> None:
    print(f"  ⚠ {msg}", flush=True)


def _fail(msg: str) -> None:
    print(f"  ✗ {msg}", flush=True)
    raise SystemExit(msg)


def preflight(*, need_youtube: bool) -> None:
    load_dotenv()
    if not shutil.which("ffmpeg"):
        _fail("ffmpeg tidak ditemukan di PATH")
    _ok("ffmpeg")

    use_openclaw = os.environ.get("PAPER2VIDEO_USE_OPENCLAW", "").lower() in (
        "1",
        "true",
        "yes",
    )
    if use_openclaw and shutil.which("openclaw"):
        _ok("LLM via OpenClaw (PAPER2VIDEO_USE_OPENCLAW=1)")
    elif llm_configured():
        provider, model, _, _ = resolve_llm_config()
        _ok(f"LLM [{provider}] model={model}")
    else:
        _fail(
            "Butuh LLM: set LLM_PROVIDER + API key (anthropic/openai/deepseek) "
            "di .env — lihat docs/LLM.md — atau PAPER2VIDEO_USE_OPENCLAW=1"
        )

    tts = os.environ.get("TTS_PROVIDER", "edge").lower()
    if tts == "elevenlabs":
        if os.environ.get("ELEVENLABS_API_KEY", "").strip():
            _ok("ElevenLabs TTS")
        else:
            _warn("ELEVENLABS_API_KEY kosong — set TTS_PROVIDER=edge di .env")
    else:
        _ok("TTS edge-tts (gratis)")

    if need_youtube:
        secret = ROOT / "config" / "youtube" / "client_secret.json"
        token = ROOT / "config" / "youtube" / "token.json"
        if not secret.exists():
            _fail(f"OAuth hilang: {secret} — lihat docs/YOUTUBE.md")
        if not token.exists():
            _fail("Jalankan dulu: python scripts/youtube/auth.py")
        _ok("YouTube OAuth token")


def run_cmd(cmd: list[str]) -> None:
    print(f"  → {' '.join(cmd)}\n", flush=True)
    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    subprocess.run(cmd, check=True, cwd=ROOT, env=env)


def resolve_arxiv_id(arg: str | None, latest: bool) -> str:
    if arg:
        return normalize_arxiv_id(arg)
    if latest:
        from fetch_latest import fetch_candidate_ids  # noqa: E402

        ids = fetch_candidate_ids(1)
        if not ids:
            _fail("Tidak ada paper baru dari arXiv (rate limit atau semua sudah diproses)")
        return normalize_arxiv_id(ids[0])
    _fail("Berikan ARXIV_ID atau --latest")


def run_e2e(
    arxiv_id: str,
    *,
    upload: bool = False,
    privacy: str | None = None,
    force_llm: bool = False,
    refetch: bool = False,
) -> Path:
    total = 6 if upload else 5
    t0 = time.time()
    arxiv_id = normalize_arxiv_id(arxiv_id)
    aid = arxiv_id.replace("/", "_")

    if force_llm:
        os.environ["PAPER2VIDEO_FORCE_LLM"] = "1"

    # A — Preflight
    _step("Preflight — cek dependensi & API key", "A", total, 1)
    preflight(need_youtube=upload)

    py = sys.executable
    pdir = paper_dir(arxiv_id)
    out_mp4 = ROOT / "output" / f"{aid}.mp4"

    # B — Fetch
    _step(f"Fetch arXiv + ekstrak PDF — {arxiv_id}", "B", total, 2)
    if pdir.joinpath("paper.txt").exists() and not refetch:
        _ok("Lewati fetch — paper.txt sudah ada (pakai --refetch untuk unduh ulang)")
    else:
        cmd = [py, str(ROOT / "scripts" / "run_pipeline.py"), arxiv_id]
        if refetch:
            cmd.append("--force")
        run_cmd(cmd)
        _ok(f"Data di {pdir.relative_to(ROOT)}/")

    # C — Summary
    _step("Ringkasan paper (problem, metode, temuan…)", "C", total, 3)
    print("  (OpenCode LLM, ~30–120 detik…)\n", flush=True)
    generate_paper_summary(pdir)
    _ok("paper-summary.json")
    log_path = pdir / "agent-run.jsonl"
    if log_path.exists():
        _ok(f"agent audit: {log_path.relative_to(ROOT)}")

    # D — Dialog
    _step("Naskah dialog Pak Nam & Zaba", "D", total, 4)
    print("  (OpenCode LLM, ~30–120 detik…)\n", flush=True)
    generate_dialog_script(pdir)
    _ok("dialog-script.json")

    # E — Render
    _step("Render video 1080×1920 + TTS", "E", total, 5)
    run_cmd(
        [
            py,
            str(ROOT / "scripts" / "video" / "render.py"),
            str(pdir),
            "--config",
            str(ROOT / "config" / "characters.paknam-zaba.json"),
        ]
    )
    if not out_mp4.exists():
        _fail(f"Video tidak ada: {out_mp4}")
    _ok(str(out_mp4.relative_to(ROOT)))

    # F — YouTube
    if upload:
        _step("Upload ke YouTube", "F", total, 6)
        from upload import publish_paper  # noqa: E402

        result = publish_paper(pdir, privacy=privacy)
        _ok(result["url"])

    elapsed = int(time.time() - t0)
    print(f"\n{'=' * 60}", flush=True)
    print(f"  SELESAI — {elapsed // 60}m {elapsed % 60}s", flush=True)
    print(f"  Video: {out_mp4}", flush=True)
    if upload:
        print(f"  YouTube: {result['url']}", flush=True)
    print(f"{'=' * 60}\n", flush=True)
    return out_mp4


def main() -> None:
    parser = argparse.ArgumentParser(
        description="E2E showcase: arXiv → video (+ YouTube opsional)"
    )
    parser.add_argument(
        "arxiv_id",
        nargs="?",
        help="ID arXiv, mis. 1706.03762",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Ambil 1 paper terbaru dari arXiv (bukan di state VPS)",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Langkah F: upload YouTube setelah render",
    )
    parser.add_argument(
        "--privacy",
        choices=["public", "unlisted", "private"],
        help="Privacy YouTube (default dari .env)",
    )
    parser.add_argument(
        "--force-llm",
        action="store_true",
        help="Regenerate paper-summary & dialog meski sudah ada",
    )
    parser.add_argument(
        "--refetch",
        action="store_true",
        help="Paksa fetch arXiv ulang (tanpa ini, lewati jika paper.txt ada)",
    )
    args = parser.parse_args()

    try:
        arxiv_id = resolve_arxiv_id(args.arxiv_id, args.latest)
        print(f"Paper: {arxiv_id}\n", flush=True)
        run_e2e(
            arxiv_id,
            upload=args.upload,
            privacy=args.privacy,
            force_llm=args.force_llm,
            refetch=args.refetch,
        )
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"Perintah gagal (exit {e.returncode})") from e
    except KeyboardInterrupt:
        raise SystemExit("Dibatalkan user") from None
    except Exception as e:
        raise SystemExit(str(e)) from e


if __name__ == "__main__":
    main()
