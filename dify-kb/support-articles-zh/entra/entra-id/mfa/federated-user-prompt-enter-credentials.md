# 意外地提示联合用户输入帐户凭据

本文介绍在访问 Office 365、Azure 或 Microsoft Intune 时意外地提示联合用户输入其工作或学校帐户凭据的方案。

*原始产品版本：*Microsoft Entra ID、Microsoft Intune、Azure 备份、Office 365 标识管理  
*原始 KB 数：* 2535227

## 现象

当联合用户登录 Office 365、Microsoft Azure 或 Microsoft Intune 时，系统会意外地提示用户输入工作或学校帐户凭据。 用户输入凭据后，将授予用户对云服务的访问权限。

注意

并非所有联合用户身份验证体验都没有凭据提示。 在某些情况下，根据设计，并预期会提示联合用户输入其凭据。 在继续之前，请确保凭据提示是意外的。

## 原因

如果满足以下一个或多个条件，则内部域客户端可能会出现此问题：

- 内部客户端将 Active Directory 联合身份验证服务 （AD FS） 终结点解析为 AD FS 代理服务的 IP 地址，而不是解析为 AD FS 联合身份验证服务的 IP 地址。
- Internet Explorer 中的安全设置未配置为单一登录 AD FS。
- Internet Explorer 中的代理服务器设置未配置为单一登录 AD FS。
- Web 浏览器不支持集成Windows 身份验证。
- 客户端计算机无法连接到本地 Active Directory域。

## 解决方法 1：确保 DNS 服务器具有 AD FS 终结点的主机记录

确保 DNS 服务器具有适用于遇到此问题的客户端计算机的 AD FS 终结点的主机记录。 对于内部客户端，这意味着内部 DNS 服务器应将 AD FS 终结点名称解析为内部 IP 地址。 对于 Internet 客户端，这意味着终结点名称应解析为公共 IP 地址。 若要在客户端上测试此操作，请执行以下步骤：

1. 选择“开始”，选择“运行”，键入 cmd，然后按 Enter。
2. 在命令提示符处，键入以下命令，其中占位符 `sts.contoso.com` 表示 AD FS 终结点名称：

   ```
   nslookup sts.contoso.com
   ```
3. 如果命令的输出显示错误的 IP 地址，请更新内部或外部 DNS 服务器上的 A 记录。 有关如何执行此操作的详细信息，请参阅 [Internet 浏览器在联合用户尝试登录 Office 365、Azure 或 Intune 时无法显示联合用户的](/zh-cn/office365/troubleshoot/sign-in/ad-fs-sign-in-page-not-display) AD FS 登录网页，Internet 浏览器无法显示 AD FS 网页

## 解决方法 2：检查 Internet Explorer 中的本地 Intranet 区域和代理服务器设置

根据情况使用下列过程之一。

### 过程 A

在 Internet Explorer 中检查本地 Intranet 区域和代理服务器设置。 为此，请按照下列步骤进行操作：

1. 启动 Internet Explorer。
2. 在"工具"菜单上，选择"Internet 选项"。
3. 选择**安全**选项卡，选择**本地 Intranet**区域，然后选择**站点**。
4. 在 **“本地 Intranet** ”对话框中，选择“ **高级**”。 在 **“网站”** 列表中，确保 AD FS 服务终结点的完全限定 DNS 名称存在条目（例如 `sts.contoso.com`）。
5. 选择“关闭”，然后选择“确定”。

   注意

   仅当网络管理员在本地环境中配置了 Web 代理服务器时，才使用以下附加步骤：
6. **选择“连接**”选项卡，然后选择“**LAN 设置**”。
7. 在“自动配置”下**，选中以清除**“自动检测设置**”复选框，然后选择清除**“使用自动配置脚本**”**复选框。
8. 在“代理服务器”下**，选中“**为 LAN** 使用代理服务器”复选框，键入代理服务器地址及其使用的端口，然后选择“高级**”。****
9. 在“例外**”下**，添加 AD FS 终结点（例如`sts.contoso.com`）。
10. 单击**确定**三次。

### 过程 B

在 Internet Explorer 中手动配置安全区域的安全设置。 对于 Internet Explorer 中的任何安全区域，可以手动配置本地 Intranet 区域不提示Windows 身份验证的默认安全设置。 若要自定义 AD FS 服务名称已是其中一部分的安全区域，请执行以下步骤：

警告

我们极不鼓励此配置，因为它可能会导致将集成 Windows 身份验证流量意外提交到网站。

1. 启动 Internet Explorer。
2. 在 **“工具”** 菜单上，选择“ **Internet”选项**。
3. **选择“安全**”选项卡，选择 AD FS 服务名称已包含的安全区域，然后选择“**自定义级别**”。
4. 在 **“安全设置”** 对话框中，滚动到底部以找到 **“用户身份验证** ”条目。
5. 在“登录”下**，选择**具有当前用户名和密码**的“自动**登录”。
6. 选择“ **确定** 两次”。

## 解决方法 3：使用 Internet Explorer 或第三方 Web 浏览器

使用支持集成Windows 身份验证的 Internet Explorer 或第三方 Web 浏览器。

## 解决方法 4：验证与 Active Directory 的连接

从客户端计算机注销，然后以 Active Directory 用户身份登录。 如果登录成功，请使用 Nltest 命令行工具验证与 Active Directory 的连接。 Nltest.exe包含在适用于 Windows 10 [的](https://www.microsoft.com/download/details.aspx?id=45520)远程服务器管理工具中。

1. 在命令提示符处，键入以下命令，然后按 Enter： `Nltest /dsgetdc:<FQDN Of Domain>` 如果设置正确，则会收到如下所示的输出：

   > DC： \DC.contoso.com Address：\ <IP Address> Dom Guid： GUID< Dom Name： >contoso.com 林名称： contoso.com Dc 站点名称： default-first-site-name our site name： default-first-site-name flags： PDC GC DS LDAP KDC TIMESERV GTIMESERV WRITABLE DNS\_DC DNS\_DOMAIN DNS\_FOREST CLOSE\_SITE 命令成功完成
2. 检查计算机的站点成员身份。 为此，请键入以下命令，然后按 Enter： `nltest /dsgetsite` 成功的结果如下所示：

   > Default-First-Site-Name 命令成功完成

## 详细信息

使用非联合帐户或来自公共 Internet 连接的联合帐户访问 Office 365 资源可能会导致单一登录体验。

登录 Microsoft Outlook 连接的体验也不应是单一登录体验。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/mfa/federated-user-prompt-enter-credentials)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
