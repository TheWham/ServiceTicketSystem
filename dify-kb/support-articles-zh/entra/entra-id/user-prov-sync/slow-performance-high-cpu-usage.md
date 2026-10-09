# 在已安装 .NET Framework 的系统上，Microsoft Entra Connect Health for Sync 监视代理中的性能降低和高 CPU 使用率

## 概要

本文介绍在 Microsoft已安装 .NET Framework 4.7.2 或 2018 年 7 月 .NET Framework 4.6、4.6.1、4.6.2、4.6.2、4.7、4.7.1 或 4.7.2 的系统上安装 .NET Framework 4.7.2、4.7.1 或 4.7.2 的较慢性能和高 CPU 使用率的问题。

*原始产品版本：* Microsoft Entra ID  
*原始 KB 数：* 4457331

## 现象

假设在已安装 .NET Framework 4.7.2 或 2018 年 7 月更新的系统上运行 Microsoft Entra Connect Health for Sync 监视代理，这些更新适用于 .NET Framework 4.6、4.6.1、4.6.2、4.7、4.7.1 或 4.7.2。 在此方案中，系统可能会遇到性能缓慢和高 CPU 使用率的问题。

若要查看高 CPU 使用率，请启动任务管理器，并在“进程**”选项卡上查看 MIcrosoft.Online.Reporting.MonitoringAgent.Startup **进程的** CPU 使用率**。

## 原因

出现此问题的原因是，Microsoft Entra Connect Health for Sync 监视代理不支持 .NET Framework 4.7.2 或 .NET Framework 4.6、4.6.1、4.6.2、4.7、4.7.1 或 4.7.2 的 2018 年 7 月更新。
以下更新可能会导致监视代理的 CPU 使用率较高。

| **.NET Framework****更新** | **服务器版本** | **更新类型** |
| --- | --- | --- |
| [KB 4340007](https://support.microsoft.com/help/4340007) | Windows Server 2008 | 安全性 |
| [KB 4340556](https://support.microsoft.com/help/4340556) | Windows Server 2008 R2 | 安全性 |
| [KB 4340004](https://support.microsoft.com/help/4340004) | Windows Server 2008 R2 | 安全性 |
| [KB 4340557](https://support.microsoft.com/help/4340557) | Windows Server 2012 | 安全性 |
| [KB 4340005](https://support.microsoft.com/help/4340005) | Windows Server 2012 | 安全性 |
| [KB 4340558](https://support.microsoft.com/help/4340558) | Windows Server 2012 R2 | 安全性 |
| [KB 4340006](https://support.microsoft.com/help/4340006) | Windows Server 2012 R2 | 安全性 |
| [KB 4054542](https://support.microsoft.com/help/4054542) | Windows Server 2012 | 非安全性 |
| [KB 4054566](https://support.microsoft.com/help/4054566) | Windows Server 2012 R2 | 非安全性 |
| [KB 4054590](https://support.microsoft.com/help/4054590) | Windows Server 2016 | 非安全性 |
| [KB 4338814](https://support.microsoft.com/help/4338814) | Windows Server 2016（内部版本 14393.2363） | 非安全性 |
| [KB 4345418](https://support.microsoft.com/help/4345418) | Windows Server 2016（内部版本 14393.2368） | 非安全性 |

## 解决方法

若要解决此问题，请安装适合你的环境的更新。

- 适用于 AD DS 和 AD FS 的 Connect Health

  安装 2018 年 7 月发布的 Microsoft Entra Connect Health 代理版本 3.1.7.0。 此更新可用于 [在此处下载]/azure/active-directory/hybrid/how-to-connect-health-agent-install#download-and-install-the-azure-ad-connect-health-agent）。
- 对于 Microsoft Entra Connect

  安装最新版本的 Microsoft Entra Connect，其中包含此高 CPU 使用率问题的修补程序。 此版本可 [在此处](https://download.microsoft.com/download/B/0/0/B00291D0-5A83-4DE7-86F5-980BC00DE05A/AzureADConnect.msi)下载。

  注意

  如果在 Microsoft Entra Connect 服务器上启用了自动升级功能，将自动安装最新版本。

### 病毒扫描声明

Microsoft扫描此文件以查找病毒，使用发布文件日期可用的最新病毒检测软件。 该文件存储在安全性得到增强的服务器上，以防止在未经授权的情况下对其进行更改。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/slow-performance-high-cpu-usage)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
