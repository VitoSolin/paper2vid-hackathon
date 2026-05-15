#!/usr/bin/env python3
"""OAuth2 YouTube — jalankan sekali untuk menyimpan token."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import CLIENT_SECRET, SCOPES, TOKEN_FILE, YOUTUBE_DIR  # noqa: E402


def _require_google():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as e:
        raise SystemExit(
            "Paket Google belum terpasang. Jalankan: pip install -r requirements.txt"
        ) from e
    return Request, Credentials, InstalledAppFlow


def get_credentials(*, force_refresh: bool = False):
    """Muat token tersimpan atau jalankan alur OAuth."""
    Request, Credentials, InstalledAppFlow = _require_google()
    creds = None

    if TOKEN_FILE.exists() and not force_refresh:
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        return creds

    if not CLIENT_SECRET.exists():
        raise SystemExit(
            f"File OAuth tidak ditemukan: {CLIENT_SECRET}\n"
            "Ikuti docs/YOUTUBE.md — unduh client_secret.json dari Google Cloud "
            "dan simpan di config/youtube/client_secret.json"
        )

    YOUTUBE_DIR.mkdir(parents=True, exist_ok=True)
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True)
    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    print(f"Token disimpan: {TOKEN_FILE}")
    return creds


def main() -> None:
    parser = argparse.ArgumentParser(description="Autorisasi YouTube OAuth2")
    parser.add_argument(
        "--reauth",
        action="store_true",
        help="Paksa login ulang (hapus token lama)",
    )
    args = parser.parse_args()
    if args.reauth and TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
    get_credentials(force_refresh=args.reauth)
    print("YouTube OAuth siap.")


if __name__ == "__main__":
    main()
