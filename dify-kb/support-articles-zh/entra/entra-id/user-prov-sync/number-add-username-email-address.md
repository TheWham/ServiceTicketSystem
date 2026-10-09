# 当用户同步到 Microsoft Entra ID 时添加到用户名和电子邮件地址的数字

## 概要

本文提供有关在用户同步到 Microsoft Entra ID 时向用户名和电子邮件地址添加数字的问题进行故障排除的信息。 如果存在重复的用户主体名称（UPN），则会出现此问题。

*原始产品版本：* Microsoft Entra ID  
*原始 KB 数：* 3166795

## 现象

当用户同步到 Microsoft Entra ID 时，会向其 UPN 和 SMTP 代理地址添加一个数字。 例如：`john1234@contoso.onmicrosoft.com`。

注意

在 Microsoft Entra ID 中创建用户时，其用户主体名称（UPN）也将用作 SMTP 代理地址之一。 因此，SMTP 代理地址还将包含数字。

此外，你可能会看到以下消息之一：

在 Office 365 门户中：

> 一个或多个用户帐户出现错误。 若要查看受影响的用户和详细的错误消息，请选择“有错误的用户”视图，然后单击用户的显示名称。

> [DIRSYNC 错误]：此用户已同步到Microsoft Entra ID，但我们必须将 UserPrincipalName 属性从 `john@contoso.com` .com 修改为 `john1234@contoso.onmicrosoft`.com，因为现有用户 `john@contoso.com`已使用此值创建。
> `john@contoso.com` 由于 `john1234@contoso.onmicrosoft.com` 现有用户已 `john@contoso.com`使用此值创建。

从电子邮件报告：

> 此对象已在Microsoft Entra ID 中更新，但具有一些修改的属性，因为以下属性与另一个对象 [ProxyAddresses SMTP：`john@contoso.com`;] 相关联。

> 此对象已在Microsoft Entra ID 中更新，但具有一些修改的属性，因为以下属性与另一个对象 [UserPrincipalName `john@contoso.com`;] 相关联。

如果另一个对象具有相同 UPN，则会出现此问题。

## 解决方法

若要解决此问题，请查找具有重复 UPN 的用户，然后更改 UPN，使其是唯一的。 要设置部门，请按照以下步骤操作。

### 步骤 1：检查本地目录

使用 IdFix DirSync 错误修正工具标识重复或无效的属性。

若要使用 IdFix 工具解析重复属性，请参阅 [ERROR 列中](https://support.microsoft.com/help/2857385)显示“重复”。

有关 IdFix 工具的详细信息，请转到 [IdFix DirSync 错误修正工具](https://github.com/microsoft/idfix)。

### 步骤 2：检查Microsoft条目 ID

可以使用适用于 Windows PowerShell 的 Office 365 门户或 Azure Active Directory 模块检查Microsoft条目 ID 以获取重复属性。

#### 方法 1：使用 Office 365 门户

1. 以管理员身份登录到 Office 365 [门户](https://portal.office.com) 。
2. 在Microsoft 365 管理中心中，转到**“用户**”，然后选择“**活动用户**”。

   如果组织中任何对象存在重复的属性冲突，则会显示页面顶部的警告。
3. 选择一个对象以查看有关冲突的详细信息。 此信息显示在页面右下角。
4. 更改用户名，使其唯一。

#### 方法 2：使用适用于 Windows PowerShell 的 Azure AD 模块

若要详细了解如何使用适用于 Windows PowerShell 的 Azure AD 模块来标识具有重复值的对象，请参阅 [标识同步和重复属性复原能力](/zh-cn/azure/active-directory/hybrid/how-to-connect-syncservice-duplicate-attribute-resiliency)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/number-add-username-email-address)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
