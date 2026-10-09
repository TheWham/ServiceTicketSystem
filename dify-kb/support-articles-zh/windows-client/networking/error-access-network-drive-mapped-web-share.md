# 尝试访问映射到 Web 共享的网络驱动器时出错：用户尚未进行身份验证

本文提供了在尝试访问映射 Web 共享时在基于 Windows 的计算机上发生的问题的解决方法。

*适用于：* Windows 10 – 所有版本、Windows 7 Service Pack 1  
*原始 KB 编号：* 941050

## 现象

在基于 Windows 的计算机上，请考虑以下方案：

- 将网络驱动器映射到需要用户凭据的 Web 共享。
- 将驱动器配置为使用 **登录时重新连接** 选项。
- 输入用户凭据，然后在访问驱动器时选中“ **记住我的密码** ”复选框。
- 重启计算机，或者从 Windows 注销。

在此方案中，再次登录到计算机时，在尝试访问映射的驱动器时，会收到如下所示的错误消息：

> 连接到 **地址时出错**  
> 未执行请求的操作，因为尚未对用户进行身份验证  
> 尚未还原连接

注意

再次登录到计算机后，映射驱动器显示为断开连接。

## 原因

出现此问题的原因是 Web 分布式创作和版本控制（WebDAV）重定向程序使用 Windows HTTP 服务（WinHTTP），而不是 Windows Internet （WinInet） API。 在非代理网络配置中，WinHTTP 仅在响应本地 Intranet 站点上发生的请求时发送用户凭据。 因此，如果未配置代理，则可能无法访问需要用户凭据的共享。

## 解决方法

重要

此部分（或称方法或任务）介绍了修改注册表的步骤。 但是，注册表修改不当可能会出现严重问题。 因此，按以下步骤操作时请务必谨慎。 作为额外保护措施，请在修改注册表之前先将其备份。 如果之后出现问题，您就可以还原注册表。 有关如何备份和还原注册表的详细信息，请单击下面的文章编号，查看相应的 Microsoft 知识库文章：  
[322756](https://support.microsoft.com/help/322756) 如何备份和还原 Windows 中的注册表

若要在 Windows Vista 中解决此问题，请应用修补程序 943280。 此修补程序仅适用于 Windows Vista。 对于更高版本的 Windows，请转到下一部分以修改注册表项。

注意

此修补程序仅适用于基于 Windows Vista 的系统。 但是，本节稍后所述的注册表更改适用于“适用于”部分中的所有操作系统。 运行 Windows 7、Windows 8.1 或 Windows 10 的系统不需要修补程序。 注册表更改单独修复了这些系统上的问题。

有关详细信息，请单击下面的文章编号，查看相应的 Microsoft 知识库文章：

[943280](https://support.microsoft.com/help/943280) 当你使用未配置代理的基于 Windows Vista 的客户端计算机访问 FQDN 站点时，系统会提示输入凭据

应用此修补程序后，必须创建注册表项。 为此，请按照下列步骤进行操作：

1. 单击“开始”**，在“开始搜索**”框中键入 regedit*，然后按 Enter。*****
2. 找到并单击下面的子项：

   `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\WebClient\Parameters`
3. 在 **“编辑”** 菜单上，指向 **“新建**”，然后单击“ **多字符串值**”。
4. 键入 **AuthForwardServerList**，然后按 Enter。
5. 在 **“编辑** ”菜单上，单击“ **修改**”。
6. 在 **“值日期** ”框中，键入承载 Web 共享的服务器 URL，然后单击“ **确定**”。

   注意

   还可以在 **“值日期** ”框中键入 URL 列表。 有关详细信息，请参阅“示例 URL 列表”部分。
7. 退出注册表编辑器。

创建此注册表项后，WebClient 服务将读取条目值。 如果客户端计算机尝试访问与列表中任何表达式匹配的 URL，则即使未配置代理，用户凭据也会成功发送到对用户进行身份验证。

注意

修改注册表后，必须重启 WebClient 服务。

### 示例 URL 列表

下面是示例 URL 列表：

`https://*.Contoso.com`

`http://*.dns.live.com`

`*.microsoft.com`

`https://172.169.4.6`

此 URL 列表使 WebClient 服务能够通过以下通道发送凭据。

注意

配置此 URL 列表后，即使这些服务器位于 Internet 上，凭据也会自动向 WebDAV 服务器进行身份验证。

- 名称为 `Contoso.com`域的子域的任何加密通道。
- 名称为 `dns.live.com`域的子域的任何非安全通道。
- 名称以“.microsoft.com”结尾的服务器的任何通道。
- IP 地址为 172.169.4.6 的主机的任何加密通道。

### URL 列表中要避免的事项

- 不要在 URL 末尾添加星号 \ 。 执行此操作时，可能会带来安全风险。 例如，请勿使用以下项：

  `http://*.dns.live.*`
- 不要在字符串之前或之后添加星号 \ 。 执行此操作时，WebClient 服务可以将用户凭据发送到更多服务器。 例如，请勿使用以下项：

  - `http://Contoso.com`

  在此示例中，服务还会将用户凭据发送到 `http://**extra_characters** Contoso.com`。

  - `http://Contoso*.com`

  在此示例中，服务还会将用户凭据发送到 `http://Contoso **extra_characters**.com`。
- 不要在 URL 列表中键入主机的 UNC 名称。 例如，请勿使用以下项：

  `*.contoso.com@SSL`
- 不要包含要在 URL 列表中使用的共享名称或端口号。 例如，请勿使用以下项：

  - `http://*.dns.live.com/DavShare`
  - `http://*dns.live.com:80`
- 不要在 URL 列表中使用 IPv6。

重要

此 URL 列表对安全区域设置没有影响，此 URL 列表仅用于将凭据转发到 WebDAV 服务器的特定目的。 尽可能严格地创建列表以避免任何安全问题。 另请注意，没有特定的拒绝列表。 因此，凭据将转发到与此列表匹配的所有服务器。

如果在网络中实现了基本身份验证或摘要式身份验证，修补程序 943280 无法更改此行为。 此行为在基本身份验证模式和摘要式身份验证模式下设计。

IIS 不支持通过 Internet Windows 身份验证。 因此，此修补程序仅适用于 Intranet 方案。

## Status

Microsoft 已经确认这是一个列于“适用范围”部分的 Microsoft 产品问题。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/error-access-network-drive-mapped-web-share)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
