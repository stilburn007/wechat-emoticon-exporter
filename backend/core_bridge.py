"""Bridge the Studio app to the existing exporter package."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Callable, Optional


def _load_core() -> tuple[Any, Any, Any, Any, Any]:
    try:
        from wechat_emoticon_exporter import crypto, exporter, locate, memory
        from wechat_emoticon_exporter.wxgf import find_ffmpeg

        return crypto, exporter, locate, memory, find_ffmpeg
    except ModuleNotFoundError:
        pass

    for parent in Path(__file__).resolve().parents:
        src = parent / "src"
        if (src / "wechat_emoticon_exporter").is_dir():
            src_text = str(src)
            if src_text not in sys.path:
                sys.path.insert(0, src_text)
            break

    from wechat_emoticon_exporter import crypto, exporter, locate, memory
    from wechat_emoticon_exporter.wxgf import find_ffmpeg

    return crypto, exporter, locate, memory, find_ffmpeg


crypto, exporter, locate, memory, find_ffmpeg = _load_core()

_CREDENTIAL_RE = re.compile(r"seed=\d+\s+key=[0-9a-fA-F]+")
_PALETTE_FILTER = "split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"
_TRANSCODE_PATCH_LOCK = threading.Lock()
_DISPLAY_NAME_RE = re.compile(rb"<displayname>([^<]{1,128})</displayname>", re.IGNORECASE)
_DISPLAY_NAME_CACHE: dict[str, str] = {}


def _run_ffmpeg_hidden(
    ffmpeg: str,
    source: str,
    target: str,
    timeout: int,
    input_format: Optional[str] = None,
) -> bool:
    """Run ffmpeg without flashing a console window in the packaged app."""
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if sys.platform == "win32" else 0
    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
    ]
    if input_format:
        command.extend(["-f", input_format])
    command.extend(
        [
            "-i",
            source,
            "-vf",
            _PALETTE_FILTER,
            "-loop",
            "0",
            target,
        ]
    )
    try:
        process = subprocess.run(
            command,
            capture_output=True,
            timeout=timeout,
            creationflags=creation_flags,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return process.returncode == 0 and os.path.exists(target) and os.path.getsize(target) > 100


def _transcode_wxgf_silent(
    src: str,
    dst: str,
    ffmpeg: Optional[str] = None,
    timeout: int = 120,
) -> bool:
    """Transcode WXGF with a hidden ffmpeg and an explicit raw-HEVC fallback."""
    from wechat_emoticon_exporter import wxgf as wxgf_module

    ffmpeg = ffmpeg or find_ffmpeg()
    if not ffmpeg:
        return False
    with open(src, "rb") as handle:
        data = handle.read()

    # Small stickers should fail quickly instead of blocking the whole queue.
    timeout = min(timeout, 20)
    temporary = src + ".h265"
    try:
        with open(temporary, "wb") as handle:
            handle.write(data)
        if _run_ffmpeg_hidden(ffmpeg, temporary, dst, timeout):
            return True

        start = wxgf_module._first_nal(data)
        if start:
            with open(temporary, "wb") as handle:
                handle.write(data[start:])
            if _run_ffmpeg_hidden(ffmpeg, temporary, dst, timeout, input_format="hevc"):
                return True
        return False
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)
        if os.path.exists(dst) and os.path.getsize(dst) <= 100:
            os.remove(dst)


def _wxgf_count(output_dir: str) -> int:
    total = 0
    for group in ("Persist", "PersistStore"):
        directory = Path(output_dir) / group
        if not directory.is_dir():
            continue
        total += sum(1 for path in directory.iterdir() if path.is_file() and path.name.endswith(".wxgf"))
    return total


def safe_log(message: str) -> str:
    """Remove account credentials before a log line reaches the browser."""
    if "using supplied key" in message:
        return "[*] using supplied key"
    return _CREDENTIAL_RE.sub("credentials verified", message)


def runtime_info() -> dict[str, Any]:
    ffmpeg = find_ffmpeg()
    return {
        "platform": sys.platform,
        "windows": sys.platform == "win32",
        "ffmpeg": ffmpeg,
        "ffmpeg_available": bool(ffmpeg),
    }


def discover_accounts(extra_roots: Optional[Iterable[str]] = None) -> tuple[list[str], list[Any]]:
    roots = locate.find_data_roots(list(extra_roots or []))
    accounts = [
        account
        for account in locate.list_accounts(roots)
        if locate.find_emoticon_dir(account.folder)
    ]
    accounts.sort(key=lambda account: Path(account.folder).stat().st_mtime, reverse=True)
    _resolve_display_names(accounts)
    return roots, accounts


def account_to_dict(account: Any) -> dict[str, Any]:
    emoticon_dir = locate.find_emoticon_dir(account.folder)
    return {
        "folder_name": account.folder_name,
        "wxid": account.wxid,
        "label": account.label,
        "display_name": _DISPLAY_NAME_CACHE.get(account.wxid),
        "has_emoticon": bool(emoticon_dir),
        "emoticon_dir": emoticon_dir,
        "last_modified": Path(account.folder).stat().st_mtime,
    }


def account_display_name(account: Any) -> str:
    return _DISPLAY_NAME_CACHE.get(account.wxid, account.folder_name)


def _resolve_display_names(accounts: list[Any]) -> None:
    """Read display names from WeChat process metadata and associate by wxid."""
    wxids = {account.wxid: account.wxid.encode("utf-8") for account in accounts}
    contextual: dict[str, Counter[str]] = {wxid: Counter() for wxid in wxids}
    unbound: Counter[str] = Counter()

    for pid in memory.list_pids():
        handle = memory._open_process(pid)
        if not handle:
            continue
        try:
            for base, size in memory.iter_regions(handle, writable_only=False):
                offset = 0
                tail = b""
                while offset < size:
                    current = min(memory.CHUNK, size - offset)
                    chunk = memory._read(handle, base + offset, current)
                    if chunk:
                        blob = tail + chunk
                        for match in _DISPLAY_NAME_RE.finditer(blob):
                            value = match.group(1).decode("utf-8", "replace").strip()
                            if not value or len(value) > 80:
                                continue
                            context = blob[max(0, match.start() - 2048) : match.end() + 2048]
                            assigned = False
                            for wxid, needle in wxids.items():
                                if needle in context:
                                    contextual[wxid][value] += 1
                                    assigned = True
                            if not assigned:
                                unbound[value] += 1
                        tail = blob[-4096:]
                    else:
                        tail = b""
                    offset += current
        finally:
            memory._kernel32.CloseHandle(handle)

    for account in accounts:
        choices = contextual.get(account.wxid)
        if choices:
            _DISPLAY_NAME_CACHE[account.wxid] = choices.most_common(1)[0][0]
    if len(accounts) == 1 and accounts[0].wxid not in _DISPLAY_NAME_CACHE and unbound:
        _DISPLAY_NAME_CACHE[accounts[0].wxid] = unbound.most_common(1)[0][0]


def select_account(accounts: list[Any], requested: str) -> Any:
    for account in accounts:
        if requested in (account.wxid, account.folder_name):
            return account
    raise RuntimeError(f"Account '{requested}' was not found.")


def _sample_sources(emoticon_dir: str, limit: int = 96) -> list[tuple[bytes, Path]]:
    """Collect first AES blocks from several files, preferring real stickers."""
    root = Path(emoticon_dir)
    candidates: list[Path] = []
    for group in ("Persist", "PersistStore", "ThumbStore", "Thumb", "Temp"):
        group_root = root / group
        if not group_root.is_dir():
            continue
        candidates.extend(
            path
            for path in sorted(group_root.rglob("*"))
            if path.is_file() and path.stat().st_size >= 16
        )
    if not candidates:
        candidates = [
            path
            for path in sorted(root.rglob("*"))
            if path.is_file() and path.stat().st_size >= 16
        ]

    samples: list[tuple[bytes, Path]] = []
    seen: set[bytes] = set()
    for path in candidates:
        try:
            block = path.read_bytes()[:16]
        except OSError:
            continue
        if block in seen:
            continue
        seen.add(block)
        samples.append((block, path))
        if len(samples) >= limit:
            break
    if not samples:
        raise RuntimeError("No emoticon files were found to verify the account key.")
    return samples


def _sample_ciphertexts(emoticon_dir: str, limit: int = 96) -> list[bytes]:
    return [block for block, _path in _sample_sources(emoticon_dir, limit)]


def _key_score(key: bytes, sample_blocks: list[bytes]) -> int:
    return sum(crypto.verify_key(key, block) for block in sample_blocks)


def _full_key_score(key: bytes, samples: list[tuple[bytes, Path]], limit: int = 24) -> int:
    score = 0
    for _block, path in samples[:limit]:
        try:
            plain = crypto.decrypt_cbc(path.read_bytes(), key)
        except OSError:
            continue
        score += int(plain is not None and crypto.detect_format(plain) is not None)
    return score


def _reliable_match(first_block_score: int, full_score: int, sample_count: int) -> bool:
    return full_score > 0 or (
        sample_count > 1 and first_block_score >= min(2, sample_count)
    )


def resolve_account_key(
    account: Any,
    emoticon_dir: str,
    *,
    seed: Optional[int] = None,
    key_hex: Optional[str] = None,
    log: Callable[[str], None] = print,
) -> tuple[Optional[int], bytes]:
    """Resolve the account key against many ciphertext samples.

    Some account folders contain placeholder or alternate files whose first
    block cannot be decrypted with the ordinary emoticon key. Testing only the
    first file makes otherwise valid memory candidates look wrong.
    """
    samples = _sample_sources(emoticon_dir)
    sample_blocks = [block for block, _path in samples]
    wxids = locate.candidate_wxids(account)

    if key_hex:
        key = bytes.fromhex(key_hex)
        if len(key) != 16:
            raise RuntimeError("The key must be exactly 32 hexadecimal characters.")
        first_block_score = _key_score(key, sample_blocks)
        full_score = _full_key_score(key, samples) if first_block_score else 0
        if not _reliable_match(first_block_score, full_score, len(samples)):
            raise RuntimeError("The supplied key did not match any emoticon file.")
        return None, key

    if seed is not None:
        best: tuple[int, int, Optional[bytes]] = (0, 0, None)
        for wxid in wxids:
            key = crypto.derive_emoticon_key(seed, wxid)
            first_block_score = _key_score(key, sample_blocks)
            full_score = _full_key_score(key, samples) if first_block_score else 0
            if _reliable_match(first_block_score, full_score, len(samples)) and (
                first_block_score,
                full_score,
            ) > best[:2]:
                best = (first_block_score, full_score, key)
        if best[2] is None:
            raise RuntimeError(f"Seed {seed} did not match the account emoticons.")
        return int(seed), best[2]

    log("[*] scanning Weixin.exe memory for the seed ...")
    candidates = memory.scan_seed_candidates()
    log(f"[*] {len(candidates)} seed candidate(s) found")
    best: tuple[int, int, Optional[int], Optional[bytes]] = (0, 0, None, None)
    stop_score = min(8, len(sample_blocks))
    for wxid in wxids:
        for value in sorted(candidates):
            key = crypto.derive_emoticon_key(value, wxid)
            first_block_score = _key_score(key, sample_blocks)
            if first_block_score < 1:
                continue
            if len(sample_blocks) > 4 and first_block_score < min(2, len(sample_blocks)):
                continue
            full_score = _full_key_score(key, samples)
            if _reliable_match(first_block_score, full_score, len(samples)) and (
                first_block_score,
                full_score,
            ) > best[:2]:
                best = (first_block_score, full_score, value, key)
                if first_block_score >= stop_score and full_score > 0:
                    return value, key
    if best[3] is None:
        raise RuntimeError(
            f"Could not recover a consistent key for {account.folder_name}. "
            "Select the account marked as Recently Used, keep Weixin.exe logged in, "
            "or provide a Seed / Key in Advanced Options."
        )
    return best[2], best[3]


def scan_account(
    account: Any,
    output_dir: str,
    *,
    seed: Optional[int] = None,
    key_hex: Optional[str] = None,
    name_from_db: bool = False,
    log: Callable[[str], None] = print,
) -> Any:
    """Decrypt one account into an app-managed cache directory."""
    emoticon_dir = locate.find_emoticon_dir(account.folder)
    if not emoticon_dir:
        raise RuntimeError(f"No emoticon directory was found under {account.folder}.")
    resolved_seed, resolved_key = resolve_account_key(
        account,
        emoticon_dir,
        seed=seed,
        key_hex=key_hex,
        log=log,
    )
    log("[+] credentials verified")
    transcode_state = {"done": 0, "total": 0}

    def transcode_with_progress(
        src: str,
        dst: str,
        ffmpeg: Optional[str] = None,
        timeout: int = 120,
    ) -> bool:
        if transcode_state["total"] == 0:
            transcode_state["total"] = max(1, _wxgf_count(output_dir))
        converted = _transcode_wxgf_silent(src, dst, ffmpeg, timeout)
        transcode_state["done"] += 1
        log(
            f"[progress] wxgf {transcode_state['done']}/{transcode_state['total']} "
            f"{Path(src).name}"
        )
        return converted

    with _TRANSCODE_PATCH_LOCK:
        previous_transcoder = exporter.transcode_wxgf
        exporter.transcode_wxgf = transcode_with_progress
        try:
            return exporter.export_account(
                account,
                output_dir,
                seed=resolved_seed,
                key_hex=resolved_key.hex(),
                convert_wxgf=True,
                keep_raw=False,
                make_flat=False,
                name_from_db=name_from_db,
                log=lambda message: log(safe_log(message)),
            )
        finally:
            exporter.transcode_wxgf = previous_transcoder
