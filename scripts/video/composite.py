#!/usr/bin/env python3
"""Komposit frame: layer belakang → karakter → subtitle atas."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps

try:
    _RESAMPLE = Image.Resampling.LANCZOS
except AttributeError:
    _RESAMPLE = Image.LANCZOS


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _cover_resize(img: Image.Image, w: int, h: int) -> Image.Image:
    return ImageOps.fit(img.convert("RGBA"), (w, h), method=_RESAMPLE)


def _place_character(
    base: Image.Image,
    sprite: Image.Image,
    side: str,
    active: bool,
    cfg: dict[str, Any],
    cast_entry: dict[str, Any] | None = None,
) -> None:
    w, h = base.size
    entry = cast_entry or {}
    ch = cfg.get("characters", {})
    margin_x = ch.get("margin_x_ratio", 0.06)

    target_h = int(h * ch.get("height_ratio", 0.42))
    scale = ch.get("active_scale", 1.0)
    target_h = int(target_h * scale)

    if entry.get("mirror", False):
        sprite = ImageOps.mirror(sprite)

    ratio = target_h / sprite.height
    target_w = int(sprite.width * ratio)
    resized = sprite.resize((target_w, target_h), _RESAMPLE)

    margin_bottom = ch.get("margin_bottom", 48)
    y = h - target_h - margin_bottom

    # Posisi: mirror = tukar sisi kiri/kanan dari default side
    place_side = side
    if entry.get("mirror_position", False):
        place_side = "left" if side == "right" else "right"

    mx = int(w * margin_x)
    if place_side == "left":
        x = mx
    else:
        x = w - target_w - mx

    base.paste(resized, (x, y), resized)


def _subtitle_y(cfg: dict[str, Any], h: int) -> int:
    sub = cfg.get("subtitle", {})
    layers_sub = cfg.get("layers", {}).get("subtitle", {})
    if "margin_top_ratio" in sub:
        return int(h * sub["margin_top_ratio"])
    if "margin_top_ratio" in layers_sub:
        return int(h * layers_sub["margin_top_ratio"])
    return layers_sub.get("margin_top", sub.get("margin_top", 72))


def _draw_subtitle(
    draw: ImageDraw.ImageDraw,
    text: str,
    w: int,
    h: int,
    cfg: dict[str, Any],
) -> None:
    sub = cfg.get("subtitle", {})
    font_size = sub.get("font_size", 52)
    font = _load_font(font_size)
    y = _subtitle_y(cfg, h)

    if sub.get("uppercase", True):
        text = text.upper()

    # Satu chunk pendek (≤ max_words); satu baris, center horizontal
    draw.text(
        (w // 2, y),
        text,
        font=font,
        fill=sub.get("fill", "#FFFFFF"),
        stroke_width=sub.get("stroke_width", 5),
        stroke_fill=sub.get("stroke", "#000000"),
        anchor="mm",
    )


def render_frame(
    background: Image.Image,
    sprites: dict[str, Image.Image],
    subtitle: str,
    active_speaker: str | None,
    cfg: dict[str, Any],
) -> Image.Image:
    """sprites: {speaker_id: Image} — mis. paknam, zaba."""
    w = cfg.get("width", 1080)
    h = cfg.get("height", 1920)
    cast = cfg.get("cast", {})

    frame = _cover_resize(background, w, h).convert("RGBA")
    # Hanya tampilkan pembicara aktif (tanpa fade / karakter kedua)
    for sid, sprite in sprites.items():
        if active_speaker is not None and sid != active_speaker:
            continue
        side = cast.get(sid, {}).get("side")
        if not side:
            side = "left" if sid in ("A", "paknam") else "right"
        entry = cast.get(sid, {})
        _place_character(frame, sprite, side, True, cfg, cast_entry=entry)

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    _draw_subtitle(draw, subtitle, w, h, cfg)
    return Image.alpha_composite(frame, overlay).convert("RGB")


def render_frame_legacy(
    background: Image.Image,
    char_a: Image.Image,
    char_b: Image.Image,
    subtitle: str,
    active_speaker: str | None,
    cfg: dict[str, Any],
) -> Image.Image:
    return render_frame(
        background,
        {"A": char_a, "B": char_b},
        subtitle,
        active_speaker,
        cfg,
    )
