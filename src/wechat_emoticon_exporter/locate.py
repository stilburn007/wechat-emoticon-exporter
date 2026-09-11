"""Locate WeChat / Weixin data roots and accounts on the local machine."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence

# WeChat 4.x appends a short hex suffix to the account folder name, e.g.
# ``wxid_abc123_7e1e``. The real wxid is the part before the suffix.
_WXID_SUFFIX = re.compile(r"_[0-9a-fA-F]{4}$")

_ACCOUNT_MARKERS = ("db_storage", "business", "msg")
_SKIP_DIRS = {"all_users", "applet", "wmpf", "backup", "backupfiles"}

ENV_VARS = ("WXEMO_DATA_ROOT", "WECHAT_DATA_ROOT")


def normalize_wxid(folder_name: str) -> str:
    """Strip the trailing ``_xxxx`` suffix WeChat 4.x adds to account folders."""
    return _WXID_SUFFIX.sub("", folder_name)


def _candidate_roots() -> List[str]:
    roots: List[str] = []
    for var in ENV_VARS:
        value = os.environ.get(var)
        if value:
            roots.append(value)

    home = os.path.expanduser("~")
    roots += [
        os.path.join(home, "xwechat_files"),
        os.path.join(home, "Documents", "xwechat_files"),
        os.path.join(home, "Documents", "WeChat Files"),
        os.path.join(os.environ.get("APPDATA", ""), "Tencent", "xwechat_files"),
    ]
    for drive in "CDEFGH":
        base = f"{drive}:\\"
        roots += [
            os.path.join(base, "Program Files", "Tencent", "xwechat_files"),
            os.path.join(base, "Program Files (x86)", "Tencent", "xwechat_files"),
            os.path.join(base, "Program", "Tencent Files", "xwechat_files"),
            os.path.join(base, "Tencent", "xwechat_files"),
        ]
    return roots


def find_data_roots(extra: Optional[Sequence[str]] = None) -> List[str]:
    """Return existing candidate data roots, de-duplicated."""
    seen = set()
    out: List[str] = []
    for path in list(extra or []) + _candidate_roots():
        if not path:
            continue
        path = os.path.abspath(os.path.expandvars(path))
        if path in seen:
            continue
        seen.add(path)
        if os.path.isdir(path):
            out.append(path)
    return out


@dataclass
class Account:
    """A WeChat account directory."""

    folder: str
    wxid: str
    folder_name: str

    @property
    def label(self) -> str:
        return self.folder_name


def _is_account_dir(path: str) -> bool:
    name = os.path.basename(path).lower()
    if name in _SKIP_DIRS or not os.path.isdir(path):
        return False
    return any(os.path.isdir(os.path.join(path, marker)) for marker in _ACCOUNT_MARKERS)


def list_accounts(roots: Iterable[str]) -> List[Account]:
    """Return every WeChat account found under *roots*."""
    accounts: List[Account] = []
    seen = set()
    for root in roots:
        try:
            entries = sorted(os.listdir(root))
        except OSError:
            continue
        for name in entries:
            folder = os.path.join(root, name)
            if name.lower() in _SKIP_DIRS or not _is_account_dir(folder):
                continue
            if folder in seen:
                continue
            seen.add(folder)
            accounts.append(Account(folder=folder, wxid=normalize_wxid(name), folder_name=name))
    return accounts


def find_emoticon_dir(account_dir: str) -> Optional[str]:
    """Return the ``business/emoticon`` directory of an account, if present."""
    for sub in ("business/emoticon", "emoticon"):
        path = os.path.join(account_dir, *sub.split("/"))
        if os.path.isdir(path):
            return path
    return None


def find_db(account_dir: str) -> Optional[str]:
    """Return the (encrypted) ``emoticon.db`` path of an account, if present."""
    path = os.path.join(account_dir, "db_storage", "emoticon", "emoticon.db")
    return path if os.path.isfile(path) else None


def candidate_wxids(account: Account) -> List[str]:
    """wxid spellings to try when deriving the key (with and without suffix)."""
    out = [account.wxid]
    if account.folder_name != account.wxid:
        out.append(account.folder_name)
    return out
