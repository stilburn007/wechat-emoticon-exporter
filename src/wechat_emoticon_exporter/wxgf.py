"""Transcode WeChat ``.wxgf`` (HEVC) animated stickers to GIF.

``.wxgf`` is WeChat's proprietary container around a raw H.265/HEVC stream.
ffmpeg can decode it once the container header is skipped, so this module writes
the payload to a temporary ``.h265`` file and converts it to a looping GIF.

ffmpeg is discovered on ``PATH`` first, then via the optional ``imageio-ffmpeg``
package (``pip install "wechat-emoticon-exporter[wxgf]"``).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Optional

_PALETTE_FILTER = "split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"


def find_ffmpeg() -> Optional[str]:
    """Return a usable ffmpeg executable path, or ``None``."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def _run(ffmpeg: str, source: str, target: str, timeout: int) -> bool:
    try:
        proc = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                source,
                "-vf",
                _PALETTE_FILTER,
                "-loop",
                "0",
                target,
            ],
            capture_output=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0 and os.path.exists(target) and os.path.getsize(target) > 100


def _first_nal(data: bytes) -> Optional[int]:
    markers = [
        pos
        for pos in (
            data.find(b"\x00\x00\x00\x01\x40\x01"),  # VPS
            data.find(b"\x00\x00\x00\x01\x42\x01"),  # SPS
        )
        if pos >= 0
    ]
    return min(markers) if markers else None


def transcode_wxgf(src: str, dst: str, ffmpeg: Optional[str] = None, timeout: int = 120) -> bool:
    """Convert a single ``.wxgf`` file at *src* to a GIF at *dst*.

    Returns ``True`` on success. The output file is removed on failure.
    """
    ffmpeg = ffmpeg or find_ffmpeg()
    if not ffmpeg:
        return False

    with open(src, "rb") as fh:
        data = fh.read()

    tmp = src + ".h265"
    try:
        with open(tmp, "wb") as fh:
            fh.write(data)
        if _run(ffmpeg, tmp, dst, timeout):
            return True

        # Fallback: strip the wxgf header up to the first VPS/SPS NAL unit.
        start = _first_nal(data)
        if start:
            with open(tmp, "wb") as fh:
                fh.write(data[start:])
            if _run(ffmpeg, tmp, dst, timeout):
                return True
        return False
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
        if os.path.exists(dst) and os.path.getsize(dst) <= 100:
            os.remove(dst)
