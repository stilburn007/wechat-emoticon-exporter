# 微信表情工坊 v0.2.3

本版本修复读取过程中出现 `Failed to fetch` 和表情预览破图的问题。

## 修复

- 增量读取时只传输新发现的表情，不再反复发送完整列表。
- 表情网格只追加新卡片，不再每次刷新都重建整个页面。
- 本地服务短暂响应超时时自动重试。
- 连接恢复后自动继续任务，不中断读取。
- 预览图片加载失败时最多自动重试两次。
- 原本的 `Failed to fetch` 等浏览器错误会显示为可理解的中文提示。

## 使用说明

1. 完整解压 `WeChatEmoticonStudio-portable.zip`。
2. 双击 `WeChatEmoticonStudio.exe`。
3. 保持微信已登录并运行。
4. 读取过程中上方 Console 会持续更新，下方表情会边读取边出现。
5. 如果本地服务暂时繁忙，日志会显示“正在自动重试”，无需关闭应用。

## 环境要求

- Windows 10/11
- Microsoft Edge WebView2 Runtime
- 微信 / Weixin 4.x
