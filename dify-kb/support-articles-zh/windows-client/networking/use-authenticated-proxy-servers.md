# 结合使用经过身份验证的代理服务器和 Windows 8

本文有助于解决在使用需要身份验证的 Internet 代理服务器时使用连接到 Internet 的应用时发生的问题。

*原始 KB 数：* 2778122

## 现象

如果使用需要身份验证的 Internet 代理服务器，则使用连接到 Internet 的应用时可能会遇到问题。

需要身份验证的代理服务器要么需要用户名和密码才能访问 Internet，要么使用其当前域凭据对用户进行身份验证。

使用 Microsoft 应用商店应用时，可能会遇到以下问题之一，具体取决于代理配置：

- 无法安装 Microsoft 应用商店中可用的更新，并且可能会收到以下错误消息之一：

  - > 未安装此应用 - 查看详细信息。
  - > 发生了一些情况，无法安装此应用。 重试。 错误代码：0x8024401c
- 无法安装新应用，可能会收到以下错误消息之一：

  - > 无法完成购买。 发生的情况，并且你的购买无法完成。
  - > 发生了一些情况，无法安装此应用。 重试。 错误代码：0x8024401c
- 启动 Microsoft 应用商店应用时，可能会收到以下错误消息：

  - > 网络代理不适用于 Microsoft 应用商店。 有关详细信息，请与系统管理员联系。
- Windows 8 附带的应用可能表示你未连接到 Internet。 如果在连接到其他网络时从 Microsoft 应用商店安装了其他应用，则这些应用可能还表示未连接到 Internet。 这些应用可能会显示以下错误消息之一：

  - > 登录时出现问题。
  - > 未连接到 Internet。
- 某些应用的动态磁贴可能不会更新其内容，也可能永远不会显示实时内容。
- Windows 更新可能无法检查更新或下载更新，并且会收到错误代码 8024401C 或以下错误消息：

  - > 检查更新时出现问题。

## 解决方法

本文中讨论的问题在 Windows 8.1 和 Windows Server 2012 R2 中得到解决。

## 详细信息

如果使用 Windows 8 或 Windows Server 2012，可以通过通过代理服务器启用未经身份验证的访问来减少这些问题的影响。 建议仅针对每个有问题的应用的 URL 地址的连接启用未经身份验证的访问。 某些代理服务器可能建议你创建 URL 地址的允许列表。

若要解决这些问题，因为它们与使用 Microsoft 应用商店应用或使用 Windows 8 或Windows 更新随附的Microsoft应用有关，可以在代理服务器上的允许列表中包含以下地址，并启用对它们的 HTTP 和 HTTPS 访问：

- login.live.com
- account.live.com
- clientconfig.passport.net
- wustat.windows.com
- \*.windowsupdate.com
- \*.wns.windows.com
- \*.hotmail.com
- \*.outlook.com
- \*.microsoft.com
- \*.msftncsi.com/ncsi.txt

若要解决其他应用的这些问题，可能需要联系应用程序供应商，以获取应包含在允许列表中的 URL 地址的信息。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/use-authenticated-proxy-servers)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
