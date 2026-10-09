# 尝试从回收站中删除用户时出错：Remove-MsolUser 用户未找到

*原始产品版本：*Office 365 标识管理、Microsoft Entra ID、云服务（Web 角色/辅助角色），Microsoft Intune，Azure 备份  
*原始 KB 数：* 3019157

## 现象

尝试从回收站中删除用户（有时也称为已删除用户容器）时，Microsoft云服务（如 Microsoft 办公室 365、Microsoft Intune 或 Microsoft Azure）中，会收到以下错误消息：

> Remove-MsolUser：找不到用户

例如，运行以下 cmdlet 时，会遇到这些症状：

```
Remove-MsolUser -RemoveFromRecyleBin
```

注意

自 2024 年 3 月 30 日起，Azure AD 和 MSOnline PowerShell 模块已弃用。 若要了解详细信息，请阅读[有关弃用的更新](https://techcommunity.microsoft.com/t5/microsoft-entra-blog/important-azure-ad-graph-retirement-and-powershell-module/ba-p/3848270)。 在此日期之后，对这些模块的支持仅限于到 Microsoft Graph PowerShell SDK 的迁移帮助和安全性修复。 弃用的模块将持续运行至 2025 年 3 月 30 日。

我们建议迁移到 [Microsoft Graph PowerShell](/zh-cn/powershell/microsoftgraph/overview)，以便与 Microsoft Entra ID（以前称为 Azure AD）进行交互。 有关常见迁移问题，请参阅[迁移常见问题解答](/zh-cn/powershell/azure/active-directory/migration-faq)。
*注意：*2024 年 6 月 30 日之后，MSOnline 版本 1.0.x 可能会遇到中断。

## 原因

如果执行操作的用户不是全局管理员，则会出现此问题。

## 解决方法

请执行以下一项操作：

- 让某人为你分配全局管理员角色，然后从回收站中删除用户。
- 让全局管理员从回收站中删除用户。
- 等待 30 天。 已删除的用户将保留在回收站中 30 天。 30 天后，它们会自动从回收站中删除。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/dir-dmns-obj/remove-msoluser-user-not-found-recyclebin)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
