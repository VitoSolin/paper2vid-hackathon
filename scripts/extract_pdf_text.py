#!/usr/bin/env python3
"""Ekstrak teks dari PDF paper (untuk dibaca agent)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


def extract(paper_path: Path, max_chars: int | None = 120_000) -> Path:
    if paper_path.is_dir():
        pdf = paper_path / "paper.pdf"
        out_dir = paper_path
    else:
        pdf = paper_path
        out_dir = pdf.parent

    if not pdf.exists():
        raise FileNotFoundError(f"PDF tidak ada: {pdf}")

    doc = fitz.open(pdf)
    parts: list[str] = []
    for page in doc:
        parts.append(page.get_text())
    doc.close()

    text = "\n".join(parts)
    text = "\n".join(line.rstrip() for line in text.splitlines())
    truncated = False
    if max_chars and len(text) > max_chars:
        text = text[:max_chars]
        truncated = True

    txt_path = out_dir / "paper.txt"
    txt_path.write_text(text, encoding="utf-8")

    info = {
        "pdf": str(pdf.relative_to(ROOT)),
        "text_file": str(txt_path.relative_to(ROOT)),
        "char_count": len(text),
        "truncated": truncated,
    }
    (out_dir / "extract.json").write_text(
        json.dumps(info, indent=2), encoding="utf-8"
    )
    print(json.dumps(info, indent=2))
    return txt_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path",
        help="Folder data/<arxiv_id> atau path ke paper.pdf",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=120_000,
        help="Batas panjang teks (0 = tanpa batas)",
    )
    args = parser.parse_args()
    target = Path(args.path)
    if not target.is_absolute():
        target = DATA_DIR / target if (DATA_DIR / target).exists() else ROOT / target
    max_chars = args.max_chars if args.max_chars > 0 else None
    try:
        extract(target, max_chars=max_chars)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
