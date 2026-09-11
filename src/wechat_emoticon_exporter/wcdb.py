"""Decrypt WeChat 4.x WCDB (SQLCipher4) databases.

The emoticon database (``db_storage/emoticon/emoticon.db``) maps sticker files
to their captions and sticker-pack names. Decrypting it is optional and only
needed for :mod:`naming`.

The page format and memory-key discovery are adapted from the open-source
projects ``TANGandXue/wcdb-key-tool`` and ``CN-Grace/Wechat-Emoticon-Parser``
(MIT licensed). This code is Windows-only.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import struct
from typing import List, Optional

from . import memory as _mem

PAGE = 4096
SALT_SIZE = 16
HMAC_SIZE = 64
RESERVE = 80
CIPHER_NAME = b"com.Tencent.WCDB.Config.Cipher"
XOR_MASK = bytes.fromhex(
    "d2c7442458020000004889442450488b450048844c2448488944254048584c24"
)
LITERAL_RE = re.compile(rb"[xX]'([0-9a-fA-F]{64,192})'")
BLOB_MAX = 1024
MAX_ADDR = 0x0000_8000_0000_0000


def _u64(data: bytes, offset: int) -> int:
    return struct.unpack_from("<Q", data, offset)[0] if offset + 8 <= len(data) else 0


def _xor_repeat(data: bytes, mask: bytes) -> bytes:
    return bytes(value ^ mask[i % len(mask)] for i, value in enumerate(data))


def verify_key(enc_key: bytes, page1: bytes) -> bool:
    """Verify a SQLCipher4 encryption key against page 1 of a database."""
    salt = page1[:SALT_SIZE]
    mac_salt = bytes(byte ^ 0x3A for byte in salt)
    mac_key = hashlib.pbkdf2_hmac("sha512", enc_key, mac_salt, 2, dklen=32)
    hmac_data = page1[SALT_SIZE : PAGE - RESERVE + 16]
    stored = page1[PAGE - HMAC_SIZE : PAGE]
    mac = hmac.new(mac_key, hmac_data, hashlib.sha512)
    mac.update(struct.pack("<I", 1))
    return hmac.compare_digest(mac.digest(), stored)


def decrypt_page(enc_key: bytes, page: bytes, page_number: int) -> bytes:
    """Decrypt a single 4096-byte SQLCipher4 page."""
    from Crypto.Cipher import AES

    iv = page[PAGE - RESERVE : PAGE - RESERVE + 16]
    if page_number == 1:
        decrypted = AES.new(enc_key, AES.MODE_CBC, iv).decrypt(page[SALT_SIZE : PAGE - RESERVE])
        return b"SQLite format 3\x00" + decrypted + b"\x00" * RESERVE
    decrypted = AES.new(enc_key, AES.MODE_CBC, iv).decrypt(page[: PAGE - RESERVE])
    return decrypted + b"\x00" * RESERVE


def scan_candidate_keys(pid: int) -> List[bytes]:
    """Scan a process for SQLCipher4 key candidates embedded in WCDB config."""
    handle = _mem._open_process(pid)
    if not handle:
        return []
    try:
        regions = _mem.iter_regions(handle)
        needle_addrs = set()
        for base, size in regions:
            offset = 0
            tail = b""
            tail_base = base
            while offset < size:
                current = min(_mem.CHUNK, size - offset)
                chunk = _mem._read(handle, base + offset, current)
                if chunk:
                    data = tail + chunk
                    data_base = tail_base if tail else base + offset
                    pos = data.find(CIPHER_NAME)
                    while pos >= 0:
                        needle_addrs.add(data_base + pos)
                        pos = data.find(CIPHER_NAME, pos + 1)
                    tail = data[-32:]
                    tail_base = data_base + max(0, len(data) - len(tail))
                else:
                    tail = b""
                    tail_base = base + offset + current
                offset += current
        if not needle_addrs:
            return []

        candidates: List[bytes] = []
        seen = set()
        patterns = [
            struct.pack("<Q", address) + struct.pack("<Q", len(CIPHER_NAME))
            for address in needle_addrs
        ]
        for base, size in regions:
            offset = 0
            tail = b""
            tail_base = base
            while offset < size:
                current = min(_mem.CHUNK, size - offset)
                chunk = _mem._read(handle, base + offset, current)
                if chunk:
                    data = tail + chunk
                    data_base = tail_base if tail else base + offset
                    for pattern in patterns:
                        pos = data.find(pattern)
                        while pos >= 0:
                            node_addr = data_base + pos
                            node = _mem._read(handle, node_addr - 0x10, 0x50)
                            if node and len(node) >= 0x40:
                                if (
                                    _u64(node, 0x10) in needle_addrs
                                    and _u64(node, 0x18) == len(CIPHER_NAME)
                                ):
                                    config = _u64(node, 0x28)
                                    if 0x10000 <= config < MAX_ADDR:
                                        obj = _mem._read(handle, config + 0x88, 0x28)
                                        if obj and len(obj) >= 0x18:
                                            data_ptr = _u64(obj, 0x8)
                                            data_len = _u64(obj, 0x10)
                                            if (
                                                0 < data_len <= BLOB_MAX
                                                and 0x10000 <= data_ptr < MAX_ADDR
                                            ):
                                                blob = _mem._read(handle, data_ptr, int(data_len))
                                                if blob and len(blob) == data_len:
                                                    decoded = _xor_repeat(blob, XOR_MASK)
                                                    for match in LITERAL_RE.finditer(decoded):
                                                        run = match.group(1).decode("ascii").lower()
                                                        starts = [0]
                                                        if len(run) > 96:
                                                            starts.extend(range(0, len(run) - 63, 32))
                                                        for start in dict.fromkeys(starts):
                                                            if start + 64 > len(run):
                                                                continue
                                                            try:
                                                                key = bytes.fromhex(run[start : start + 64])
                                                            except ValueError:
                                                                continue
                                                            if len(set(key)) < 15 or key in seen:
                                                                continue
                                                            seen.add(key)
                                                            candidates.append(key)
                            pos = data.find(pattern, pos + 1)
                    tail = data[-0x80:]
                    tail_base = data_base + max(0, len(data) - len(tail))
                else:
                    tail = b""
                    tail_base = base + offset + current
                offset += current
        return candidates
    finally:
        _mem._kernel32.CloseHandle(handle)


def decrypt_db(db_path: str, out_path: str, pid: Optional[int] = None) -> Optional[str]:
    """Decrypt *db_path* to *out_path*. Returns the output path or ``None``."""
    if not os.path.isfile(db_path):
        return None
    size = os.path.getsize(db_path)
    if size < PAGE:
        return None
    with open(db_path, "rb") as fh:
        page1 = fh.read(PAGE)

    if pid is None:
        pids = _mem.list_pids()
        pid = pids[0] if pids else None
    if pid is None:
        return None

    enc_key = next((key for key in scan_candidate_keys(pid) if verify_key(key, page1)), None)
    if enc_key is None:
        return None

    total_pages = (size + PAGE - 1) // PAGE
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(db_path, "rb") as fin, open(out_path, "wb") as fout:
        for page_number in range(1, total_pages + 1):
            page = fin.read(PAGE)
            if len(page) < PAGE:
                if not page:
                    break
                page += b"\x00" * (PAGE - len(page))
            fout.write(decrypt_page(enc_key, page, page_number))
    return out_path
