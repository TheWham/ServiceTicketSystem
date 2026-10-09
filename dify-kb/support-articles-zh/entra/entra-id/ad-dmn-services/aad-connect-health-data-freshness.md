# 排查 Microsoft Entra Connect Health 中数据新鲜度警报

本文针对"Health service data is not up to date"（健康服务数据不是最新的）这一数据新鲜度警报提供常见的诊断修复方法。当 Microsoft Entra Connect Health 服务在过去两小时内未收到数据时，就会生成此警报。该警报在以下服务的健康服务中出现：

- Azure AD Sync 服务
- Microsoft Entra 域服务
- Active Directory 联合身份验证服务（AD FS）

## 先决条件

- [Microsoft Entra Connect](https://www.microsoft.com/download/details.aspx?id=47594)。
- [适用于 AD DS 的 Microsoft Entra Connect Health 代理](https://go.microsoft.com/fwlink/?LinkID=820540)。
- [适用于 Active Directory 联合身份验证服务的 Microsoft Entra Connect Health 代理](https://go.microsoft.com/fwlink/?LinkID=518973)。
- [PsExec](/sysinternals/downloads/psexec) 工具。

## 症状

要查看数据新鲜度警报，请执行以下步骤：

1. 在 [Azure 门户](https://portal.azure.com)中，搜索并选择 **Microsoft Entra Connect Health**。

1. 在 **Microsoft Entra Connect Health | 快速入门**菜单窗格中，选择 **AD DS Services**。

1. 选择你的域名，然后选择**警报**。

1. 在 **Active Directory 域服务警报**窗格中，选择 **Health service data is not up to date**（健康服务数据不是最新的）。

1. 在 **Health service data is not up to date** 窗格中，选择**服务器名称**。此时会显示**警报详细信息**和**数据类型详细信息**的属性列表。

## 常见诊断步骤

在继续之前，请参阅[健康服务数据不是最新的警报](/azure/active-directory/hybrid/how-to-connect-health-data-freshness)。

## HTTP 代理排查步骤

如果使用 HTTP 代理，请按照以下步骤操作：

1. 如果启用了安全套接字层（SSL）检查，请确保已将策略密钥服务终结点（`policykeyservice.dc.ad.msft.net`）添加到允许列表。

1. 使用 PowerShell cmdlet 查找连接问题。你可以以普通用户身份[成功运行 Test-AzureADConnectHealthConnectivity cmdlet](/azure/active-directory/hybrid/how-to-connect-health-agent-install#test-connectivity-to-azure-ad-connect-health-service)。但是，如果所有数据类型都缺失，则代理设置可能对用户正确，但对 **Local System**（服务运行所用的上下文）不正确。在这种情况下，请改为运行相应的 `Test-AzureADConnectHealthConnectivityAsSystem` cmdlet：

    ### [Sync](#tab/sync)

    ```powershell
    Test-AzureADConnectHealthConnectivityAsSystem -Role Sync
    ```

    ### [AD DS](#tab/azure-ad-ds)

    ```powershell
    Test-AzureADConnectHealthConnectivityAsSystem -Role ADDS
    ```

    ### [AD FS](#tab/ad-fs)

    ```powershell
    Test-AzureADConnectHealthConnectivityAsSystem -Role ADFS
    ```

    ---

1. 检查代理设置对 **Local System** 是否正确：

    1. 输入以下 `PsExec` 命令以远程查看 Windows 设置：

        ```console
        PsExec.exe -i -s "start ms-settings:"
        ```

    1. 选择**网络和 Internet** > **代理**，然后在**手动代理设置**标题下选择**编辑**。

    1. 在**编辑代理服务器**对话框中，更新代理服务器设置以匹配当前配置。

    1. 重启服务。

## 性能计数器排查步骤

运行以下 PowerShell 命令以检查某些性能计数器类别是否存在。

### [Sync](#tab/sync)

```powershell
[System.Diagnostics.PerformanceCounterCategory]::Exists("Processor")
[System.Diagnostics.PerformanceCounterCategory]::Exists("TCPv4")
[System.Diagnostics.PerformanceCounterCategory]::Exists("Memory")
[System.Diagnostics.PerformanceCounterCategory]::Exists("Process")
```

### [AD DS](#tab/azure-ad-ds)

```powershell
[System.Diagnostics.PerformanceCounterCategory]::Exists("Processor")
[System.Diagnostics.PerformanceCounterCategory]::Exists("TCPv4")
[System.Diagnostics.PerformanceCounterCategory]::Exists("Memory")
[System.Diagnostics.PerformanceCounterCategory]::Exists("Process")
[System.Diagnostics.PerformanceCounterCategory]::Exists("DirectoryServices(NTDS)")
[System.Diagnostics.PerformanceCounterCategory]::Exists("Security System-Wide Statistics")
[System.Diagnostics.PerformanceCounterCategory]::Exists("LogicalDisk")
```

### [AD FS](#tab/ad-fs)

Microsoft 正在开发适用于 AD FS 的脚本，并将在脚本可用时发布到本文中。

---

如果这些命令中的任何一个返回 **False**，请运行以下脚本以获取有关性能计数器的更多信息：

### [Sync](#tab/sync)

```powershell
$perfCounters = @(
    "\Processor(_Total)\% Processor Time", 
    "\Memory\Available MBytes", 
    "\TCPv4\Connections Established", 
    "\Process(Microsoft.Identity.AadConnect.Health.AadSync.Host)\Private Bytes", 
    "\Process(Microsoft.Identity.Health.AadSync.MonitoringAgent.Startup)\Private Bytes"
)
foreach($counter in $perfCounters)
{
    try
    {
        $counterResult = Get-Counter -Counter $counter -MaxSamples 1 -ErrorAction SilentlyContinue
        if($counterResult -eq $null)
        {
            Write-Host $counter " ->  does not exist" -ForegroundColor Red
            if($counter -eq "\Process(Microsoft.Identity.AadConnect.Health.AadSync.Host)\Private Bytes")
            {
                Write-Host "     Please make sure Azure AD Connect Health Sync Insights Service is running." -ForegroundColor Magenta
            }
            elseif($counter -eq "\Process(Microsoft.Identity.Health.AadSync.MonitoringAgent.Startup)\Private Bytes")
            {
                Write-Host "     Please make sure Azure AD Connect Health Sync Monitoring Service is running." -ForegroundColor Magenta
            }
        }
        else
        {
            Write-Host $counter " -> exists " -ForegroundColor Green
        }
    }
    catch {}
}
```

### [AD DS](#tab/azure-ad-ds)

```powershell
$perfCounters = @(
    "\Processor(_Total)\% Processor Time", 
    "\Memory\Available MBytes", 
    "\TCPv4\Connections Established", 
    "\Process(Microsoft.Identity.Health.Adds.InsightsService)\Private Bytes", 
    "\Process(Microsoft.Identity.Health.Adds.MonitoringAgent.Startup)\Private Bytes", 
    "\Process(lsass)\% Processor Time", 
    "\DirectoryServices(NTDS)\LDAP Searches/sec", 
    "\DirectoryServices(NTDS)\LDAP Successful Binds/sec", 
    "\DirectoryServices(NTDS)\ATQ Estimated Queue Delay", 
    "\DirectoryServices(NTDS)\ATQ Outstanding Queued Requests", 
    "\DirectoryServices(NTDS)\ATQ Request Latency", 
    "\DirectoryServices(NTDS)\ATQ Threads LDAP", 
    "\DirectoryServices(NTDS)\ATQ Threads Other",
    "\DirectoryServices(NTDS)\ATQ Threads Total",
    "\Security System-Wide Statistics\Kerberos Authentications", 
    "\Security System-Wide Statistics\NTLM Authentications", 
    "\LogicalDisk(_Total)\% Free Space"
)
foreach($counter in $perfCounters)
{
    try
    {
        $counterResult = Get-Counter -Counter $counter -MaxSamples 1 -ErrorAction SilentlyContinue
        if($counterResult -eq $null)
        {
            Write-Host $counter " ->  does not exist" -ForegroundColor Red
            if($counter -eq "\Process(Microsoft.Identity.Health.Adds.InsightsService)\Private Bytes")
            {
                Write-Host "     Please make sure Azure AD Connect Health AD DS Insights Service is running." -ForegroundColor Magenta
            }
            elseif($counter -eq "\Process(Microsoft.Identity.Health.Adds.MonitoringAgent.Startup)\Private Bytes")
            {
                Write-Host "     Please make sure Azure AD Connect Health AD DS Monitoring Service is running." -ForegroundColor Magenta
            }
            elseif($counter.ToString().Contains("NTDS"))
            {
                Write-Host "     Please make sure NTDS Perf counters are loaded." -ForegroundColor Magenta
            }
        }
        else
        {
            Write-Host $counter " -> exists " -ForegroundColor Green
        }
    }
    catch {}
}
# We handle both cases. If "\NTDS\X" is missing, we check for "\DirectoryServices(NTDS)\X"
$ntdsPrefix = "NTDS"
$dsPrefix = "DirectoryServices(NTDS)"
$dupePerfCounters = @(
    "DRA Pending Replication Synchronizations", 
    "LDAP Bind Time", 
    "LDAP Active Threads", 
    "DS Threads in Use", 
    "DRA Outbound Bytes Total/sec", 
    "DRA Inbound Bytes Total/sec"
)
foreach($counter in $dupePerfCounters)
{
    try
    {
        $ntdsCounter = "\" + $ntdsPrefix + "\" + $counter
        $counterResult = Get-Counter -Counter $ntdsCounter -MaxSamples 1 -ErrorAction SilentlyContinue
        if($counterResult -eq $null)
        {
            $dsCounter = "\" + $dsPrefix + "\" + $counter
            Write-Host $ntdsCounter " ->  does not exist, checking for" $dsCounter -ForegroundColor Yellow
            $counterResult = Get-Counter -Counter $dsCounter -MaxSamples 1 -ErrorAction SilentlyContinue
            if($counterResult -eq $null)
            {
                Write-Host "     Please make sure NTDS or \DirectoryServices\NTDS Perf counters are loaded." -ForegroundColor Magenta
            }
            else
            {
                Write-Host $dsCounter " -> exists " -ForegroundColor Green
            }
        }
        else
        {
            Write-Host $counter " -> exists " -ForegroundColor Green
        }
    }
    catch {}
}
```

### [AD FS](#tab/ad-fs)

Microsoft 正在开发适用于 AD FS 的脚本，并将在脚本可用时发布到本文中。

---

## 数据类型排查步骤

本节包含用于修复数据类型问题的排查步骤。

### [Sync](#tab/sync)

| 数据类型 | 排查步骤 |
| --------- | --------------------- |
| PerfCounter | <ul><li>确保性能计数器存在。</li><li>确保 Microsoft Entra Connect Health Sync Monitoring Service 正在运行。</li></ul> |
| AadSyncService&#8209;Connectors<br/>AadSyncService&#8209;GlobalConfigurations<br/>AadSyncService&#8209;RunProfileResults<br/>AadSyncService&#8209;ServiceConfigurations<br/>AadSyncService&#8209;ServiceStatus<br/>AadSyncService&#8209;SynchronizationRules | 确保 Microsoft Entra Connect Health Sync Insights Service 正在运行。 |

### [AD DS](#tab/azure-ad-ds)

| 数据类型 | 排查步骤 |
| --------- | --------------------- |
| PerfCounter | <ul><li>确保性能计数器存在。</li><li>确保 Microsoft Entra Connect Health AD DS Monitoring Service 正在运行。</li></ul> |
| Adds&#8209;TopologyInfo&#8209;Json<br/>Common&#8209;TestData&#8209;Json | <ul><li>确保 Microsoft Entra Connect Health AD DS Insights Service 正在运行。</li><li>确保 Microsoft Entra Connect Health AD DS Monitoring Service 正在运行。</li></ul> |

### [AD FS](#tab/ad-fs)

首先按照 [Connect Health for AD FS 数据新鲜度警报排查步骤](https://adfshelp.microsoft.com/TroubleshootingGuides/Workflow/29afc119-3b45-4088-bfe5-4252f726900e)中的说明操作。

| 数据类型 | 排查步骤 |
| --------- | --------------------- |
| PerfCounter | <ul><li>确保性能计数器存在。</li><li>确保 Microsoft Entra Connect Health AD FS Monitoring Service 正在运行。</li></ul> |
| TestResult | <ul><li>确保 Microsoft Entra Connect Health AD FS Diagnostics Service 正在运行。</li><li>确保 Microsoft Entra Connect Health AD FS Monitoring Service 正在运行。 |
| Adfs&#8209;UsageMetrics | 确保 Microsoft Entra Connect Health AD FS Insights Service 正在运行。 |

---

## 收集 Monitoring Agent 和 Insights Agent 的日志

如果仪表板无法提供帮助，请收集代理日志。相关服务可以在控制台中运行，以获取更多信息。

首先输入以下 `PsExec` 命令以远程运行命令提示符：

```console
PsExec.exe -i -s cmd
```

然后，按照下一节所述，收集 Sync、AD DS 或 AD FS 的 Monitoring 和 Insights 服务的代理日志。
> **备注**
> AD FS 还有 Diagnostics 服务。收集相应 Diagnostic Agent 日志的说明位于 Monitoring 和 Insights 的日志收集部分之后。

### 收集 Monitoring Agent 日志

要收集 Monitoring Agent 日志，请按照以下步骤操作：

1. 在远程命令提示符下，输入 `services.msc` 以打开"服务"管理单元。

1. 停止相应服务类型的 Monitoring 服务。

    按照服务类型更改当前目录，然后直接运行 Monitoring Agent 服务的可执行文件。每种服务类型的路径名和可执行文件名如下表所示。

    | 服务类型 | 路径                                                                       | 可执行文件                                                      |
    | ------------ | -------------------------------------------------------------------------- | --------------------------------------------------------------- |
    | Sync         | *C:\\Program Files\\Microsoft Azure AD Connect Health Sync Agent\\Monitor* | *Microsoft.Identity.Health.AadSync.MonitoringAgent.Startup.exe* |
    | AD DS        | *C:\\Program Files\\Azure AD Connect Health Adds Agent\\Monitor*           | *Microsoft.Identity.Health.Adds.MonitoringAgent.Startup.exe*    |
    | AD FS        | *C:\\Program Files\\Azure AD Connect Health Adfs Agent\\Monitor*           | *Microsoft.Identity.Health.Adfs.MonitoringAgent.Startup.exe*    |

    例如，对于 AD FS，输入以下命令：

    ```console
    cd "C:\Program Files\Azure Ad Connect Health Adfs Agent\Monitor"
    notepad "Microsoft.Identity.Health.Adfs.MonitoringAgent.Startup.exe.config"
    ```

1. 在文本编辑器中，插入以下行将 `ConsoleDebug` 键设置为 `true`：

    ```xml
    <add key="ConsoleDebug" value="true" />
    ```

1. 保存并关闭配置文件。

1. 运行 Monitoring Agent 服务，并将其输出重定向到日志文件（*monitor.log*）。

    例如，对于 AD FS，输入以下命令：

    ```console
    Microsoft.Identity.Health.Adfs.MonitoringAgent.Startup.exe > monitor.log
    ```

1. 让 Monitoring Agent 服务运行 15 分钟。然后按 Ctrl+C 停止服务，并检查 *monitor.log* 文件。

### 收集 Insights Agent 日志

要收集 Insights Agent 日志，请按照以下步骤操作：

1. 在远程命令提示符下，输入 `services.msc` 以打开"服务"管理单元。

1. 停止相应服务类型的 Insights 服务。

    例如，对于 AD FS，在服务列表中选择 **Microsoft Entra Connect Health AD FS Insights Service**，然后选择**停止服务**图标。

1. 按照服务类型将当前目录更改为相应目录。然后，使用 `/console` 参数运行 Insights Agent 服务可执行文件，并将其输出重定向到日志文件（*insights.log*）。每种服务类型的路径名和可执行文件名如下表所示。

    | 服务类型 | 路径                                                                        | 可执行文件                                              |
    | ------------ | --------------------------------------------------------------------------- | ------------------------------------------------------- |
    | Sync         | *C:\\Program Files\\Microsoft Azure AD Connect Health Sync Agent\\Insights* | *Microsoft.Identity.AadConnect.Health.AadSync.Host.exe* |
    | AD DS        | *C:\\Program Files\\Azure AD Connect Health Adds Agent\\Insights*           | *Microsoft.Identity.Health.Adds.InsightsService.exe*    |
    | AD FS        | *C:\\Program Files\\Azure AD Connect Health Adfs Agent\\Insights*           | *Microsoft.Identity.Health.Adfs.InsightsService.exe*    |

    例如，对于 AD FS，输入以下命令：

    ```console
    cd "C:\Program Files\Azure Ad Connect Health Adfs Agent\Insights"
    Microsoft.Identity.Health.Adfs.InsightsService.exe /console > insights.log
    ```

1. 让 Insights Agent 服务运行 15 分钟。然后按 Ctrl+C 停止服务，并检查 *insights.log* 文件。

## 收集 Diagnostics Agent 的日志（仅限 AD FS）

要收集 AD FS 的 Diagnostics Agent 日志，请按照以下步骤操作：

1. 在远程命令提示符下，输入 `services.msc` 以打开"服务"管理单元。

1. 停止相应服务类型的 Diagnostics 服务。

    例如，对于 AD FS，在服务列表中选择 **Microsoft Entra Connect Health AD FS Diagnostics Service**，然后选择**停止服务**图标。

1. 将当前目录更改为 AD FS 的 diagnostics 目录。然后，使用 `-Debug` 参数运行 Diagnostics Agent 服务可执行文件，并将其输出重定向到日志文件（*diagnostics.log*）。

    ```console
    cd "C:\Program Files\Azure Ad Connect Health Adfs Agent\Diagnostics"
    Microsoft.Identity.Health.Adfs.DiagnosticsAgent.exe -Debug > diagnostics.log
    ```

1. 按 Enter。

1. 让 Diagnostics Agent 服务运行 15 分钟。然后按 Ctrl+C 停止服务，并将控制台输出复制到 *diagnostics.log*。

1. 在日志中搜索 `Error`，并检查是否有任何错误条目表明存在特定问题（例如连接或代理配置问题）。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/ad-dmn-services/aad-connect-health-data-freshness)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权，本文档为社区中文翻译）
