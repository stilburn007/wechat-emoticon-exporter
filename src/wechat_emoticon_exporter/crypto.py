"""Key derivation and AES decryption for WeChat 4.x media files.

WeChat / Weixin 4.x stores emoticon files (``business/emoticon/**``) as
AES-128-CBC ciphertext. The IV is the key itself and the key is derived from an
account-level ``seed`` plus the account ``wxid``::

    key       = MD5(f"{seed}{wxid}EMOTICON").digest()[:16]
    plaintext = AES-128-CBC(key, iv=key).decrypt(ciphertext)   # PKCS7 padded

There is **no** universal fixed key: ``seed`` is generated per account/session
and must be read from the running ``Weixin.exe`` process (see :mod:`memory`).
"""

from __future__ import annotations

import hashlib
from typing import Optional

from Crypto.Cipher import AES

#: Recognised plaintext magic bytes -> file extension.
MAGICS = (
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"GIF87a", "gif"),
    (b"GIF89a", "gif"),
    (b"\xff\xd8\xff", "jpg"),
    (b"wxgf", "wxgf"),
    (b"RIFF", "webp"),
    (b"BM", "bmp"),
)


def detect_format(data: bytes) -> Optional[str]:
    """Return a file extension for *data* based on its magic bytes, else ``None``."""
    for magic, ext in MAGICS:
        if data.startswith(magic):
            return ext
    return None


def derive_emoticon_key(seed: int | str, wxid: str) -> bytes:
    """Derive the 16-byte AES key used for an account's emoticon files."""
    digest = hashlib.md5(f"{seed}{wxid}EMOTICON".encode("utf-8")).hexdigest()
    return bytes.fromhex(digest)[:16]


def derive_v2_image_key(seed: int | str, wxid: str) -> bytes:
    """Derive the key used by WeChat 4.x ``V2`` chat images (``msg/**/*.dat``)."""
    return hashlib.md5(f"{seed}{wxid}".encode("utf-8")).hexdigest()[:16].encode("ascii")


def _pkcs7_unpad(data: bytes) -> Optional[bytes]:
    if not data:
        return None
    pad = data[-1]
    if not (1 <= pad <= 16) or len(data) < pad:
        return None
    if data[-pad:] != bytes([pad]) * pad:
        return None
    return data[:-pad]


def decrypt_cbc(data: bytes, key: bytes) -> Optional[bytes]:
    """Decrypt *data* with AES-128-CBC (IV = key) and strip PKCS7 padding.

    Returns ``None`` when the input is malformed or the padding is invalid,
    which is the normal signal that *key* is wrong.
    """
    if not data or len(data) % 16 != 0 or len(key) != 16:
        return None
    try:
        decrypted = AES.new(key, AES.MODE_CBC, key).decrypt(data)
    except ValueError:
        return None
    return _pkcs7_unpad(decrypted)


def verify_key(key: bytes, ciphertext_block: bytes) -> bool:
    """Cheaply test *key* against the first ciphertext block of a known file.

    ``ciphertext_block`` should be the first 16 bytes of any emoticon file.
    """
    if len(key) != 16 or len(ciphertext_block) < 16:
        return False
    try:
        raw = AES.new(key, AES.MODE_CBC, key).decrypt(ciphertext_block[:16])
    except ValueError:
        return False
    return detect_format(raw) is not None
