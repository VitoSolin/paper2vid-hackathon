#!/usr/bin/env python3
"""07:00 — tarik 3 paper terbaru & proses semua."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))

from fetch_latest import fetch_candidate_ids, load_schedule  # noqa: E402
from process_paper import process_one  # noqa: E402
from state import load_state, save_state  # noqa: E402


def main() -> None:
    sched = load_schedule()
    count = int(sched.get("fetch", {}).get("count", 3))
    ids = fetch_candidate_ids(count, sched)
    print(f"Paper baru: {ids}", flush=True)

    st = load_state()
    st["last_fetch"] = datetime.now(timezone.utc).isoformat()
    save_state(st)

    results = []
    for arxiv_id in ids:
        try:
            out = process_one(arxiv_id)
            results.append({"arxiv_id": arxiv_id, "ok": out is not None})
        except Exception as e:
            print(f"GAGAL {arxiv_id}: {e}", flush=True)
            results.append({"arxiv_id": arxiv_id, "ok": False, "error": str(e)})

    print(json.dumps({"fetched": ids, "results": results}, indent=2))


if __name__ == "__main__":
    main()
