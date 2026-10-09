# 使用 NetLog 作为 Fiddler 和 HAR 捕获的替代方案

本文提供有关使用网络日志（NetLog）工具作为 Fiddler 和 HTTP 存档 （HAR） 捕获的替代方法，以诊断 Microsoft Entra 中的网络问题的指导。 NetLog 内置于基于 Chromium 的浏览器（如 Microsoft Edge、Google Chrome 和 Electron）。 当标准 Fiddler 捕获不可用，或来自开发人员工具的 HAR 捕获导致必要信息被截断时，可以使用 NetLog 进行网络活动捕获。

## 已知的限制

在使用 NetLog 之前，请注意以下限制：

- 不会捕获 POST 请求正文。
- 不会捕获在 Internet Explorer 兼容模式下运行的站点。

根据所需的信息，你仍可能需要使用 Fiddler 或 HAR 捕获数据。

## 在浏览器中使用 NetLog

按照以下步骤使用 NetLog 捕获网络活动：

1. （可选但有帮助）关闭除一个浏览器选项卡以外的所有浏览器选项卡。
2. 请导航到 NetLog。

   - 对于 Google Chrome：打开一个新选项卡并转到 `chrome://net-export`。
   - 对于 Microsoft Edge：打开新选项卡并转到 `edge://net-export`。
3. 在“**选项**”部分中，选择“**包括原始字节”（将包含 Cookie 和凭据）。**
4. 将 **“最大日志大小** ”字段留空。
5. 选择“ **开始日志记录到磁盘**”。
6. 选择一个位置（如 **桌面**）以保存日志文件（**edge-net-export-log.json** 或 **chrome-net-export-log.json**）。
7. 在同一浏览器窗口中，打开一个新选项卡。
8. 重现问题。

   注释

   如果关闭或离开 NetLog 选项卡，日志记录将自动停止。
9. 重现问题后，返回到 NetLog 选项卡并选择“ **停止日志记录** ”按钮。
10. 找到在步骤 6 中保存的 NetLog 文件。

有关详细信息，请参阅 [如何捕获 NetLog 转储](https://dev.chromium.org/for-testers/providing-network-details)。

## 在移动设备上使用 NetLog

Microsoft Edge 和 Google Chrome 的移动版本支持 NetLog：

- Android：NetLog 在适用于 Android 的 Edge 和 Google Chrome 中工作。
- iOS：NetLog 适用于 iOS 的 Google Chrome 中工作。

在移动设备上，可以使用电子邮件选项发送日志。

## 查看和分析 NetLog 数据

可以使用 [联机 NetLog 查看器查看 NetLog](https://netlog-viewer.appspot.com/#import) 文件。 为此，请打开 NetLog 查看器，选择 **“文件**”，然后上传导出的 NetLog 文件。

可以使用 NetLog 查看器中的以下选项卡来检查网络活动的不同方面：

- **事件**：查看详细的网络事件。
- **代理**：检查代理设置。
- **时间线**：分析请求计时。
- **DNS**：检查域名系统（DNS）查找。
- **套接字**：查看传输控制协议（TCP）连接。
- **缓存**：检查缓存的资源。

**第三方信息免责声明**

本文讨论的第三方产品由独立于微软的公司制造。 Microsoft对这些产品的性能或可靠性不作任何明示或暗示的保证。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/use-netlog-capture-network-traffic)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
