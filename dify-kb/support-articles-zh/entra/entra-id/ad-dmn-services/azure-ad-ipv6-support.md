# Microsoft Entra ID 中的 IPv6 支持

注意

本文有帮助吗? 你的输入对我们很重要。 请使用此页上的 **“反馈** ”按钮告诉我们本文为你工作得有多好，或者我们如何改进它。

我们很高兴地将 IPv6 支持引入Microsoft Entra ID，以支持移动性更高的客户，并帮助减少快速消耗、昂贵的 IPv4 地址上的支出。 有关此更改如何影响 Microsoft 365 的详细信息，请参阅 [Microsoft 365 服务](/zh-cn/microsoft-365/enterprise/ipv6-support)中的 IPv6 支持。

如果组织的网络目前不支持 IPv6，则可以安全地忽略此信息，直到它们这样做。

## 有什么变化？

服务终结点 URL 现在解析为同时返回 IPv4 和 IPv6 地址。 如果客户端平台或网络支持 IPv6，则主要使用 IPv6 尝试连接，前提是两者之间的网络跃点（如防火墙或 Web 代理）也支持 IPv6。 对于不支持 IPv6 的环境，客户端应用程序将继续通过 IPv4 连接到 Microsoft Entra ID。

以下功能还将支持 IPv6 地址：

- 命名位置
- 条件访问策略
- 标识保护
- 登录日志

## Microsoft Entra ID 中何时支持 IPv6？

我们将在 2023 年 4 月开始引入对 Microsoft Entra ID 的 IPv6 支持。

我们知道，IPv6 支持对于某些组织来说是一个重大变化。 我们现在正在发布此信息，以便客户能够制定计划以确保就绪。

## 我的组织必须做什么？

如果具有表示网络的公共 IPv6 地址，请尽快执行以下部分中介绍的操作。

**如果客户未使用这些 IPv6 地址更新其命名位置，将阻止其用户。**

![显示用户因网络位置而阻止登录的屏幕截图。](media/azure-ad-ipv6-support/cant-sign-in-blocked-location-condition.png)

### 要执行的操作

- [通过 IPv6 测试Microsoft Entra 身份验证](#test-azure-ad-authentication-over-ipv6)
- [在登录日志中查找 IPv6 地址](#find-ipv6-addresses-in-sign-in-logs)
- [创建或更新命名位置，以包括标识的 IPv6 地址](/zh-cn/azure/active-directory/conditional-access/location-condition#ip-address-ranges)

### 命名位置

命名位置在许多功能之间共享，例如条件访问、标识保护和 B2C。 客户应与其网络管理员和 Internet 服务提供商（ISP）合作，以识别其面向公众的 IPv6 地址。 然后，客户应使用此列表 [创建或更新命名位置，以包括其标识的 IPv6 地址](/zh-cn/azure/active-directory/conditional-access/location-condition#ip-address-ranges)。

#### 条件访问

配置条件访问策略时，组织可以选择将位置作为条件包含或排除。 这些命名位置可能包括公共 IPv4 或 IPv6 地址、国家或地区或不映射到特定国家或地区的未知区域。

- 如果将 IPv6 范围添加到现有命名位置（用于现有条件访问策略中），则无需更改。
- 如果为组织的 IPv6 范围创建新的命名位置，则必须使用这些新位置更新相关的条件访问策略。

#### 云代理和 VPN

云代理准备就绪后，需要 [Microsoft Entra 混合加入或投诉设备](/zh-cn/azure/active-directory/conditional-access/howto-conditional-access-policy-compliant-device#create-a-conditional-access-policy) 的策略更易于管理。 对于云托管的代理或 VPN 解决方案的 IP 地址列表，要随时保持最新状态几乎是不可能的。

### Microsoft每用户多重身份验证的 Entra

如果你是使用每用户多重身份验证的客户，你是否添加了表示使用 [受信任 IP 地址而不是命名位置的本地受信任网络的 IPv4 地址](/zh-cn/azure/active-directory/authentication/howto-mfa-mfasettings#trusted-ips) ？ 如果有，可能会看到多重身份验证提示，提示通过启用了本地 IPv6 的出口点启动的请求。

不建议使用每用户多重身份验证，除非Microsoft Entra ID 许可证不包含条件访问，并且不想使用安全默认值。

### 出站流量限制

如果组织将出站网络流量限制到特定 IP 范围，则必须更新这些地址以包括 IPv6 终结点。 管理员可以在以下文章中找到这些 IP 范围：

- [Office 365 URL 和 IP 地址范围](/zh-cn/microsoft-365/enterprise/urls-and-ip-address-ranges#microsoft-365-common-and-office-online)
- [Microsoft Entra Connect：排查Microsoft Entra 连接问题](/zh-cn/azure/active-directory/hybrid/tshoot-connect-connectivity#troubleshoot-connectivity-issues-in-the-installation-wizard)

对于为 Microsoft Entra ID 指定的 IP 范围，请确保允许在代理或防火墙中进行出站访问。

### 设备配置

默认情况下，Windows 和大多数其他操作系统（OS）平台都支持 IPv6 和 IPv4 流量。 对标准 IPv6 配置的更改可能会导致意外后果。 有关详细信息，请参阅[适用于高级用户的在 Windows 中配置 IPv6 指南](../../../windows-server/networking/configure-ipv6-in-windows)。

### 服务终结点

Microsoft Entra ID 中 IPv6 支持的实现不会影响 Azure 虚拟网络 服务终结点。 服务终结点仍不支持 IPv6 流量。 有关详细信息，请参阅[虚拟网络服务终结点的限制](/zh-cn/azure/virtual-network/virtual-network-service-endpoints-overview#limitations)。

## 通过 IPv6 测试Microsoft Entra 身份验证

可以通过 IPv6 测试 Microsoft Entra 身份验证，然后才能使用以下过程在全球启用它。 这些过程有助于验证 IPv6 范围配置。 建议的方法是使用 [推送到已加入 Microsoft Entra 的 Windows 设备的名称解析策略表（NRPT）](/zh-cn/previous-versions/windows/it-pro/windows-server-2012-R2-and-2012/dn593632(v=ws.11)) 规则。 在 Windows Server 中，NRPT 允许你实现替代 DNS 解析路径的全局或本地策略。 使用此功能，可以将各种完全限定的域名（FQDN）的 DNS 重定向到配置为将 IPv6 DNS 条目配置为Microsoft Entra 登录的特殊 DNS 服务器。 使用 PowerShell 脚本启用和禁用 NRPT 规则非常简单。 可以使用 [Microsoft Intune](/zh-cn/mem/intune/fundamentals/what-is-intune) 将此功能推送到客户端。

注意

- Microsoft仅为测试目的提供这些说明。 必须在 2023 年 5 月前删除以下配置，以确保客户端正在使用生产 DNS 服务器。 以下过程中的 DNS 服务器可能在 2023 年 5 月之后解除授权。
- 建议使用 [Resolve-DnsName](/zh-cn/powershell/module/dnsclient/resolve-dnsname) cmdlet 来验证 NRPT 规则。 如果使用 [nslookup](/zh-cn/windows-server/administration/windows-commands/nslookup) 命令，则鉴于这些工具之间存在的差异，结果可能有所不同。
- 请确保在客户端设备和用于 NRPT 规则的 DNS 服务器之间在 TCP 和 UDP 端口 53 上打开网络连接。

### 手动配置客户端 NRPT 规则 - 公有云

1. 以管理员身份打开 PowerShell 控制台（右键单击 PowerShell 图标并选择“ **以管理员**身份运行”）。
2. 通过运行以下命令添加 NRPT 规则：

   ```
   $DnsServers = (
       "ns1-37.azure-dns.com.",
       "ns2-37.azure-dns.net.",
       "ns3-37.azure-dns.org.",
       "ns4-37.azure-dns.info."
   )
   $DnsServerIPs = $DnsServers | Foreach-Object {
       (Resolve-DnsName $_).IPAddress | Select-Object -Unique
   }
   $params = @{
       Namespace = "login.microsoftonline.com"
       NameServers = $DnsServerIPs
       DisplayName = "AZURE-AD-NRPT"
   }
   Add-DnsClientNrptRule @params
   ```
3. 通过运行 `login.microsoftonline.com` cmdlet 验证客户端是否获取 IPv6 响应。 命令输出应类似于以下文本：

   ```
   PS C:\users\username> Resolve-DnsName login.microsoftonline.com
   Name                          Type   TTL   Section    IPAddress 
   ----                          ----   ---   -------    --------- 
   login.microsoftonline.com     AAAA   300   Answer     2603:1037:1:c8::8 
   login.microsoftonline.com     AAAA   300   Answer     2603:1036:3000:d8::5 
   login.microsoftonline.com     AAAA   300   Answer     2603:1036:3000:d0::5 
   login.microsoftonline.com     AAAA   300   Answer     2603:1036:3000:d8::4 
   login.microsoftonline.com     AAAA   300   Answer     2603:1037:1:c8::9 
   login.microsoftonline.com     AAAA   300   Answer     2603:1037:1:c8::a 
   login.microsoftonline.com     AAAA   300   Answer     2603:1036:3000:d8::2 
   login.microsoftonline.com     AAAA   300   Answer     2603:1036:3000:d0::7 
   login.microsoftonline.com     A      300   Answer     20.190.151.7 
   login.microsoftonline.com     A      300   Answer     20.190.151.67 
   login.microsoftonline.com     A      300   Answer     20.190.151.69 
   login.microsoftonline.com     A      300   Answer     20.190.151.68 
   login.microsoftonline.com     A      300   Answer     20.190.151.132 
   login.microsoftonline.com     A      300   Answer     20.190.151.70 
   login.microsoftonline.com     A      300   Answer     20.190.151.9 
   login.microsoftonline.com     A      300   Answer     20.190.151.133
   ```
4. 如果要删除 NRPT 规则，请运行以下 PowerShell 脚本：

   ```
   Get-DnsClientNrptRule | Where-Object {
       $_.DisplayName -match "AZURE-AD-NRPT" -or $_.Namespace -match "login.microsoftonline.com"
   } | Remove-DnsClientNrptRule -Force
   ```

### 手动配置客户端 NRPT 规则 - US Gov 云

与公有云的脚本类似，以下脚本为 US Gov 登录终结点 `login.microsfotonline.us`创建 NRPT 规则。

1. 右键单击 PowerShell 图标并选择“ **以管理员**身份运行”，以管理员身份打开 PowerShell 控制台。
2. 通过运行以下命令添加 NRPT 规则：

   ```
   $DnsServers = (
       "ns1-35.azure-dns.com.",
       "ns2-35.azure-dns.net.",
       "ns3-35.azure-dns.org.",
       "ns4-35.azure-dns.info."
   )
   $DnsServerIPs = $DnsServers | Foreach-Object {
       (Resolve-DnsName $_).IPAddress | Select-Object -Unique
   }
   $params = @{
       Namespace = "login.microsoftonline.us"
       NameServers = $DnsServerIPs
       DisplayName = "AZURE-AD-NRPT-USGOV"
   }
   Add-DnsClientNrptRule @params
   ```

### 使用 Intune 部署 NRPT 规则

若要使用 Intune 将 NRPT 规则部署到多台计算机，请创建 Win32 应用并将其分配给一个或多个设备。

#### 步骤 1：创建脚本

创建一个文件夹，然后将以下安装和回滚脚本（InstallScript.ps1 *和 *RollbackScript.ps1*）保存在其中，以便你可以创建 *.intunewin* 文件以便在部署*中使用。

##### InstallScript.ps1

```
# Add Azure AD NRPT rule.
$DnsServers = (
    "ns1-37.azure-dns.com.",
    "ns2-37.azure-dns.net.",
    "ns3-37.azure-dns.org.",
    "ns4-37.azure-dns.info."
)
$DnsServerIPs = $DnsServers | Foreach-Object {
    (Resolve-DnsName $_).IPAddress | Select-Object -Unique
}

# List the rules.
$existingRules = Get-DnsClientNrptRule | Where-Object {
    $_.DisplayName -match "AZURE-AD-NRPT" -or $_.Namespace -match "login.microsoftonline.com"
}
if ($existingRules) { 
    Write-Output ("Azure AD NRPT rule exists: {0}" -F $existingRules) 
} 
else { 
    Write-Output "Adding Azure AD NRPT DNS rule for login.microsoftonline.com ..." 
    $params = @{
        Namespace = "login.microsoftonline.com"
        NameServers = $DnsServerIPs
        DisplayName = "AZURE-AD-NRPT"
    }
    Add-DnsClientNrptRule @params
}
```

##### RollbackScript.ps1

```
# Remove the Azure AD NRPT rule.
# List the rules.
$existingRules = Get-DnsClientNrptRule | Where-Object {
    $_.DisplayName -match "AZURE-AD-NRPT" -or $_.Namespace -match "login.microsoftonline.com"
}
if ($existingRules) { 
    Write-Output "Removing Azure AD NRPT DNS rule for login.microsoftonline.com ..." 
    $existingRules | Format-Table 
    $existingRules | Remove-DnsClientNrptRule -Force 
} 
else { 
    Write-Output "Azure AD NRPT rule does not exist. Device was successfully remediated."
}
```

##### DetectionScript.ps1

将以下脚本（*DetectionScript.ps1*）保存到另一个位置。 然后，可以在 Intune 中创建检测脚本时引用应用程序中的检测脚本。

```
# Add Azure AD NRPT rule.
$DnsServers = (
    "ns1-37.azure-dns.com.",
    "ns2-37.azure-dns.net.",
    "ns3-37.azure-dns.org.",
    "ns4-37.azure-dns.info."
)
$DnsServerIPs = $DnsServers | Foreach-Object {
    (Resolve-DnsName $_).IPAddress | Select-Object -Unique
}
# List the rules.
$existingRules = Get-DnsClientNrptRule | Where-Object {
    $_.DisplayName -match "AZURE-AD-NRPT" -or $_.Namespace -match "login.microsoftonline.com"
}
if ($existingRules) { 
    Write-Output 'Compliant' 
}
```

#### 步骤 2：将脚本打包为 .intunewin 文件

请参阅 [准备 Win32 应用内容，以便从](/zh-cn/mem/intune/apps/apps-win32-prepare) 之前保存的文件夹和脚本创建 *.intunewin* 文件。

#### 步骤 3：创建 Win32 应用程序

以下说明演示如何创建必要的 Win32 应用程序。 有关详细信息，请参阅 [Microsoft Intune](/zh-cn/mem/intune/apps/apps-win32-add) 中的“添加”、“分配和监视 Win32”应用。

1. 登录到 [Intune 门户](https://endpoint.microsoft.com)。
2. 选择**“应用****>所有应用**”，然后选择“+ 添加**”**以创建新的 Win32 应用。
3. 在 **“应用类型** ”下拉列表中，选择 **“Windows 应用”（Win32），**然后选择“ **选择**”。
4. 在 **“应用信息** ”页上，单击“ **选择应用包文件** ”以选择 *之前创建的 .intunewin* 文件。 选择**确定**以继续。
5. 返回到 **“应用信息** ”页，然后输入应用程序的描述性 **名称**、 **说明**和 **发布者** 。 其他字段是可选的。 选择“下一步”继续。
6. 在 **“程序** ”页上，输入以下信息，然后选择“ **下一步**”。

   - **安装命令** 字符串：  
     `powershell.exe -executionpolicy bypass -NoLogo -NoProfile -NonInteractive -WindowStyle Hidden -file "InstallScript.ps1"`
   - **卸载命令** 字符串：  
     `powershell.exe -executionpolicy bypass -NoLogo -NoProfile -NonInteractive -WindowStyle Hidden -file "RollbackScript.ps1"`
   - **安装行为**：  
     `System`
7. 在**“要求**”页中，选择**操作系统体系结构**并将最低操作系统**设置为** **Windows 10 1607**。 选择“下一步”继续。
8. 在**“检测**”页上，从**“规则格式**”下拉列表中选择“**使用自定义检测脚本**”。 选择“脚本文件**”框旁边的**浏览按钮以选择检测脚本。 将其余字段保留为默认值。 选择“下一步”继续。
9. 在“依赖项**”页上选择“下一步****”**以继续不进行任何更改。
10. 在“取代（预览）”页面上选择“**下一步****”**以继续不进行任何更改。
11. 在**“分配**”页上，根据要求创建作业，然后选择“下一步**”**继续。
12. 在 **“查看 + 创建** ”页面上最后一次查看信息。 完成验证后，选择“创建**”**以创建应用程序。

## 在登录日志中查找 IPv6 地址

使用以下一个或多个方法，将 IPv6 地址列表与预期的地址进行比较。 请考虑将这些 IPv6 地址添加到命名位置，并在适当情况下将某些地址标记为受信任。 至少需要分配的 [报表读取者角色](/zh-cn/azure/active-directory/roles/permissions-reference#reports-reader) 才能读取登录日志。

### Azure 门户

1. **以具有权限的报表读取者、安全读取者、全局读取者、安全管理员或其他角色登录到Azure 门户**。
2. 浏览到**Microsoft Entra ID>登录日志。**
3. 选择“**+ 添加筛选器****>IP 地址**”，然后选择“**应用”。**
4. 在 **“按 IP 地址** 筛选”框中，插入冒号（**：**）。
5. （可选）将此日志条目列表下载到 JSON 或 CSV 格式以供进一步处理。

### Log Analytics

如果组织使用 [Log Analytics](/zh-cn/azure/active-directory/reports-monitoring/howto-integrate-activity-logs-with-log-analytics)，则可以使用以下查询查询日志中的 IPv6 地址。

```
union SigninLogs, AADNonInteractiveUserSignInLogs
| where IPAddress has ":"
| summarize RequestCount = count() by IPAddress, AppDisplayName, NetworkLocationDetails
| sort by RequestCount
```

### PowerShell

组织可以使用以下 PowerShell 脚本在 Microsoft Graph PowerShell [中](/zh-cn/powershell/microsoftgraph/authentication-commands)查询 Microsoft Entra 登录日志。 该脚本提供 IPv6 地址列表以及应用程序及其显示次数。

```
$tId = "TENANT ID"  # Add the Azure Active Directory tenant ID.
$agoDays = 2  # Will filter the log for $agoDays from the current date and time.
$startDate = (Get-Date).AddDays(-($agoDays)).ToString('yyyy-MM-dd')  # Get filter start date.
$pathForExport = "./"  # The path to the local filesystem for export of the CSV file. 

Connect-MgGraph -Scopes "AuditLog.Read.All" -TenantId $tId 

# Get both interactive and non-interactive IPv6 sign-ins.
$signInsInteractive = Get-MgAuditLogSignIn -Filter "contains(IPAddress, ':')" -All
$signInsNonInteractive = Get-MgAuditLogSignIn -Filter "contains(IPAddress, ':')" -All 

# Summarize IPv6 & app display name count.
$signInsInteractive |
    Group-Object IPaddress, AppDisplayName |
    Select-Object @{Name = 'IPaddress'; Expression = {$_.Group[0].IPaddress}},
        @{Name = 'AppDisplayName'; Expression = {$_.Group[0].AppDisplayName}},
        Count |
    Sort-Object -Property Count –Descending |
    Export-Csv -Path ($pathForExport + "Summary_Interactive_IPv6_$tId.csv") -NoTypeInformation
$signInsNonInteractive |
    Group-Object IPaddress, AppDisplayName |
    Select-Object @{Name = 'IPaddress'; Expression = {$_.Group[0].IPaddress}},
        @{Name = 'AppDisplayName'; Expression = {$_.Group[0].AppDisplayName}},
        Count |
    Sort-Object -Property Count –Descending |
    Export-Csv -Path ($pathForExport + "Summary_NonInteractive_IPv6_$tId.csv") -NoTypeInformation
```

## 后续步骤

我们将更新本文。 下面是一个简短的链接，可用于返回更新和新信息： <https://aka.ms/azureadipv6>

- [在条件访问策略中使用位置条件](/zh-cn/azure/active-directory/conditional-access/location-condition)
- [条件访问：按位置阻止访问](/zh-cn/azure/active-directory/conditional-access/howto-conditional-access-policy-location)
- [查找帮助并获取对 Microsoft Entra ID 的支持](/zh-cn/azure/active-directory/fundamentals/how-to-get-support)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/ad-dmn-services/azure-ad-ipv6-support)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
