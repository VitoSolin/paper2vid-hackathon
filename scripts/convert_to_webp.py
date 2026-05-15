#!/usr/bin/env python3
"""Konversi PNG/JPG di personA/ dan assets/ ke WebP."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DIRS = [ROOT / "personA", ROOT / "assets"]


def convert_file(path: Path, quality: int = 90, remove_source: bool = True) -> Path:
    out = path.with_suffix(".webp")
    if out == path:
        return path
    img = Image.open(path)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")
    img.save(out, "WEBP", quality=quality, method=6)
    if remove_source and path.suffix.lower() in (".png", ".jpg", ".jpeg"):
        path.unlink()
    return out


def main() -> None:
    converted = 0
    for base in DIRS:
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.suffix.lower() not in (".png", ".jpg", ".jpeg"):
                continue
            convert_file(path)
            converted += 1
            print(f"  {path.relative_to(ROOT)} → {path.with_suffix('.webp').name}")
    print(f"Selesai: {converted} file")
    if converted == 0:
        print("Tidak ada PNG/JPG untuk dikonversi.")


if __name__ == "__main__":
    main()
