# Changelog

All notable changes to this project are documented here.

## [0.1.0] - 2026-09-11

### Added

- Auto-detection of WeChat / Weixin 4.x data roots and accounts.
- Recovery of the per-account `seed` from the running `Weixin.exe` process memory.
- AES-128-CBC (key = IV) decryption of `business/emoticon` files.
- Splitting of concatenated `PersistStore` containers.
- `.wxgf` (HEVC) to GIF transcoding via ffmpeg.
- CLI (`wxemo` / `wechat-emoticon-exporter`) with `list` and `export` commands.
- `manifest.json` output.
- Experimental `db` command and `--name-from-db` option for SQLCipher4 databases.
