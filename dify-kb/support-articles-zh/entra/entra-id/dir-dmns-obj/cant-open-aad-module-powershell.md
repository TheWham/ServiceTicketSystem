# 无法打开适用于 Windows PowerShell 的 Azure Active Directory 模块

*原始产品版本：*云服务（Web 角色/辅助角色）、Microsoft Entra ID、Microsoft Intune、Azure 备份、Office 365 用户和域管理、Office 365 标识管理  
*原始 KB 数：* 2461873

## 现象

尝试打开适用于 Windows PowerShell 的 Microsoft Azure Active Directory 模块时，Windows PowerShell 控制台窗口将打开，并显示许多文本错误，指示无法加载模块包。

## 原因

如果没有在计算机上启用 Microsoft .NET Framework 3.51，则会出现此问题。

## 解决方法

若要解决此问题，请手动启用 .NET Framework 3.51。 为此，请根据正在运行的操作系统执行以下步骤：

**在 Windows 2008 R2** 中：

1. 打开 **“服务器管理器”** 。
2. 依次选择**“功能**”、“添加功能****”、“**.NET Framework 3.51 功能**”和“**.NET Framework 3.51”。**

**在 Windows 7** 中：

1. 打开“程序和功能”。
2. 选择“打开或关闭 Windows 功能”。
3. 选中以选中 **Microsoft NET Framework 3.51** 复选框，然后选择“ **确定**”。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/dir-dmns-obj/cant-open-aad-module-powershell)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
