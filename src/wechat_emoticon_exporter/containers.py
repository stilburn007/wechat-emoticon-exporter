"""Split concatenated WeChat ``PersistStore`` containers into single files.

``business/emoticon/PersistStore/**`` files may hold several stickers
concatenated back to back. This module walks the byte stream, recognises known
image magics (PNG / GIF / JPEG) and parses each format to its real end marker,
which avoids false positives from magic bytes appearing inside image data.
"""

from __future__ import annotations

import struct
from typing import List, Optional

from .crypto import detect_format

_MIN_PART = 16


def _png_end(data: bytes, start: int) -> Optional[int]:
    if data[start : start + 8] != b"\x89PNG\r\n\x1a\n":
        return None
    pos = start + 8
    n = len(data)
    while pos + 8 <= n:
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        chunk_type = data[pos + 4 : pos + 8]
        if pos + 8 + length + 4 > n:
            return None
        if chunk_type == b"IEND":
            return pos + 8 + length + 4
        pos += 8 + length + 4
    return None


def _gif_end(data: bytes, start: int) -> Optional[int]:
    if data[start : start + 6] not in (b"GIF87a", b"GIF89a"):
        return None
    pos = start + 6
    n = len(data)
    if pos + 7 > n:
        return None
    flags = data[pos + 4]
    pos += 7
    if flags & 0x80:  # global colour table
        pos += 3 * (2 ** ((flags & 0x07) + 1))
    while pos < n:
        block = data[pos]
        if block == 0x3B:  # trailer
            return pos + 1
        if block == 0x21:  # extension introducer
            pos += 2
        elif block == 0x2C:  # image descriptor
            pos += 10
            if pos <= n and data[pos - 1] & 0x80:  # local colour table
                pos += 3 * (2 ** ((data[pos - 1] & 0x07) + 1))
            if pos >= n:
                return None
            pos += 1  # LZW minimum code size
        else:
            return None
        # Skip data sub-blocks (length-prefixed, 0-terminated).
        while pos < n:
            size = data[pos]
            pos += 1
            if size == 0:
                break
            pos += size
        if pos > n:
            return None
    return None


def _jpeg_end(data: bytes, start: int) -> Optional[int]:
    if data[start : start + 2] != b"\xff\xd8":
        return None
    pos = start + 2
    n = len(data)
    while pos + 2 <= n:
        if data[pos] != 0xFF:
            pos += 1
            continue
        if data[pos + 1] == 0x00:  # byte stuffing
            pos += 2
            continue
        marker = data[pos + 1]
        if marker == 0xD9:  # EOI
            return pos + 2
        if marker == 0x01 or 0xD0 <= marker <= 0xD8:
            pos += 2
            continue
        if pos + 4 > n:
            return None
        seg_len = struct.unpack(">H", data[pos + 2 : pos + 4])[0]
        if seg_len < 2 or pos + 2 + seg_len > n:
            return None
        pos += 2 + seg_len
    return None


def _parse_end(data: bytes, start: int, ext: str) -> Optional[int]:
    if ext == "png":
        return _png_end(data, start)
    if ext == "gif":
        return _gif_end(data, start)
    if ext == "jpg":
        return _jpeg_end(data, start)
    return None  # wxgf / webp: variable structure, cannot parse precisely


def split_container(data: bytes) -> List[bytes]:
    """Split *data* into a list of individual image byte strings."""
    parts: List[bytes] = []
    i = 0
    n = len(data)
    while i < n - 3:
        ext = detect_format(data[i:])
        if ext is None:
            i += 1
            continue
        end = _parse_end(data, i, ext)
        if end is None:
            if ext in ("wxgf", "webp"):
                nxt = None
                for j in range(i + 4, n - 3):
                    if detect_format(data[j:]) is not None:
                        nxt = j
                        break
                end = nxt if nxt is not None else n
            else:
                i += 1
                continue
        if end - i < _MIN_PART:
            i += 1
            continue
        parts.append(data[i:end])
        i = end
    return parts
