# Microsoft Entra Connect Health for Sync 中的 CPU 使用率较高

## 概要

本文提供有关解决Microsoft Entra Connect Health for Sync 中出现 CPU 使用率过高的问题的信息。

*原始产品版本：* Microsoft Entra ID  
*原始 KB 数：* 4346822

## 现象

在运行 Microsoft Entra Connect Health for Sync 监视代理的计算机上，遇到性能缓慢和高 CPU 使用率（高达 100%）。 在任务管理器中，你注意到 **Microsoft.Online.Reporting.MonitoringAgent.Startup** 进程导致 CPU 使用率过高。

注意

此问题不限于任何特定的Microsoft Entra Connect Health 版本或操作系统版本。

## 原因

出现此问题的原因是计算机上安装了 .NET Framework 4.7.2 的 2018 年 6 月更新，并且 Microsoft Entra Connect Health for Sync 监视代理不支持此更新。

以下 .NET Framework 更新会导致监视代理出现高 CPU 问题。

| .NET Framework 更新 | 系统版本 |
| --- | --- |
| KB4338420 | Windows Server 2008 |
| KB4338606 | Windows Server 2008 R2 |
| KB4054542 | Windows Server 2012 |
| KB4054566 | Windows Server 2012 R2 |
| KB4054590 KB4338814 KB4338419 KB4338605 KB4345418 | 常规 |

## 解决方法

### 适用于 AD DS 和 AD FS 的 Connect Health

若要解决此问题，Active Directory 域服务（AD DS）和Active Directory 联合身份验证服务（AD FS），请安装 2018 年 7 月发布的新 Microsoft Entra Connect Health 代理版本 3.1.7.0。 可以从 Connect Health 公共文档[下载](/zh-cn/azure/active-directory/connect-health/active-directory-aadconnect-health-agent-install#download-and-install-the-azure-ad-connect-health-agent)代理。

### 对于 Microsoft Entra Connect

若要解决此问题，Microsoft Entra Connect，请安装 [最新版本的 Microsoft Entra Connect](https://go.microsoft.com/fwlink/?LinkId=615771)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/high-cpu-usage)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
