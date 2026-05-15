#!/usr/bin/env python3
"""Pecah teks dialog menjadi chunk subtitle (maks N kata)."""

from __future__ import annotations

import re


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
