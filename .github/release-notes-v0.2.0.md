# 微信表情工坊 v0.2.0

微信 4.x 自定义表情桌面应用与命令行导出工具。

## 下载与运行

1. 下载 `WeChatEmoticonStudio-portable.zip`。
2. 完整解压到一个普通文件夹，不要直接在压缩包内运行。
3. 双击解压后的 `WeChatEmoticonStudio.exe`。
4. 保持微信 4.x 已登录并运行。
5. 选择显示的微信昵称，点击“读取表情”。

## 环境要求

- Windows 10 或 Windows 11
- Microsoft Edge WebView2 Runtime
- 微信 / Weixin 4.x

Windows 10/11 通常已经包含 WebView2 Runtime。如果程序无法打开，请从微软官网安装
Evergreen WebView2 Runtime 后重试。

## 主要功能

- 自动发现账号、表情目录并读取当前微信昵称
- 中文浏览、搜索、筛选、收藏和批量选择
- GIF 预览和 `0.1x` 到 `4x` 任意倍速
- 按当前倍速保存单个或批量表情
- WXGF/HEVC 动图转 GIF
- 保留原有 `wxemo` 命令行导出功能

## 文件校验

Release 中提供 `WeChatEmoticonStudio-portable.zip.sha256`。可以在 PowerShell 中验证：

```powershell
Get-FileHash .\WeChatEmoticonStudio-portable.zip -Algorithm SHA256
```

结果应与 SHA-256 文件中的内容一致。

## 隐私

- 只读取本机微信数据和当前用户自己的微信进程内存
- 不上传账号、昵称、seed、key 或表情内容
- 不修改微信数据库和微信文件
