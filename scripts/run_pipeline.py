#!/usr/bin/env python3
"""CLI: fetch arXiv + ekstrak teks PDF. Ringkasan struktur oleh OpenClaw agent."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def run(cmd: list[str]) -> None:
    print(f"\n→ {' '.join(cmd)}\n", flush=True)
    subprocess.run(cmd, check=True, cwd=ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pipeline paper2video (fetch + PDF text)"
    )
    parser.add_argument("arxiv_id")
    parser.add_argument("--no-pdf", action="store_true")
    args = parser.parse_args()

    py = sys.executable
    fetch_cmd = [py, str(SCRIPTS / "fetch_arxiv.py"), args.arxiv_id]
    if args.no_pdf:
        fetch_cmd.append("--no-pdf")
    run(fetch_cmd)

    if not args.no_pdf:
        sys.path.insert(0, str(SCRIPTS))
        from fetch_arxiv import normalize_arxiv_id, paper_dir

        run(
            [
                py,
                str(SCRIPTS / "extract_pdf_text.py"),
                str(paper_dir(normalize_arxiv_id(args.arxiv_id))),
            ]
        )

    print(
        "\nSelesai. Langkah berikutnya (OpenClaw):\n"
        '  openclaw agent --message "Ekstrak paper '
        f'{args.arxiv_id} ke paper-summary.json"\n'
    )


if __name__ == "__main__":
    main()
