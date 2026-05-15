#!/usr/bin/env python3
"""TTS per giliran dialog (edge-tts, gratis, mendukung Bahasa Indonesia)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import edge_tts


async def synthesize(
    text: str,
    voice: str,
    out_path: Path,
    rate: str = "+0%",
) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(text.strip(), voice, rate=rate)
    await communicate.save(str(out_path))
    return out_path


def synthesize_sync(
    text: str,
    voice: str,
    out_path: Path,
    rate: str = "+0%",
) -> Path:
    return asyncio.run(synthesize(text, voice, out_path, rate=rate))
