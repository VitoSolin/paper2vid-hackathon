#!/usr/bin/env python3
"""Komposit frame: layer belakang → karakter → subtitle atas."""

from __future__ import annotations

import textwrap
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
) -> None:
    w, h = base.size
    ch = cfg.get("characters", {})
    target_h = int(h * ch.get("height_ratio", 0.42))
    scale = ch.get("active_scale", 1.0) if active else ch.get("inactive_scale", 0.88)
    target_h = int(target_h * scale)

    ratio = target_h / sprite.height
    target_w = int(sprite.width * ratio)
    resized = sprite.resize((target_w, target_h), _RESAMPLE)

    if not active:
        alpha = resized.split()[3]
        opacity = int(255 * ch.get("inactive_opacity", 0.55))
        alpha = alpha.point(lambda p: int(p * opacity / 255))
        resized.putalpha(alpha)

    margin_bottom = ch.get("margin_bottom", 48)
    y = h - target_h - margin_bottom
    if side == "left":
        x = int(w * 0.06)
    else:
        x = w - target_w - int(w * 0.06)

    base.paste(resized, (x, y), resized)


def _draw_subtitle(
    draw: ImageDraw.ImageDraw,
    text: str,
    w: int,
    cfg: dict[str, Any],
) -> None:
    sub = cfg.get("subtitle", {})
    font_size = sub.get("font_size", 52)
    font = _load_font(font_size)
    margin_top = cfg.get("layers", {}).get("subtitle", {}).get("margin_top", 72)
    max_w = int(w * sub.get("max_width_ratio", 0.9))

    if sub.get("uppercase", True):
        text = text.upper()

    # perkiraan lebar karakter untuk wrap
    avg_char = font_size * 0.55
    cols = max(12, int(max_w / avg_char))
    lines = textwrap.wrap(text, width=cols)
    line_h = font_size + 12
    block_h = len(lines) * line_h
    y = margin_top

    for line in lines:
        draw.text(
            (w // 2, y + line_h // 2),
            line,
            font=font,
            fill=sub.get("fill", "#FFFFFF"),
            stroke_width=sub.get("stroke_width", 5),
            stroke_fill=sub.get("stroke", "#000000"),
            anchor="mm",
        )
        y += line_h


def render_frame(
    background: Image.Image,
    char_a: Image.Image,
    char_b: Image.Image,
    subtitle: str,
    active_speaker: str | None,
    cfg: dict[str, Any],
) -> Image.Image:
    w = cfg.get("width", 1080)
    h = cfg.get("height", 1920)

    frame = _cover_resize(background, w, h).convert("RGBA")
    _place_character(frame, char_a, "left", active_speaker == "A", cfg)
    _place_character(frame, char_b, "right", active_speaker == "B", cfg)

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    _draw_subtitle(draw, subtitle, w, cfg)
    return Image.alpha_composite(frame, overlay).convert("RGB")
