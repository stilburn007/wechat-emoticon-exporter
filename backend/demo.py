"""Create a small local emoticon library for trying the interface."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

from .library import EmoticonLibrary, build_library


def _rounded_frame(background: tuple[int, int, int, int] = (0, 0, 0, 0)) -> Image.Image:
    return Image.new("RGBA", (112, 112), background)


def _save_gif(frames: list[Image.Image], path: Path, duration: int = 80) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=duration,
        loop=0,
        disposal=2,
        optimize=False,
    )


def _face(color: tuple[int, int, int, int], accent: tuple[int, int, int, int]) -> list[Image.Image]:
    frames: list[Image.Image] = []
    for index in range(12):
        image = _rounded_frame()
        draw = ImageDraw.Draw(image)
        offset = round(3 * math.sin(index / 12 * math.tau))
        draw.ellipse((18, 18 + offset, 94, 94 + offset), fill=color, outline=(43, 48, 53, 255), width=3)
        draw.ellipse((36, 45 + offset, 44, 53 + offset), fill=(35, 39, 43, 255))
        draw.ellipse((68, 45 + offset, 76, 53 + offset), fill=(35, 39, 43, 255))
        smile = 5 + int(4 * (index % 6) / 5)
        draw.arc((43, 58 + offset, 69, 78 + offset), 12, 168, fill=(35, 39, 43, 255), width=3)
        draw.ellipse((31, 63 + offset, 40, 69 + offset), fill=accent)
        draw.ellipse((72, 63 + offset, 81, 69 + offset), fill=accent)
        if smile > 7:
            draw.arc((49, 66 + offset, 63, 79 + offset), 5, 175, fill=(35, 39, 43, 255), width=2)
        frames.append(image)
    return frames


def _spinner() -> list[Image.Image]:
    frames: list[Image.Image] = []
    colors = [(15, 118, 110, 255), (217, 119, 6, 255), (220, 38, 38, 255), (37, 99, 235, 255)]
    for index in range(16):
        image = _rounded_frame()
        draw = ImageDraw.Draw(image)
        draw.ellipse((15, 15, 97, 97), outline=(231, 226, 216, 255), width=8)
        start = index / 16 * 360
        draw.arc((15, 15, 97, 97), start, start + 110, fill=colors[index % len(colors)], width=8)
        draw.ellipse((48, 48, 64, 64), fill=colors[(index + 1) % len(colors)])
        frames.append(image)
    return frames


def _heartbeat() -> list[Image.Image]:
    frames: list[Image.Image] = []
    for index in range(14):
        scale = 0.88 + 0.12 * abs(math.sin(index / 14 * math.tau))
        width = round(54 * scale)
        height = round(48 * scale)
        image = _rounded_frame()
        draw = ImageDraw.Draw(image)
        left = 56 - width // 2
        top = 57 - height // 2
        right = left + width
        bottom = top + height
        color = (220, 38, 38, 255) if index < 9 else (244, 63, 94, 255)
        draw.ellipse((left, top, left + width // 2, top + height // 2), fill=color)
        draw.ellipse((left + width // 2, top, right, top + height // 2), fill=color)
        draw.polygon(
            [(left + 2, top + height // 3), (right - 2, top + height // 3), (56, bottom)],
            fill=color,
        )
        draw.ellipse((46, 38, 52, 44), fill=(255, 255, 255, 210))
        frames.append(image)
    return frames


def _burst() -> list[Image.Image]:
    frames: list[Image.Image] = []
    colors = [(217, 119, 6, 255), (15, 118, 110, 255), (236, 72, 153, 255), (59, 130, 246, 255)]
    for index in range(16):
        image = _rounded_frame()
        draw = ImageDraw.Draw(image)
        radius = 11 + index % 5 * 2
        draw.ellipse((56 - radius, 56 - radius, 56 + radius, 56 + radius), fill=colors[index % 4])
        angle = index / 16 * 360
        for ray in range(8):
            theta = math.radians(angle + ray * 45)
            x1 = 56 + math.cos(theta) * 29
            y1 = 56 + math.sin(theta) * 29
            x2 = 56 + math.cos(theta) * (42 + index % 3)
            y2 = 56 + math.sin(theta) * (42 + index % 3)
            draw.line((x1, y1, x2, y2), fill=colors[(ray + index) % 4], width=4)
        frames.append(image)
    return frames


def _static_badge(path: Path, background: tuple[int, int, int, int], accent: tuple[int, int, int, int]) -> None:
    image = _rounded_frame(background)
    draw = ImageDraw.Draw(image)
    draw.ellipse((19, 19, 93, 93), outline=accent, width=7)
    draw.line((39, 58, 52, 71), fill=accent, width=8)
    draw.line((52, 71, 76, 42), fill=accent, width=8)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def build_demo_library(runtime_dir: str) -> EmoticonLibrary:
    root = Path(runtime_dir) / "demo-library"
    persist = root / "Persist"
    thumbs = root / "ThumbStore"
    persist.mkdir(parents=True, exist_ok=True)
    thumbs.mkdir(parents=True, exist_ok=True)

    _save_gif(_face((255, 214, 102, 255), (239, 68, 68, 170)), persist / "happy_bounce.gif")
    _save_gif(_face((134, 239, 172, 255), (37, 99, 235, 160)), persist / "friendly_green.gif", 90)
    _save_gif(_spinner(), persist / "loading_spin.gif", 65)
    _save_gif(_heartbeat(), persist / "heartbeat.gif", 75)
    _save_gif(_burst(), persist / "celebration.gif", 70)
    _static_badge(persist / "approved.png", (239, 246, 255, 255), (37, 99, 235, 255))
    _static_badge(persist / "ready.png", (240, 253, 244, 255), (15, 118, 110, 255))

    _save_gif(_face((196, 181, 253, 255), (236, 72, 153, 160)), thumbs / "happy_bounce_thumb.gif", 100)
    _static_badge(thumbs / "approved_thumb.png", (255, 251, 235, 255), (217, 119, 6, 255))

    return build_library(str(root), "演示账号", "wxid_demo")
