# 排查Microsoft基于证书的身份验证问题

## 概要

iOS 或 Android 设备的 Microsoft Entra ID 中的基于证书的身份验证功能允许使用 X.509 证书进行单一登录（SSO）。 通过启用此功能，您可以登录帐户或服务，而无需在连接到 Exchange Online 帐户或 Office 移动应用程序时输入用户名和密码。

本文提供的信息有助于排查基于证书的身份验证问题。

*原始产品版本：* Microsoft Entra ID  
*原始 KB 数：* 4032987

## 一般要求

- 基于证书的身份验证仅支持使用新式身份验证（ADAL）的联合环境。 Exchange ActiveSync（EAS）是 Exchange Online 的一个例外，这些 Exchange Online 可供托管帐户使用。
- 在用户配置文件中颁发的用户证书要求用户的可路由电子邮件地址列在使用者可选名称**中**。 这可以是 UserPrincipalName 或 RFC822 格式。 Microsoft Entra ID 将 RFC822 值映射到目录中的 **代理地址** 属性。

## 确定基于证书的身份验证是否适用于Azure 门户

1. 浏览到[设备中的Azure 门户](https://portal.office.com)以测试基于证书的身份验证。

   注意

   必须先清除浏览器缓存，然后才能尝试连接，以便用户看到证书审批提示。
2. 键入用户的电子邮件地址。 这会重定向到 ADFS 身份验证页。
3. 选择使用 X.509 证书登录，并在出现提示时批准使用客户端证书**，而不是键入密码（如果 ADFS** 中启用了基于表单的身份验证方法）。

   如果在清除设备上的浏览器缓存后未收到证书审批提示，请执行以下步骤：

   1. 验证设备上是否安装了用户证书和证书颁发机构根证书。
   2. 验证 ADFS/Web 应用程序代理 服务器上是否打开了 TCP 端口 49443，以及颁发证书颁发机构的证书链是否已安装在所有 ADFS/Web 应用程序代理 服务器上。

## 确定是否已正确配置 Microsoft Entra ID

1. 运行以下 PowerShell 命令以安装 Azure Active Directory PowerShell（预览版）模块：

   ```
   Install-Module AzureAD
   ```
2. 若要创建受信任的证书颁发机构，请使用 [New-AzureADTrustedCertificateAuthority](/zh-cn/powershell/module/azuread/new-azureadtrustedcertificateauthority?view=azureadps-2.0&preserve-view=true) cmdlet，并将 **crlDistributionPoint** 属性设置为正确的值。

   注意

   在 Microsoft Entra ID 中创建 **TrustedRootCertificateAuthority** 对象时，在 中定义的 CRL URL。不使用 CER 文件。
   **CrlDistributionPoint** 和 **DeltaCrlDistributionPoint** 值必须由 web 位置手动填充，其中Microsoft Entra ID 可以访问 CRL。 颁发的证书中的 CRL 路径不必包含可供Microsoft Entra ID 访问的 URL。 此外，下载时间超过 15 秒的大型 CRL 应置于更快的链接（如 Azure 存储），以避免缓存延迟，从而导致中间身份验证失败。

   ```
   $cert=Get-Content -Encoding byte "[LOCATION OF THE CER FILE]"
   $new_ca=New-Object -TypeName Microsoft.Open.AzureAD.Model.CertificateAuthorityInformation $new_ca.AuthorityType=0 $new_ca.TrustedCertificate=$cert
   $new_ca.crlDistributionPoint="<CRL Distribution URL>"
   New-AzureADTrustedCertificateAuthority -CertificateAuthorityInformation $new_ca
   ```
3. 请确保根据以下准则正确定义 TrustedCertificateAuthority **对象上的**以下值：

   - 客户端设备和 ADFS 和 Web 应用程序代理服务器必须可从 Internet 访问所有 **CrlDistributionPoint** 和 **DeltaCrlDistributionPoint** URL。
   - 这\*。根 CA 的 CER 应列为 **AuthorityType = RootAuthority**。
   - 这\*。中间 CA 的 CER 应如下所示列出：

     AuthorityType = IntermediateAuthority  
     AuthorityType = 0 = RootAuthority  
     AuthorityType = 1 = 中级权限机构

   注意

   若要对这些对象进行更改，请参阅 [“配置证书颁发机构](/zh-cn/azure/active-directory/authentication/active-directory-certificate-based-authentication-get-started#step-2-configure-the-certificate-authorities)”。
4. 运行以下命令以确保 ADFS 设置未设置为 **PromptLoginBehavior：true**。 否则，系统会提示用户为某些新式应用输入其用户名和密码。

   ```
   Connect-msolService
   ```

   ```
    Get-MSOLDomainFederationSettings -DomainName contoso.com
   ```

   注意

   自 2024 年 3 月 30 日起，Azure AD 和 MSOnline PowerShell 模块已弃用。 若要了解详细信息，请阅读[有关弃用的更新](https://techcommunity.microsoft.com/t5/microsoft-entra-blog/important-azure-ad-graph-retirement-and-powershell-module/ba-p/3848270)。 在此日期之后，对这些模块的支持仅限于到 Microsoft Graph PowerShell SDK 的迁移帮助和安全性修复。 弃用的模块将持续运行至 2025 年 3 月 30 日。

   我们建议迁移到 [Microsoft Graph PowerShell](/zh-cn/powershell/microsoftgraph/overview)，以便与 Microsoft Entra ID（以前称为 Azure AD）进行交互。 有关常见迁移问题，请参阅[迁移常见问题解答](/zh-cn/powershell/azure/active-directory/migration-faq)。
   *注意：*2024 年 6 月 30 日之后，MSOnline 版本 1.0.x 可能会遇到中断。

   注意

   之所以发生这种情况，是因为某些新式应用在其请求中发送 *prompt=login* to Microsoft Entra ID。 Microsoft Entra ID 会将 ADFS 请求 **中的此项转换为 wauth=usernamepassworduri** （这指示 ADFS 执行用户名/密码身份验证）和 **wfresh=0** （告知 ADFS 忽略 SSO 状态并执行新的身份验证）。 如果用户必须使用基于证书的身份验证， **则 PromptLoginBehavior** 必须设置为 **False**。

   若要在 Microsoft Entra 域中禁用 **PromptLoginBehavior** ，请运行以下命令：

   ```
   Set-MSOLDomainFederationSettings -domainname <domain> -PromptLoginBehavior Disabled
   ```

## 确定是否正确配置了 ADFS 和 Web 应用程序代理配置

1. 基于证书的身份验证需要 ADFS 2012R2 或更高版本，并且必须使用 Web 应用程序代理。

   注意

   不支持使用第三方 Web 应用程序代理，除非它支持 MS-ADFSPIP 协议文档中[的所有 MUST](/zh-cn/openspecs/windows_protocols/ms-adfspip/76deccb1-1429-4c80-8349-d38e61da5cbb)。
2. 根 `*.CER` 文件必须位于计算机的 **受信任根证书颁发机构\证书** 容器中。 此外，所有中间 `*.CER` 文件都必须位于计算机的 **中间根证书颁发机构\证书** 容器中。 可以通过在提升的命令提示符处运行 `certlm.msc` 或运行以下命令 `certutil.exe` 来验证这一点：

   ```
   certutil -verifystore root
   ```

   ```
   certutil -verifystore CA**
   ```
3. 客户端设备、ADFS 服务器和 Web 应用程序代理必须能够解析中间 CA \*上存在的 CRL 终结点。CER 和设备上颁发给用户配置文件的用户证书。

   若要验证 ADFS 服务器和 Web 应用程序代理是否可以解析这些服务器，请执行以下步骤：

   1. 导出中间 CA \*。CER：
      1. 查看计算机证书存储。 为此，请运行 **certlm.msc**，展开 **\中间证书颁发机构\证书**，然后双击中间 CA 证书。
      2. **单击“详细信息**”选项卡，然后单击“复制到文件**”**按钮。
      3. 单击“ **下一步** ”两次并接受向导中的所有默认值。
      4. 指定文件名和位置，单击“下一步**”**，然后单击“**完成**”。
   2. 在颁发 CA 上，导出颁发给设备的用户证书之一。 要实现这一点，请执行下列操作：
      1. 运行 **certsrv.msc**，然后选择“颁发的证书**”**节点。
      2. 在 **“已颁发公用名** ”列中，找到颁发给无法连接的用户的证书。
      3. 双击证书，然后单击“ **详细信息** ”选项卡将证书导出到 \*。CER 文件。

         注意

         如果向用户颁发了多个证书，请在“ **详细信息** ”选项卡上找到证书的序列号，并验证它是否与设备上的证书匹配。
      4. 下载[PSEXEC.EXE](https://technet.microsoft.com/sysinternals/pxexec.aspx)，然后将psexec.exe与 \*一起复制。从中间 CA 和用户到所有 ADFS 和 Web 应用程序代理服务器的 CER 文件。
      5. 在 SYSTEM 安全上下文中打开新的命令提示符。 为此，请为每个服务器打开提升的命令提示符，然后运行以下命令：

         ```
         psexec -s -i -d cmd.exe
         ```
      6. 在新命令提示符下，运行以下命令以确定是否可以访问 CRL：

         ```
         certutil.exe -verify -urlfetch SubCA.cer > %computername%_%username%_SubCA.txt
         ```

         ```
         certutil.exe -verify -urlfetch usercert.cer > %computername%_%username%_usercert.txt
         ```
      7. 在输出中 **，检查----------------证书 CDP ----------------** 部分，并确定是否可以解析所有终结点。
      8. 如果 ADFS 服务器无法解析 HTTP URL，请确保 ADFS 正在运行的组托管服务帐户有权通过防火墙和代理进行访问。 Web 应用程序代理服务在网络服务下运行，因此 **ComputerName$** 帐户需要通过防火墙和代理进行访问。
4. 必须为 Active Directory **声明提供程序信任和 **Microsoft 办公室 365 标识平台**信赖方信任配置** serialNumber **和**颁发者的**声明**。 可以通过在提升的提示符处运行以下 PowerShell 命令，从 ADFS 服务器检索这些命令：

   ```
   Get-AdfsClaimsProviderTrust -Name "Active Directory"
   @RuleTemplate = "PassThroughClaims"
   @RuleName = "<serialnumber AD for cert based auth>"
   c:[Type ==
   http://schemas.microsoft.com/ws/2008/06/identity/claims/serialnumber]
     => issue(claim = c);
   @RuleTemplate = "PassThroughClaims"
   @RuleName = "<Issuer AD for cert based auth>"
   c:[Type ==
   http://schemas.microsoft.com/2012/12/certificatecontext/field/issuer]
     => issue(claim = c);
   ```

   ```
   Get-AdfsRelyingPartyTrust -Name "Microsoft Office 365 Identity Platform"
   @RuleTemplate = "PassThroughClaims"
   @RuleName = "<serialnumber RP for cert based auth>"
   c:[Type ==
   http://schemas.microsoft.com/ws/2008/06/identity/claims/serialnumber]
     => issue(claim = c);
   @RuleTemplate = "PassThroughClaims"
   @RuleName = "<Issuer RP for cert based auth>"
   c:[Type ==
   http://schemas.microsoft.com/2012/12/certificatecontext/field/issuer]
     => issue(claim = c);
   ```
5. 由于使用证书身份验证的大多数设备可能位于 Extranet（企业网络外），因此可以根据需要为 Extranet 或 Intranet 启用基于证书的身份验证。 若要确定是否为任一选项或两个选项启用“证书身份验证”方法，请从提升的 PowerShell 命令提示符运行以下 cmdlet：

   ```
   Get-AdfsAuthenticationProvider:

   ----------Output sample----------

   AdminName                          : Certificate Authentication
   AllowedForPrimaryExtranet          : True
   AllowedForPrimaryIntranet          : True
   AllowedForAdditionalAuthentication : True
   AuthenticationMethods              : {urn:ietf:rfc:2246, urn:oasis:names:tc:SAML:1.0:am:X509-PKI,
                                        urn:oasis:names:tc:SAML:2.0:ac:classes:TLSClient,
                                        urn:oasis:names:tc:SAML:2.0:ac:classes:X509...}
   Descriptions                       : {}
   DisplayNames                       : {}
   Name                               : CertificateAuthentication
   IdentityClaims                     : {}
   IsCustom                           : False
   RequiresIdentity                   : False
   ```

   1. 找到名为**“证书身份验证**”的 **AdminName** 条目。
   2. **验证 AllowedForPrimaryExtranet** 是否设置为 **True。**
   3. （可选）如果想要来自 Intranet 用户的基于证书的身份验证，还可以将 **AllowedForPrimaryIntranet** 设置为 **True** 。
   4. **单击“详细信息**”选项卡，然后单击“复制到文件**”**按钮。
6. 必须在客户端设备和 ADFS 之间访问 TCP 端口 49443，也可以在客户端设备和 Web 应用程序代理服务器之间访问。 若要验证 TCP 49443 是否在 ADFS 服务器和 Web 应用程序代理上侦听并绑定到 ADFS，请运行以下命令：

   ```
   netsh http show urlacl > %computername%_49443.txt
   ```

   如果 TCP 端口 49443 可访问，应会看到如下输出：

   ```
   Reserved URL: https://<URL>:49443/adfs/
   User: NT SERVICE\adfssrv
   Listen: Yes
   Delegate: Yes
   SDDL: D:(A;;GA;;;S-1-5-80-2246541699-21809830-3603976364-117610243-975697593)
   ```
7. 在客户端设备上，尝试连接到 CertificateTransport 终结点。 例如，使用以下 URL：`Contoso.com`

   `https://sts.contoso.com:49443/adfs/services/trust/2005/certificatetransport`

   注意

   如果终结点可访问并侦听，则连接尝试在等待答案时应无限期旋转。

## 详细信息

- [Microsoft Entra ID：适用于 iOS 和 Android 的基于证书的身份验证现在以预览版提供。](https://techcommunity.microsoft.com/t5/azure-active-directory-identity/azuread-certificate-based-authentication-for-ios-and-android-now/ba-p/244999)
- [iOS 上基于证书的身份验证入门 - 公共预览版](/zh-cn/azure/active-directory/authentication/active-directory-certificate-based-authentication-ios)
- [ADFS：使用 Microsoft Entra ID 和 Office 365 进行证书身份验证](/zh-cn/archive/blogs/samueld/adfs-certauth-aad-o365)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/certificate-based-authenticate-issue)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
