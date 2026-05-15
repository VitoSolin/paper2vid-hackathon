#!/usr/bin/env python3
"""Offset wiggle untuk animasi karakter (geser + rotasi halus)."""

from __future__ import annotations

import math
from typing import Any


def wiggle_offsets(
    t: float,
    wiggle_cfg: dict[str, Any],
    phase: float = 0.0,
    time_offset: float = 0.0,
) -> tuple[float, float, float]:
    """Return (dx, dy, rot_deg) pada detik t (+ offset global agar fase kontinu)."""
    if not wiggle_cfg.get("enabled", True):
        return 0.0, 0.0, 0.0

    freq = float(wiggle_cfg.get("frequency_hz", 2.4))
    ax = float(wiggle_cfg.get("amplitude_x", 12))
    ay = float(wiggle_cfg.get("amplitude_y", 10))
    ar = float(wiggle_cfg.get("amplitude_rot", 1.5))
    w = 2.0 * math.pi * freq
    tg = t + time_offset

    dx = ax * math.sin(w * tg + phase)
    dy = ay * math.cos(w * tg * 0.9 + phase * 1.1)
    rot = ar * math.sin(w * tg * 1.05 + phase * 0.7)
    return dx, dy, rot


def ffmpeg_overlay_expressions(
    wiggle_cfg: dict[str, Any],
    phase: float,
    base_x: float,
    base_y: float,
    time_offset: float = 0.0,
) -> tuple[str, str]:
    """Ekspresi x/y untuk filter overlay ffmpeg (sama rumus dengan wiggle_offsets)."""
    freq = float(wiggle_cfg.get("frequency_hz", 2.4))
    ax = float(wiggle_cfg.get("amplitude_x", 12))
    ay = float(wiggle_cfg.get("amplitude_y", 10))
    to = f"{time_offset:.4f}"
    x_expr = (
        f"{base_x:.1f}+{ax}*sin(2*PI*{freq}*(t+{to})+{phase:.4f})"
    )
    y_expr = (
        f"{base_y:.1f}+{ay}*cos(2*PI*{freq}*(t+{to})*0.9+{phase * 1.1:.4f})"
    )
    return x_expr, y_expr
