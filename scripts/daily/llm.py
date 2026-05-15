#!/usr/bin/env python3
"""Generate paper-summary & dialog via Anthropic (headless VPS)."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[2]


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


def load_schedule() -> dict:
    return json.loads((ROOT / "config" / "schedule.json").read_text(encoding="utf-8"))


def _read_paper_context(paper_dir: Path, max_chars: int = 48000) -> str:
    parts: list[str] = []
    meta = paper_dir / "metadata.json"
    if meta.exists():
        parts.append("=== metadata.json ===\n" + meta.read_text(encoding="utf-8")[:8000])
    abstract = paper_dir / "abstract.txt"
    if abstract.exists():
        parts.append("=== abstract.txt ===\n" + abstract.read_text(encoding="utf-8")[:6000])
    body = paper_dir / "paper.txt"
    if body.exists():
        text = body.read_text(encoding="utf-8", errors="replace")
        parts.append("=== paper.txt (potongan) ===\n" + text[:max_chars])
    return "\n\n".join(parts)


def _parse_json_response(text: str) -> dict[str, Any]:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    return json.loads(text)


def _anthropic_chat(system: str, user: str, model: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY kosong di .env")

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": 8192,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        },
        timeout=300,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Anthropic API {resp.status_code}: {resp.text[:500]}")
    data = resp.json()
    blocks = data.get("content", [])
    return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")


def _try_openclaw(message: str) -> bool:
    import shutil
    import subprocess

    if os.environ.get("PAPER2VIDEO_USE_OPENCLAW", "").lower() not in (
        "1",
        "true",
        "yes",
    ):
        return False
    if not shutil.which("openclaw"):
        return False
    try:
        subprocess.run(
            ["openclaw", "agent", "--message", message],
            cwd=ROOT,
            check=True,
            timeout=600,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def generate_paper_summary(paper_dir: Path) -> Path:
    out = paper_dir / "paper-summary.json"
    if out.exists() and os.environ.get("PAPER2VIDEO_FORCE_LLM") != "1":
        return out

    aid = paper_dir.name
    msg = f"Ekstrak paper {aid} ke paper-summary.json sesuai schemas/paper-summary.schema.json"
    if _try_openclaw(msg) and out.exists():
        return out

    load_dotenv()
    sched = load_schedule()
    model = sched.get("llm", {}).get("model", "claude-sonnet-4-20250514")
    ctx = _read_paper_context(paper_dir)

    system = (
        "Kamu asisten riset paper. Tulis HANYA JSON valid (tanpa markdown) "
        "sesuai schema paper-summary: arxiv_id, title, authors, published, "
        "categories, pdf_url, abstract, problem, method, main_findings, "
        "why_important, limitations, sources — semua narasi field dalam Bahasa Indonesia."
    )
    user = f"Buat paper-summary.json untuk folder {aid}.\n\n{ctx}"
    raw = _anthropic_chat(system, user, model)
    data = _parse_json_response(raw)
    data["arxiv_id"] = data.get("arxiv_id", aid.replace("_", "/"))
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def generate_dialog_script(paper_dir: Path) -> Path:
    out = paper_dir / "dialog-script.json"
    if out.exists() and os.environ.get("PAPER2VIDEO_FORCE_LLM") != "1":
        return out

    aid = paper_dir.name
    msg = f"Buat dialog Pak Nam dan Zaba untuk paper {aid} ke dialog-script.json"
    if _try_openclaw(msg) and out.exists():
        return out

    load_dotenv()
    sched = load_schedule()
    model = sched.get("llm", {}).get("model", "claude-sonnet-4-20250514")
    summary = (paper_dir / "paper-summary.json").read_text(encoding="utf-8")

    system = (
        "Kamu penulis naskah video edukasi. Zaba = pemula (bertanya), "
        "Pak Nam = mentor (jelas + analogi). Tulis HANYA JSON: arxiv_id, title, "
        "speakers {paknam, zaba}, turns[{speaker, text, expression}], "
        "estimated_duration_sec, notes. 8-14 giliran, Bahasa Indonesia, "
        "expression: neutral|laugh|thinking|confused."
    )
    user = f"Buat dialog-script dari paper-summary:\n\n{summary}"
    raw = _anthropic_chat(system, user, model)
    data = _parse_json_response(raw)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
