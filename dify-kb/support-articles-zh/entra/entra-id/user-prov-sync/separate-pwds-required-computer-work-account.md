# 使用密码同步和 Azure Active Directory 同步工具时，计算机和工作或学校帐户所需的单独密码

## 概要

本文提供指南，帮助解决在使用密码同步及 Azure Active Directory 同步工具时，当计算机和工作或学校帐户需要单独密码的情况。

*原始产品版本：* 云服务（Web 角色/辅助角色）、Microsoft Entra ID、Microsoft Intune、Azure 备份、Office 365 标识管理  
*原始 KB 数：* 2853316

## 现象

用户必须使用不同的密码登录到Microsoft云服务（如 Office 365、Microsoft Azure 或 Microsoft Intune）中的工作或学校帐户，并登录到其计算机。 即使已执行以下操作，也会出现此问题：

- Microsoft Entra ID 中启用了密码同步
- 设置 Active Directory 同步以将本地 Active Directory域服务（AD DS）环境中的用户帐户同步到Microsoft Entra ID

## 原因

如果用户的云服务密码发生更改，则会出现此问题。 密码同步不会同步云服务密码。 因此，在此方案中，用户对其本地计算机和云服务具有不同的密码。

## 解决方法

若要解决此问题，请执行下列操作之一：

- 让用户更改其计算机密码。
- 重置用户的计算机密码。 重置用户密码时，请确保 **清除“下次登录** 时用户必须更改密码”复选框。

目录同步后，本地 Active Directory环境中的用户计算机密码将同步到 Microsoft Entra ID。 然后，用户可以使用同一密码登录到其计算机并登录到云服务。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/separate-pwds-required-computer-work-account)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
