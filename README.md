# 微信表情工坊

![微信表情工坊](assets/app-icon.png)

微信 4.x 自定义表情桌面应用与命令行导出工具。应用会读取本机微信数据，解密自定义
表情，提供中文界面预览、筛选、收藏、任意倍速播放和选择性导出。

## 功能

- 自动发现微信账号、数据目录和自定义表情
- 从运行中的 `Weixin.exe` 进程恢复当前账号密钥
- 自动读取并显示当前微信用户昵称
- 中文网格/列表浏览、搜索、来源筛选和排序
- GIF 动态预览，支持 `0.1x` 到 `4x` 任意倍速
- 选择单个或多个表情，按当前倍速重新生成 GIF
- 通过原生 Windows 保存窗口保存当前表情
- 保存到指定文件夹、直接选择浏览器文件夹或下载 ZIP
- `.wxgf` HEVC 动图转 GIF，自动隐藏 ffmpeg 控制台窗口
- 收藏、批量选择和本地预览缓存自动清理
- 保留原始 `wxemo` 命令行导出功能

## 启动桌面应用

Windows 10/11，Python 3.10 及以上：

```powershell
cd D:\GitHubProjects\wechat-emoticon-exporter
.\start_studio.ps1
```

默认会打开原生 WebView2 窗口，不跳转浏览器。也可以手动运行：

```powershell
python -m pip install -e .
python run_studio.py
```

浏览器调试模式：

```powershell
python run_studio.py --browser
```

## 构建 Windows 应用

```powershell
.\build_windows.ps1
```

输出：

```text
dist\WeChatEmoticonStudio.exe
dist\WeChatEmoticonStudio\WeChatEmoticonStudio.exe
dist\WeChatEmoticonStudio-portable.zip
```

根目录 `dist\WeChatEmoticonStudio.exe` 是小型启动器，实际应用位于
`dist\WeChatEmoticonStudio`。二者需要一起保留；复制到其他电脑时使用便携压缩包。

## 使用流程

1. 保持微信 4.x 已登录并运行。
2. 启动应用，选择账号。当前账号显示微信昵称，最近使用账号会标出。
3. 点击“读取表情”，等待解密和 WXGF 转码完成。
4. 按来源、类型或名称筛选，点击表情查看详情。
5. 在详情面板输入或拖动播放速度。
6. 勾选表情后点击“保存选中”，选择导出速度、目标文件夹或 ZIP。
7. 点击“保存当前配置”可直接通过 Windows 文件保存窗口导出当前倍速版本。

## 命令行导出

原有 CLI 保留：

```powershell
wxemo list
wxemo export --account wxid_xxxxxxxx
wxemo export --account wxid_xxxxxxxx -o D:\微信表情
wxemo export --account wxid_xxxxxxxx --no-wxgf
```

内存扫描失败时可手动提供：

```powershell
wxemo export --account wxid_xxxxxxxx --seed 123456789
wxemo export --account wxid_xxxxxxxx --key 0123456789abcdef0123456789abcdef
```

## 工作原理

微信 4.x 把表情文件存成 AES-128-CBC 密文，IV 等于密钥：

```text
key       = MD5(f"{seed}{wxid}EMOTICON").digest()[:16]
plaintext = AES-128-CBC(key, iv=key).decrypt(ciphertext)
```

- `seed` 保存在运行中的微信进程内存中。
- 应用扫描内存候选值，并用多个表情文件进行一致性和完整解密校验。
- 微信昵称从与当前 wxid 关联的 `<displayname>` 元数据中读取。
- `.wxgf` 先按微信容器交给 ffmpeg，失败后显式按 raw HEVC 重新解析。

## 隐私

- 只读取本机微信数据和当前用户自己的微信进程内存。
- 不修改微信数据库或微信文件。
- 不上传账号、昵称、seed、key 或表情内容。
- 本地预览缓存位于系统临时目录，退出或清理后删除。
- 请不要公开分享包含 `seed` 和 `key` 的旧版 `manifest.json`。

## 开发

```powershell
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
```

项目结构：

```text
backend/                  # 桌面应用 API、缓存目录和导出适配
frontend/                 # 原生 WebView 前端
assets/                   # 应用 PNG/ICO 图标
src/wechat_emoticon_exporter/
                          # 原始解密、CLI、WXGF 和 WCDB 核心
run_studio.py             # 桌面窗口启动入口
launcher.py               # dist 根目录启动器
build_windows.ps1         # Windows 打包脚本
```

## 致谢

- [CN-Grace/Wechat-Emoticon-Parser](https://github.com/CN-Grace/Wechat-Emoticon-Parser)
- [TANGandXue/wcdb-key-tool](https://github.com/TANGandXue/wcdb-key-tool)

## License

[MIT](LICENSE) © 2026 Zhou Kang
