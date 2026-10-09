# 在 Azure Active Directory 同步工具配置向导中输入企业管理员凭据后，错误（LogonUser（） 失败并出现错误代码：1789

## 概要

本文提供有关在 Azure Active Directory 同步工具配置向导中输入企业管理员凭据后解决“LogonUser（） 失败并出现错误代码：1789”错误的指南。

*原始产品版本：* 云服务（Web 角色/辅助角色）、Microsoft Entra ID、Microsoft Intune、Azure 备份、Office 365 标识管理  
*原始 KB 数：* 2508225

## 现象

在 Microsoft Azure Active Directory 同步工具配置向导中输入企业管理员凭据后，会收到以下错误消息：

> LogonUser（） 失败并出现错误代码：1789

## 原因

运行目录同步工具的计算机无法使用 Active Directory 进行身份验证时，通常会发生此问题。

## 解决方法

若要解决此问题，请使用以下一个或多个方法：

- 重新启动计算机。
- 将计算机加入工作组，然后将计算机加入域。
  1. 选择“开始**”**，右键单击“**计算机**”，然后选择“**属性**”。
  2. 在“计算机名称”、“域”和“工作组设置”下**，选择“**更改设置**”。**
  3. 选择“ **计算机名称** ”选项卡，然后选择“ **更改**”。
  4. 选择**“**工作组”选项，然后在“工作组**”对话框中键入工作组**。
  5. 重新启动计算机。
  6. 重复步骤 1 到 3。
  7. 选择**“域**”选项，然后在“域**”对话框中键入域名**，将计算机添加回域。
  8. 重新启动计算机。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/error-code-1789-configuration-wizard)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
