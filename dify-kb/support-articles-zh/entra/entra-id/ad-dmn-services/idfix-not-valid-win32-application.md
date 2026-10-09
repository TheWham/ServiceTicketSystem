# 运行 IdFix 工具时出错：IdFix.exe不是有效的 Win32 应用程序

*原始产品版本：* 云服务（Web 角色/辅助角色）、Microsoft Entra ID、Microsoft Intune、Azure 备份、Office 365 标识管理  
*原始 KB 数：* 2859165

## 现象

尝试在 本地 Active Directory 域服务（AD DS）环境中运行 IdFix DirSync 错误修正工具时，会收到以下错误消息：

> IdFix.exe不是有效的 Win32 应用程序

## 原因

如果在该工具不支持的操作系统上运行 IdFix 工具，则会出现此问题。

## 解决方法

在运行 64 位版本的 Windows 7 或更高版本的计算机上安装并运行 IdFix 工具。

## 详细信息

有关 IdFix 工具的详细信息，请参阅 [IdFix DirSync 错误修正工具](https://github.com/microsoft/idfix) （这包括系统要求列表）。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/ad-dmn-services/idfix-not-valid-win32-application)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
