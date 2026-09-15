# Changelog

All notable changes to this project are documented here.

## [0.2.0] - 2026-09-15

### Added

- Native Windows desktop application with a WebView2 interface.
- Chinese emoticon browser with search, filters, favorites and bulk selection.
- Arbitrary GIF preview/export speed from `0.1x` to `4x`.
- Native save dialog for exporting the current preview configuration.
- Automatic WeChat display-name lookup for the active account.
- Application icon and portable Windows build.

### Fixed

- Prefer the most recently used WeChat account when several are present.
- Validate encryption keys against multiple files instead of one probe.
- Use explicit raw HEVC fallback for WXGF transcoding.
- Hide ffmpeg subprocess windows in packaged builds.
- Report per-file WXGF conversion progress.
- Avoid Windows long-path failures in temporary GIF generation.

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
