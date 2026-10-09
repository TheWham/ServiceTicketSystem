# 当计算机连接到企业网络或公用网络时，将打开 Internet Explorer 或 Edge 窗口

本文提供有关计算机连接到企业网络或公用网络时 Internet Explorer 或 Edge 窗口打开的问题的一些信息。

*原始 KB 数：* 4494446

## 现象

在以下任一条件下，将运行 Windows 8 的计算机（或更高版本）连接到网络：

- 将计算机连接到需要热点登录信息的公用网络（例如酒店、机场等）。
- 将计算机连接到使用代理服务器连接到 Internet 的公司网络。

请注意以下行为：

- 默认浏览器（例如 **Internet Explorer** 或 **Edge**）将打开，并显示网页，例如网络或 MSN 门户页的登录页。
- 任务栏上的网络图标显示警报符号（例如![](media/internet-explorer-edge-open-connect-corporate-public-network/network-status-alert.png) ）。 如果将鼠标悬停在图标上，则会看到“无连接”或“Internet 受限访问”等消息。

登录到网络后，可以通常使用网络。 使用网络几秒钟后，任务栏上的网络警报将消失。

## 原因

此为有意行为。

## 详细信息

Windows 使用网络位置感知（NLA）服务来检测网络的属性，并确定如何管理与该网络的连接。 NLA 使用名为“网络连接状态指示器”（NCSI）的组件来确定计算机是否已成功连接到网络，以及网络是否具有 Intranet 或 Internet 连接。

NCSI 同时使用主动和被动探测。 这些探测由任何网络接口中的更改触发。 如“症状[”部分所述](#symptoms)，将计算机连接到网络时，NCSI 将开始包括以下一个或多个过程：

- [NCSI 主动探测和网络状态警报](#ncsi-active-probes-and-the-network-status-alert)
- [身份验证和自动登录页](#authentication-and-the-automatic-sign-in-page)
- [NCSI 被动监视和网络状态警报](#ncsi-passive-monitoring-the-msn-portal-page-and-the-network-status-alert)

### NCSI 主动探测和网络状态警报

活动探测过程包括以下步骤：

- Windows 10 或更高版本：

  1. NCSI 发送 DNS 请求来解析 FQDN 的 `www.msftconnecttest.com` 地址。
  2. 如果 NCSI 从 DNS 服务器收到有效的响应，NCSI 会向 `http://www.msftconnecttest.com/connecttest.txt`该服务器发送一个纯 HTTP GET 请求。
  3. 如果 NCSI 成功下载文本文件，请确保该文件包含Microsoft连接测试。
  4. NCSI 发送另一个 DNS 请求来解析 FQDN 的 `dns.msftncsi.com` 地址。

     - 如果其中任一请求失败，网络警报会显示在任务栏中（如症状中所述）。 如果将鼠标悬停在图标上，则会看到一条消息，例如“无连接”或“受限 Internet 访问”（具体取决于请求失败）。
     - 如果所有这些请求都成功，任务栏会显示常用的网络图标。 如果将鼠标悬停在图标上，则会看到一条消息，例如“Internet 访问”。
- Windows 8.1 或更低版本：

  1. NCSI 发送 DNS 请求来解析 FQDN 的 `www.msftncsi.com` 地址。
  2. 如果 NCSI 从 DNS 服务器收到有效的响应，NCSI 会向 `http://www.msftncsi.com/ncsi.txt`该服务器发送一个纯 HTTP GET 请求。
  3. 如果 NCSI 成功下载文本文件，请确保该文件包含 Microsoft NCSI。
  4. NCSI 发送另一个 DNS 请求来解析 FQDN 的 `dns.msftncsi.com` 地址。

     - 如果其中任一请求失败，网络警报会显示在任务栏中（如症状中所述）。 如果将鼠标悬停在图标上，则会看到一条消息，例如“无连接”或“受限 Internet 访问”（具体取决于请求失败）。
     - 如果所有这些请求都成功，任务栏会显示常用的网络图标。 如果将鼠标悬停在图标上，则会看到一条消息，例如“Internet 访问”。

NCSI 和 NLA 服务将这些响应与其他信息相结合，以生成网络连接的配置文件，或标识其现有配置文件。 网络连接配置文件提供了 Windows 配置相应 Windows 防火墙配置文件所需的信息：

- 对于 Active Directory 身份验证的网络：防火墙域配置文件。
- 对于用户标记为“专用”的网络：防火墙专用配置文件。
- 对于用户标记为“public”的网络：公共防火墙配置文件。

注意

可以使用组策略来限制活动探测过程，并且可以将其他网站替换为目标（尽管此替换不是推荐的解决方案）。 有关更多信息，请参阅以下资源：

- [管理从 Windows 操作系统组件到 Microsoft 服务 的连接：14。 网络连接状态指示器](/zh-cn/windows/privacy/manage-connections-from-windows-operating-system-components-to-microsoft-services#14-network-connection-status-indicator)
- [策略 CSP - 连接性：Connectivity/DisallowNetworkConnectivityActiveTests](/zh-cn/windows/client-management/mdm/policy-csp-connectivity#connectivity-disallownetworkconnectivityactivetests)

### 身份验证和自动登录页

如果网络需要凭据，Windows 将打开默认浏览器（如 Internet Explorer 或 Edge）。 如果网络具有登录页，则该页将显示在浏览器中。

引入了此行为以提高 Windows 用户体验。 在早期版本的 Windows 中，当你连接到需要进行身份验证的网络时，浏览器窗口不会自动打开。 你可能会看到一条消息，指出必须采取进一步操作才能完全连接到网络。 若要完成连接，必须单击该消息以打开浏览器窗口（或手动打开浏览器窗口），然后输入用户名和密码。

由于网络不允许在没有凭据的情况下访问 Internet，因此网络警报将显示在任务栏中。

### NCSI 被动监视、MSN 门户页和网络状态警报

除了本文介绍的活动探测之外，NCSI 还会监视计算机上的其他应用程序的网络活动。 即使主动探测进程失败，此被动监视过程也会继续。 NCSI 根据其他应用程序是否可以成功建立 TCP 连接来调整其网络状态确定。 如果网络警报由于主动探测失败而出现，则被动探测成功时会消失。

注意

NCSI 被动监视过程不会将任何信息传输到计算机或从计算机传输，也不会读取其他应用程序传输的任何信息。

在某些情况下，例如，当你连接到使用代理服务器连接到 Internet 的网络或网络限制阻止 NCSI 完成其活动探测过程时，Windows 会在默认浏览器中打开 MSN 门户页面。 如果分析计算机上的网络跟踪，则会显示与 `http://www.msftconnecttest.com/redirect` 该网络跟踪的 HTTP 连接，后跟与 MSN 门户的连接。 Windows 将打开此页面，以获取被动探测过程的好处。 如果页面加载，NCSI 的结论是计算机具有 Internet 访问权限。 由于不同的探测失败，然后成功，网络状态警报会显示，然后消失。

注意

若要防止浏览器窗口在计算机连接到具有代理服务器的网络时打开，必须配置网络防火墙以允许访问端口 80 上的以下 URL：

- \*.msftncsi.com
- \*.msftconnecttest.com

有关详细信息，请参阅 [KB 2778122，将经过身份验证的代理服务器与 Windows 8 配合使用](use-authenticated-proxy-servers)

## 解决方法

可以使用注册表或组策略对象（GPO）禁用 NCSI 主动或被动探测。

注意

Microsoft不建议禁用 NCSI 探测。 多个操作系统组件和应用程序依赖于 NCSI。 例如，如果 NCSI 无法正常工作，Microsoft Outlook 可能无法连接到邮件服务器，或者即使计算机连接到 Internet，Windows 也可能无法下载更新。

若要使用注册表禁用 NCSI 活动探测，请配置以下注册表项之一。

重要

请认真遵循本部分所述的步骤。 如果注册表修改不正确，可能会发生严重问题。 在修改注册表之前，请[备份注册表](https://support.microsoft.com/help/322756)，以便在出现问题时可以还原。

- `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\NlaSvc\Parameters\Internet\EnableActiveProbing`
  - 键类型：DWORD
  - 值：十进制 0 （False）
- `HKLM\Software\Policies\Microsoft\Windows\NetworkConnectivityStatusIndicator\NoActiveProbe`
  - 键类型：DWORD
  - 值：十进制 1 （True）

    注意

    在默认注册表配置中，此注册表项不存在。 必须创建它。

若要使用注册表禁用 NCSI 被动探测，请创建以下注册表项。

- `HKLM\Software\Policies\Microsoft\Windows\NetworkConnectivityStatusIndicator\DisablePassivePolling`
  - 键类型：DWORD
  - 值：十进制 1 （True）

    注意

    在默认注册表配置中，此注册表项不存在。 必须创建它。

若要使用组策略禁用 NCSI 活动探测，请配置以下 GPO：

- **计算机配置**\**管理模板****\系统**\**Internet 通信管理**\**Internet 通信设置**\**关闭 Windows 网络连接状态指示器活动测试**
  - 值：已启用

若要使用组策略禁用 NCSI 被动探测，请配置以下 GPO：

- **计算机配置****\管理模板**\**\网络连接状态指示器\****指定被动轮询。**
  - 值：已启用

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/internet-explorer-edge-open-connect-corporate-public-network)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
