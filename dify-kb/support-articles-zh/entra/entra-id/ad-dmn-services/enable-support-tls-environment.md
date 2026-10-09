# 在环境中为 Microsoft Entra 启用 TLS 1.2 支持

## 总结

本文介绍如何在环境中启用对传输层安全性 （TLS） 1.2 的支持，以准备即将弃用 Microsoft Entra TLS 1.0 和 1.1。

为了改善租户的安全状况，并保持符合行业标准，Microsoft Entra ID 将很快停止支持以下 TLS 协议和密码：

- TLS 1.1
- TLS 1.0
- 3DES 密码套件 (TLS\_RSA\_WITH\_3DES\_EDE\_CBC\_SHA)

## 此更改可能对组织造成的影响

应用程序是否与 Microsoft Entra ID 通信或进行身份验证？ 如果这些应用程序无法使用 TLS 1.2 进行通信，则可能无法按预期工作。 这种情况包括：

- Microsoft Entra Connect
- Microsoft Graph PowerShell
- Microsoft Entra 应用程序代理连接器
- PTA 代理人
- 旧版浏览器
- 与 Microsoft Entra ID 集成的应用程序

## 进行此更改的原因

由于以下原因，正在弃用这些协议和密码：

- 遵循[联邦风险和授权管理计划 (FedRAMP)](https://www.fedramp.gov/) 的最新合规标准。
- 提高用户与我们的云服务交互时的安全性。

**TLS 1.0**、**TLS 1.1** 和 **3DES 密码套件**服务将按以下计划弃用。

| 实例类型 | 弃用日期 | 状态 |
| --- | --- | --- |
| 美国政府实例 | 2021 年 3 月 31 日 | **完成** |
| 公共实例 | 2022 年 1 月 31 日 | **完成** |
| 由世纪互联在中国运营的Microsoft Entra 实例 | 2025 年 1 月 31 日 | **正在进行** |

## 对 Microsoft Entra 服务的 TLS 1.3 支持

除了支持 TLS 1.2 外，Microsoft Entra 还对其终结点推出对 TLS 1.3 的支持，以符合安全最佳做法（[NIST - SP 800-52 Rev. 2](https://csrc.nist.gov/pubs/sp/800/52/r2/final)）。 通过此更改，Microsoft Entra 终结点将同时支持 TLS 1.2 和 TLS 1.3 协议。

## 在环境中启用 TLS 1.2 支持

若要确保与 Microsoft Entra ID 和 Microsoft 365 服务建立安全连接，请将客户端应用和客户端和服务器操作系统（OS）配置为支持 TLS 1.2 和当代密码套件。

### 在客户端上启用 TLS 1.2 的指南

- 更新 Windows 及其用于“WinHTTP”的默认 TLS 版本。
- 识别并减少对不支持 TLS 1.2 的客户端应用和操作系统的依赖。
- 为与 Microsoft Entra ID 通信的应用程序和服务启用 TLS 1.2。
- 更新和配置 .NET Framework 安装以支持 TLS 1.2。
- 确保应用程序和 PowerShell（使用 [Microsoft Graph](https://graph.microsoft.com) 和 [Microsoft Graph PowerShell](/zh-cn/powershell/microsoftgraph/overview)）脚本托管并在支持 TLS 1.2 的平台上运行。
- 确保 Web 浏览器具有最新更新。 我们建议你使用新的 Microsoft Edge 浏览器（基于 Chromium）。 有关详细信息，请参阅 [Microsoft Edge Stable 渠道发行说明](/zh-cn/deployedge/microsoft-edge-relnote-stable-channel)。
- 确保 Web 代理支持 TLS 1.2。 若要详细了解如何更新 Web 代理，请咨询 Web 代理解决方案的供应商。

有关详细信息，请参阅以下文章：

- [如何在客户端上启用 TLS 1.2](/zh-cn/mem/configmgr/core/plan-design/security/enable-tls-1-2-client)
- [为 Office 365 和 Office 365 GCC 准备 TLS 1.2 - Microsoft 365 合规性](/zh-cn/purview/prepare-tls-1.2-in-office-365)

### 更新 Windows OS 和你用于 WinHTTP 的默认 TLS。

这些操作系统本机支持将 TLS 1.2 用于通过 WinHTTP 进行客户端-服务器通信：

- Windows 8.1、Windows 10 及更高版本
- Windows Server 2012 R2、Windows Server 2016 及更高版本

验证你是否尚未在这些平台上明确禁用 TLS 1.2。

默认情况下，Windows 早期版本（如 Windows 8 和 Windows Server 2012）不会使用 WinHTTP 为安全通信启用 TLS 1.2 或 TLS 1.1。 对于这些早期版本的 Windows 操作系统：

1. 安装[更新 3140245](https://support.microsoft.com/help/3140245)。
2. “在客户端或服务器操作系统上启用 TLS 1.2”部分中启用注册表值。

你可以配置这些值以将 TLS 1.2 和 TLS 1.1 添加到 WinHTTP 的默认安全协议列表中。

有关详细信息，请参阅[如何在客户端上启用 TLS 1.2](/zh-cn/mem/configmgr/core/plan-design/security/enable-tls-1-2-client)。

注意

默认情况下，支持 TLS 1.2（例如 Windows 10）的 OS 也支持旧版 TLS 协议。 使用 TLS 1.2 进行连接时，不会及时响应，或者连接重置时，OS 可能会尝试使用较旧的 TLS 协议（例如 TLS 1.0 或 1.1）连接到目标 Web 服务。 如果网络繁忙，或者数据包在网络中丢弃，则通常会发生这种情况。 临时回退到旧版 TLS 后，OS 将重试建立 TLS 1.2 连接。

Microsoft停止支持旧版 TLS 后，此类回退流量的状态是什么？ OS 仍可能尝试使用旧版 TLS 协议建立 TLS 连接。 但是，如果Microsoft服务不再支持旧版 TLS 协议，则基于 TLS 的旧连接不会成功。 这将强制 OS 改用 TLS 1.2 再次尝试连接。

### 识别和减少对不支持 TLS 1.2 的客户端的依赖项

更新以下客户端以提供不间断访问：

- Android 版本 4.3 及更早版本
- Firefox 版本 5.0 及更早版本
- Windows 7 上的 Internet Explorer 版本 8-10 及更早版本
- Windows Phone 8.0 上的 Internet Explorer 10
- OS X 10.8.4 上的 Safari 6.0.4 及更早版本

有关详细信息，请参阅[针对 SSLLabs.com 提供的连接到 www.microsoft.com 的各种客户端的握手模拟](/zh-cn/security/engineering/solving-tls1-problem#appendix-a-handshake-simulation)。

### 在与 Microsoft Entra ID 通信的常见服务器角色上启用 TLS 1.2

- Microsoft Entra Connect （安装最新版本）

  - 是否还要在同步引擎服务器和远程 SQL Server 之间启用 TLS 1.2？ 然后，请确保已安装支持 Microsoft SQL Server 的 TLS 1.2 所需版本。
- Microsoft Entra Connect 身份验证代理（直通身份验证）（版本 1.5.643.0 及更高版本）
- Azure 应用程序代理（版本 1.5.1526.0 及更高版本强制执行 TLS 1.2）
- Active Directory 联合身份验证服务（AD FS）用于配置为使用 Azure 多重身份验证的服务器（Azure MFA）
- 配置为使用 NPS 扩展进行 Microsoft Entra 多重身份验证的 NPS 服务器
- MFA 服务器版本 8.0. *x* 或更高版本
- Microsoft Entra 密码保护代理服务

  **必需的操作**

  1. 强烈建议运行最新版本的代理、服务或连接器。
  2. 默认情况下，Windows Server 2012 R2 和更高版本上会启用 TLS 1.2。 在极少数情况下，默认 OS 配置可能已被修改为禁用 TLS 1。

     若要确保启用 TLS 1.2，我们建议在运行 Windows Server 并与 Microsoft Entra ID 通信的服务器上，明确添加“启用 TLS 1.2 于客户端或服务器操作系统”部分中的注册表值。
  3. 以前列出的大多数服务都依赖于.NET Framework。 请确保已按照[更新和配置 .NET Framework 以支持 TLS 1.2](#update-and-configure-net-framework-to-support-tls-12-)部分中所述进行更新。

  有关详细信息，请参阅以下文章：

  - [TLS 1.2 强制实施 - 为 Microsoft Entra 注册服务强制实施 TLS 1.2](/zh-cn/azure/active-directory/devices/reference-device-registration-tls-1-2)
  - [Microsoft Entra Connect：Microsoft Entra Connect 的 TLS 1.2 强制实施](/zh-cn/azure/active-directory/hybrid/reference-connect-tls-enforcement)
  - [了解 Microsoft Entra 应用程序代理连接器](/zh-cn/azure/active-directory/manage-apps/application-proxy-connectors#requirements-and-deployment)

## 在客户端或服务器操作系统上启用 TLS 1.2

### 注册表字符串

对于 Windows 2012 R2、Windows 8.1 及更高版本的操作系统，默认启用 TLS 1.2。 因此，除非使用不同的值设置以下注册表值，否则不会显示这些值。

若要在操作系统级别手动配置和启用 TLS 1.2，可以添加以下 DWORD 值：

- **HKEY\_LOCAL\_MACHINE\SYSTEM\CurrentControlSet\Control\SecurityProviders\SCHANNEL\Protocols\TLS 1.2\Client**
  - `DisabledByDefault`： **000000000**
  - `Enabled`： **00000001**
- **HKEY\_LOCAL\_MACHINE\SYSTEM\CurrentControlSet\Control\SecurityProviders\SCHANNEL\Protocols\TLS 1.2\Server**
  - `DisabledByDefault`： **000000000**
  - `Enabled`： **00000001**
- **HKEY\_LOCAL\_MACHINE\SOFTWARE\Microsoft\。NETFramework\v4.0.30319**
  - `SchUseStrongCrypto`： **00000001**

若要使用 PowerShell 脚本启用 TLS 1.2，请参阅 [Microsoft Entra Connect](/zh-cn/azure/active-directory/hybrid/reference-connect-tls-enforcement) 的 TLS 1.2 强制实施。

## 如何检查正在使用的 TLS 协议

下面是检查正在使用的 TLS 的两种方法：

- 浏览器安全设置
- Windows 中的 Internet 属性

若要检查使用 Internet 属性使用的 TLS 协议，请执行以下步骤：

1. 按 `Windows`+`R` 打开 **“运行** ”框。
2. 键入 *inetcpl.cpl* ，然后选择“ **确定**”。 然后， **将打开“Internet 属性”** 窗口。
3. 在 **“Internet 属性** ”窗口中，选择“ **高级** ”选项卡并向下滚动以检查与 TLS 相关的设置。

   ![显示 Internet 属性中与 TLS 相关的设置的屏幕截图。](media/enable-support-tls-environment/used-tls-protocol.png)

## 更新和配置 .NET Framework 以支持 TLS 1.2

托管的 Microsoft Entra 集成应用程序和 Windows PowerShell 脚本（使用 [Microsoft Graph PowerShell](/zh-cn/powershell/microsoftgraph/overview) 和 [Microsoft Graph](https://graph.microsoft.com)）可以使用 .NET Framework。

### 安装 .NET 更新以启用强加密

#### 确定 .NET 版本

首先，确定已安装的 .NET 版本。

- 有关详细信息，请参阅[确定所安装的 .NET Framework 版本和 Service Pack 级别](../../../dotnet/framework/determine-dotnet-versions-service-pack-levels)。

#### 安装 .NET 更新

安装 .NET 更新，以便启用强加密。 某些版本的 .NET Framework 可能需要更新才能启用强加密。

使用以下准则：

- .NET Framework 4.6.2 及更高版本支持 TLS 1.2 和 TLS 1.1。 检查注册表设置。 无需进行其他更改。
- 更新 .NET Framework 4.6 及更早版本以支持 TLS 1.2 和 TLS 1.1。

  有关详细信息，请参阅 [.NET Framework 版本和依赖项](/zh-cn/dotnet/framework/migration-guide/versions-and-dependencies)。
- 是否在 Windows 8.1 或 Windows Server 2012 上使用 .NET Framework 4.5.2 或 4.5.1？ 然后，还可从 [Microsoft 更新目录](https://www.catalog.update.microsoft.com/Search.aspx?q=2898850)获取相关更新和详细信息。

  - 另请参阅 [Microsoft 安全通报 2960358](/zh-cn/security-updates/SecurityAdvisories/2015/2960358)。

对于跨网络通信并运行启用了 TLS 1.2 的系统的任何计算机，请设置以下注册表 DWORD 值。

- 对于在 32 位 OS 上运行的 32 位应用程序或在 64 位 OS 上运行的 64 位应用程序，请更新以下子项值：

  - **HKEY\_LOCAL\_MACHINE\SOFTWARE\Microsoft\。NETFramework\v2.0.50727**

    - `SystemDefaultTlsVersions`： **00000001**
    - `SchUseStrongCrypto`： **00000001**
  - **HKEY\_LOCAL\_MACHINE\SOFTWARE\Microsoft\。NETFramework\v4.0.30319**

    - `SystemDefaultTlsVersions`： **00000001**
    - `SchUseStrongCrypto`： **00000001**
- 对于在 64 位 OS 上运行的 32 位应用程序，请更新以下子项值：

  - **HKEY\_LOCAL\_MACHINE\SOFTWARE\Wow6432Node\Microsoft\。NETFramework\v2.0.50727**
    - `SystemDefaultTlsVersions`： **dword：00000001**
    - `SchUseStrongCrypto`： **dword：00000001**
  - **HKEY\_LOCAL\_MACHINE\SOFTWARE\WOW6432Node\Microsoft\。NETFramework\v4.0.30319**
    - `SystemDefaultTlsVersions`： **dword：00000001**
    - `SchUseStrongCrypto`： **dword：00000001**

例如，设置这些值如下：

- Configuration Manager 客户端
- 未安装在站点服务器上的远程站点系统角色
- 站点服务器本身

有关详细信息，请参阅以下文章：

- [Microsoft Entra ID 支持的 TLS 密码套件](/zh-cn/azure/active-directory-b2c/https-cipher-tls-requirements#cipher-suites)
- [如何在客户端上启用 TLS 1.2](/zh-cn/mem/configmgr/core/plan-design/security/enable-tls-1-2-client)
- [.NET Framework 中的传输层安全性 (TLS) 最佳做法](/zh-cn/dotnet/framework/network-programming/tls#configuring-schannel-protocols-in-the-windows-registry)
- [解决 TLS 1.0 问题 - 安全文档](/zh-cn/security/engineering/solving-tls1-problem)

## 登录日志中新遥测数据的概述

为了帮助你识别环境中仍使用旧版 TLS 的任何客户端或应用，请查看 Microsoft Entra 登录日志。 对于通过旧版 TLS 登录的客户端或应用，Microsoft Entra ID 会将“其他详细信息”**中的**“旧版 TLS**”字段标记为 **True**。** 仅当通过旧版 TLS 登录时才会显示旧版 TLS 字段。 如果在日志中看不到任何旧版 TLS，则可以切换到 TLS 1.2。

要查找使用旧版 TLS 协议的登录尝试，管理员可以通过以下方式查看日志：

- 在 Azure Monitor 中导出和查询日志。
- 以 JavaScript 对象表示法 (JSON) 格式下载过去 7 天的日志。
- 使用 PowerShell 筛选和导出登录日志。

将在下面介绍这些方法。

- [Azure Monitor](#tabpanel_1_azure-monitor)
- [JSON](#tabpanel_1_json)
- [PowerShell](#tabpanel_1_powershell)

可以使用 Azure Monitor 查询登录日志。 Azure Monitor 是一款功能强大的日志分析、监视和警报工具。 将 Azure Monitor 用于：

- Microsoft Entra 日志
- Azure 资源日志
- 独立软件工具的日志

注意

需要Microsoft Entra ID P1 或 P2 许可证才能将报告数据导出到 Azure Monitor。

若要使用 Azure Monitor 查询旧版 TLS 条目：

1. 在 [将 Microsoft Entra 日志与 Azure Monitor 日志](/zh-cn/azure/active-directory/reports-monitoring/howto-integrate-activity-logs-with-log-analytics)集成中，请按照有关如何访问 Azure Monitor 中的 Microsoft Entra 登录日志的说明进行操作。
2. 在查询定义区域中，粘贴以下 Kusto 查询语言查询：

   ```
   // Interactive sign-ins only
   SigninLogs
   | where AuthenticationProcessingDetails has "Legacy TLS"
       and AuthenticationProcessingDetails has "True"
   | extend JsonAuthProcDetails = parse_json(AuthenticationProcessingDetails)
   | mv-apply JsonAuthProcDetails on (
       where JsonAuthProcDetails.key startswith "Legacy TLS"
       | project HasLegacyTls=JsonAuthProcDetails.value
   )
   | where HasLegacyTls == true

   // Non-interactive sign-ins
   AADNonInteractiveUserSignInLogs
   | where AuthenticationProcessingDetails has "Legacy TLS"
       and AuthenticationProcessingDetails has "True"
   | extend JsonAuthProcDetails = parse_json(AuthenticationProcessingDetails)
   | mv-apply JsonAuthProcDetails on (
       where JsonAuthProcDetails.key startswith "Legacy TLS"
       | project HasLegacyTls=JsonAuthProcDetails.value
   )
   | where HasLegacyTls == true

   // Workload Identity (service principal) sign-ins
   AADServicePrincipalSignInLogs
   | where AuthenticationProcessingDetails has "Legacy TLS"
       and AuthenticationProcessingDetails has "True"
   | extend JsonAuthProcDetails = parse_json(AuthenticationProcessingDetails)
   | mv-apply JsonAuthProcDetails on (
       where JsonAuthProcDetails.key startswith "Legacy TLS"
       | project HasLegacyTls=JsonAuthProcDetails.value
   )
   | where HasLegacyTls == true
   ```
3. 选择“**运行**”以执行查询。 与查询匹配的日志条目显示在查询定义下方的“结果”选项卡中。
4. 若要了解有关旧版 TLS 请求源的信息，请查找以下字段：

   - **用户显示名称**
   - **AppDisplayName**
   - **ResourceDisplayName**
   - **UserAgent**

要查看“旧版 TLS”标记，可以下载最近七天的登录日志（JSON 格式）。

注意

1. 只有在旧版 TLS 用于登录请求时，“旧版 TLS”标记才会显示。
2. 如果下载逗号分隔值 (CSV) 格式的登录日志，则旧版 TLS 标记不会显示。

### 下载 JSON 日志

若要下载登录日志 JSON，请进行以下操作：

1. 在 [Azure 门户](https://portal.azure.com)中，搜索并选择“Microsoft Entra ID”。
2. 在“概述”页菜单中，选择“登录日志”。
3. 清除除“日期”筛选器之外的所有筛选器。
4. 将“日期”筛选器设置为“最近 7 天”。
5. 选择**下载**。
6. 选择每个日志类别：

   - 用户交互
   - 用户非交互
   - 托管身份

### 查看 JSON 文件

现在，可以使用你选择的 JSON 查看器查看 JSON 日志。

注意

如果需要 JSON 查看器，可以[下载 Visual Studio Code](https://code.visualstudio.com/Download)。

要查看 JSON 日志，请进行以下操作：

1. 在 JSON 查看器中打开 JSON 日志文件。
2. 搜索词语“旧版 TLS”。
3. 如果发现带有“旧版 TLS”的日志文件，请查看该登录日志条目，详细了解旧版 TLS 请求的源。 查找以下字段：

   - **UserDisplayName**
   - **AppDisplayName**
   - **ResourceDisplayName**
   - **UserAgent**

使用 PowerShell 筛选和导出使用旧版 TLS 的登录日志条目。

注意

需要Microsoft Entra ID P1 或 P2 许可证才能通过 PowerShell 调用 [Microsoft图形 API](/zh-cn/graph/use-the-api) 。

要筛选和导出登录日志条目，请进行以下操作：

1. 使用“以管理员身份运行”选项，从“开始”菜单打开 Windows PowerShell。
2. 运行以下命令以安装 [Microsoft Graph SDK](/zh-cn/graph/sdks/sdk-installation) 并设置执行策略：

   ```
   Install-Module Microsoft.Graph -Scope AllUsers
   Set-ExecutionPolicy -ExecutionPolicy Unrestricted -Scope CurrentUser
   ```
3. 将以下脚本保存到 PowerShell 脚本 (.ps1) 文件中。

   ```
   $tId = "your-tenant-id"  # Add tenant ID from Azure Active Directory page on portal.
   $agoDays = 4  # Will filter the log for $agoDays from the current date and time.
   $startDate = (Get-Date).AddDays(-($agoDays)).ToString('yyyy-MM-dd')  # Get filter start date.
   $pathForExport = "./"  # The path to the local filesystem for export of the CSV file.

   Connect-MgGraph -Scopes "AuditLog.Read.All" -TenantId $tId  # Or use Directory.Read.All.
   Select-MgProfile "beta"  # Low TLS is available in Microsoft Graph preview endpoint.

   # Define the filtering strings for interactive and non-interactive sign-ins.
   $procDetailFunction = "x: x/key eq 'legacy tls (tls 1.0, 1.1, 3des)' and x/value eq '1'"
   $clauses = (
       "createdDateTime ge $startDate",
       "signInEventTypes/any(t: t eq 'nonInteractiveUser')",
       "signInEventTypes/any(t: t eq 'servicePrincipal')",
       "(authenticationProcessingDetails/any($procDetailFunction))"
   )

   # Get the interactive and non-interactive sign-ins based on filtering clauses.
   $signInsInteractive = Get-MgAuditLogSignIn -Filter ($clauses[0,3] -Join " and ") -All
   $signInsNonInteractive = Get-MgAuditLogSignIn -Filter ($clauses[0,1,3] -Join " and ") -All
   $signInsWorkloadIdentities = Get-MgAuditLogSignIn -Filter ($clauses[0,2,3] -Join " and ") -All

   $columnList = @{  # Enumerate the list of properties to be exported to the CSV files.
       Property = "CorrelationId", "createdDateTime", "userPrincipalName", "userId",
                 "UserDisplayName", "AppDisplayName", "AppId", "IPAddress", "isInteractive",
                 "ResourceDisplayName", "ResourceId", "UserAgent"
   }

   $columnListWorkloadId = @{ #Enumerate the list of properties for workload identities to be exported to the CSV files.
       Property = "CorrelationId", "createdDateTime", "AppDisplayName", "AppId", "IPAddress",
                 "ResourceDisplayName", "ResourceId", "ServicePrincipalId", "ServicePrincipalName"
   }

   $signInsInteractive | ForEach-Object {
       foreach ($authDetail in $_.AuthenticationProcessingDetails)
       {
           if (($authDetail.Key -match "Legacy TLS") -and ($authDetail.Value -eq "True"))
           {
               $_ | Select-Object @columnList
           }
       }
   } | Export-Csv -Path ($pathForExport + "Interactive_lowTls_$tId.csv") -NoTypeInformation

   $signInsNonInteractive | ForEach-Object {
       foreach ($authDetail in $_.AuthenticationProcessingDetails)
       {
           if (($authDetail.Key -match "Legacy TLS") -and ($authDetail.Value -eq "True"))
           {
               $_ | Select-Object @columnList
           }
       }
   } | Export-Csv -Path ($pathForExport + "NonInteractive_lowTls_$tId.csv") -NoTypeInformation

   $signInsWorkloadIdentities | ForEach-Object {
       foreach ($authDetail in $_.AuthenticationProcessingDetails)
       {
           if (($authDetail.Key -match "Legacy TLS") -and ($authDetail.Value -eq "True"))
           {
               $_ | Select-Object @columnListWorkloadId
           }
       }
   } | Export-Csv -Path ($pathForExport + "WorkloadIdentities_lowTls_$tId.csv") -NoTypeInformation
   ```
4. 在 [Azure 门户](https://portal.azure.com)中，搜索并选择“Microsoft Entra ID”。
5. 将 **租户 ID** 值从 Microsoft Entra ID 页复制到 PowerShell 脚本的第一个语句中，并将其分配给变量 `$tId` 。
6. 保存并运行脚本。 如果在脚本运行时收到提示，请以全局管理员身份登录。 然后同意让 Microsoft Graph 读取审核日志信息。
7. 若要了解旧版 TLS 请求的源，请搜索脚本输出文件（*Interactive\_lowTls\_<Tenant-ID>.csv* 和 *NonInteractive\_lowTls\_<Tenant-ID>.csv*） 以获取以下字段：

   - **用户显示名称**
   - **AppDisplayName**
   - **ResourceDisplayName**
   - **UserAgent**

### 在 Microsoft Entra 管理中心查看有关日志条目的详细信息

获取日志后，可以在 Microsoft Entra 管理中心获取有关旧版基于 TLS 的登录日志条目的更多详细信息。 执行以下步骤：

1. 在 [Azure 门户](https://portal.azure.com)中，搜索并选择“Microsoft Entra ID”。
2. 在“概述”页菜单中，选择“登录日志”。
3. 为用户选择登录日志条目。
4. 选择"其他详细信息"选项卡。 (如果看不到此选项卡，请首先选择右上角的省略号 (**...**) 以查看选项卡的完整列表。
5. 检查**旧版 TLS（TLS 1.0、1.1 或 3DES）**的值是否设置为**真**。 如果看到该特定字段和值，则说明尝试登录时使用了旧版 TLS。 如果尝试使用 TLS 1.2 进行登录，则不会显示该字段。

有关详细信息，请参阅 [Microsoft Entra ID 中的登录日志](/zh-cn/azure/active-directory/reports-monitoring/concept-sign-ins)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/ad-dmn-services/enable-support-tls-environment)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
