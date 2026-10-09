# 电子邮件地址不会同步到 Microsoft Entra ID

## 概要

本文介绍用户同步到 Microsoft Entra ID 但一个或多个 SMTP 代理地址未同步的问题。 如果存在重复的 SMTP 代理地址，则会出现此问题。

*原始产品版本：* Microsoft Entra ID  
*原始 KB 数：* 3166798

## 现象

尽管用户已同步到 Microsoft Entra ID，但不会同步一个或多个 SMTP 代理地址。 此外，你可能会看到类似于以下内容之一的消息：

在 Office 365 门户中：

> 一个或多个用户帐户出现错误。 若要查看受影响的用户和详细的错误消息，请选择“有错误的用户”视图，然后选择用户的显示名称。

> 我们检测到值<>上存在重复的代理地址冲突。 所有属性值都需要在对象之间唯一。 若要解决冲突，请首先确定应使用冲突值的对象。 然后，从其他对象更新或删除冲突值。 在日期和时间<检测到>此错误。

从电子邮件报告：

> 此对象已在Microsoft Entra ID 中更新，但具有一些修改的属性，因为以下属性与另一个对象 [ProxyAddresses SMTP：`john@contoso.com`;] 相关联。

如果另一个对象具有相同的 SMTP 代理地址，则会出现此问题。

## 解决方法

若要解决此问题，请查找具有重复 SMTP 代理地址的用户，然后更改地址，使其唯一。 要设置部门，请按照以下步骤操作。

### 步骤 1：检查本地目录

使用 IdFix DirSync 错误修正工具标识重复或无效的属性。

若要使用 IdFix 工具解析重复属性，请参阅 [ERROR 列中](/zh-cn/office365/troubleshoot/active-directory/run-idfix-dirsync-error-remediation-tool)显示“重复”。

有关 IdFix 工具的详细信息，请转到 [IdFix DirSync 错误修正工具](https://github.com/microsoft/idfix)。

### 步骤 2：检查Microsoft条目 ID

可以使用适用于 Windows PowerShell 的 Office 365 门户或 Azure Active Directory 模块检查Microsoft条目 ID 以获取重复属性。

注意

Office 365 门户中的报表仅显示存在这些错误的用户对象。 报告不显示有关组、联系人或公用文件夹之间的冲突的信息。 请参阅方法 2，了解如何查看其他对象的冲突。

#### 方法 1：使用 Office 365 门户

1. 以管理员身份登录到 Office 365 门户（<https://portal.office.com>）。
2. 在Microsoft 365 管理中心中，转到**“用户**”，然后选择“**活动用户**”。

   如果组织中任何对象存在重复的属性冲突，则会显示页面顶部的警告。
3. 若要筛选视图以仅显示有错误的用户，请选择“ **有错误**的用户”。
4. 选择一个对象以查看有关冲突的详细信息。 此信息显示在页面右下角。
5. 更改电子邮件地址，使其唯一。

#### 方法 2：使用适用于 Windows PowerShell 的 Azure AD 模块

若要详细了解如何使用适用于 Windows PowerShell 的 Azure AD 模块来标识具有重复值的对象，请参阅 [标识同步和重复属性复原能力](/zh-cn/azure/active-directory/hybrid/how-to-connect-syncservice-duplicate-attribute-resiliency)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/email-addresses-not-sync)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
