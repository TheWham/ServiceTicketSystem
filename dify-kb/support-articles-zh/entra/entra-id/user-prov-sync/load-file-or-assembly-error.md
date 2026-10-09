# 在 Windows Server 2008 R2 中运行 DirSyncConfigShell.psc1 时出错：无法加载文件或程序集

## 概要

本文介绍在基于 Windows Server 2008 R2 的计算机上安装基于 Windows Server 2008 R2 的目录同步工具版本 6765.0006 后运行 `DirSyncConfigShell.psc1` 时收到错误的情况。

*原始产品版本：*Microsoft Entra ID、云服务（Web 角色/辅助角色）、Microsoft Intune、Azure 备份、Office 365 标识管理  
*原始 KB 数：* 2964373

## 现象

在基于 Windows Server 2008 R2 的计算机上安装 Microsoft Azure Active Directory 同步工具版本 6765.0006 后运行 `DirSyncConfigShell.psc1` 时，会收到以下错误消息：

> 警告：加载控制台 c：\program files\Windows Azure Active Directory Sync\dirsyncfonfigshell.psc1 时发生以下错误：由于以下错误，无法加载 Windows PowerShell 管理单元共存配置：无法加载文件或程序集“file:///c：\programSync\Microsoft Online.Coexistence.PS.Config.dll”或其依赖项之一。 此程序集由比当前加载的运行时更新的运行时生成，无法加载。
> 例如，运行 DirSyncConfigShell.psc1 强制进行目录同步时，会出现此问题。

## 原因

如果未在基于 Windows Server 2008 R2 的计算机上安装 Windows Management Framework 3.0，则会出现此问题。

## 解决方法

执行下列操作之一：

- 在基于 Windows Server 2008 R2 的计算机上安装 Windows Management Framework 3.0。 有关详细信息，请参阅 [Windows Management Framework 3.0](https://www.microsoft.com/download/details.aspx?id=34595)。
- 从基于 Windows Server 2012 R2 的计算机运行目录同步工具。 若要安装目录同步工具，请参阅 [安装或升级目录同步工具](/zh-cn/azure/active-directory/hybrid/whatis-hybrid-identity)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/load-file-or-assembly-error)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
