"""In-memory catalog and local cache helpers for decrypted emoticons."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from PIL import Image, ImageSequence

from wechat_emoticon_exporter.exporter import RAW_BACKUP_DIR, SUBDIRS

IMAGE_EXTENSIONS = {".gif", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".wxgf"}
STATIC_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
SPEED_MIN = 0.1
SPEED_MAX = 4.0
MIME_TYPES = {
    ".gif": "image/gif",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".wxgf": "application/octet-stream",
}
INVALID_FILENAME = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
_VARIANT_LOCK = threading.RLock()


def _safe_filename(name: str) -> str:
    cleaned = INVALID_FILENAME.sub("_", name).strip(" .")
    return cleaned or "emoticon"


def _unique_path(directory: Path, filename: str, used: set[str]) -> Path:
    base = _safe_filename(filename)
    stem, suffix = os.path.splitext(base)
    candidate = base
    index = 2
    key = candidate.casefold()
    while key in used or (directory / candidate).exists():
        candidate = f"{stem}_{index}{suffix}"
        key = candidate.casefold()
        index += 1
    used.add(key)
    return directory / candidate


def _image_metadata(path: Path) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "width": None,
        "height": None,
        "frame_count": 1,
        "duration_ms": None,
        "animated": False,
    }
    try:
        with Image.open(path) as image:
            metadata["width"], metadata["height"] = image.size
            frame_count = int(getattr(image, "n_frames", 1) or 1)
            metadata["frame_count"] = frame_count
            animated = bool(getattr(image, "is_animated", False)) and frame_count > 1
            metadata["animated"] = animated
            if animated:
                total = 0
                for index in range(frame_count):
                    image.seek(index)
                    total += int(image.info.get("duration", 100) or 100)
                metadata["duration_ms"] = total
    except Exception:
        pass
    return metadata


@dataclass
class EmoticonItem:
    id: str
    name: str
    path: str
    relative_path: str
    group: str
    category: str
    extension: str
    mime_type: str
    size: int
    modified_at: float
    width: Optional[int] = None
    height: Optional[int] = None
    frame_count: int = 1
    duration_ms: Optional[int] = None
    animated: bool = False

    @property
    def previewable(self) -> bool:
        return self.extension != ".wxgf"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "relative_path": self.relative_path,
            "group": self.group,
            "category": self.category,
            "extension": self.extension,
            "mime_type": self.mime_type,
            "size": self.size,
            "modified_at": self.modified_at,
            "width": self.width,
            "height": self.height,
            "frame_count": self.frame_count,
            "duration_ms": self.duration_ms,
            "animated": self.animated,
            "previewable": self.previewable,
        }


@dataclass
class EmoticonLibrary:
    id: str
    account: str
    wxid: str
    root: str
    created_at: float
    items: list[EmoticonItem] = field(default_factory=list)

    def item_map(self) -> dict[str, EmoticonItem]:
        return {item.id: item for item in self.items}

    def summary(self) -> dict[str, Any]:
        groups: dict[str, int] = {}
        extensions: dict[str, int] = {}
        animated = 0
        total_size = 0
        for item in self.items:
            groups[item.group] = groups.get(item.group, 0) + 1
            extensions[item.extension.lstrip(".")] = extensions.get(item.extension.lstrip("."), 0) + 1
            animated += int(item.animated)
            total_size += item.size
        return {
            "id": self.id,
            "account": self.account,
            "wxid": self.wxid,
            "created_at": self.created_at,
            "total": len(self.items),
            "animated": animated,
            "groups": groups,
            "extensions": extensions,
            "total_size": total_size,
        }

    def to_dict(self) -> dict[str, Any]:
        result = self.summary()
        result["items"] = [item.to_dict() for item in self.items]
        return result

    def variant_path(self, item: EmoticonItem, speed: float = 1.0) -> Path:
        speed = max(SPEED_MIN, min(SPEED_MAX, float(speed)))
        source = Path(item.path)
        if abs(speed - 1.0) < 0.001 or not item.animated or item.extension != ".gif":
            return source

        variant_dir = Path(self.root) / ".preview"
        variant_dir.mkdir(parents=True, exist_ok=True)
        speed_key = f"{round(speed * 100):03d}"
        target = variant_dir / f"{item.id}-{speed_key}.gif"
        if target.exists() and target.stat().st_size > 0:
            return target

        with _VARIANT_LOCK:
            if target.exists() and target.stat().st_size > 0:
                return target
            # Keep this filename short: packaged builds can run under deeply
            # virtualized AppData paths close to Windows' 260-character limit.
            temporary = target.with_name(f"t-{uuid.uuid4().hex[:10]}.tmp")
            try:
                _adjust_gif_speed(source, temporary, speed)
                os.replace(temporary, target)
            finally:
                if temporary.exists():
                    temporary.unlink(missing_ok=True)
        return target


def _adjust_gif_speed(source: Path, target: Path, speed: float) -> None:
    frames: list[Image.Image] = []
    durations: list[int] = []
    loop = 0
    with Image.open(source) as image:
        loop = int(image.info.get("loop", 0) or 0)
        for frame in ImageSequence.Iterator(image):
            frames.append(frame.convert("RGBA").copy())
            duration = int(frame.info.get("duration", image.info.get("duration", 100)) or 100)
            durations.append(max(20, round(duration / speed)))
    if not frames:
        raise RuntimeError(f"No frames found in {source.name}")
    frames[0].save(
        target,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=loop,
        disposal=2,
        optimize=False,
    )


def build_library(
    export_dir: str,
    account: str,
    wxid: str,
    *,
    library_id: Optional[str] = None,
    created_at: Optional[float] = None,
) -> EmoticonLibrary:
    root = Path(export_dir).resolve()
    library = EmoticonLibrary(
        id=library_id or uuid.uuid4().hex,
        account=account,
        wxid=wxid,
        root=str(root),
        created_at=created_at or time.time(),
    )
    items: list[EmoticonItem] = []
    for group in SUBDIRS:
        group_dir = root / group
        if not group_dir.is_dir():
            continue
        for path in sorted(group_dir.rglob("*")):
            if not path.is_file():
                continue
            if RAW_BACKUP_DIR in path.parts:
                continue
            extension = path.suffix.lower()
            if extension not in IMAGE_EXTENSIONS:
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            relative = path.relative_to(root).as_posix()
            item_id = hashlib.sha1(relative.encode("utf-8")).hexdigest()[:16]
            metadata = _image_metadata(path)
            category = "original" if group in {"Persist", "PersistStore"} else "thumbnail"
            items.append(
                EmoticonItem(
                    id=item_id,
                    name=path.name,
                    path=str(path),
                    relative_path=relative,
                    group=group,
                    category=category,
                    extension=extension,
                    mime_type=MIME_TYPES.get(extension, "application/octet-stream"),
                    size=stat.st_size,
                    modified_at=stat.st_mtime,
                    **metadata,
                )
            )
    library.items = items
    return library


def copy_item_to(
    library: EmoticonLibrary,
    item: EmoticonItem,
    target_dir: Path,
    *,
    speed: float,
    preserve_groups: bool,
    used_names: set[str],
) -> Path:
    destination_dir = target_dir / item.group if preserve_groups else target_dir
    destination_dir.mkdir(parents=True, exist_ok=True)
    source = library.variant_path(item, speed)
    destination = _unique_path(destination_dir, item.name, used_names)
    shutil.copy2(source, destination)
    return destination
