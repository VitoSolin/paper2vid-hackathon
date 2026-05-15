#!/usr/bin/env python3
"""Buat placeholder background + karakter jika belum ada."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"


def _gradient_bg(path: Path, w: int = 1080, h: int = 1920) -> None:
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        r = int(30 + 40 * t)
        g = int(45 + 55 * t)
        b = int(80 + 90 * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    # panel sci-fi sederhana
    draw.rectangle([80, 400, w - 80, h - 200], outline=(120, 140, 180), width=4)
    draw.line([w // 2, 420, w // 2, h - 220], fill=(90, 110, 150), width=2)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "WEBP", quality=90, method=6)


def _character(path: Path, color: tuple[int, int, int], label: str) -> None:
    w, h = 600, 900
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # siluet tubuh + kepala (placeholder — ganti dengan PNG Anda)
    draw.ellipse([180, 40, 420, 280], fill=color + (255,))
    draw.rounded_rectangle([140, 260, 460, 820], radius=80, fill=color + (255,))
    draw.text((w // 2, h - 60), label, fill=(255, 255, 255, 200), anchor="mm")
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "WEBP", quality=90, method=6)


def ensure_defaults() -> dict[str, Path]:
    bg = ASSETS / "backgrounds" / "default.webp"
    a = ASSETS / "characters" / "speaker_a.webp"
    b = ASSETS / "characters" / "speaker_b.webp"
    if not bg.exists():
        _gradient_bg(bg)
    if not a.exists():
        _character(a, (90, 160, 220), "HOST")
    if not b.exists():
        _character(b, (220, 120, 90), "AHLI")
    return {"background": bg, "speaker_a": a, "speaker_b": b}


if __name__ == "__main__":
    paths = ensure_defaults()
    for k, p in paths.items():
        print(f"{k}: {p}")
