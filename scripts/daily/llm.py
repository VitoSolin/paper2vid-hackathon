#!/usr/bin/env python3
"""Generate paper-summary & dialog — Anthropic, OpenAI, atau DeepSeek."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[2]

DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-20250514",
    "openai": "gpt-4o-mini",
    "deepseek": "deepseek-chat",
    # OpenCode Zen / Go — key dari dashboard opencode.ai (bukan platform.deepseek.com)
    "opencode": "deepseek-v4-flash",
}

DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com",
    "opencode": "https://opencode.ai/zen/go/v1",
}


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


def resolve_llm_config() -> tuple[str, str, str, str]:
    """Return (provider, model, api_key, base_url)."""
    load_dotenv()
    sched = load_schedule()
    llm = sched.get("llm", {})
    provider = (
        os.environ.get("LLM_PROVIDER") or llm.get("provider") or "anthropic"
    ).lower().strip()

    if provider not in DEFAULT_MODELS:
        raise RuntimeError(
            f"LLM_PROVIDER tidak dikenal: {provider}. "
            f"Pilih: {', '.join(DEFAULT_MODELS.keys())}"
        )

    env_provider = os.environ.get("LLM_PROVIDER", "").lower().strip()
    sched_provider = (llm.get("provider") or "anthropic").lower()
    if os.environ.get("LLM_MODEL"):
        model = os.environ["LLM_MODEL"].strip()
    elif env_provider and env_provider != sched_provider:
        model = DEFAULT_MODELS[provider]
    else:
        model = llm.get("model") or DEFAULT_MODELS[provider]
    base_url = (
        os.environ.get("LLM_BASE_URL")
        or llm.get("base_url")
        or DEFAULT_BASE_URLS.get(provider, "")
    )

    if provider == "anthropic":
        api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY kosong di .env")
        return provider, model, api_key, ""

    if provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY kosong di .env")
        return provider, model, api_key, base_url or DEFAULT_BASE_URLS["openai"]

    if provider == "deepseek":
        api_key = (
            os.environ.get("DEEPSEEK_API_KEY", "").strip()
            or os.environ.get("OPENAI_API_KEY", "").strip()
        )
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY kosong di .env")
        return provider, model, api_key, base_url or DEFAULT_BASE_URLS["deepseek"]

    # opencode — key dari opencode.ai → API Keys (Zen / Go)
    api_key = (
        os.environ.get("OPENCODE_API_KEY", "").strip()
        or os.environ.get("DEEPSEEK_API_KEY", "").strip()
    )
    if not api_key:
        raise RuntimeError(
            "OPENCODE_API_KEY kosong — salin dari dashboard OpenCode → API Keys"
        )
    return provider, model, api_key, base_url or DEFAULT_BASE_URLS["opencode"]


def llm_configured() -> bool:
    """True jika ada provider LLM headless yang siap (tanpa OpenClaw)."""
    load_dotenv()
    if os.environ.get("PAPER2VIDEO_USE_OPENCLAW", "").lower() in ("1", "true", "yes"):
        import shutil

        if shutil.which("openclaw"):
            return True
    try:
        resolve_llm_config()
        return True
    except RuntimeError:
        return False


def _read_paper_context(paper_dir: Path, max_chars: int = 48000) -> str:
    """Konteks ekstraksi: RAG ringan jika paper.txt ada, else metadata+abstract."""
    if (paper_dir / "paper.txt").exists():
        sys.path.insert(0, str(ROOT / "scripts"))
        from agent.rag_context import build_rag_context

        ctx = build_rag_context(paper_dir, max_chars=max_chars)
        meta = paper_dir / "metadata.json"
        if meta.exists():
            head = "=== metadata.json ===\n" + meta.read_text(encoding="utf-8")[:8000]
            return head + "\n\n" + ctx
        return ctx

    parts: list[str] = []
    meta = paper_dir / "metadata.json"
    if meta.exists():
        parts.append("=== metadata.json ===\n" + meta.read_text(encoding="utf-8")[:8000])
    abstract = paper_dir / "abstract.txt"
    if abstract.exists():
        parts.append("=== abstract.txt ===\n" + abstract.read_text(encoding="utf-8")[:6000])
    return "\n\n".join(parts)


def _parse_json_response(text: str) -> dict[str, Any]:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    return json.loads(text)


def _anthropic_chat(system: str, user: str, model: str, api_key: str) -> str:
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


def _openai_compatible_chat(
    system: str,
    user: str,
    model: str,
    api_key: str,
    base_url: str,
    provider: str,
) -> str:
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload: dict[str, Any] = {
        "model": model,
        "max_tokens": 8192,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    # OpenAI / DeepSeek: minta JSON murni
    if provider in ("openai", "deepseek", "opencode"):
        payload["response_format"] = {"type": "json_object"}

    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "content-type": "application/json",
        },
        json=payload,
        timeout=300,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"{provider} API {resp.status_code}: {resp.text[:500]}")
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def llm_chat(system: str, user: str) -> str:
    provider, model, api_key, base_url = resolve_llm_config()
    if provider == "anthropic":
        return _anthropic_chat(system, user, model, api_key)
    return _openai_compatible_chat(system, user, model, api_key, base_url, provider)


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


def _agent_log(paper_dir: Path, **kwargs: Any) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from agent.log import log_step

    log_step(paper_dir, **kwargs)


def generate_paper_summary(paper_dir: Path, *, max_verify_retries: int = 2) -> Path:
    out = paper_dir / "paper-summary.json"
    if out.exists() and os.environ.get("PAPER2VIDEO_FORCE_LLM") != "1":
        return out

    aid = paper_dir.name
    arxiv_slash = aid.replace("_", "/")
    msg = (
        f"Orkestrasi paper {arxiv_slash}: ekstrak paper-summary, verifikasi (paper-verify), "
        f"lalu dialog jika belum ada."
    )
    if _try_openclaw(msg) and out.exists():
        _agent_log(
            paper_dir,
            agent="orchestrator",
            action="openclaw_pipeline",
            status="ok",
            detail={"via": "openclaw"},
        )
        return out

    load_dotenv()
    ctx = _read_paper_context(paper_dir)
    provider, model, _, _ = resolve_llm_config()
    print(f"  LLM [{provider}] {model} → paper-summary (+ verify loop)", flush=True)

    _agent_log(
        paper_dir,
        agent="extractor",
        action="start_extract",
        status="running",
        detail={"provider": provider, "model": model, "rag": (paper_dir / "paper.txt").exists()},
    )

    system = (
        "Kamu Agent Extractor — asisten riset paper. Tulis HANYA JSON valid (tanpa markdown) "
        "sesuai schema paper-summary: arxiv_id, title, authors, published, "
        "categories, pdf_url, abstract, problem, method, main_findings, "
        "why_important, limitations, sources — semua narasi field dalam Bahasa Indonesia. "
        "Jangan mengarang angka/eksperimen di luar sumber. "
        "sources.used_abstract true jika abstract dipakai; used_pdf true jika paper.txt dipakai."
    )
    user_base = f"Buat paper-summary.json untuk arxiv_id {arxiv_slash}.\n\n{ctx}"

    sys.path.insert(0, str(ROOT / "scripts"))
    from agent.verify_summary import verify_summary

    data: dict[str, Any] = {}
    last_verify: dict[str, Any] = {"ok": False, "issues": []}
    for attempt in range(max_verify_retries + 1):
        user = user_base
        if attempt > 0:
            issues = last_verify.get("issues", [])
            user += (
                "\n\n=== PERBAIKAN (Agent Verifier) ===\n"
                "Percobaan sebelumnya gagal QA. Perbaiki HANYA field bermasalah:\n"
                + "\n".join(f"- {i}" for i in issues)
            )
            print(f"  ↻ retry ekstraksi ({attempt}/{max_verify_retries})…", flush=True)

        raw = llm_chat(system, user)
        data = _parse_json_response(raw)
        data["arxiv_id"] = data.get("arxiv_id", arxiv_slash)
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

        last_verify = verify_summary(data, paper_dir)
        _agent_log(
            paper_dir,
            agent="verifier",
            action="verify_summary",
            status="ok" if last_verify["ok"] else "fail",
            detail={"attempt": attempt + 1, **last_verify},
        )
        if last_verify["ok"]:
            print(f"  ✓ verify OK (score={last_verify['score']:.2f})", flush=True)
            break
        if attempt >= max_verify_retries:
            print(
                f"  ⚠ verify masih gagal — lanjut pipeline: {last_verify['issues']}",
                flush=True,
            )
        else:
            print(f"  ✗ verify: {last_verify['issues']}", flush=True)

    _agent_log(
        paper_dir,
        agent="extractor",
        action="finish_extract",
        status="ok",
        detail={"arxiv_id": data.get("arxiv_id", arxiv_slash)},
    )
    return out


def generate_dialog_script(paper_dir: Path) -> Path:
    out = paper_dir / "dialog-script.json"
    if out.exists() and os.environ.get("PAPER2VIDEO_FORCE_LLM") != "1":
        return out

    aid = paper_dir.name
    msg = f"Buat dialog Pak Nam dan Zaba untuk paper {aid} ke dialog-script.json"
    if _try_openclaw(msg) and out.exists():
        _agent_log(
            paper_dir,
            agent="writer",
            action="dialog_via_openclaw",
            status="ok",
        )
        return out

    load_dotenv()
    summary = (paper_dir / "paper-summary.json").read_text(encoding="utf-8")
    provider, model, _, _ = resolve_llm_config()
    print(f"  LLM [{provider}] {model} → dialog-script", flush=True)

    _agent_log(
        paper_dir,
        agent="writer",
        action="start_dialog",
        status="running",
        detail={"provider": provider, "model": model},
    )

    system = (
        "Kamu Agent Writer — penulis naskah video edukasi. Zaba = pemula (bertanya), "
        "Pak Nam = mentor (jelas + analogi). Tulis HANYA JSON: arxiv_id, title, "
        "speakers {paknam, zaba}, turns[{speaker, text, expression}], "
        "estimated_duration_sec, notes. 8-14 giliran, Bahasa Indonesia, "
        "expression: neutral|laugh|thinking|confused. "
        "Jangan tambahkan klaim di luar paper-summary."
    )
    user = f"Buat dialog-script dari paper-summary:\n\n{summary}"
    raw = llm_chat(system, user)
    data = _parse_json_response(raw)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    turns = len(data.get("turns") or [])
    _agent_log(
        paper_dir,
        agent="writer",
        action="finish_dialog",
        status="ok" if turns >= 6 else "warn",
        detail={"turns": turns},
    )
    return out
