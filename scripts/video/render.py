#!/usr/bin/env python3
"""
Render video 9:16 berlapis:
  z=0 background (per pembicara aktif)
  z=1 Pak Nam + Zaba (sprite + ekspresi)
  z=2 subtitle atas
+ TTS terpisah per giliran.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
OUTPUT = ROOT / "output"
CONFIG_DEFAULT = ROOT / "config" / "video.default.json"
CAST_CONFIG = ROOT / "config" / "characters.paknam-zaba.json"

sys.path.insert(0, str(Path(__file__).parent))
from characters import (  # noqa: E402
    load_cast_config,
    normalize_speaker,
    resolve_background,
    sprite_for_turn,
)
from composite import render_frame  # noqa: E402
from generate_assets import ensure_defaults  # noqa: E402
from subtitles import chunk_subtitle  # noqa: E402
from tts import synthesize_sync  # noqa: E402


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def audio_duration(path: Path) -> float:
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(out.stdout.strip()) + 0.12


def make_segment(
    frame_path: Path,
    audio_path: Path,
    duration: float,
    segment_path: Path,
    fps: int = 30,
    audio_start: float = 0.0,
) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        str(frame_path),
        "-ss",
        f"{audio_start:.3f}",
        "-i",
        str(audio_path),
        "-c:v",
        "libx264",
        "-tune",
        "stillimage",
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(fps),
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-t",
        f"{duration:.3f}",
        "-shortest",
        str(segment_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def concat_segments(segment_paths: list[Path], out_mp4: Path) -> None:
    list_file = out_mp4.with_suffix(".txt")
    lines = [f"file '{p.resolve()}'" for p in segment_paths]
    list_file.write_text("\n".join(lines), encoding="utf-8")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            str(out_mp4),
        ],
        check=True,
        capture_output=True,
    )
    list_file.unlink(missing_ok=True)




def render_dialog(
    dialog_path: Path,
    out_mp4: Path | None = None,
    config_path: Path | None = None,
    use_cast: bool | None = None,
) -> Path:
    dialog = load_json(dialog_path)
    arxiv_id = dialog.get("arxiv_id", dialog_path.parent.name)
    paper_dir = dialog_path.parent

    cfg_path = Path(config_path or CONFIG_DEFAULT).resolve()
    if use_cast is not False and CAST_CONFIG.exists():
        if config_path is None or config_path == CAST_CONFIG:
            cfg_path = CAST_CONFIG.resolve()
    cfg = load_json(cfg_path)
    cast_mode = "cast" in cfg

    if out_mp4 is None:
        OUTPUT.mkdir(parents=True, exist_ok=True)
        out_mp4 = OUTPUT / f"{arxiv_id.replace('/', '_')}.mp4"

    audio_dir = paper_dir / "audio"
    audio_dir.mkdir(exist_ok=True)

    # Legacy generic assets
    legacy_bg = legacy_a = legacy_b = None
    if not cast_mode:
        assets = ensure_defaults()
        legacy_bg = Image.open(assets["background"])
        legacy_a = Image.open(assets["speaker_a"]).convert("RGBA")
        legacy_b = Image.open(assets["speaker_b"]).convert("RGBA")

    cast_ids = list(cfg.get("cast", {}).keys()) if cast_mode else ["A", "B"]

    with tempfile.TemporaryDirectory(prefix="p2v_") as tmp:
        tmp_path = Path(tmp)
        segments: list[Path] = []

        for i, turn in enumerate(dialog.get("turns", [])):
            if cast_mode:
                speaker = normalize_speaker(turn["speaker"], cfg)
                expr = turn.get("expression")
            else:
                speaker = turn["speaker"].upper()
                expr = None

            text = turn["text"]
            audio_name = f"turn_{i:02d}_{speaker}.mp3"
            audio_file = audio_dir / audio_name
            if not audio_file.exists():
                synthesize_sync(
                    text,
                    audio_file,
                    speaker=speaker if cast_mode else speaker.lower(),
                    cfg=cfg,
                )

            duration = audio_duration(audio_file)
            max_words = cfg.get("subtitle", {}).get("max_words_per_chunk", 5)
            sub_chunks = chunk_subtitle(text, max_words=max_words)
            chunk_dur = duration / len(sub_chunks)

            if cast_mode:
                bg_path = resolve_background(cfg, speaker)
                bg_img = Image.open(bg_path)
                sprites = {speaker: sprite_for_turn(cfg, speaker, expr)}
            else:
                legacy_sprites = {"A": legacy_a, "B": legacy_b}
                key = speaker if speaker in legacy_sprites else "A"
                sprites = {key: legacy_sprites[key]}
                bg_img = legacy_bg
                speaker = key

            for j, sub_text in enumerate(sub_chunks):
                frame = render_frame(bg_img, sprites, sub_text, speaker, cfg)
                frame_path = tmp_path / f"frame_{i:02d}_{j:02d}.png"
                frame.save(frame_path)
                seg_path = tmp_path / f"seg_{i:02d}_{j:02d}.mp4"
                make_segment(
                    frame_path,
                    audio_file,
                    chunk_dur,
                    seg_path,
                    fps=cfg.get("fps", 30),
                    audio_start=j * chunk_dur,
                )
                segments.append(seg_path)

        concat_segments(segments, out_mp4)

    meta = {
        "arxiv_id": arxiv_id,
        "output": str(out_mp4.relative_to(ROOT)),
        "turns": len(dialog.get("turns", [])),
        "cast": cast_ids if cast_mode else ["A", "B"],
        "config": str(cfg_path.relative_to(ROOT.resolve())),
        "layers": ["background", "characters", "subtitle"],
        "size": f"{cfg.get('width')}x{cfg.get('height')}",
    }
    (paper_dir / "video-render.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    print(json.dumps(meta, indent=2))
    return out_mp4


def main() -> None:
    parser = argparse.ArgumentParser(description="Render video dialog 9:16 + TTS")
    parser.add_argument("dialog", help="dialog-script.json atau folder data/<id>")
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument(
        "--config",
        type=Path,
        help="Default: characters.paknam-zaba.json jika ada",
    )
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="Pakai placeholder assets/ generik",
    )
    args = parser.parse_args()

    dialog_path = Path(args.dialog)
    if dialog_path.is_dir():
        dialog_path = dialog_path / "dialog-script.json"
    if not dialog_path.is_absolute():
        cand = DATA / dialog_path
        if cand.exists():
            dialog_path = cand / "dialog-script.json" if cand.is_dir() else cand
        elif (ROOT / dialog_path).exists():
            dialog_path = ROOT / dialog_path

    if not dialog_path.exists():
        raise SystemExit(f"dialog-script tidak ditemukan: {dialog_path}")

    config_path = args.config
    if args.legacy:
        config_path = CONFIG_DEFAULT
    elif config_path is None and not args.legacy:
        config_path = CAST_CONFIG if CAST_CONFIG.exists() else CONFIG_DEFAULT

    try:
        render_dialog(
            dialog_path,
            out_mp4=args.output,
            config_path=config_path,
            use_cast=not args.legacy,
        )
    except subprocess.CalledProcessError as e:
        err = e.stderr.decode() if e.stderr else str(e)
        raise SystemExit(f"ffmpeg error: {err}") from e
    except Exception as e:
        raise SystemExit(str(e)) from e


if __name__ == "__main__":
    main()
