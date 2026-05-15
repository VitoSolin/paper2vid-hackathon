#!/usr/bin/env python3
"""
Rate limit global untuk API arXiv (semua script share satu jeda).

Rekomendasi resmi arXiv: ≥3 detik antar request ke export.arxiv.org.
Default: 3 detik (atur via ARXIV_REQUEST_INTERVAL di .env).
"""

from __future__ import annotations

import fcntl
import json
import os
import time
from pathlib import Path

import arxiv

ROOT = Path(__file__).resolve().parents[1]
RATE_STATE = ROOT / "data" / ".schedule" / "arxiv_rate.json"


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def request_interval() -> float:
    _load_dotenv()
    raw = os.environ.get(
        "ARXIV_REQUEST_INTERVAL",
        os.environ.get("ARXIV_DELAY_SECONDS", "3"),
    )
    return max(2.0, float(raw))


def wait_before_arxiv_request(label: str = "") -> None:
    """Tunggu sampai aman mengirim request API berikutnya (lintas proses)."""
    interval = request_interval()
    RATE_STATE.parent.mkdir(parents=True, exist_ok=True)

    with open(RATE_STATE, "a+", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.seek(0)
            raw = f.read().strip()
            last = 0.0
            if raw:
                try:
                    last = float(json.loads(raw).get("last_request", 0))
                except json.JSONDecodeError:
                    last = 0.0

            now = time.time()
            wait = interval - (now - last)
            if wait > 0:
                msg = f"arXiv rate limit: tunggu {wait:.1f}s"
                if label:
                    msg += f" ({label})"
                print(msg, flush=True)
                time.sleep(wait)

            f.seek(0)
            f.truncate()
            f.write(
                json.dumps(
                    {"last_request": time.time(), "interval_sec": interval},
                    indent=2,
                )
            )
            f.flush()
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def make_arxiv_client() -> arxiv.Client:
    """Client arxiv dengan retry + delay internal (tambahan dari wait global)."""
    interval = request_interval()
    return arxiv.Client(
        page_size=10,
        delay_seconds=interval,
        num_retries=6,
    )


def arxiv_search_results(search: arxiv.Search, label: str = "") -> list:
    """Satu panggilan API dengan jeda global."""
    wait_before_arxiv_request(label)
    client = make_arxiv_client()
    return list(client.results(search))
