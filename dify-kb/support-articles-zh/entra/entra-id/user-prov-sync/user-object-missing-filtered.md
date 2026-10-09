# Azure Active Directory Sync 中的 Microsoft Entra 连接器中缺少或筛选用户对象

## 概要

本文介绍阻止用户对象从本地同步到 Azure 的问题。 文中提供了一种替代方法。

*原始产品版本：* Microsoft Entra ID  
*原始 KB 数：* 3066176

## 现象

尝试将用户对象同步到 Microsoft Entra ID 时，操作将失败。

在 Metaverse 对象中搜索用户对象时，只会看到“连接器**”选项卡上列出的** Active Directory 连接器。未列出 Windows Microsoft Entra 连接器。 此外，此特定用户不会返回任何错误。

你可能还会注意到 `msExchRecipientTypeDetails` ，未正确同步的用户对象的值为 2。 这对应于链接邮箱类型，并且用户没有此值。

注意

以下值是触发用户对象的筛选的唯一值： `msExchRecipientTypeDetails == (0x1000 OR 0x2000 OR 0x4000 OR 0x400000 OR 0x800000 OR 0x1000000 OR 0x20000000)`

有关筛选的用户对象的详细信息，请参阅 [目录同步如何确定从本地环境同步到 Windows Azure AD](https://social.technet.microsoft.com/wiki/contents/articles/19901.dirsync-list-of-attributes-that-are-synced-by-the-azure-active-directory-sync-tool.aspx#how_directory_synchronization_determines_what_isn_t_synced_from_the_on-premises_environment_to_windows_azure_ad) 的内容。

## 原因

出现此问题的原因是 sourceAnchor 属性存在规则。 该规则用于确定值 `msexchRecipientTypeDetails` 是否为 **2**。

注意

可以在以下位置查看此规则： *同步规则配置编辑器\Inbound\In From AD\Common\Transformation*。 还可以查看目标 sourceAnchor 属性和表达式规则，如下所示： *IIF（IsPresent（[msExchRecipientTypeDetails]），IIF（[msExchRecipientTypeDetails]=2，NULL，IIF（IsStr）ing（[objectGUID]）、CStr（[objectGUID]）、ConvertToBase64（[objectGUID]））、IIF（IsString（[objectGUID]）、CStr（[objectGUID]）、ConvertToBase64（[objectGUID]））*

如果 `msExchRecipientTypeDetails` 值为 **2**，则 sourceAnchor 的值设置为 NULL。 但是，如果 sourceAnchor 的值为 NULL，则将筛选用户。

## 解决方法

要解决此问题，请执行以下操作之一：

- 请确保首先同步主用户帐户（在帐户林中）。
- 将 msExchRecipientTypeDetails 的属性值更改为 1。 使用任何不应由任一规则筛选的值。

## 详细信息

根据 [DirSync：Azure Active Directory 同步工具](https://social.technet.microsoft.com/wiki/contents/articles/19901.dirsync-list-of-attributes-that-are-synced-by-the-azure-active-directory-sync-tool.aspx)同步的属性列表，筛选用户对象的一个原因是以下原因：

```
msExchRecipientTypeDetails == (0x1000 OR 0x2000 OR 0x4000 OR 0x400000 OR 0x800000 OR 0x1000000 OR 0x20000000)
```

`msExchRecipientTypeDetails`假设用户的属性设置为值 2，AADSync 服务器将筛选此对象。 这不正确。 AADSync 不筛选此用户对象，它只是等待主帐户（从帐户林）加入对象，因为它需要 UPN 和 sourceAnchor。

属性 `msExchRecipientTypeDetails` 的值为 2，表示邮箱类型为“链接邮箱”。 链接邮箱位于帐户资源林拓扑中，帐户林中的用户对象必须先同步，然后才能将这些资源对象预配到 Microsoft Entra ID。

因此，如果 `msExchRecipientTypeDetails` 设置为 2，则不会筛选对象。 但是，设置此标志时，AADSync 会等待主帐户（从帐户林）同步，以便它可以联接这两个对象，并为 AADSync 中的最终用户对象创建云连接器。

在没有帐户资源林拓扑且用户具有 `msExchRecipientTypeDetails` 值 2 的情况下，将值更改为类似于常用对象的值将同步用户对象。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/user-object-missing-filtered)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
