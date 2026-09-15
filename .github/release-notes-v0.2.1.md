# 微信表情工坊 v0.2.1

这是账号检测和数据目录选择修复版本。

## 修复内容

- 扩大微信数据目录自动搜索范围：
  - 用户目录和文档目录
  - OneDrive 文档目录
  - 各本地磁盘的 `xwechat_files`
  - 各磁盘的 `Documents\xwechat_files`
  - `WeChat`、`Weixin` 和 `Tencent` 常见目录
- 支持直接把 `wxid_...` 账号文件夹作为数据目录。
- 检测到账号但尚未发现表情目录时，也会保留账号记录并标记。
- 自动去重账号，优先选择包含表情目录的账号记录。
- “微信数据目录”窗口新增原生“选择文件夹”按钮。

## 下载与运行

1. 下载 `WeChatEmoticonStudio-portable.zip`。
2. 完整解压。
3. 双击 `WeChatEmoticonStudio.exe`。
4. 保持微信已登录并运行。
5. 如果仍未自动发现账号，点击顶部文件夹图标，然后点击“选择文件夹”。
6. 选择包含 `wxid_...` 账号目录的微信数据根目录，通常是：

```text
某盘符:\xwechat_files
某盘符:\Documents\xwechat_files
```

也可以直接选择账号文件夹：

```text
...\xwechat_files\wxid_xxxxxxxx_xxxx
```

## 环境要求

- Windows 10/11
- Microsoft Edge WebView2 Runtime
- 微信 / Weixin 4.x
