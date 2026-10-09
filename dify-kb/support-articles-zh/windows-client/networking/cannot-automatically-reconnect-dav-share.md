# 使用基本身份验证时，Windows 7 无法自动重新连接 DAV 共享

本文介绍使用基本身份验证时 Windows 7 无法自动重新连接 DAV 共享的按设计行为。

*适用于：* Windows 7 Service Pack 1  
*原始 KB 数：* 2673544

## 现象

请考虑基于 Windows 7 的计算机上的以下方案：

- 你使用了地图网络驱动器向导或“添加网络位置”向导来连接 WebDav 共享或文件夹。
- 基本身份验证用于此资源。

  注意

  基本身份验证通常用于连接到第三方 DAV 服务器，例如 Apache、Oracle 和 SAP。

在此方案中，系统重启或用户注销和登录后，无法访问资源。

此外，Windows 无法访问 SSL WebDav 文件夹。 而是返回以下网络错误消息之一。

### 错误消息 1

> Windows 无法访问 \\`server.company.com`@SSL\davWWWRoot\folder1\folder2\folder3\docs。  
> 检查名称的拼写。 否则，网络可能存在问题。 若要尝试识别和解决网络问题，请单击“诊断”。  
> 错误代码：0x80070035  
> 找不到网络路径。

注意

错误代码0x80070035映射到ERROR\_BAD\_NETPATH。

### 错误消息 2

> 系统错误 1244：  
> 未执行所请求的操作，因为尚未对用户进行身份验证。

注意

错误代码 1244 映射到ERROR\_NOT\_AUTHENTICATED。

## 解决方法

从 Windows 7 开始，凭据管理器无法保留基本身份验证。 在基本身份验证模式下重新连接的唯一方法是断开连接并重新连接驱动器。 这是因为 WinHttp 无法检索保存的基本身份验证或摘要式身份验证凭据。

对于持久连接，请确保已选择身份验证方案，以便通过重启启用持久性凭据。 例如，Kerberos 为身份验证或基于证书的身份验证启用持久性凭据。

## 解决方法

使用在用户登录时重新连接 DAV 共享的登录脚本。 例如，在用户登录脚本中包括以下任一行：

net use X： `http://server.company.com@8080/folder1/folder2/docs` /persistent：no

net use X： \\`server.company.com`@SSL\davWWWRoot\folder1\folder2\docs

注意

8080 是与 DAV 服务器的 SSL 连接的 TCP 端口号。

## Status

此行为在 Windows 7 的基本身份验证模式下设计。

## 详细信息

基本身份验证是一种广泛使用的行业标准方法，用于收集用户名和密码信息。 基本身份验证的优点是它是 HTTP 规范的一部分，大多数浏览器都支持它。

但是，基本身份验证会提示用户输入用户名和密码。 然后，通过网络未加密发送此信息。

除非确定用户与 Web 服务器之间的连接是安全的（例如，使用 SSL 或直接连接），否则不建议使用基本身份验证方法。

在基本身份验证中，密码以纯文本形式通过网络发送。 如果网络探查器通过网络截获此密码，则未经授权的用户可以确定用户名和密码，并重复使用这些凭据。

这是因为 Office 2010 应用程序在默认配置中通过非 SSL 连接禁用基本身份验证，因此存在这种安全风险。

### 特定情况

2123563不能直接从仅支持通过非 SSL 连接进行基本身份验证的服务器打开 Office 文件类型

如果尝试连接到 HTTP 资源，则默认情况下不会启用 Windows 7 中的基本身份验证。 对于 HTTP 访问，必须设置 BasicAuthLevel=2 密钥（2 = 为 SSL 和非 SSL 连接启用基本身份验证）。

如果未配置代理，WinHTTP 仅将凭据发送到本地 Intranet 站点。 如果 HTTP 代理程序在客户端上运行，或者未配置代理服务器条目，并且尝试使用 FQDN（例如`http://server.company.com`）连接到资源，则应使用 KB 943280 [中所述](https://support.microsoft.com/help/943280)的 **AuthForwardServerList** 注册表项显式列出要视为内部的服务器，以便传递凭据。

[943280 从 Windows Vista 或 Windows 7 计算机访问 FQDN 站点时提示输入凭据](https://support.microsoft.com/help/943280)

尝试访问映射到 Web 共享的网络驱动器时，Windows Vista 计算机上的错误消息：“请求的操作未执行，因为用户尚未进行身份验证”

## 参考

[WebDAV 重定向程序注册表设置](/zh-cn/archive/blogs/robert_mcmurray/webdav-redirector-registry-settings)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/cannot-automatically-reconnect-dav-share)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
