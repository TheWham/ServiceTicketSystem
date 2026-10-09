# 使用 Fiddler 为 Microsoft Entra ID 应用收集 HTTPS 流量

本文提供有关使用 Fiddler 收集 HTTPS 流量以排查Microsoft Entra ID 应用问题的说明。

## 收集 HTTPS 流量

1. 在用于重现问题的设备上下载并安装 [Fiddler](https://www.telerik.com/fiddler/fiddler-classic)。

   注释

   Fiddler 是第三方软件，不受Microsoft所有。
2. 在 **工具** 菜单上，选择 **选项**。
3. 在“**HTTPS**”选项卡上，选择“**解密 HTTPS 流量**。 如果系统提示安装 Fiddler 证书，请选择“是”。

   ![解密 HTTPS 流量选项的屏幕截图。](media/capture-https-traffic-http-fiddler-entra-id-app/enable-https-decrypt.png)
4. 重启 Fiddler。
5. 为流量收集准备环境。 根据要进行故障排除的应用程序类型，请执行以下步骤：

   **对于基于浏览器的应用程序，**：

   使用专用浏览模式或清除将用于测试的设备上的浏览器缓存。 此作可确保清除以前会话中的任何过时或不必要的文件。 它还允许 Web 应用加载最新版本的基本文件，例如 JavaScript 和 CSS 样式表。 测试对 Web 应用的更改或更新时，拥有最新文件尤其重要，因为它会阻止旧的缓存文件干扰当前版本。

   **对于基于浏览器的应用程序，**：

   启动要测试的客户端应用程序。
6. 重现此问题。 应会看到 HTTPS 流量显示在 Fiddler 窗口中。
7. 在“**文件**”菜单上，选择“**保存**>**所有会话** 以将会话另存为 SAZ 文件。

**第三方信息免责声明**

本文讨论的第三方产品由独立于Microsoft的公司制造。 Microsoft对这些产品的性能或可靠性不作任何默示或其他保证。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/capture-https-traffic-fiddler-entra-id-app)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
