#!/usr/bin/env python3
"""Ambil N paper arXiv terbaru di kategori target (belum pernah diproses)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import arxiv

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).parent))

from arxiv_rate import arxiv_search_results  # noqa: E402
from arxiv_rss import fetch_ids_from_rss  # noqa: E402
from state import is_known  # noqa: E402


def load_schedule() -> dict:
    path = ROOT / "config" / "schedule.json"
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_candidate_ids(count: int, schedule: dict | None = None) -> list[str]:
    cfg = schedule or load_schedule()
    arxiv_cfg = cfg.get("arxiv", {})
    max_scan = int(arxiv_cfg.get("max_scan", 40))
    discover = arxiv_cfg.get("discover", "rss").lower()

    candidates: list[str] = []

    if discover == "rss":
        categories = arxiv_cfg.get(
            "rss_categories", ["cs.LG", "cs.CL", "cs.AI", "stat.ML"]
        )
        print(f"Discover via RSS: {categories}", flush=True)
        candidates = fetch_ids_from_rss(categories, max_items=max_scan)

    if len(candidates) < count or discover == "api":
        query = arxiv_cfg.get(
            "query", "cat:cs.CL OR cat:cs.LG OR cat:cs.AI OR cat:stat.ML"
        )
        print("Discover via arXiv API (query)…", flush=True)
        search = arxiv.Search(
            query=query,
            max_results=max_scan,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )
        for result in arxiv_search_results(search, label="fetch_latest"):
            raw_id = result.get_short_id()
            if raw_id not in candidates:
                candidates.append(raw_id)

    picked: list[str] = []
    for raw_id in candidates:
        aid = raw_id.replace("/", "_")
        if is_known(aid):
            continue
        picked.append(raw_id)
        if len(picked) >= count:
            break
    return picked


def main() -> None:
    parser = argparse.ArgumentParser(description="Daftar paper arXiv terbaru")
    parser.add_argument("-n", "--count", type=int, default=3)
    parser.add_argument("--json", action="store_true", help="Output JSON array")
    args = parser.parse_args()

    ids = fetch_candidate_ids(args.count)
    if args.json:
        print(json.dumps(ids, indent=2))
    else:
        for i in ids:
            print(i)
    if not ids:
        print("Tidak ada paper baru.", file=sys.stderr)


if __name__ == "__main__":
    main()
