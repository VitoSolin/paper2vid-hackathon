#!/usr/bin/env python3
"""Ambil metadata + PDF dari arXiv ke folder data/<arxiv_id>/."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import arxiv
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

ARXIV_ID_RE = re.compile(
    r"(?:arxiv\.org/(?:abs|pdf)/)?(\d{4}\.\d{4,5}(?:v\d+)?|[a-z-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?)",
    re.I,
)


def normalize_arxiv_id(raw: str) -> str:
    raw = raw.strip()
    m = ARXIV_ID_RE.search(raw)
    if m:
        return m.group(1)
    return raw.replace("arXiv:", "").strip()


def paper_dir(arxiv_id: str) -> Path:
    safe = arxiv_id.replace("/", "_")
    return DATA_DIR / safe


def fetch(arxiv_id: str, download_pdf: bool = True) -> Path:
    arxiv_id = normalize_arxiv_id(arxiv_id)
    out = paper_dir(arxiv_id)
    out.mkdir(parents=True, exist_ok=True)

    client = arxiv.Client()
    results = list(client.results(arxiv.Search(id_list=[arxiv_id])))
    if not results:
        raise SystemExit(f"Paper tidak ditemukan: {arxiv_id}")

    p = results[0]
    meta = {
        "arxiv_id": arxiv_id,
        "title": p.title.strip(),
        "authors": [a.name for a in p.authors],
        "published": p.published.isoformat() if p.published else None,
        "updated": p.updated.isoformat() if p.updated else None,
        "categories": list(p.categories),
        "abstract": p.summary.strip(),
        "pdf_url": p.pdf_url,
        "entry_id": p.entry_id,
    }
    (out / "metadata.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out / "abstract.txt").write_text(meta["abstract"], encoding="utf-8")

    if download_pdf:
        pdf_path = out / "paper.pdf"
        if not pdf_path.exists():
            resp = requests.get(p.pdf_url, timeout=120)
            resp.raise_for_status()
            pdf_path.write_bytes(resp.content)
        meta["pdf_path"] = str(pdf_path.relative_to(ROOT))

    (out / "fetch.json").write_text(
        json.dumps({"status": "ok", "dir": str(out.relative_to(ROOT))}, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch arXiv paper")
    parser.add_argument("arxiv_id", help="e.g. 2301.07041 or https://arxiv.org/abs/...")
    parser.add_argument("--no-pdf", action="store_true", help="Skip PDF download")
    args = parser.parse_args()
    try:
        fetch(args.arxiv_id, download_pdf=not args.no_pdf)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
