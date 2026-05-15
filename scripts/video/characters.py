#!/usr/bin/env python3
"""Muat aset Pak Nam / Zaba dari config."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
CAST_CONFIG = ROOT / "config" / "characters.paknam-zaba.json"


def load_cast_config(path: Path | None = None) -> dict[str, Any]:
    p = path or CAST_CONFIG
    return json.loads(p.read_text(encoding="utf-8"))


def normalize_speaker(raw: str, cfg: dict[str, Any]) -> str:
    key = raw.strip().upper()
    aliases = cfg.get("speaker_aliases", {})
    if key in aliases:
        return aliases[key]
    return raw.strip().lower()


def resolve_sprite(cast: dict[str, Any], speaker: str, expression: str | None) -> Path:
    entry = cast["cast"][speaker]
    expr = expression or entry.get("default_expression", "neutral")
    sprites = entry["sprites"]
    if expr not in sprites:
        expr = entry.get("default_expression", "neutral")
    return ROOT / sprites[expr]


def resolve_background(cast: dict[str, Any], active_speaker: str) -> Path:
    return ROOT / cast["cast"][active_speaker]["background"]


def load_speaker_images(
    cfg: dict[str, Any],
) -> tuple[dict[str, Image.Image], dict[str, Image.Image]]:
    """Return (backgrounds, sprites) per speaker id — sprite default neutral."""
    bgs: dict[str, Image.Image] = {}
    sprites: dict[str, Image.Image] = {}
    for sid, entry in cfg["cast"].items():
        bgs[sid] = Image.open(ROOT / entry["background"])
        default = entry.get("default_expression", "neutral")
        sprites[sid] = Image.open(ROOT / entry["sprites"][default]).convert("RGBA")
    return bgs, sprites


def sprite_for_turn(
    cfg: dict[str, Any],
    speaker: str,
    expression: str | None,
) -> Image.Image:
    path = resolve_sprite(cfg, speaker, expression)
    return Image.open(path).convert("RGBA")
