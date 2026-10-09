# 运行 Azure Active Directory 同步工具配置向导时出错：无法获取方法的地址：CreateIdentityHandle2

## 概要

本文提供有关在运行 Azure Active Directory 同步工具配置向导时解决“无法获取方法地址”错误的指南。

*原始产品版本：* 云服务（Web 角色/辅助角色）、Microsoft Entra ID、Microsoft Intune、Azure 备份、Office 365 标识管理  
*原始 KB 数：* 3037953

## 现象

运行 Microsoft Azure Active Directory 同步工具配置向导时，会收到以下错误消息：

> 无法获取方法的地址：从库 C：\Program Files\Common Files\Microsoft Shared\Microsoft Online Services\msoidcli.dll的 CreateIdentityHandle2。 GetLastError 代码：127

## 原因

如果运行的是早期版本的 Microsoft Online Services 登录助手，则会出现此问题。

## 解决方法

若要解决此问题，请执行以下步骤：

1. 卸载当前安装在目录同步计算机上的 Microsoft Online Services 登录助手的任何版本。
2. 从 [面向 IT 专业人员 RTW](https://download.microsoft.com/download/7/1/E/71EF1D05-A42C-4A1F-8162-96494B5E615C/msoidcli_32bit.msi) 的 Microsoft Online Services 登录助手安装最新版本的 Microsoft Online Services 登录助手。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/failed-get-address-method)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
