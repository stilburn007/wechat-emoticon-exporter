"""Small launcher for the onedir desktop application."""

from __future__ import annotations

import ctypes
import subprocess
import sys
from pathlib import Path


def main() -> int:
    base = Path(sys.executable).resolve().parent
    executable = base / "WeChatEmoticonStudio" / "WeChatEmoticonStudio.exe"
    if not executable.is_file():
        ctypes.windll.user32.MessageBoxW(
            0,
            f"找不到应用程序：\n{executable}",
            "微信表情工坊",
            0x10,
        )
        return 1
    subprocess.Popen([str(executable)], cwd=str(executable.parent))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

