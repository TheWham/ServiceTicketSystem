# 尝试安装适用于 Windows PowerShell 的 Azure Active Directory 模块时出错：必须安装 Windows PowerShell 2.0 或更高版本

## 概要

本文介绍无法为 Windows PowerShell 安装 Azure Active Directory 模块的问题。 它提供解决方法。

*原始产品版本：* Microsoft Entra ID、Office 365 用户和域管理、Office 365 标识管理  
*原始 KB 数：* 2913017

## 现象

尝试安装适用于 Windows PowerShell 的 Azure Active Directory 模块时，会收到以下错误消息：

> 若要安装适用于 PowerShell 的 Windows Azure Active Directory 模块，必须在此计算机上安装 Windows PowerShell 2.0 或更高版本。

## 解决方法

若要解决此问题，请尝试以下方法之一。 如果一个不适用于你，请尝试另一个。

### 方法 1：以本地管理员身份登录时安装适用于 Windows PowerShell 的 Azure Active Directory 模块

1. 以本地管理员身份登录。（仅以域管理员身份登录可能不起作用。
2. 安装 [适用于 PowerShell](/zh-cn/previous-versions/azure/jj151815(v=azure.100)?redirectedfrom=MSDN#install-the-azure-ad-module) 的 Azure Active Directory 模块。

### 方法 2：确保已启用 Windows PowerShell 2.0

1. 以本地管理员身份登录。（仅以域管理员身份登录可能不起作用。
2. 在控制面板中，选择“程序和功能”**，或选择“程序”下的**“**卸载程序****”。**
3. 选择“ **打开或关闭**窗口功能”。
4. 在 Windows 功能窗口中，确保 **选中 Windows PowerShell 2.0** 复选框，然后选择“ **确定**”。
5. 安装 [适用于 PowerShell](/zh-cn/previous-versions/azure/jj151815(v=azure.100)?redirectedfrom=MSDN#install-the-azure-ad-module) 的 Azure Active Directory 模块。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/unable-install-aad-module-powershell)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
