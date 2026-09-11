"""Allow ``python -m wechat_emoticon_exporter``."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
