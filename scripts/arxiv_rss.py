#!/usr/bin/env python3
"""Discover paper terbaru via RSS arXiv — tanpa API query (hindari rate limit)."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

from fetch_arxiv import ARXIV_ID_RE, normalize_arxiv_id

USER_AGENT = "paper2video/1.0 (arxiv-rss; mailto:local)"


def _id_from_link(link: str) -> str | None:
    m = ARXIV_ID_RE.search(link)
    if m:
        return normalize_arxiv_id(m.group(1))
    return None


def fetch_ids_from_rss(
    categories: list[str],
    *,
    max_items: int = 40,
) -> list[str]:
    """
    Ambil arXiv ID dari feed RSS per kategori.
    Contoh kategori: cs.LG, cs.CL, cs.AI, stat.ML
    """
    seen: set[str] = set()
    ordered: list[str] = []

    for cat in categories:
        url = f"https://rss.arxiv.org/rss/{cat.strip()}"
        try:
            resp = requests.get(
                url,
                timeout=45,
                headers={"User-Agent": USER_AGENT},
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"RSS {cat} gagal: {e}", flush=True)
            continue

        try:
            root = ET.fromstring(resp.content)
        except ET.ParseError as e:
            print(f"RSS {cat} parse error: {e}", flush=True)
            continue

        for item in root.findall(".//item"):
            link_el = item.find("link")
            if link_el is None or not link_el.text:
                continue
            aid = _id_from_link(link_el.text.strip())
            if not aid or aid in seen:
                continue
            seen.add(aid)
            ordered.append(aid)
            if len(ordered) >= max_items:
                return ordered

    return ordered
