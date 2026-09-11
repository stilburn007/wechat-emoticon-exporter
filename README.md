# wechat-emoticon-exporter

> 微信 4.x 自定义表情导出工具：从本机微信数据中解密并导出表情，支持把微信专有的 `.wxgf` 动图转成 GIF。

[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-0078D4.svg)](#环境要求)

**English** — Decrypt and export WeChat / Weixin 4.x custom emoticons from local
data, including transcoding WeChat's proprietary `.wxgf` (HEVC) animated stickers
to GIF. See [How it works](#工作原理) below.

---

## 免责声明

- 本工具仅用于导出**你自己的**微信数据，请勿用于他人数据或任何违法用途。
- 工具只**读取**本机文件与运行中的微信进程内存，**不会修改**微信数据库或任何微信文件，**不会联网上传**任何数据。
- 请自行确认使用行为符合当地法律法规与微信用户协议，使用风险自负。

## 特性

- 自动定位微信数据目录与账号
- 从运行中的 `Weixin.exe` 进程内存恢复账号 `seed`，推导 AES 密钥
- 解密 `business/emoticon` 下的全部表情（`Persist` / `PersistStore` / `Thumb` / `ThumbStore`）
- 拆分 `PersistStore` 容器中拼接的多张贴纸
- 将 `.wxgf`（HEVC）动图转码为可播放的 GIF
- 输出 `manifest.json` 汇总
- （实验性）解密 `emoticon.db`，按表情标题重命名文件

## 环境要求

| 项目 | 要求 |
| --- | --- |
| 系统 | Windows 10 / 11（进程内存扫描仅支持 Windows） |
| Python | 3.9 及以上 |
| 微信 | Weixin / 微信 4.x（针对 4.1.x 开发测试） |
| ffmpeg | 可选，用于 `.wxgf` → GIF |

## 安装

```bash
# 从 PyPI（含 wxgf 转码依赖）
pip install "wechat-emoticon-exporter[wxgf]"
```

或从源码安装：

```bash
git clone https://github.com/stilburn007/wechat-emoticon-exporter.git
cd wechat-emoticon-exporter
pip install -e ".[dev,wxgf]"
```

## 使用

确保微信**正在运行并已登录**。

```bash
# 列出检测到的账号
wxemo list

# 导出（默认输出到 ./emoticon_export）
wxemo export --account wxid_xxxxxxxx

# 指定输出目录
wxemo export --account wxid_xxxxxxxx -o D:\微信表情

# 不转换 .wxgf，保留原始文件
wxemo export --no-wxgf

# 转换后删除原始 .wxgf（默认保留到 _wxgf原始格式/）
wxemo export --discard-raw

# 额外把全部文件平铺到 <out>/flat
wxemo export --flat

# 多账号时指定数据目录
wxemo export --data-root "D:\Program Files\Tencent\xwechat_files" --account wxid_xxxxxxxx
```

若内存中找不到 `seed`（例如微信版本不匹配），可手动提供：

```bash
wxemo export --seed 352428248
wxemo export --key e5596a6092f5673aa81ad3511fc90b02   # 16 字节密钥的 hex
```

命令别名：安装后同时提供 `wxemo` 与 `wechat-emoticon-exporter`，也可用
`python -m wechat_emoticon_exporter`。

## 输出结构

```
emoticon_export/
├── Persist/              # 自定义表情原图（gif / png / jpg；.wxgf 转换后为 gif）
│   └── _wxgf原始格式/     # 转换前的原始 .wxgf（默认保留）
├── PersistStore/         # 表情包容器拆分出的贴纸
├── Thumb/                # 缩略图
├── ThumbStore/           # 表情包缩略图
├── manifest.json         # 统计与密钥信息
└── flat/                 # 使用 --flat 时的平铺副本
```

## 工作原理

微信 4.x 把表情文件存成 **AES-128-CBC** 密文，且 **IV 等于密钥**：

```
key       = MD5(f"{seed}{wxid}EMOTICON").digest()[:16]
plaintext = AES-128-CBC(key, iv=key).decrypt(ciphertext)   # PKCS7 填充
```

- `wxid` 是账号标识（账号目录名去掉尾部 `_xxxx`）。
- `seed` 是账号级随机整数，仅存在于运行中的 `Weixin.exe` 进程内存里。
- 本工具扫描进程内存收集 8–12 位数字候选，用已知文件头部（PNG / GIF / JPEG 魔数）逐个校验，命中即为正确 `seed`。
- 由于同一账号所有表情共用该密钥，且 `IV = key`，明文首块相同的文件（例如都以 PNG 头开始）密文首块也相同——这正是识别该加密方案的线索。

## 已知限制

- 仅支持 Windows。
- `seed` 需在微信运行时获取；内存扫描依赖具体微信版本，失败时请用 `--seed` / `--key`。
- `.wxgf` → GIF 需要 ffmpeg（可通过 `imageio-ffmpeg` 自动提供）。
- **实验性**：`--name-from-db` 与 `db` 子命令依赖 `emoticon.db` 的 SQLCipher4
  密钥在进程内存中的布局。在部分微信版本（如 4.1.13+）上可能无法解出密钥，
  此时导出会**自动回退**为 md5 文件名。欢迎提交 PR 适配新版本。

## 开发

```bash
pip install -e ".[dev,wxgf]"
python -m pytest          # 运行测试
python -m ruff check .    # 代码检查
```

项目结构：

```
src/wechat_emoticon_exporter/
├── cli.py          # 命令行入口
├── locate.py       # 定位数据目录与账号
├── memory.py       # 读取 Weixin.exe 进程内存（Windows）
├── crypto.py       # 密钥推导与 AES 解密
├── containers.py   # 拆分 PersistStore 容器
├── wxgf.py         # .wxgf → GIF 转码
├── wcdb.py         # （实验性）解密 SQLCipher4 数据库
├── naming.py       # （实验性）按标题重命名
└── exporter.py     # 导出流程编排
```

## 致谢

解密方案与 WCDB 处理思路参考了以下开源项目，特此致谢：

- [CN-Grace/Wechat-Emoticon-Parser](https://github.com/CN-Grace/Wechat-Emoticon-Parser)
- [TANGandXue/wcdb-key-tool](https://github.com/TANGandXue/wcdb-key-tool)

## License

[MIT](LICENSE) © 2026 Zhou Kang
