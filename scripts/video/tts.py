#!/usr/bin/env python3
"""TTS per giliran: edge-tts (gratis) atau ElevenLabs (natural)."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

import edge_tts
import requests

ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def _speaker_tts_entry(cfg: dict[str, Any], speaker: str) -> dict[str, Any]:
    tts = cfg.get("tts", {})
    entry = dict(tts.get(speaker, {}) if isinstance(tts.get(speaker), dict) else {})
    entry.setdefault("provider", tts.get("provider", "edge"))
    entry.setdefault("model_id", tts.get("model_id", "eleven_multilingual_v2"))
    return entry


async def _edge_synthesize(text: str, voice: str, out_path: Path, rate: str = "+0%") -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(text.strip(), voice, rate=rate)
    await communicate.save(str(out_path))
    return out_path


def _elevenlabs_synthesize(
    text: str,
    voice_id: str,
    out_path: Path,
    *,
    api_key: str,
    model_id: str = "eleven_multilingual_v2",
    stability: float = 0.45,
    similarity_boost: float = 0.8,
    style: float = 0.35,
) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload: dict[str, Any] = {
        "text": text.strip(),
        "model_id": model_id,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
        },
    }
    if style:
        payload["voice_settings"]["style"] = style

    resp = requests.post(
        url,
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        json=payload,
        timeout=120,
    )
    if resp.status_code in (401, 402):
        try:
            detail = resp.json().get("detail", {})
            if detail.get("status") == "quota_exceeded":
                raise RuntimeError(
                    "ElevenLabs: kuota/kredit habis. "
                    f"{detail.get('message', '')} "
                    "Cek https://elevenlabs.io/app/usage — atau TTS_PROVIDER=edge di .env"
                )
        except (ValueError, AttributeError):
            pass
        if resp.status_code == 401:
            raise RuntimeError("ElevenLabs API key invalid — cek ELEVENLABS_API_KEY di .env")
        raise RuntimeError(
            "ElevenLabs: billing diperlukan (402). "
            "Cek https://elevenlabs.io/app/subscription"
        )
    if resp.status_code == 404:
        raise RuntimeError(
            f"Voice ID tidak ditemukan ({voice_id}). "
            "Tambahkan voice ke akun Anda di Voice Library → Add to My Voices."
        )
    resp.raise_for_status()
    out_path.write_bytes(resp.content)
    return out_path


def synthesize_sync(
    text: str,
    out_path: Path,
    *,
    speaker: str,
    cfg: dict[str, Any] | None = None,
    voice: str | None = None,
    rate: str = "+0%",
) -> Path:
    """Generate audio. Pakai entry tts per speaker di config, atau override voice/rate (edge)."""
    _load_dotenv()
    entry = _speaker_tts_entry(cfg or {}, speaker)
    provider = os.environ.get("TTS_PROVIDER", entry.get("provider", "edge")).lower()
    api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if provider == "elevenlabs" and not api_key:
        print("⚠ ELEVENLABS_API_KEY kosong — fallback ke edge-tts", file=__import__("sys").stderr)
        provider = "edge"

    if provider == "elevenlabs":
        voice_id = entry.get("voice_id") or voice
        if not voice_id:
            raise RuntimeError(f"voice_id ElevenLabs belum diset untuk speaker '{speaker}'")
        return _elevenlabs_synthesize(
            text,
            voice_id,
            out_path,
            api_key=api_key,
            model_id=entry.get("model_id", "eleven_multilingual_v2"),
            stability=float(entry.get("stability", 0.45)),
            similarity_boost=float(entry.get("similarity_boost", 0.8)),
            style=float(entry.get("style", 0.35)),
        )

    edge_voice = voice or entry.get("voice", "id-ID-ArdiNeural")
    edge_rate = entry.get("rate", rate)
    return asyncio.run(_edge_synthesize(text, edge_voice, out_path, rate=edge_rate))
