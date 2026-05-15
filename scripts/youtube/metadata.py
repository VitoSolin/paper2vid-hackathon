#!/usr/bin/env python3
"""Bangun judul, deskripsi, dan tag YouTube dari artefak paper."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from paths import DATA, OUTPUT, ROOT  # noqa: E402

MAX_TITLE = 100
MAX_DESC = 4900
MAX_TAGS = 500  # total chars YouTube limit for tags combined


def _load_json(path: Path) -> dict[str, Any] | None:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def resolve_paper_dir(arg: str | Path) -> Path:
    p = Path(arg)
    if not p.is_absolute():
        cand = DATA / p
        if cand.is_dir():
            p = cand
        elif (ROOT / p).is_dir():
            p = ROOT / p
    if p.is_file():
        p = p.parent
    if not p.exists():
        raise FileNotFoundError(f"Folder paper tidak ditemukan: {p}")
    return p.resolve()


def arxiv_id_from_dir(paper_dir: Path) -> str:
    meta = _load_json(paper_dir / "metadata.json")
    if meta and meta.get("arxiv_id"):
        return str(meta["arxiv_id"]).replace("/", "_")
    return paper_dir.name


def resolve_video_path(paper_dir: Path, arxiv_id: str) -> Path:
    render = _load_json(paper_dir / "video-render.json")
    if render and render.get("output"):
        vid = ROOT / render["output"]
        if vid.exists():
            return vid.resolve()
    safe = arxiv_id.replace("/", "_")
    for cand in (
        OUTPUT / f"{safe}.mp4",
        OUTPUT / f"{arxiv_id}.mp4",
    ):
        if cand.exists():
            return cand.resolve()
    raise FileNotFoundError(
        f"Video tidak ditemukan untuk {arxiv_id}. "
        f"Jalankan: python scripts/video/render.py data/{paper_dir.name}"
    )


def _truncate(s: str, n: int) -> str:
    s = s.strip()
    if len(s) <= n:
        return s
    return s[: n - 1].rstrip() + "…"


def _sanitize_youtube_text(s: str) -> str:
    """
    YouTube menolak < > di deskripsi (dianggap HTML), mis. K<3 di temuan paper.
  """
    if not s:
        return s
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)
    # Perbandingan: K<3, K < 3 → teks biasa
    s = re.sub(r"(\w+)\s*<\s*(\w+)", r"\1 kurang dari \2", s)
    s = re.sub(r"(\w+)\s*>\s*(\w+)", r"\1 lebih dari \2", s)
    # Sisa bracket (jangan sampai ada < > sama sekali)
    s = s.replace("<", "(").replace(">", ")")
    s = re.sub(r"  +", " ", s)
    return s.strip()


def build_minimal_description(paper_dir: Path) -> str:
    """Deskripsi aman jika versi panjang ditolak API YouTube."""
    meta = _load_json(paper_dir / "metadata.json") or {}
    summary = _load_json(paper_dir / "paper-summary.json") or {}
    arxiv_id = str(summary.get("arxiv_id") or meta.get("arxiv_id") or paper_dir.name)
    title = _sanitize_youtube_text(summary.get("title") or meta.get("title") or arxiv_id)
    abs_url = _arxiv_abs_url(arxiv_id)
    hook = _sanitize_youtube_text(
        summary.get("why_important") or summary.get("main_findings") or ""
    )
    hook = _truncate(hook, 500) if hook else ""
    lines = [
        title,
        "",
        "Ringkasan paper arXiv dalam format video edukasi (Pak Nam dan Zaba).",
        f"Paper: {abs_url}",
    ]
    if hook:
        lines.extend(["", hook])
    lines.extend(["", "#arXiv #MachineLearning #PaperReview"])
    return _sanitize_youtube_text("\n".join(lines))


def _arxiv_abs_url(arxiv_id: str) -> str:
    aid = arxiv_id.replace("_", "/").split("v")[0]
    return f"https://arxiv.org/abs/{aid}"


def _arxiv_pdf_url(meta: dict | None, arxiv_id: str) -> str:
    if meta and meta.get("pdf_url"):
        return str(meta["pdf_url"])
    aid = arxiv_id.replace("_", "/").split("v")[0]
    return f"https://arxiv.org/pdf/{aid}"


def _category_tags(categories: list[str] | None) -> list[str]:
    if not categories:
        return []
    mapping = {
        "cs.LG": "machine learning",
        "cs.CL": "NLP",
        "cs.CV": "computer vision",
        "cs.AI": "artificial intelligence",
        "stat.ML": "machine learning",
    }
    out: list[str] = []
    for c in categories:
        out.append(c.replace(".", " "))
        if c in mapping:
            out.append(mapping[c])
    return out


def build_metadata(
    paper_dir: Path,
    *,
    channel_suffix: str = "Pak Nam & Zaba",
    extra_tags: list[str] | None = None,
) -> dict[str, Any]:
    """Return dict: title, description, tags, category_id."""
    meta = _load_json(paper_dir / "metadata.json") or {}
    summary = _load_json(paper_dir / "paper-summary.json") or {}
    arxiv_id = summary.get("arxiv_id") or meta.get("arxiv_id") or paper_dir.name
    title = summary.get("title") or meta.get("title") or arxiv_id

    abs_url = _arxiv_abs_url(str(arxiv_id))
    pdf_url = _arxiv_pdf_url(meta, str(arxiv_id))

    hook = summary.get("why_important") or summary.get("main_findings")
    if not hook:
        abstract = summary.get("abstract") or meta.get("abstract") or ""
        hook = _truncate(abstract, 400)

    problem = _sanitize_youtube_text(summary.get("problem", ""))
    method = _sanitize_youtube_text(summary.get("method", ""))
    findings = _sanitize_youtube_text(summary.get("main_findings", ""))
    hook = _sanitize_youtube_text(hook) if hook else ""
    title = _sanitize_youtube_text(title)

    body_parts = [
        f"📄 {title}",
        f"🔗 arXiv: {abs_url}",
        f"📥 PDF: {pdf_url}",
        "",
        f"Dijelaskan oleh {channel_suffix} — ringkasan paper riset dalam format singkat.",
        "",
    ]
    if problem:
        body_parts.extend(["🎯 Masalah", problem, ""])
    if method:
        body_parts.extend(["🔬 Metode", method, ""])
    if findings:
        body_parts.extend(["✨ Temuan utama", findings, ""])
    elif hook:
        body_parts.extend(["📝 Ringkasan", hook, ""])

    body_parts.extend(
        [
            "---",
            "#Shorts #arXiv #PaperReview #Riset #MachineLearning",
            "",
            "Subscribe untuk paper berikutnya!",
        ]
    )
    description = _sanitize_youtube_text(
        _truncate("\n".join(body_parts), MAX_DESC)
    )

    base_title = f"{title} — {channel_suffix}"
    yt_title = _truncate(_sanitize_youtube_text(base_title), MAX_TITLE)

    tags = [
        "arXiv",
        "paper review",
        "research paper",
        "machine learning",
        "AI",
        "shorts",
        "bahasa indonesia",
        "pak nam zaba",
    ]
    tags.extend(_category_tags(meta.get("categories") or summary.get("categories")))
    # judul kata kunci
    for word in re.findall(r"[A-Za-z0-9]{4,}", title):
        if word.lower() not in {t.lower() for t in tags}:
            tags.append(word)
    if extra_tags:
        tags.extend(extra_tags)

    seen: set[str] = set()
    unique: list[str] = []
    total = 0
    for t in tags:
        key = t.lower().strip()
        if not key or key in seen:
            continue
        t = _sanitize_youtube_text(t)
        if len(t) > 30:
            t = t[:30]
        if total + len(t) + 1 > MAX_TAGS:
            break
        seen.add(key)
        unique.append(t)
        total += len(t) + 1

    return {
        "arxiv_id": arxiv_id,
        "title": yt_title,
        "description": description,
        "tags": unique,
        "arxiv_abs_url": abs_url,
    }
