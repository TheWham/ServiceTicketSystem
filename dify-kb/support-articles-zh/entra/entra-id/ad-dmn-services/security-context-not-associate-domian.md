# 运行 IdFix 工具时出错：当前安全上下文未与 Active Directory 域或林关联

*原始产品版本：* 云服务（Web 角色/辅助角色）、Microsoft Entra ID、Microsoft Intune、Azure 备份、Office 365 标识管理  
*原始 KB 数：* 2859144

## 现象

运行 IdFix DirSync 错误修正工具以在 本地 Active Directory 域服务（AD DS）环境中执行查询时，会收到以下错误消息：

> 异常：当前安全上下文不与 Active Directory 域或林关联。

使用不是运行查询的域成员的用户帐户登录到计算机后，会出现此问题。 IdFix 工具使用运行该工具的用户的安全上下文来确定要查询的域。

## 解决方法

使用作为运行查询的域成员的用户帐户登录到计算机。

## 详细信息

有关 IdFix 工具的详细信息，请参阅 [IdFix DirSync 错误修正工具](https://github.com/microsoft/idfix)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/ad-dmn-services/security-context-not-associate-domian)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
