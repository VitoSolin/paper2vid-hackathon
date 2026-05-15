#!/usr/bin/env python3
"""Audit trail agent — bukti autonomous loop untuk demo juri."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def log_step(
    paper_dir: Path,
    *,
    agent: str,
    action: str,
    status: str,
    detail: dict[str, Any] | None = None,
) -> None:
    paper_dir.mkdir(parents=True, exist_ok=True)
    path = paper_dir / "agent-run.jsonl"
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "agent": agent,
        "action": action,
        "status": status,
        "detail": detail or {},
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
