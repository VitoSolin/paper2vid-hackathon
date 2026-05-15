#!/usr/bin/env python3
"""Pecah & wrap teks subtitle."""

from __future__ import annotations

import re
from typing import Any


def _text_width(font: Any, text: str, stroke_width: int = 0) -> float:
    try:
        return float(font.getlength(text)) + stroke_width * 2
    except AttributeError:
        bbox = font.getbbox(text)
        return float(bbox[2] - bbox[0]) + stroke_width * 2


def wrap_subtitle_lines(
    text: str,
    font: Any,
    max_width: int,
    stroke_width: int = 0,
) -> list[str]:
    """Wrap kata demi kata; jika satu kata terlalu panjang, pecah per karakter."""
    words = re.findall(r"\S+", text.strip())
    if not words:
        return [""]

    lines: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            lines.append(" ".join(current))
            current.clear()

    for word in words:
        candidate = " ".join(current + [word]) if current else word
        if _text_width(font, candidate, stroke_width) <= max_width:
            current.append(word)
            continue
        flush()
        if _text_width(font, word, stroke_width) <= max_width:
            current.append(word)
            continue
        # kata tunggal lebih lebar dari safe zone
        chunk = ""
        for ch in word:
            test = chunk + ch
            if _text_width(font, test, stroke_width) <= max_width:
                chunk = test
            else:
                if chunk:
                    lines.append(chunk)
                chunk = ch
        if chunk:
            lines.append(chunk)

    flush()
    return lines if lines else [text.strip()]


def chunk_subtitle(text: str, max_words: int = 5) -> list[str]:
    """Contoh: 'model sekuens lama susah diparelelkan dan latihannya lama'
    → ['model sekuens lama susah diparelelkan', 'dan latihannya lama'] (max 5 kata).
    """
    words = re.findall(r"\S+", text.strip())
    if not words:
        return [""]
    max_words = max(1, max_words)
    return [
        " ".join(words[i : i + max_words])
        for i in range(0, len(words), max_words)
    ]
