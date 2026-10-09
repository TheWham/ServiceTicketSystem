# 使用标准用户帐户登录时，无法在"系统属性"对话框中修改用户环境变量

本文解决无法在"系统属性"对话框中修改用户环境变量的问题。

_适用于：_ &nbsp; Windows Vista  
_原始 KB 编号：_ &nbsp; 931715

## 症状

如果你在 Windows Vista 中以标准用户帐户登录，则无法在**系统属性**对话框中修改用户环境变量。

例如，如果你通过控制面板中"系统"项下的"高级系统设置"访问"系统属性"对话框，系统会提示你输入管理员帐户凭据。如果你输入某个管理员帐户的凭据，那么你所能访问的用户环境变量将属于该管理员帐户，而不是你自己的帐户。

## 原因

此问题是由于 Windows Vista 增强了安全性而导致的。在 Windows Vista 中，修改用户环境变量的方法与早期版本的 Microsoft Windows 不同。

## 解决方法

要解决此问题，请使用控制面板中的"用户帐户"项来修改用户环境变量。操作步骤如下：

1. 单击"开始"，在"开始搜索"框中键入 Accounts，然后在"程序"下单击"用户帐户"。

     如果系统提示你输入管理员密码或进行确认，请键入密码或单击"允许"。
2. 在"用户帐户"对话框的"任务"下，单击"更改我的环境变量"。

3. 对你的用户帐户的用户环境变量进行所需的更改，然后单击"确定"。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/cannot-modify-user-environment-variables-system-properties)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权，本文档为社区中文翻译）
