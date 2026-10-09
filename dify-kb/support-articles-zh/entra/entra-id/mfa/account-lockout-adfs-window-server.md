# 排查 Windows Server 上的 AD FS 中的帐户锁定问题

本文提供了在 Windows Server 上的 Microsoft Active Directory 联合身份验证服务 （AD FS） 中排查帐户锁定问题的步骤。

*原始产品版本：* Windows Server 2019、Windows Server 2016、Windows Server 2012 R2、Windows Server 2012  
*原始 KB 数：* 4471013

你可能会在 Windows Server 上的 AD FS 中遇到帐户锁定问题。 若要排查此问题，请先检查以下几点：

- 如果已 [为 AD FS 服务器配置了 Microsoft Entra Connect Health](/zh-cn/azure/active-directory/connect-health/active-directory-aadconnect-health) ，请转到 [“使用 Connect Health 为用户登录活动](#use-connect-health-to-generate-data-for-user-login-activities) ”部分生成数据。
- 如果没有[为 AD FS 服务器配置Microsoft Entra Connect Health](/zh-cn/azure/active-directory/connect-health/active-directory-aadconnect-health)，请转到[“从 AD FS 和 Web 应用程序代理 服务器](#collect-ad-fs-event-logs-from-ad-fs-and-web-application-proxy-servers)”部分收集 AD FS 事件日志。

## 使用 Connect Health 生成用户登录活动的数据

可以使用 Connect Health 生成有关用户登录活动的数据。 Connect Health 生成有关 AD FS 场上发生的顶级错误密码尝试的报告。

请参阅本文[中](/zh-cn/azure/active-directory/connect-health/active-directory-aadconnect-health-adfs#reports-for-ad-fs)的信息，以分析错误密码尝试的用户帐户和 IP 列表。 然后，转到 [“分析受密码尝试](#analyze-the-ip-and-username-of-the-accounts-that-are-affected-by-bad-password-attempts)错误影响的帐户的 IP 和用户名”。

## 从 AD FS 和 Web 应用程序代理服务器收集 AD FS 事件日志

### 步骤 1：从 AD FS 和 Web 应用程序代理 服务器收集 AD FS 事件日志

若要收集事件日志，必须先配置 AD FS 服务器进行审核。 如果有 AD FS 场的负载均衡器，则必须在场中的每个 AD FS 服务器上启用审核。 无需在 Web 应用程序代理 服务器上配置审核。

若要配置 AD FS 服务器进行审核，可以使用以下方法：

- [手动配置 AD FS 服务器进行审核](https://technet.microsoft.com/library/cc738766%28v=ws.10%29.aspx)

### 步骤 2：搜索 AD FS 日志

对于 Windows Server 2012 R2 或 Windows Server 2016 AD FS，请在所有 AD FS 服务器的安全事件日志中搜索“事件 ID 411 源 AD FS 审核”事件。 请注意有关“411 事件”的以下信息：

- 可以下载 [ADFS 帐户锁定和错误的 Cred 搜索（AD FSBadCredsSearch.ps1）](#adfs-account-lockout-and-bad-cred-search)PowerShell 脚本，以搜索 AD FS 服务器中的“411”事件。 该脚本提供一个 CSV 文件，其中包含提交者的 UserPrincipalName、IP 地址，以及向 AD FS 场提交所有错误的凭据提交的时间。 在 Excel 中打开 CSV 文件，并按用户名、IP 地址或时间快速筛选。
- 这些事件包含目标用户的用户主体名称（UPN）。
- 这些事件包含消息“令牌验证失败”消息，该消息指出该事件指示密码尝试错误还是帐户锁定。
- 如果服务器显示“411”事件，但 IP 地址字段不在事件中，请确保已将最新的 AD FS 修补程序应用到服务器。 有关详细信息，请参阅 [MS16-020：用于解决拒绝服务的Active Directory 联合身份验证服务安全更新：2016](https://support.microsoft.com/help/3134222/ms16-020-security-update-for-active-directory-federation-services-to-a) 年 2 月 9 日。

对于 Windows Server 2008 R2 或 Windows Server 2012 AD FS，你将没有必要的事件 411 详细信息。 请改为下载并运行以下 PowerShell 脚本，以关联安全事件 4625（密码尝试错误）和 501（AD FS 审核详细信息），以查找有关受影响的用户的详细信息。

- 可以下载 [ADFS 安全审核事件分析器（ADFSSecAuditParse.ps1）](#adfs-security-audit-events-parser) PowerShell 脚本，以搜索 AD FS 服务器中的事件。 该脚本提供一个 CSV 文件，其中包含提交者的 UserPrincipalName、IP 地址，以及向 AD FS 场提交所有错误的凭据提交的时间。
- 还可以使用此方法调查“411”事件中用户成功的连接。 可以在 AD FS“501”事件中搜索更多详细信息。
- 运行 PowerShell 脚本以搜索事件时，传递“411”事件中标识的用户的 UPN，或按帐户锁定报告进行搜索。
- 恶意提交者的 IP 地址显示在“501”事件的两个字段中之一。
- 对于基于 Web 的方案和大多数应用程序身份验证方案，恶意 IP 将位于 **x-ms-client-ip** 字段中。

## 分析受密码尝试错误影响的帐户的 IP 和用户名

枚举 IP 地址和用户名后，确定用于访问意外位置的 IP。

是否尝试从外部未知 IP 进行？

- 如果尝试来自外部未知 IP，请转到 [使用最新修补程序](#update-ad-fs-servers-with-latest-hotfixes)更新 AD FS 服务器。
- 如果未从外部未知 IP 进行尝试，请转到 [确保凭据在服务或应用程序中](#make-sure-that-credentials-are-updated-in-the-service-or-application)更新。

## 使用最新修补程序更新 AD FS 服务器

若要确保 AD FS 服务器具有最新功能，请为 AD FS 和 Web 应用程序代理服务器应用最新的修补程序。 此外，Windows Server 2012 R2 上需要修补程序 [3134222](https://www.microsoft.com/download/details.aspx?id=51059) 才能在事件 411 中记录稍后使用的 IP 地址。

## 检查 Extranet 锁定是否已启用

使用 [Get-ADFSProperties](https://technet.microsoft.com/library/ee892323.aspx) 检查是否启用了 Extranet 锁定。

- 如果启用了 Extranet 锁定，请转到 [检查 Extranet 锁定和内部锁定阈值](#step-1-check-extranet-lockout-and-internal-lockout-thresholds)。
- 如果未启用 Extranet 锁定，请针对相应版本的 AD FS 启动以下步骤。

### 检查锁定状态的步骤

#### 对于 Windows Server 2012 R2 或更高版本

智能锁定是一项新功能，即将在 AD FS 2016 和 2012 R2 中通过更新提供。 在功能可用后，此部分将更新为启用智能锁定的相应步骤。 然后，转到 [“检查 Extranet 锁定”和“内部锁定阈值](#step-1-check-extranet-lockout-and-internal-lockout-thresholds)”。

#### 对于 Windows Server 2008 R2 Windows 或更高版本

建议将 AD FS 服务器升级到 Windows Server 2012 R2 或 Windows Server 2016。 有关详细信息，请参阅[升级到 Windows Server 2016 中的 AD FS](/zh-cn/windows-server/identity/ad-fs/deployment/upgrading-to-ad-fs-in-windows-server-2016)。 然后，按照 Windows Server 2012 R2 或更高版本的步骤进行操作。

##### 步骤 1：检查 Extranet 锁定和内部锁定阈值

确保正确配置 Extranet 锁定和内部锁定阈值。 有关详细信息，请参阅 [建议的安全配置](/zh-cn/windows-server/identity/ad-fs/deployment/best-practices-securing-ad-fs#recommended-security-configurations)。 通常， **ExtranetLockoutThreshold** 应小于 AD 的锁定阈值，以便用户仅锁定 Extranet 访问，而不会在 Active Directory 中锁定内部访问。

##### 步骤 2：启用新式身份验证和基于证书的身份验证

建议启用新式身份验证、基于证书的身份验证，以及此步骤中列出的其他功能，以降低暴力攻击的风险。

**部署新式身份验证**

除了删除当前通过 Exchange Online 使用的攻击途径之一外，为 Office 客户端应用程序部署新式身份验证使组织能够受益于多重身份验证。 Windows、iOS 和 Android 平台中的所有最新Office 应用复制都支持新式身份验证。

有关详细信息，请参阅 [如何为 Office 365](https://support.office.com/article/Using-Office-365-modern-authentication-with-Office-clients-776c0036-66fd-41cb-8928-5495c0f9168a#bk_getstarted) 部署新式身份验证。

由于尽管我们的主动和反应防御措施，但基于用户名和密码的访问请求将继续易受攻击，因此组织应计划尽快采用基于密码的访问方法。

以下非基于密码的身份验证类型可用于 AD FS 和 Web 应用程序代理。

- 基于证书的身份验证

  当基于证书的身份验证用作用户名和密码访问的替代方法时，用户帐户和访问权限将受到以下保护：

  - 由于用户不通过 Internet 使用其密码，因此这些密码更容易泄露。 可以在防火墙中完全阻止用户名和密码终结点。 这消除了锁定或暴力攻击的攻击途径。
  - 即使用户名和密码终结点在防火墙中可用，导致锁定的恶意用户名和密码请求也不会影响使用证书的访问请求。 因此，将保留合法用户的访问权限。

    有关 Microsoft Entra ID 和 Office 365 的基于证书的身份验证的详细信息，请参阅 [此Microsoft Entra 标识博客文章](https://blogs.technet.microsoft.com/enterprisemobility/2016/12/14/azuread-certificate-based-authentication-is-generally-available/)。
- Azure 多重身份验证 (MFA)

  Azure MFA 是另一种基于密码的访问方法，可以采用与基于证书的身份验证相同的方式使用，以避免完全使用密码和用户名终结点。

  Azure MFA 可用于在以下方案中保护帐户。

  | 方案 | 优点 |
  | --- | --- |
  | 通过 Extranet 使用 Azure MFA 作为其他身份验证 | 将 Azure MFA 或任何其他身份验证提供程序添加到 AD FS，并要求将其他方法用于 Extranet 请求，从而通过使用被盗或暴力破解的密码来保护帐户免受访问。 这可以在 AD FS 2012 R2 和 2016 中完成。 |
  | 使用 Azure MFA 作为主要身份验证 | 这是 AD FS 2016 中的一项新功能，使用 Azure MFA 而不是密码启用无密码访问。 这可防范密码泄露和锁定。 |

  有关如何使用 AD FS 配置 Azure MFA 的详细信息，请参阅 [配置 AD FS 2016 和 Azure MFA](https://technet.microsoft.com/windows-server-docs/identity/ad-fs/operations/configure-ad-fs-2016-and-azure-mfa)
- Windows Hello 企业版

  Windows 10 中提供了Windows Hello 企业版。 Windows Hello 企业版基于绑定到用户和设备的强大加密密钥，从 Extranet 中启用无密码访问。

  Windows Server 2016 中的 AD FS 支持Windows Hello 企业版。 请参阅[通过Windows Hello 企业版](/zh-cn/azure/active-directory/active-directory-azureadjoin-passport)对不使用密码的标识进行身份验证。

##### 步骤 3：禁用旧式身份验证和未使用的终结点

禁用 EAS 客户端通过 Exchange Online 使用的旧终结点，如下所示：

`/adfs/services/trust/13/usernamemixed endpoint`

注意

执行此操作可能会中断某些功能。 但是，它可以帮助减少可供攻击者利用的图面向量。 此外，建议禁用未使用的终结点。

检查是否解决了问题。

## 确保在服务或应用程序中更新凭据

如果用户帐户用作服务帐户，则可能不会更新服务或应用程序的最新凭据。 在这种情况下，服务可能会继续使用错误的凭据进行身份验证。 这会导致锁定条件。

若要解决此问题，请检查服务或应用程序中的服务帐户配置，确保凭据正确。 否则，请按照下一步操作。

## 清除应用程序中的缓存凭据

如果某个应用程序中缓存了用户凭据，重复的身份验证尝试可能会导致帐户锁定。 若要解决此问题，请清除应用程序中的缓存凭据。 检查是否解决了问题。

## ADFS 帐户锁定和错误的 Cred 搜索

```
PARAM ($PastDays = 1, $PastHours)
#************************************************
# ADFSBadCredsSearch.ps1
# Version 1.0
# Date: 6-20-2016
# Author: Tim Springston [MSFT]
# Description: This script will parse the ADFS server's (not proxy) security ADFS
#  for events which indicate an incorrectly entered username or password. The script can specify a
#  past period to search the log for and it defaults to the past 24 hours. Results will be placed into a CSV for 
#  review of UPN, IP address of submitter, and timestamp.
#************************************************

cls
if ($PastHours -gt 0)
 {$PastPeriod = (Get-Date).AddHours(-($PastHours))}
 else
  {$PastPeriod = (Get-Date).AddDays(-($PastDays)) }
$Outputfile = $Pwd.path + "\BadCredAttempts.csv"
$CS = get-wmiobject -class win32_computersystem
$Hostname = $CS.Name + '.' + $CS.Domain
$Instances = @{}
$OSVersion = gwmi win32_operatingsystem
[int]$BN = $OSVersion.Buildnumber 
if ($BN -lt 9200){$ADFSLogName = "AD FS 2.0/Admin"}
 else {$ADFSLogName = "AD FS/Admin"}

$Users = @()
$IPAddresses = @()
$Times = @()
$AllInstances = @()
Write-Host "Searching event log for bad credential events..."
if ($BN -ge 9200) {Get-Winevent  -FilterHashTable @{LogName= "Security"; StartTime=$PastPeriod; ID=411} -ErrorAction SilentlyContinue | Where-Object  {$_.Message -match "The user name or password is incorrect"} |  % {
 $Instance = New-Object PSObject
 $UPN = $_.Properties[2].Value
 $UPN = $UPN.Split("-")[0]
 $IPAddress = $_.Properties[4].Value
 $Users += $UPN
 $IPAddresses += $IPAddress
 $Times += $_.TimeCreated
 add-member -inputobject $Instance -membertype noteproperty -name "UserPrincipalName" -value $UPN
 add-member -inputobject $Instance -membertype noteproperty -name "IP Address" -value $IPAddress
 add-member -inputobject $Instance -membertype noteproperty -name "Time" -value ($_.TimeCreated).ToString()
 $AllInstances += $Instance
 $Instance = $null
 }
}

$AllInstances | select * | Export-Csv -Path $Outputfile -append -force -NoTypeInformation 
Write-Host "Data collection finished. The output file can be found at $outputfile`."
$AllInstances = $null
```

## ADFS 安全审核事件分析器

```
PARAM ($SearchCriteria, $PastDays = 1, $PastHours)
#************************************************
# ADFSSecAuditParse.ps1
# Version 1.0
# Date: 2-2-2016
# Author: Tim Springston [MSFT]
# Description: This script will parse an ADFS Security event log file (EVTX)
#  and search for audit events related to a specific user or other criteria.
#  The script will work for the each ADFS login instance for a given criteria during a stated time frame.
#  If you need to locate a second then filter and save the event log to focus in.
# Return an array of initial instance IDs with the criteria, run the search function against each and output
# a unique text file for each.
#************************************************

cls
if ($PastHours -gt 0)
 {
 $PastPeriod = (Get-Date).AddHours(-($PastHours))
 }
 else
  {$PastPeriod = $PastDays}
 
$CS = get-wmiobject -class win32_computersystem
$Hostname = $CS.Name + '.' + $CS.Domain
$Instances = @()
Get-Winevent -ComputerName $Hostname -LogName Security  | Where-Object {(($_.ID -eq 501) `
-and ($_.Properties.Value -contains $SearchCriteria) -and ($_.TimeCreated -gt $PastPeriod))} | % { $Instances += $_.Properties[0].Value}

function FindADFSAuditEvents  { 
 param ($valuetomatch, $counter, $instance, $PastPeriod)
  $Results = $pwd.Path + "\" + $SearchCriteria + "-ADFSSecAudit" + '-' + $Counter + ".txt" 
  $SearchString = $SearchCriteria + " and instance " + $Instance + " in Security event log."
  "Security Audit Events which match $SearchString" | Out-File $Results -Encoding UTF8 
  Get-WinEvent -ComputerName $Hostname -LogName Security  -WarningAction SilentlyContinue | `
  Where-Object -ErrorAction SilentlyContinue {($_.TimeCreated -gt $PastPeriod) -and (($_.Properties -contains $ValueToMatch) -or ($_.Properties[0].Value -match $Instance))}  | % {
  $Event = New-object PSObject
  add-member -inputobject $Event -membertype noteproperty -name "Event ID" -value $_.ID
  add-member -inputobject $Event -membertype noteproperty -name "Provider" -value $_.ProviderName
  add-member -inputobject $Event -membertype noteproperty -name "Machine Name" -value $_.MachineName
  add-member -inputobject $Event -membertype noteproperty -name "User ID" -value $_.UserID
  add-member -inputobject $Event -membertype noteproperty -name "Time Created " -value $_.TimeCreated  
  $Event | FL *
  $Event | Out-File $Results -Encoding UTF8  -Append
  $_.Properties | FL *
  $_.Properties | Out-File $Results -Encoding UTF8  -Append
  $DateTimeExport = $_.TimeCreated
  }
 $DateTime = (($DateTimeExport.ToShortDateString()).Replace('/','-') + '@' + (($DateTimeExport.ToShortTimeString()).Replace(' ','')))
 $DateTime = $DateTime.Replace(':','')
 $Results2 = $pwd.Path + "\" + $SearchCriteria + '-' + $DateTime + "-ADFSSecAudit" + $Counter + ".txt"
 Rename-Item -Path $Results -NewName $Results2
 } 

$Counter = 1
foreach ($instance in $Instances)
 {
 FindADFSAuditEvents -ValueToMatch $SearchCriteria  -Instance $Instance -PastPeriod $PastPeriod -Counter $Counter
 $Counter++
 }
```

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/mfa/account-lockout-adfs-window-server)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
