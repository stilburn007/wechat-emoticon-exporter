# Contributing

Thanks for your interest in improving `wechat-emoticon-exporter`!

## Development setup

```bash
git clone https://github.com/stilburn007/wechat-emoticon-exporter.git
cd wechat-emoticon-exporter
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev,wxgf]"
```

## Before opening a pull request

```bash
python -m pytest
python -m ruff check .
```

Please make sure:

- Tests pass on Windows (the memory module is Windows-only; other tests run on any OS).
- New pure logic (crypto, container parsing, key derivation) is covered by tests
  that do **not** require WeChat to be installed or running.
- No real WeChat data, keys, seeds or personal information is committed.

## Reporting bugs

Please include:

- WeChat / Weixin version and Windows version.
- The full command you ran and the output.
- Whether `wxemo list` detects your account.

Never paste your real `seed` or `key` in a public issue.

## Code style

- Target Python 3.9+.
- Keep the dependency footprint small; `pycryptodome` is the only required
  runtime dependency.
