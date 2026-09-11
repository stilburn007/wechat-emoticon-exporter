"""Name exported stickers using captions from the decrypted emoticon database."""

from __future__ import annotations

import os
import re
import sqlite3
from typing import Dict

_INVALID = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def _clean(name: str) -> str:
    return _INVALID.sub("_", str(name)).strip() or "untitled"


def load_captions(db_path: str) -> Dict[str, str]:
    """Return a ``{md5: caption}`` mapping from a decrypted emoticon.db."""
    captions: Dict[str, str] = {}
    try:
        connection = sqlite3.connect(db_path)
    except sqlite3.Error:
        return captions
    try:
        cursor = connection.cursor()
        try:
            rows = cursor.execute(
                "SELECT md5_, caption_ FROM kStoreEmoticonCaptionsTable"
            )
            for md5, caption in rows:
                if md5 and caption:
                    captions[str(md5).lower()] = str(caption)
        except sqlite3.Error:
            pass
    finally:
        connection.close()
    return captions


def rename_files(directory: str, captions: Dict[str, str], log=print) -> int:
    """Rename ``<md5>.<ext>`` files in *directory* to ``<caption>.<ext>``."""
    if not os.path.isdir(directory):
        return 0
    used = set(os.listdir(directory))
    renamed = 0
    for name in sorted(os.listdir(directory)):
        stem, ext = os.path.splitext(name)
        if len(stem) != 32:
            continue
        caption = captions.get(stem.lower())
        if not caption:
            continue
        base = _clean(caption)
        new_name = f"{base}{ext}"
        index = 2
        while new_name in used:
            new_name = f"{base}_{index}{ext}"
            index += 1
        os.replace(os.path.join(directory, name), os.path.join(directory, new_name))
        used.discard(name)
        used.add(new_name)
        renamed += 1
    return renamed
