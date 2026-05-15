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
) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(frame_path),
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
        ],
        check=True,
        capture_output=True,
    )


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


def _tts_voice(cfg: dict, speaker: str) -> tuple[str, str]:
    tts = cfg.get("tts", {})
    if speaker in tts and isinstance(tts[speaker], dict):
        entry = tts[speaker]
        return entry.get("voice", "id-ID-ArdiNeural"), entry.get("rate", "+0%")
    if speaker == "paknam":
        return tts.get("voice_a", "id-ID-ArdiNeural"), tts.get("rate", "+0%")
    return tts.get("voice_b", "id-ID-GadisNeural"), tts.get("rate", "+0%")


def render_dialog(
    dialog_path: Path,
    out_mp4: Path | None = None,
    config_path: Path | None = None,
    use_cast: bool | None = None,
) -> Path:
    dialog = load_json(dialog_path)
    arxiv_id = dialog.get("arxiv_id", dialog_path.parent.name)
    paper_dir = dialog_path.parent

    cfg_path = config_path or (
        CAST_CONFIG if (use_cast is True or (use_cast is None and CAST_CONFIG.exists()))
        else CONFIG_DEFAULT
    )
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
            voice, rate = _tts_voice(cfg, speaker if cast_mode else speaker)

            audio_name = f"turn_{i:02d}_{speaker}.mp3"
            audio_file = audio_dir / audio_name
            if not audio_file.exists():
                synthesize_sync(text, voice, audio_file, rate=rate)

            duration = audio_duration(audio_file)

            if cast_mode:
                bg_path = resolve_background(cfg, speaker)
                bg_img = Image.open(bg_path)
                sprites = {}
                for sid in cast_ids:
                    if sid == speaker:
                        sprites[sid] = sprite_for_turn(cfg, sid, expr)
                    else:
                        sprites[sid] = sprite_for_turn(cfg, sid, None)
                frame = render_frame(bg_img, sprites, text, speaker, cfg)
            else:
                frame = render_frame(
                    legacy_bg,
                    {"A": legacy_a, "B": legacy_b},
                    text,
                    speaker,
                    cfg,
                )

            frame_path = tmp_path / f"frame_{i:02d}.png"
            frame.save(frame_path)
            seg_path = tmp_path / f"seg_{i:02d}.mp4"
            make_segment(frame_path, audio_file, duration, seg_path, fps=cfg.get("fps", 30))
            segments.append(seg_path)

        concat_segments(segments, out_mp4)

    meta = {
        "arxiv_id": arxiv_id,
        "output": str(out_mp4.relative_to(ROOT)),
        "turns": len(dialog.get("turns", [])),
        "cast": cast_ids if cast_mode else ["A", "B"],
        "config": str(cfg_path.relative_to(ROOT)),
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
