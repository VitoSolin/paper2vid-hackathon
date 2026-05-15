"""Path & env untuk integrasi YouTube."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))
DATA = ROOT / "data"
OUTPUT = ROOT / "output"
YOUTUBE_DIR = ROOT / "config" / "youtube"
CLIENT_SECRET = YOUTUBE_DIR / "client_secret.json"
TOKEN_FILE = YOUTUBE_DIR / "token.json"

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def privacy_default() -> str:
    load_dotenv()
    return os.environ.get("YOUTUBE_PRIVACY_DEFAULT", "unlisted").lower()


def category_id() -> str:
    load_dotenv()
    return os.environ.get("YOUTUBE_CATEGORY_ID", "28")
