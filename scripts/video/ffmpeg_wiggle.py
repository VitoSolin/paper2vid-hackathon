#!/usr/bin/env python3
"""Wiggle via ffmpeg overlay expressions — satu encode, tanpa ratusan frame PNG."""

from __future__ import annotations

import subprocess
from pathlib import Path

from wiggle import ffmpeg_overlay_expressions  # noqa: E402


def build_wiggle_filter(
    wiggle_cfg: dict,
    phase: float,
    base_x: float,
    base_y: float,
    time_offset: float = 0.0,
) -> str:
    x_expr, y_expr = ffmpeg_overlay_expressions(
        wiggle_cfg, phase, base_x, base_y, time_offset=time_offset
    )
    return (
        f"[1:v]format=rgba[char];"
        f"[0:v][char]overlay=x='{x_expr}':y='{y_expr}':eval=frame[v]"
    )


def make_segment_wiggle_ffmpeg(
    base_path: Path,
    char_path: Path,
    audio_path: Path,
    duration: float,
    segment_path: Path,
    wiggle_cfg: dict,
    phase: float,
    base_x: float,
    base_y: float,
    fps: int = 30,
    audio_start: float = 0.0,
    time_offset: float = 0.0,
) -> None:
    filt = build_wiggle_filter(
        wiggle_cfg, phase, base_x, base_y, time_offset=time_offset
    )
    dur = f"{duration:.3f}"
    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-framerate",
        str(fps),
        "-t",
        dur,
        "-i",
        str(base_path),
        "-loop",
        "1",
        "-framerate",
        str(fps),
        "-t",
        dur,
        "-i",
        str(char_path),
        "-ss",
        f"{audio_start:.3f}",
        "-i",
        str(audio_path),
        "-filter_complex",
        filt,
        "-map",
        "[v]",
        "-map",
        "2:a",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(fps),
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-t",
        dur,
        "-shortest",
        str(segment_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
