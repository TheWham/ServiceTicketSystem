# 更改密码不会保存在 Azure、Office 365 或 Intune 中

*原始产品版本：*云服务（Web 角色/辅助角色），Microsoft Intune  
*原始 KB 数：* 2951280

## 现象

在 Microsoft Azure 中更改密码时，Microsoft 办公室 365 或 Microsoft Intune，然后选择“**完成**”保存更改时，不会保存更改的密码。

## 原因

使用特殊字符（如小于符号或大于符号`<``>`）作为密码的一部分时，会出现此问题。

## 解决方法

若要解决此问题，请不要将特殊字符用作密码的一部分。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/dir-dmns-obj/pwd-change-not-save)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
