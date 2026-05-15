#!/usr/bin/env python3
"""
Render video dialog berlapis:
  z=0 background | z=1 dua karakter (bergantian aktif) | z=2 subtitle atas
+ TTS per giliran.
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

sys.path.insert(0, str(Path(__file__).parent))
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
    return float(out.stdout.strip()) + 0.15  # jeda kecil antar giliran


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


def render_dialog(
    dialog_path: Path,
    out_mp4: Path | None = None,
    config_path: Path | None = None,
    background: Path | None = None,
    char_a: Path | None = None,
    char_b: Path | None = None,
) -> Path:
    dialog = load_json(dialog_path)
    arxiv_id = dialog.get("arxiv_id", dialog_path.parent.name)
    paper_dir = dialog_path.parent

    cfg = load_json(config_path or CONFIG_DEFAULT)
    assets = ensure_defaults()
    bg_img = Image.open(background or assets["background"])
    img_a = Image.open(char_a or assets["speaker_a"]).convert("RGBA")
    img_b = Image.open(char_b or assets["speaker_b"]).convert("RGBA")

    tts_cfg = cfg.get("tts", {})
    voice_a = tts_cfg.get("voice_a", "id-ID-GadisNeural")
    voice_b = tts_cfg.get("voice_b", "id-ID-ArdiNeural")
    rate = tts_cfg.get("rate", "+0%")

    if out_mp4 is None:
        OUTPUT.mkdir(parents=True, exist_ok=True)
        out_mp4 = OUTPUT / f"{arxiv_id.replace('/', '_')}.mp4"

    audio_dir = paper_dir / "audio"
    audio_dir.mkdir(exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="p2v_") as tmp:
        tmp_path = Path(tmp)
        segments: list[Path] = []

        for i, turn in enumerate(dialog.get("turns", [])):
            speaker = turn["speaker"].upper()
            text = turn["text"]
            voice = voice_a if speaker == "A" else voice_b

            audio_file = audio_dir / f"turn_{i:02d}_{speaker}.mp3"
            if not audio_file.exists():
                synthesize_sync(text, voice, audio_file, rate=rate)

            duration = audio_duration(audio_file)
            frame = render_frame(
                bg_img,
                img_a,
                img_b,
                text,
                active_speaker=speaker,
                cfg=cfg,
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
        "layers": ["background", "characters", "subtitle"],
    }
    (paper_dir / "video-render.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    print(json.dumps(meta, indent=2))
    return out_mp4


def main() -> None:
    parser = argparse.ArgumentParser(description="Render video dialog (layered + TTS)")
    parser.add_argument(
        "dialog",
        help="Path ke dialog-script.json atau folder data/<arxiv_id>",
    )
    parser.add_argument("-o", "--output", type=Path, help="Output .mp4")
    parser.add_argument("--config", type=Path, default=CONFIG_DEFAULT)
    parser.add_argument("--background", type=Path)
    parser.add_argument("--char-a", type=Path)
    parser.add_argument("--char-b", type=Path)
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

    try:
        render_dialog(
            dialog_path,
            out_mp4=args.output,
            config_path=args.config,
            background=args.background,
            char_a=args.char_a,
            char_b=args.char_b,
        )
    except subprocess.CalledProcessError as e:
        err = e.stderr.decode() if e.stderr else str(e)
        raise SystemExit(f"ffmpeg error: {err}") from e
    except Exception as e:
        raise SystemExit(str(e)) from e


if __name__ == "__main__":
    main()
