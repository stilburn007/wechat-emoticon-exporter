"""Generate the Windows application icon from the supplied raster artwork."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps


def build_icon(source: Path) -> Image.Image:
    with Image.open(source) as original:
        artwork = ImageOps.contain(
            original.convert("RGBA"),
            (248, 248),
            Image.Resampling.LANCZOS,
        )
    canvas = Image.new("RGBA", (256, 256), (255, 255, 255, 255))
    canvas.alpha_composite(
        artwork,
        ((canvas.width - artwork.width) // 2, (canvas.height - artwork.height) // 2),
    )
    return canvas


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    source = root / "assets" / "app-icon.png"
    target = root / "assets" / "app.ico"
    target.parent.mkdir(parents=True, exist_ok=True)
    icon = build_icon(source)
    icon.save(
        target,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
