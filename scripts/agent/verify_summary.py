#!/usr/bin/env python3
"""
Verifikasi paper-summary.json — agent QA sebelum dialog.
Gagal → kembalikan issues untuk retry LLM (autonomous loop).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REQUIRED = ("problem", "method", "main_findings", "why_important", "limitations")
MIN_LEN = 40


def _word_set(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{4,}", text.lower()))


def verify_summary(
    summary: dict[str, Any],
    paper_dir: Path,
) -> dict[str, Any]:
    issues: list[str] = []

    for field in REQUIRED:
        val = (summary.get(field) or "").strip()
        if len(val) < MIN_LEN:
            issues.append(f"Field `{field}` terlalu pendek atau kosong.")

    abstract_path = paper_dir / "abstract.txt"
    if abstract_path.exists():
        abs_words = _word_set(abstract_path.read_text(encoding="utf-8"))
        findings = _word_set(summary.get("main_findings", ""))
        overlap = len(abs_words & findings)
        if overlap < 3 and len(abs_words) > 20:
            issues.append(
                "main_findings kurang selaras dengan abstract "
                "(sedikit overlap istilah kunci)."
            )

    sources = summary.get("sources") or {}
    if not sources.get("used_abstract"):
        issues.append("sources.used_abstract harus true jika abstract ada.")
    if paper_dir.joinpath("paper.txt").exists() and not sources.get("used_pdf"):
        issues.append("paper.txt ada — set sources.used_pdf: true.")

    ok = len(issues) == 0
    return {
        "ok": ok,
        "issues": issues,
        "score": max(0.0, 1.0 - 0.2 * len(issues)),
    }


def verify_summary_file(paper_dir: Path) -> dict[str, Any]:
    path = paper_dir / "paper-summary.json"
    if not path.exists():
        return {"ok": False, "issues": ["paper-summary.json belum ada"], "score": 0.0}
    summary = json.loads(path.read_text(encoding="utf-8"))
    return verify_summary(summary, paper_dir)


def main() -> None:
    import argparse
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from fetch_arxiv import paper_dir, normalize_arxiv_id

    p = argparse.ArgumentParser(description="Verifikasi paper-summary.json")
    p.add_argument("arxiv_id")
    args = p.parse_args()
    result = verify_summary_file(paper_dir(normalize_arxiv_id(args.arxiv_id)))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
