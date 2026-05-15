#!/usr/bin/env python3
"""State antrian harian: paper diproses & siap upload."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = ROOT / "data" / ".schedule" / "state.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {
            "processed_ids": [],
            "queue": [],
            "uploaded": [],
            "last_fetch": None,
            "last_upload": None,
        }
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def is_known(arxiv_id: str, state: dict[str, Any] | None = None) -> bool:
    st = state or load_state()
    aid = arxiv_id.replace("/", "_")
    if aid in st.get("processed_ids", []):
        return True
    for item in st.get("queue", []):
        if item.get("arxiv_id") == aid:
            return True
    for item in st.get("uploaded", []):
        if item.get("arxiv_id") == aid:
            return True
    return False


def mark_processed(arxiv_id: str, state: dict[str, Any] | None = None) -> dict[str, Any]:
    st = state or load_state()
    aid = arxiv_id.replace("/", "_")
    ids = st.setdefault("processed_ids", [])
    if aid not in ids:
        ids.append(aid)
    save_state(st)
    return st


def enqueue_ready(arxiv_id: str, video_path: str) -> None:
    st = load_state()
    aid = arxiv_id.replace("/", "_")
    st["queue"] = [q for q in st.get("queue", []) if q.get("arxiv_id") != aid]
    st["queue"].append(
        {
            "arxiv_id": aid,
            "status": "ready",
            "video_path": video_path,
            "ready_at": _now(),
        }
    )
    mark_processed(aid, st)
    save_state(st)


def pop_next_upload() -> dict[str, Any] | None:
    st = load_state()
    queue = st.get("queue", [])
    for i, item in enumerate(queue):
        if item.get("status") == "ready":
            picked = queue.pop(i)
            st["queue"] = queue
            save_state(st)
            return picked
    return None


def mark_uploaded(arxiv_id: str, url: str, video_id: str) -> None:
    st = load_state()
    aid = arxiv_id.replace("/", "_")
    st.setdefault("uploaded", []).append(
        {
            "arxiv_id": aid,
            "url": url,
            "video_id": video_id,
            "uploaded_at": _now(),
        }
    )
    st["last_upload"] = _now()
    save_state(st)
