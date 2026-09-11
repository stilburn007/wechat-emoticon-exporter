"""High-level orchestration: locate, decrypt, split, transcode and export."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from . import __version__, crypto
from .containers import split_container
from .locate import Account, candidate_wxids, find_db, find_emoticon_dir
from .memory import scan_seed_candidates
from .wxgf import find_ffmpeg, transcode_wxgf

SUBDIRS = ("Persist", "PersistStore", "Thumb", "ThumbStore", "Temp")
RAW_BACKUP_DIR = "_wxgf原始格式"
FLAT_DIR = "flat"

Logger = Callable[[str], None]


@dataclass
class ExportResult:
    """Summary of one account export."""

    account: str
    wxid: str
    out_dir: str
    seed: Optional[int] = None
    key: Optional[str] = None
    counts: Dict[str, Dict[str, int]] = field(default_factory=dict)
    converted: int = 0
    named: int = 0
    failed: List[str] = field(default_factory=list)

    @property
    def total_files(self) -> int:
        return sum(entry.get("ok", 0) for entry in self.counts.values())


def _read(path: str) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()


def _write(path: str, data: bytes) -> None:
    with open(path, "wb") as fh:
        fh.write(data)


def probe_ciphertext(emoticon_dir: str) -> Optional[bytes]:
    """Return the first 16 bytes of any emoticon file, used to verify keys."""
    for root, _dirs, names in os.walk(emoticon_dir):
        for name in names:
            path = os.path.join(root, name)
            try:
                if os.path.getsize(path) >= 16:
                    with open(path, "rb") as fh:
                        return fh.read(16)
            except OSError:
                continue
    return None


def resolve_key(
    emoticon_dir: str,
    wxids: List[str],
    seed: Optional[int] = None,
    log: Logger = print,
) -> tuple[int, bytes]:
    """Determine the emoticon key, from a supplied seed or process memory."""
    probe = probe_ciphertext(emoticon_dir)
    if probe is None:
        raise RuntimeError("no emoticon files found to verify the key against")

    if seed is not None:
        for wxid in wxids:
            key = crypto.derive_emoticon_key(seed, wxid)
            if crypto.verify_key(key, probe):
                return int(seed), key
        raise RuntimeError(f"seed {seed} did not match wxid(s): {', '.join(wxids)}")

    log("[*] scanning Weixin.exe memory for the seed ...")
    candidates = scan_seed_candidates()
    log(f"[*] {len(candidates)} seed candidate(s) found")
    for wxid in wxids:
        for value in sorted(candidates):
            key = crypto.derive_emoticon_key(value, wxid)
            if crypto.verify_key(key, probe):
                return value, key
    raise RuntimeError(
        "could not recover the account seed. Make sure Weixin.exe is running and "
        "you are on Windows; or pass --seed / --key explicitly."
    )


def _convert_wxgf_files(
    out_dir: str, ffmpeg: str, keep_raw: bool, log: Logger
) -> int:
    converted = 0
    for sub in ("Persist", "PersistStore"):
        directory = os.path.join(out_dir, sub)
        if not os.path.isdir(directory):
            continue
        raw_dir = os.path.join(directory, RAW_BACKUP_DIR)
        wxgfs = sorted(n for n in os.listdir(directory) if n.endswith(".wxgf"))
        if wxgfs and keep_raw:
            os.makedirs(raw_dir, exist_ok=True)
        for name in wxgfs:
            src = os.path.join(directory, name)
            dst = os.path.join(directory, name[:-5] + ".gif")
            if transcode_wxgf(src, dst, ffmpeg):
                converted += 1
                if keep_raw:
                    os.replace(src, os.path.join(raw_dir, name))
                else:
                    os.remove(src)
            else:
                log(f"[!] failed to transcode {sub}/{name}")
    return converted


def flatten(out_dir: str) -> int:
    """Copy every exported sticker into a single ``flat/`` directory."""
    target = os.path.join(out_dir, FLAT_DIR)
    os.makedirs(target, exist_ok=True)
    used = set()
    count = 0
    for sub in SUBDIRS:
        directory = os.path.join(out_dir, sub)
        if not os.path.isdir(directory):
            continue
        for root, _dirs, names in os.walk(directory):
            if os.path.basename(root) == RAW_BACKUP_DIR:
                continue
            for name in names:
                if name.endswith((".dat", ".thumb")):
                    continue
                candidate = f"{sub}_{name}"
                stem, ext = os.path.splitext(candidate)
                unique = candidate
                index = 2
                while unique in used:
                    unique = f"{stem}_{index}{ext}"
                    index += 1
                used.add(unique)
                with open(os.path.join(root, name), "rb") as src, open(
                    os.path.join(target, unique), "wb"
                ) as dst:
                    dst.write(src.read())
                count += 1
    return count


def _name_from_database(account: Account, out_dir: str, log: Logger) -> int:
    from .naming import load_captions, rename_files
    from .wcdb import decrypt_db

    db_path = find_db(account.folder)
    if not db_path:
        log("[!] emoticon.db not found; keeping md5 names")
        return 0
    decrypted = os.path.join(out_dir, "_emoticon.db")
    if not decrypt_db(db_path, decrypted):
        log("[!] could not decrypt emoticon.db; keeping md5 names")
        return 0
    try:
        captions = load_captions(decrypted)
    finally:
        if os.path.exists(decrypted):
            os.remove(decrypted)
    renamed = 0
    for sub in ("Persist", "PersistStore", "Thumb", "ThumbStore"):
        renamed += rename_files(os.path.join(out_dir, sub), captions, log)
    log(f"[*] named {renamed} file(s) from emoticon.db")
    return renamed


def export_account(
    account: Account,
    out_dir: str,
    seed: Optional[int] = None,
    key_hex: Optional[str] = None,
    convert_wxgf: bool = True,
    keep_raw: bool = True,
    ffmpeg: Optional[str] = None,
    make_flat: bool = False,
    name_from_db: bool = False,
    log: Logger = print,
) -> ExportResult:
    """Export every emoticon of *account* into *out_dir*."""
    emoticon_dir = find_emoticon_dir(account.folder)
    if not emoticon_dir:
        raise RuntimeError(f"no emoticon directory found under {account.folder}")

    os.makedirs(out_dir, exist_ok=True)
    result = ExportResult(account=account.folder_name, wxid=account.wxid, out_dir=out_dir)

    if key_hex:
        key = bytes.fromhex(key_hex)
        if len(key) != 16:
            raise RuntimeError("--key must be a 32-character hex string (16 bytes)")
        result.key = key.hex()
        log(f"[*] using supplied key {result.key}")
    else:
        seed, key = resolve_key(emoticon_dir, candidate_wxids(account), seed=seed, log=log)
        result.seed = seed
        result.key = key.hex()
        log(f"[+] seed={seed}  key={key.hex()}")

    ffmpeg_exe = (ffmpeg or find_ffmpeg()) if convert_wxgf else None
    if convert_wxgf and not ffmpeg_exe:
        log("[!] ffmpeg not found; exporting .wxgf files as-is")
        convert_wxgf = False

    for sub in SUBDIRS:
        src_dir = os.path.join(emoticon_dir, sub)
        if not os.path.isdir(src_dir):
            continue
        dst_dir = os.path.join(out_dir, sub)
        os.makedirs(dst_dir, exist_ok=True)
        ok = fail = 0
        for root, _dirs, names in os.walk(src_dir):
            for name in names:
                path = os.path.join(root, name)
                stem = name[:-6] if name.endswith(".thumb") else name
                plain = crypto.decrypt_cbc(_read(path), key)
                if plain is None:
                    fail += 1
                    result.failed.append(os.path.relpath(path, emoticon_dir))
                    continue
                if sub == "PersistStore":
                    for part in split_container(plain):
                        ext = crypto.detect_format(part)
                        if ext in (None, "wxgf"):
                            continue
                        _write(
                            os.path.join(dst_dir, f"{hashlib.md5(part).hexdigest()}.{ext}"),
                            part,
                        )
                        ok += 1
                else:
                    ext = crypto.detect_format(plain) or "dat"
                    _write(os.path.join(dst_dir, f"{stem}.{ext}"), plain)
                    ok += 1
        result.counts[sub] = {"ok": ok, "fail": fail}
        log(f"[*] {sub}: {ok} ok, {fail} failed")

    if name_from_db:
        result.named = _name_from_database(account, out_dir, log)

    if convert_wxgf:
        result.converted = _convert_wxgf_files(out_dir, ffmpeg_exe, keep_raw, log)
        log(f"[*] wxgf -> gif: {result.converted} converted")

    if make_flat:
        n_flat = flatten(out_dir)
        log(f"[*] flat copy: {n_flat} files -> {os.path.join(out_dir, FLAT_DIR)}")

    manifest = {
        "tool": "wechat-emoticon-exporter",
        "version": __version__,
        "account": result.account,
        "wxid": result.wxid,
        "seed": result.seed,
        "key": result.key,
        "counts": result.counts,
        "converted_wxgf": result.converted,
        "named": result.named,
        "failed": result.failed,
        "total_files": result.total_files,
    }
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)

    return result
