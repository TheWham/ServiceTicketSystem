# 排查错误 SSPR\_009：已同步的 Microsoft Entra 管理员无法从云重置密码

本文介绍如何排查具有Microsoft Entra Administrator 角色的同步用户尝试重置其密码失败时发生的密码重置错误。

在用户访问登录页<https://login.microsoftonline.com>**并选择“无法访问你的帐户？”****、忘记了密码**或**立即**重置密码之后，会出现这种情况。 然后，浏览器会将用户重定向到自助密码重置（SSPR）页 <https://passwordreset.microsoftonline.com> ，以启动 SSPR 进程。 此过程要求用户输入“captcha”代码。 如果操作成功，密码写回会将用户的密码重置请求发送到本地 Active Directory域。 同时，SSPR 在 Microsoft Entra ID 中设置新密码。 如果操作失败，将改为返回“SSPR\_009”错误。 如果发生此错误，请使用本文解决此问题。

## 现象

同步用户尝试通过输入 captcha 代码重置密码失败后，浏览器会显示以下错误消息：

> 无法重置自己的密码，因为组织未启用密码重置。
>
> SSPR\_009：组织尚未启用密码重置。 如果你是管理员，可以从“如何启用密码重置”[一文中获取详细信息](/zh-cn/azure/active-directory/authentication/tutorial-enable-sspr)。 如果你不是管理员，可以在联系管理员时提供此信息。

注意

此方案仅适用于分配有Microsoft Entra 管理员角色的 Microsoft Entra 用户。 密码更改或重置流对标准帐户按预期工作。

## 原因

未在租户上启用适用于管理员的 SSPR。 适用于管理员的 SSPR（SSPR-A）是 SSPR 的第一个实现。 引入 SSPR for Users（SSPR-U）后，用户可以有两个单独的配置。

Microsoft Entra 帐户具有管理员角色（例如全局管理员或计费管理员）时，将使用旧的 SSPR-A 实现。 但是，Azure 门户上的 SSPR 管理仅适用于 SSPR-U。 因此，可能无法在租户上启用 SSPR-A。

## 解决方案

通过运行 [Update-MgPolicyAuthorizationPolicy](/zh-cn/powershell/module/microsoft.graph.identity.signins/update-mgpolicyauthorizationpolicy) Microsoft Graph PowerShell cmdlet 在租户上启用 SSPR-A，如下所示：

```
Import-Module Microsoft.Graph.Identity.SignIns

$params = @{
	allowedToUseSSPR = $true
}

Update-MgPolicyAuthorizationPolicy -BodyParameter $params
```

有关详细信息，请参阅 [Microsoft Graph PowerShell SDK 入门](/zh-cn/powershell/microsoftgraph/get-started)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/password-writeback-error-code-sspr-009)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
