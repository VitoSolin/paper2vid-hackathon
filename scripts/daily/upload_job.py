#!/usr/bin/env python3
"""Upload slot — ambil 1 video dari antrian & publish ke YouTube."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "youtube"))
sys.path.insert(0, str(Path(__file__).parent))

from fetch_latest import load_schedule  # noqa: E402
from state import mark_uploaded, pop_next_upload  # noqa: E402
from upload import publish_paper  # noqa: E402


def main() -> None:
    item = pop_next_upload()
    if not item:
        print("Antrian upload kosong — tidak ada yang di-upload.")
        return

    aid = item["arxiv_id"]
    paper_dir = ROOT / "data" / aid
    sched = load_schedule()
    privacy = sched.get("youtube", {}).get("privacy", "public")

    print(f"Upload {aid} ({privacy})…", flush=True)
    result = publish_paper(paper_dir, privacy=privacy)
    mark_uploaded(aid, result["url"], result["video_id"])
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        raise SystemExit(str(e)) from e
    except Exception as e:
        raise SystemExit(str(e)) from e
