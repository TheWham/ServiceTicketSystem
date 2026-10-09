# 单一登录不适用于 Office 365、Azure 或 Intune 中的某些设备

## Summary

本文可帮助你解决使用单一登录（SSO）无法从某些设备登录 Office 365、Azure 或 Microsoft Intune 的问题。 此问题通常发生在将 Azure 无缝单一登录配置为使用直通身份验证（PTA）或密码哈希同步（PHS）用于加入 Active Directory 域的设备的环境中。

## 症状

尝试使用联合帐户通过 Web 客户端或富客户端应用程序访问 Microsoft 云服务（如 Office 365、Azure 或 Intune）时，身份验证在特定客户端计算机上失败。

使用 Web 浏览器通过联合帐户从同一台计算机访问云服务门户时，会遇到以下症状之一：

- 连接到门户终结点并收到以下错误消息之一：

  - **Microsoft Edge 无法显示网页。**
  - **403 错误 页面无法访问**
- 连接至 Active Directory 联合身份验证服务（AD FS）端点，并收到以下错误消息之一：

  - **Microsoft Edge 无法显示网页。**
  - **403 错误 页面无法访问**
- 连接到 AD FS 终结点时会收到证书警告。
- 在您已登录公司域的情况下连接到 AD FS 终结点，会收到一个凭据提示。 此提示不使用基于表单的身份验证。
- 使用第三方 Web 浏览器连接到 AD FS 终结点，并接收循环身份验证提示。 这些提示不使用基于表单的身份验证。
- 你连接到`login.microsoftonline.com`终结点并收到以下错误消息：

  - **访问被拒绝**

## 原因

此问题通常发生在客户端计算机或一组客户端设备上。 如果 SSO 未完全正常运行，则所有用户和客户端计算机可能会出现此问题。 如果未正确设置客户端设置，SSO 可能无法正常运行。 以下客户端设备情况可能会导致此问题：

- 网络连接有限。
- 客户端设备从内部拆分脑 DNS 实现中收到 AD FS 服务的名称解析不正确。
- 如果在计算机上配置 Internet 代理服务器，则不会将 AD FS 名称添加到代理旁路列表。
- 不会在 **Internet 选项** 设置中将 AD FS 名称添加到本地 Intranet 安全区域。
- 客户端计算机未向 Active Directory 域服务（AD DS）进行身份验证。
- 第三方 Web 浏览器不支持对 AD FS 服务 **进行身份验证的扩展保护** 。
- 由于早期安装了 Office 365 Beta 版的单点登录管理工具，联合元数据终结点在注册表中被硬编码。
- 禁用特定客户端应用程序所需的 AD FS 服务终结点。

在继续之前，请确保满足以下条件：

- 访问问题不限于客户端计算机上的丰富客户端应用程序。 如果仅富客户端身份验证（而不是基于浏览器的身份验证）不起作用，则此条件可能表示富客户端身份验证问题。 例如，这可能是一个与富客户端应用程序的先决条件或配置相关的问题。 有关详细信息，请参阅 [如何排查无法登录到 Office 365、Azure 或 Intune 的非浏览器应用](https://support.microsoft.com/office/account-management/how-to-troubleshoot-non-browser-apps-that-can-t-sign-in-to-microsoft-365-azure-or-intune)的问题。
- 所有启用了 SSO 的用户帐户的 SSO 身份验证都不会失败。 如果所有启用了 SSO 的用户都遇到相同的症状，则此情况可能表示联合问题。 有关详细信息，请参阅[单一登录不适用于Office 365、Azure或 Intune 中的某些设备](sign-in-office-365-azure-intune-sso-does-not-work)。
- 用户帐户的 SSO 身份验证在其他客户端计算机上成功。 如果用户帐户无法登录到任何云服务客户端，请参阅本文中涉及客户端计算机的解决方案。 还可能存在影响用户帐户而不是客户端计算机的问题。 有关详细信息，请参阅 [在 Microsoft 365、Azure 或 Intune 中排查联合用户的帐户问题](/zh-cn/troubleshoot/microsoft-365/admin/authentication/account-issues-for-federated-users)。
- 客户端计算机上的键盘正常工作，用户名和密码输入正确。

## 解决方案

若要解决此问题，请使用以下一个或多个方法，具体取决于问题的原因。

### 解决方法 1：无法连接到云服务门户或 AD FS

尝试浏览到 `http://www.msn.com`。 如果此尝试不起作用，请排查网络连接问题。 执行以下步骤：

1. 在命令提示符下，使用 ipconfig 和 ping 工具排查 IP 连接问题。 有关详细信息，请参阅 [如何排查基本 TCP/IP 问题](https://support.microsoft.com/help/169790)。
2. 在命令提示符下，输入 `nslookup www.msn.com` 以确定 DNS 是否正在解析 Internet 服务器名称。
3. 如果本地网络中使用了代理服务器，请确保 **Internet 选项** 代理设置反映相应的代理服务器。
4. 如果在网络边界上安装 Forefront Threat Management Gateway （TMG） 防火墙，并且防火墙需要客户端身份验证，则可能需要在客户端设备上安装 Forefront TMG 客户端程序才能进行 Internet 访问。 如果需要帮助，请联系云服务管理员。

### 解决方法 2：无法连接到 AD FS

若要解决此问题，请执行以下步骤：

1. 使用 [解决方案 1](#resolution-1-cant-connect-to-cloud-service-portal-or-ad-fs) 消除 IP 连接问题。
2. 在命令提示符下输入 `nslookup <AD FS 2.0 FQDN>`，然后按 Enter 检查 DNS 是否正确解析 AD FS 服务名称。

注释

在此命令中， `<AD FS FQDN>` 表示 AD FS 服务名称的完全限定域名（FQDN）。 它不表示 AD FS 服务器的 Windows 主机名。

如果客户端连接到公司网络，请确保 IP 地址是专用 IP 地址。 IP 地址应与以下模式之一匹配：

- `10.x.x.x`
- `172.16.x.x`
- `192.168.x.x`

如果客户端位于公司网络外部，请确保 IP 地址是公共 IP 地址。 请确保它与以下模式之一不匹配：

- `10.x.x.x`
- `172.16.x.x`
- `192.168.x.x`

如果 IP 地址根据前面的步骤不正确，并且其他客户端计算机没有遇到相同的行为，请执行以下步骤：

1. 在命令提示符下，输入 `ipconfig /all`，然后检查主 DNS 服务器条目是否适用于客户端附加到的网络。
2. 将`%windir%\system32\drivers\etc\hosts`文件在记事本中打开，然后删除任何关于 AD FS FQDN 的条目。 保存文件。
3. 在命令提示符下，输入 `ipconfig /flushdns` 以清除 DNS 缓存。

注释

如果客户端设备仅连接到企业网络，请转到下一步。

1. 将 AD FS FQDN 添加到代理旁路列表。 有关详细信息，请参阅 [Microsoft Edge 中的代理支持](/zh-cn/deployedge/configure-microsoft-edge-proxy-support)。

### 解决方法 3：连接到 AD FS 终结点时出现证书警告

若要解决此问题，请排查安全套接字层（SSL）证书问题。 有关详细信息，请参阅 [尝试登录到 Office 365、Azure 或 Intune 时收到 AD FS 的证书警告](/zh-cn/previous-versions/troubleshoot/microsoft-365/admin/certificate-warning-from-ad-fs)。

### 方案 4：当您从连接到公司网络的客户端计算机登录时，会收到一个意外的凭据提示。

若要解决此问题，请执行以下步骤：

1. 确保客户端计算机已成功登录到域。
2. 选择“**开始**>，输入 `%logonserver%\sysvol`，然后选择“**确定**”。 如果出现凭据提示，请注销，然后使用公司凭据重新登录。
3. 将 AD FS FQDN 添加到本地 Intranet 区域。
4. 在“ **安全** ”选项卡上，选择 **“本地 Intranet**>**站点**>**高级**”。
5. 检查**网站**列表以获取 AD FS 服务终结点的完全限定 DNS 名称（例如 **sts.contoso.com**）。

   注释

   通配符值（例如“\*.consoto.com”）也适用于此配置。
6. 将 AD FS FQDN 添加到代理旁路列表。 有关详细信息，请参阅 [Microsoft Edge 中的代理支持](/zh-cn/deployedge/configure-microsoft-edge-proxy-support)。

### 解决方法 5：第三方 Web 浏览器不支持扩展身份验证保护，并且会收到循环身份验证提示

若要解决此问题，请执行以下步骤：

- 使用 Microsoft Edge，而不是不支持身份验证扩展保护的第三方 Web 浏览器。

如果Microsoft Edge 不是选项，请参阅 [登录 Office 365、Azure 或 Intune 期间反复提示联合用户输入凭据](/zh-cn/troubleshoot/microsoft-365/admin/sign-in/federated-user-repeatedly-prompted-for-credentials)。

### 解决方法 6：尝试连接到 login.microsoftonline.com 时出现“访问被拒绝”错误消息

重要

此解决方法包含有关如何修改注册表的步骤。 如果注册表修改不正确，则可能会出现严重问题。 在修改注册表之前，请务必备份注册表。 有关详细信息，请参阅 [如何在 Windows 中备份和还原注册表](https://support.microsoft.com/help/322756)。

若要解决此问题，请使用注册表编辑器删除以下注册表子项：

`HKEY_LOCAL_MACHINE\Software\Microsoft\MOCHA\IdentityFederation`

然后，AD FS 根据 SSO 依赖方信任退回到正确的终结点。

### 解决方法 7：将禁用的 AD FS 服务终结点设置重置为默认配置

有关如何进行重置的详细信息，请参阅 [在更改联合身份验证服务终结点后登录到 Office 365、Azure 或 Intune 失败](/zh-cn/troubleshoot/microsoft-365/admin/active-directory/sign-in-fails-if-federation-endpoint-changes)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/mfa/sign-in-office-365-azure-intune-sso-does-not-work)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
