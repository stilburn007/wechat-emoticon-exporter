"""Export every detected WeChat account using the Python API.

Run with:  python examples/batch_export.py [output_root]
"""

from __future__ import annotations

import sys

from wechat_emoticon_exporter.exporter import export_account
from wechat_emoticon_exporter.locate import find_data_roots, list_accounts


def main() -> int:
    output_root = sys.argv[1] if len(sys.argv) > 1 else "emoticon_export"
    accounts = list_accounts(find_data_roots())
    if not accounts:
        print("no WeChat accounts found")
        return 1

    for account in accounts:
        print(f"==> {account.folder_name}")
        try:
            result = export_account(account, f"{output_root}/{account.wxid}")
        except RuntimeError as exc:
            print(f"    skipped: {exc}")
            continue
        print(f"    exported {result.total_files} files, {result.converted} wxgf converted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
