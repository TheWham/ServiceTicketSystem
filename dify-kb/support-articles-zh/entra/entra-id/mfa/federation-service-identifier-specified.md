# 尝试在 Office 365、Azure 或 Intune 中设置另一个联合域时出错：AD FS 2.0 服务器中指定的联合服务标识符已在使用中

本文介绍如何解决在使用适用于 Windows PowerShell 的 `New-MSOLFederatedDomain` Azure Active Directory 模块运行命令或 `Convert-MSOLDomainToFederated` 命令时收到错误消息的问题。

*原始产品版本：* 云服务（Web 角色/辅助角色）、Microsoft Entra ID、Microsoft Intune、Azure 备份、Office 365 标识管理  
*原始 KB 数：* 2618887

注意

自 2024 年 3 月 30 日起，Azure AD 和 MSOnline PowerShell 模块已弃用。 若要了解详细信息，请阅读[有关弃用的更新](https://techcommunity.microsoft.com/t5/microsoft-entra-blog/important-azure-ad-graph-retirement-and-powershell-module/ba-p/3848270)。 在此日期之后，对这些模块的支持仅限于到 Microsoft Graph PowerShell SDK 的迁移帮助和安全性修复。 弃用的模块将持续运行至 2025 年 3 月 30 日。

我们建议迁移到 [Microsoft Graph PowerShell](/zh-cn/powershell/microsoftgraph/overview)，以便与 Microsoft Entra ID（以前称为 Azure AD）进行交互。 有关常见迁移问题，请参阅[迁移常见问题解答](/zh-cn/powershell/azure/active-directory/migration-faq)。
*注意：*2024 年 6 月 30 日之后，MSOnline 版本 1.0.x 可能会遇到中断。

## 现象

在 office 365、Microsoft Azure 或 Microsoft Intune 等Microsoft云服务中，无法在 Active Directory 联合身份验证服务 （AD FS） 服务器上设置第二个联合域。 使用适用于 Windows PowerShell 的 Azure Active Directory 模块运行 `New-MSOLFederatedDomain` 命令或 `Convert-MSOLDomainToFederated` 命令时，会收到以下错误消息：

> Active Directory 联合身份验证服务 2.0 服务器中指定的联合身份验证服务标识符已在使用中。 请在 AD FS 2.0 管理控制台中更正此值，然后再次运行该命令。

## 原因

Microsoft Entra 身份验证系统需要每个联合域的唯一联合品牌统一资源标识符（URI）。 默认情况下，AD FS 对所有联合信任使用全局值。 尝试在联合信任已存在的情况下联合第二个域时，请求会失败，因为 URI 已被使用。

## 解决方法

若要解决此问题，必须使用 `-supportmultipledomain` 开关添加或转换云服务联合的每个域。 这包括已存在的联合域。

### 步骤 1：为 AD FS 2.0 安装更新汇总 1

在 AD FS 2.0 联合身份验证服务场的每个节点上，下载并安装 AD FS 2.0 的更新汇总 1。 有关如何下载和安装 AD FS 2.0 更新汇总 1 的详细信息，请参阅[适用于 Active Directory 联合身份验证服务 （AD FS） 2.0](https://support.microsoft.com/help/2607496) 的更新汇总 1 的说明。

注意

此更新需要重新启动计算机。 如果未重新启动计算机，当联合用户尝试登录到 Office 365、Azure 或 Intune [时，会遇到](https://support.microsoft.com/help/2635357)“抱歉，但登录时遇到问题”和“8004789A”错误。

### 步骤 2：检查 `Update-MSOLFederatedDomain` 是否可以针对 AD FS 环境成功运行命令

1. 选择“**启动****>所有程序****>Windows Azure Active Directory**”，右键单击 **Windows PowerShell** 的 Windows Azure Active Directory 模块，然后选择“**以管理员**身份运行”。
2. 在命令提示符处，按照显示命令的顺序运行以下命令。 在每个命令后按 **Enter** 。

   ```
   Connect-MSOLService
   ```

   注意

   出现提示时， **输入** 云服务全局管理员凭据。

   ```
   Set-MSOLADFSContext -Computer <AD FS 2.0 server name>
   ```

   注意

   在此命令中， <AD FS 2.0 服务器名称> 是 AD FS 联合身份验证服务场中节点的计算机名称。

   ```
   Update-MSOLFederatedDomain -DomainName <Federated Domain Name>
   ```

   注意

   在此命令中， <联合域名> 是已与单一登录的 Microsoft Entra ID 联合的域的名称。
3. `Update-MSOLFederatedDomain`如果命令成功且未收到错误消息，请转到步骤 3 以从 AD FS 服务器中删除联合信任。

### 步骤 3：更新 AD FS 服务器上的联合信任

警告

应仔细规划以下步骤。 在联合域中启用 SSO 功能的用户无法在完成步骤 C 和 D 之间进行身份验证。 `Update-MSOLFederatedDomain` 如果步骤 2 中的命令测试未成功完成，则此过程的步骤 D 将无法正确完成。 在成功运行命令之前 `Update-MSOLFederatedDomain` ，联合用户将无法进行身份验证。

1. 登录到 AD FS 服务器的控制台，选择“**启动****>所有程序>管理工具**”，然后选择“**D FS”（2.0）管理。**
2. 在左侧导航窗格中，选择 **AD FS （2.0），**选择 **“信任关系**”，然后选择“ **信赖方信任**”。
3. 在右侧的窗格中，删除Microsoft 办公室 365 标识平台条目。
4. 使用 `-supportmultipledomain` 开关重新创建已删除的信任对象。 在从步骤 1C 打开的 PowerShell 窗口中运行以下命令，然后按 **Enter**：

   ```
   Update-MSOLFederatedDomain -DomainName <Federated Domain Name> -supportmultipledomain
   ```

注意

在此命令中， <联合域名> 是已与用于 SSO 的云服务联合的域的名称。

### 步骤 4：使用 `-supportmultipledomain` 开关添加或转换其他联合域

更新步骤 2 中的现有信任后，请使用 -supportmultipledomain 开关添加或转换其他联合域。 此开关通知命令对云服务联合的每个域使用唯一 URI 命名空间。 为此，请使用以下命令语法之一：

```
New-MSOLFederatedDomain -domainname <domain name> -supportmultipledomain
```

```
Convert-MSOLDomainToFederated -domainname <domain name> -supportmultipledomain
```

注意

在此命令中， <域名> 表示您尝试联合的域的名称。

## 解决方法

实现 AD FS 联合身份验证服务场，以联合将使用 SSO 功能的每个云服务域。 有关 Office 365 的 AD FS 实现指南，请参阅以下文章：

分步实施指南：[规划和部署 Active Directory 联合身份验证服务 2.0 以用于单一登录](https://onlinehelp.microsoft.com/office365-**enter**prises/ff652539.aspx)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/mfa/federation-service-identifier-specified)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
