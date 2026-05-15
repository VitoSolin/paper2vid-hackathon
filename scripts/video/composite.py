#!/usr/bin/env python3
"""Komposit frame: layer belakang → karakter → subtitle atas."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps

from subtitles import wrap_subtitle_lines  # noqa: E402

try:
    _RESAMPLE = Image.Resampling.LANCZOS
except AttributeError:
    _RESAMPLE = Image.LANCZOS

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FONT = ROOT / "assets" / "fonts" / "LilitaOne-Regular.ttf"


def _resolve_font_path(cfg: dict[str, Any]) -> Path | None:
    sub = cfg.get("subtitle", {})
    raw = sub.get("font_file")
    if not raw:
        return DEFAULT_FONT if DEFAULT_FONT.exists() else None
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    return path if path.exists() else None


def _load_font(size: int, cfg: dict[str, Any]) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    custom = _resolve_font_path(cfg)
    if custom:
        return ImageFont.truetype(str(custom), size)

    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _cover_resize(img: Image.Image, w: int, h: int) -> Image.Image:
    return ImageOps.fit(img.convert("RGBA"), (w, h), method=_RESAMPLE)


def _trim_transparent(sprite: Image.Image) -> Image.Image:
    """Potong area transparan agar anchor kiri/kanan mengikuti tubuh karakter."""
    bbox = sprite.getbbox()
    if bbox:
        return sprite.crop(bbox)
    return sprite


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
    layout = entry.get("layout", {})

    margin_x = layout.get("margin_x_ratio", ch.get("margin_x_ratio", 0.06))
    height_ratio = layout.get("height_ratio", ch.get("height_ratio", 0.42))
    scale = layout.get("scale", ch.get("active_scale", 1.0))
    target_h = int(h * height_ratio * scale)

    if layout.get("trim_alpha", True):
        sprite = _trim_transparent(sprite)

    if entry.get("mirror", False):
        sprite = ImageOps.mirror(sprite)

    ratio = target_h / sprite.height
    target_w = int(sprite.width * ratio)
    resized = sprite.resize((target_w, target_h), _RESAMPLE)

    margin_bottom = layout.get("margin_bottom", ch.get("margin_bottom", 48))
    offset_y = layout.get("offset_y", 0)
    offset_x = layout.get("offset_x", 0)
    visible_ratio = layout.get("visible_body_ratio")
    if visible_ratio is not None:
        # Bagian bawah sprite boleh terpotong; ~70% tubuh dari atas terlihat
        y = h - int(target_h * float(visible_ratio)) + offset_y
    else:
        y = h - target_h - margin_bottom + offset_y

    place_side = side
    if entry.get("mirror_position", False):
        place_side = "left" if side == "right" else "right"

    if "position_x_ratio" in layout:
        px = int(w * layout["position_x_ratio"])
        anchor = layout.get("anchor", "center")
        if anchor == "left":
            # tepi kiri sprite di px (hindari ilusi ke kanan karena padding PNG)
            x = px + offset_x
        elif anchor == "right":
            x = px - target_w + offset_x
        else:
            x = px - target_w // 2 + offset_x
    else:
        mx = int(w * margin_x)
        if place_side == "left":
            x = mx + offset_x
        else:
            x = w - target_w - mx + offset_x

    if not layout.get("allow_side_crop", False):
        x = max(0, min(x, w - target_w))
    if visible_ratio is None:
        y = max(0, min(y, h - target_h))
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
    font_size = sub.get("font_size", 54)
    font = _load_font(font_size, cfg)
    anchor_y = _subtitle_y(cfg, h)
    stroke_w = sub.get("stroke_width", 6)

    if sub.get("uppercase", True):
        text = text.upper()

    max_width = int(w * sub.get("max_width_ratio", 0.85))
    pad = sub.get("safe_padding_px", 24)
    max_width = max(200, max_width - pad * 2)

    lines = wrap_subtitle_lines(text, font, max_width, stroke_width=stroke_w)
    line_gap = int(font_size * sub.get("line_spacing", 0.28))
    line_h = font_size + line_gap
    block_h = len(lines) * line_h
    y0 = anchor_y - block_h // 2 + line_h // 2

    fill = sub.get("fill", "#FFFFFF")
    stroke_fill = sub.get("stroke", "#000000")

    for i, line in enumerate(lines):
        draw.text(
            (w // 2, y0 + i * line_h),
            line,
            font=font,
            fill=fill,
            stroke_width=stroke_w,
            stroke_fill=stroke_fill,
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
