# 尝试在 Azure、Office 365 或 Intune 中重置密码时出错：我们无法验证你的帐户

*原始产品版本：* 云服务（Web 角色/辅助角色）、Microsoft Entra ID、Microsoft Intune、Azure 备份、Office 365 标识管理  
*原始 KB 数：* 2951274

## 现象

当新用户尝试在 Azure Microsoft、Microsoft 办公室 365 或 Microsoft Intune 中重置密码时，用户会收到以下错误消息：

> 重置密码
>
> 我们无法验证帐户
>
> 如果需要，我们可以联系组织中的管理员重置密码。

## 解决方法

向用户分配Microsoft Entra ID P1 或 P2 许可证。 用户必须具有Microsoft Entra ID P1 或 P2 许可证才能重置自己的密码。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/mfa/cannot-verify-account-reset-pwd)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
