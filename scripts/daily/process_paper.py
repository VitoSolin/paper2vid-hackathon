#!/usr/bin/env python3
"""Pipeline penuh satu paper: fetch → LLM → render video → antrian upload."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).parent))

from llm import generate_dialog_script, generate_paper_summary  # noqa: E402
from state import enqueue_ready, is_known  # noqa: E402
from fetch_arxiv import normalize_arxiv_id, paper_dir  # noqa: E402


def run(cmd: list[str]) -> None:
    print(f"→ {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, check=True, cwd=ROOT)


def process_one(arxiv_id: str, *, skip_if_known: bool = True) -> Path | None:
    arxiv_id = normalize_arxiv_id(arxiv_id)
    aid = arxiv_id.replace("/", "_")
    if skip_if_known and is_known(aid):
        print(f"Lewati {aid} (sudah ada di state)")
        return None

    py = sys.executable
    run([py, str(ROOT / "scripts" / "run_pipeline.py"), arxiv_id])

    pdir = paper_dir(arxiv_id)
    generate_paper_summary(pdir)
    generate_dialog_script(pdir)

    run(
        [
            py,
            str(ROOT / "scripts" / "video" / "render.py"),
            str(pdir),
            "--config",
            str(ROOT / "config" / "characters.paknam-zaba.json"),
        ]
    )

    out_mp4 = ROOT / "output" / f"{aid}.mp4"
    if not out_mp4.exists():
        raise FileNotFoundError(f"Render gagal: {out_mp4}")

    enqueue_ready(aid, str(out_mp4.relative_to(ROOT)))
    print(f"Siap upload: {out_mp4}")
    return out_mp4


def main() -> None:
    parser = argparse.ArgumentParser(description="Proses satu paper end-to-end")
    parser.add_argument("arxiv_id")
    parser.add_argument("--force", action="store_true", help="Proses meski sudah dikenal")
    args = parser.parse_args()
    try:
        process_one(args.arxiv_id, skip_if_known=not args.force)
    except Exception as e:
        raise SystemExit(str(e)) from e


if __name__ == "__main__":
    main()
