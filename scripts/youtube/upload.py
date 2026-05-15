#!/usr/bin/env python3
"""
Upload video paper ke YouTube.

Prasyarat:
  1. docs/YOUTUBE.md — OAuth client_secret.json
  2. python scripts/youtube/auth.py
  3. output/<arxiv_id>.mp4 sudah ada
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from auth import get_credentials  # noqa: E402
from metadata import (  # noqa: E402
    arxiv_id_from_dir,
    build_metadata,
    build_minimal_description,
    resolve_paper_dir,
    resolve_video_path,
)
from paths import category_id, privacy_default  # noqa: E402


def _require_google():
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError as e:
        raise SystemExit(
            "Paket Google belum terpasang. Jalankan: pip install -r requirements.txt"
        ) from e
    return build, MediaFileUpload


def _insert_video(
    youtube,
    MediaFileUpload,
    video_path: Path,
    meta: dict,
    privacy: str,
):
    body = {
        "snippet": {
            "title": meta["title"],
            "description": meta["description"],
            "tags": meta["tags"],
            "categoryId": category_id(),
            "defaultLanguage": "id",
            "defaultAudioLanguage": "id",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=8 * 1024 * 1024,
    )
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"  upload {pct}%", flush=True)
    return response


def upload_video(
    video_path: Path,
    meta: dict,
    *,
    privacy: str,
    dry_run: bool = False,
    paper_dir: Path | None = None,
) -> dict:
    if dry_run:
        return {
            "dry_run": True,
            "video_path": str(video_path),
            "title": meta["title"],
            "privacy": privacy,
        }

    build, MediaFileUpload = _require_google()
    from googleapiclient.errors import HttpError

    creds = get_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    desc_mode = "full"
    try:
        response = _insert_video(
            youtube, MediaFileUpload, video_path, meta, privacy
        )
    except HttpError as e:
        err = str(e)
        if paper_dir and "invalidDescription" in err:
            print(
                "  ⚠ Deskripsi ditolak YouTube — coba versi minimal…",
                flush=True,
            )
            meta = {
                **meta,
                "description": build_minimal_description(paper_dir),
            }
            desc_mode = "minimal"
            response = _insert_video(
                youtube, MediaFileUpload, video_path, meta, privacy
            )
        else:
            raise

    vid = response["id"]
    url = f"https://www.youtube.com/watch?v={vid}"
    return {
        "video_id": vid,
        "url": url,
        "title": meta["title"],
        "privacy": privacy,
        "description_mode": desc_mode,
    }


def publish_paper(
    paper_dir: Path,
    *,
    privacy: str | None = None,
    dry_run: bool = False,
    extra_tags: list[str] | None = None,
) -> dict:
    paper_dir = resolve_paper_dir(paper_dir)
    arxiv_id = arxiv_id_from_dir(paper_dir)
    video_path = resolve_video_path(paper_dir, arxiv_id)
    meta = build_metadata(paper_dir, extra_tags=extra_tags)
    priv = (privacy or privacy_default()).lower()
    if priv not in ("public", "unlisted", "private"):
        raise ValueError(f"privacy tidak valid: {priv}")

    print(f"Video: {video_path}")
    print(f"Judul: {meta['title']}")
    print(f"Privacy: {priv}")

    result = upload_video(
        video_path,
        meta,
        privacy=priv,
        dry_run=dry_run,
        paper_dir=paper_dir,
    )
    result["arxiv_id"] = arxiv_id
    result["video_path"] = str(video_path)

    if not dry_run:
        record = {
            **result,
            "description_preview": meta["description"][:200] + "…",
            "tags": meta["tags"],
        }
        out = paper_dir / "youtube-publish.json"
        out.write_text(json.dumps(record, indent=2), encoding="utf-8")
        print(f"Catatan: {out}")
        print(f"URL: {result['url']}")

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload video paper ke YouTube"
    )
    parser.add_argument(
        "paper",
        help="Folder data/<arxiv_id> atau arxiv id",
    )
    parser.add_argument(
        "--privacy",
        choices=["public", "unlisted", "private"],
        help="Default: env YOUTUBE_PRIVACY_DEFAULT atau unlisted",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Hanya tampilkan metadata, tanpa upload",
    )
    parser.add_argument(
        "--tag",
        action="append",
        dest="tags",
        help="Tag tambahan (bisa diulang)",
    )
    args = parser.parse_args()

    try:
        result = publish_paper(
            Path(args.paper),
            privacy=args.privacy,
            dry_run=args.dry_run,
            extra_tags=args.tags,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except FileNotFoundError as e:
        raise SystemExit(str(e)) from e
    except Exception as e:
        raise SystemExit(str(e)) from e


if __name__ == "__main__":
    main()
