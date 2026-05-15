#!/usr/bin/env python3
"""RAG ringan: ambil cuplikan paper.txt paling relevan untuk ekstraksi."""

from __future__ import annotations

import re
from pathlib import Path


def _chunks(text: str, max_chunk: int = 2000) -> list[str]:
    parts = re.split(r"\n\s*\n", text)
    out: list[str] = []
    buf: list[str] = []
    size = 0
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if size + len(p) > max_chunk and buf:
            out.append("\n\n".join(buf))
            buf = [p]
            size = len(p)
        else:
            buf.append(p)
            size += len(p)
    if buf:
        out.append("\n\n".join(buf))
    return out


def _score(chunk: str, keywords: list[str]) -> int:
    low = chunk.lower()
    return sum(low.count(k) for k in keywords if k)


def build_rag_context(paper_dir: Path, max_chars: int = 24000) -> str:
    """Return teks terkurasi dari paper.txt + abstract."""
    parts: list[str] = []
    abstract = paper_dir / "abstract.txt"
    if abstract.exists():
        parts.append("=== abstract (prioritas) ===\n" + abstract.read_text(encoding="utf-8")[:6000])

    body = paper_dir / "paper.txt"
    if not body.exists():
        return "\n\n".join(parts)[:max_chars]

    text = body.read_text(encoding="utf-8", errors="replace")
    keywords = [
        "method",
        "result",
        "experiment",
        "conclusion",
        "abstract",
        "introduction",
        "we propose",
        "dataset",
        "accuracy",
        "model",
    ]
    chunks = _chunks(text)
    ranked = sorted(chunks, key=lambda c: _score(c, keywords), reverse=True)

    selected: list[str] = []
    total = len(parts[0]) if parts else 0
    for c in ranked:
        if total + len(c) > max_chars:
            break
        selected.append(c)
        total += len(c)

    if selected:
        parts.append("=== paper.txt (cuplikan RAG) ===\n" + "\n\n---\n\n".join(selected))
    return "\n\n".join(parts)[:max_chars]
