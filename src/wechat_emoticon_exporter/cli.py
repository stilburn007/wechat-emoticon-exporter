"""Command line interface for wechat-emoticon-exporter."""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional, Sequence

from . import __version__
from .exporter import export_account
from .locate import Account, find_data_roots, find_emoticon_dir, list_accounts


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--data-root",
        action="append",
        default=[],
        metavar="PATH",
        help="WeChat data root (repeatable). Defaults to auto-detection.",
    )
    parser.add_argument(
        "--account",
        metavar="WXID",
        help="Account wxid or folder name to use when several are found.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wechat-emoticon-exporter",
        description="Decrypt and export WeChat / Weixin 4.x custom emoticons.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    list_parser = sub.add_parser("list", help="list detected accounts")
    _add_common(list_parser)

    export_parser = sub.add_parser("export", help="export emoticons for an account")
    _add_common(export_parser)
    export_parser.add_argument(
        "-o", "--out", default="emoticon_export", metavar="DIR",
        help="output directory (default: ./emoticon_export)",
    )
    export_parser.add_argument("--seed", type=int, help="account seed (skips the memory scan)")
    export_parser.add_argument(
        "--key", metavar="HEX", help="raw 16-byte AES key as hex (skips the memory scan)"
    )
    export_parser.add_argument(
        "--no-wxgf", action="store_true", help="do not transcode .wxgf stickers to GIF"
    )
    export_parser.add_argument(
        "--discard-raw", action="store_true", help="delete original .wxgf after conversion"
    )
    export_parser.add_argument(
        "--flat", action="store_true", help="also copy every sticker into <out>/flat"
    )
    export_parser.add_argument(
        "--name-from-db",
        action="store_true",
        help="rename files using captions from the emoticon database (experimental)",
    )
    export_parser.add_argument("--ffmpeg", metavar="PATH", help="path to an ffmpeg executable")

    db_parser = sub.add_parser("db", help="decrypt the account emoticon database")
    _add_common(db_parser)
    db_parser.add_argument(
        "-o", "--out", default="emoticon.db", metavar="FILE", help="output database path"
    )
    return parser


def _discover(roots_arg: Sequence[str]) -> tuple[List[str], List[Account]]:
    roots = find_data_roots(roots_arg)
    if not roots:
        print("[!] no WeChat data root found; pass --data-root PATH", file=sys.stderr)
        return [], []
    return roots, list_accounts(roots)


def _select_account(accounts: List[Account], requested: Optional[str]) -> Optional[Account]:
    if requested:
        for account in accounts:
            if requested in (account.wxid, account.folder_name):
                return account
        print(f"[!] account '{requested}' not found", file=sys.stderr)
        return None
    if len(accounts) == 1:
        return accounts[0]
    if not accounts:
        print("[!] no WeChat accounts found", file=sys.stderr)
        return None
    print("[!] multiple accounts found; pick one with --account:", file=sys.stderr)
    for account in accounts:
        print(f"    {account.folder_name}  (wxid: {account.wxid})", file=sys.stderr)
    return None


def _cmd_list(args: argparse.Namespace) -> int:
    roots, accounts = _discover(args.data_root)
    for root in roots:
        print(f"root: {root}")
    if not accounts:
        print("no accounts found")
        return 1
    for account in accounts:
        emoticon = find_emoticon_dir(account.folder)
        print(f"  {account.folder_name}  wxid={account.wxid}  emoticon={'yes' if emoticon else 'no'}")
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    _roots, accounts = _discover(args.data_root)
    account = _select_account(accounts, args.account)
    if account is None:
        return 1

    out_dir = os.path.abspath(args.out)
    print(f"[*] account: {account.folder_name}")
    print(f"[*] output : {out_dir}")
    try:
        result = export_account(
            account,
            out_dir,
            seed=args.seed,
            key_hex=args.key,
            convert_wxgf=not args.no_wxgf,
            keep_raw=not args.discard_raw,
            ffmpeg=args.ffmpeg,
            make_flat=args.flat,
            name_from_db=args.name_from_db,
        )
    except RuntimeError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 2
    print(f"[OK] exported {result.total_files} files to {out_dir}")
    return 0


def _cmd_db(args: argparse.Namespace) -> int:
    _roots, accounts = _discover(args.data_root)
    account = _select_account(accounts, args.account)
    if account is None:
        return 1
    from .locate import find_db
    from .wcdb import decrypt_db

    db_path = find_db(account.folder)
    if not db_path:
        print("[!] emoticon.db not found", file=sys.stderr)
        return 1
    out_path = os.path.abspath(args.out)
    print(f"[*] decrypting {db_path}")
    result = decrypt_db(db_path, out_path)
    if not result:
        print("[!] failed to decrypt database (is Weixin.exe running?)", file=sys.stderr)
        return 2
    print(f"[OK] wrote {result}")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "list":
        return _cmd_list(args)
    if args.command == "export":
        return _cmd_export(args)
    if args.command == "db":
        return _cmd_db(args)
    parser.print_help()
    return 1
