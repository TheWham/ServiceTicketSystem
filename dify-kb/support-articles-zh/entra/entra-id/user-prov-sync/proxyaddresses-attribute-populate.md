# 如何在 Microsoft Entra ID 中填充 proxyAddresses 属性

## 概要

本文介绍如何在 Microsoft Entra ID 中填充 proxyAddresses 属性，并讨论常见方案，以帮助你了解如何在 Microsoft Entra ID 中填充 proxyAddresses 属性。

*原始产品版本：* Microsoft Entra ID  
*原始 KB 数：* 3190357

注意

本文有帮助吗? 你的输入对我们很重要。 请使用此页上的 **“反馈** ”按钮告诉我们本文为你工作得有多好，或者我们如何改进它。

Active Directory 中的 proxyAddresses 属性是一个多值属性，可包含各种已知地址条目。 例如，它可以包含 SMTP 地址、X500 地址和 SIP 地址。 当对象同步到 Microsoft Entra ID 时，Active Directory 中邮件或 proxyAddresses 属性中指定的值将复制到 Microsoft Entra ID 中的影子邮件或 proxyAddresses 属性。 然后，它们用于根据内部Microsoft Entra ID 规则计算Microsoft Entra 中对象的最终 proxyAddresses。 在 Microsoft Entra ID 中填充邮件、mailNickName 和 proxyAddresses 属性的逻辑称为代理计算。 它考虑了本地 Active Directory数据的许多不同方面，例如：

- 根据本地部署的 ProxyAddresses 或 UserPrincipalName 设置或更新主 SMTP 地址及其他次要地址。
- 根据计算的主 SMTP 地址设置或更新 Mail 属性。
- 根据本地部署的 MailNickName 或主 SMTP 地址前缀，设置或更新 MailNickName 属性。
- 放弃具有保留域后缀的本地地址，例如 @\*.onmicrosoft.com、@\*.microsoftonline.com;
- 放弃具有旧协议（如 MSMAIL、X400 等）的本地 ProxyAddresses;
- 放弃格式不正确的本地地址或不符合 RFC 5322，例如缺少协议前缀“SMTP：”，包含空格或其他无效字符;
- 如果用户分配了 Exchange Online 许可证，则删除具有未验证域后缀的 ProxyAddresses。

因此，Active Directory 中对象的 Mail 和 ProxyAddresses 属性的值可能与 Microsoft Entra ID 中 ProxyAddresses 属性的值不同。

注意

对于从本地 Active Directory同步的用户，在不更新相应电子邮件地址属性的情况下更改 UserPrincipalName （UPN）可能会导致Exchange Online邮箱主 SMTP 地址与权威同步地址不同。 在初始邮箱预配期间或现有主 SMTP 地址与以前的 WindowsLiveID 匹配时，可能会发生这种情况。 若要保留预期的主要 SMTP 地址，请随着 UPN 的更改，更新并同步相应的 mail 和 proxyAddresses 属性。

## 术语

本文使用了以下术语：

- 初始域：租户中预配的第一个域。 例如，`Contoso.onmicrosoft.com`。
- Microsoft 在线电子邮件路由地址 (MOERA)：由用户的 userPrincipalName 前缀加上初始域后缀构成的地址，该地址会自动添加到 Microsoft Entra ID 中的 proxyAddresses。 例如，`smtp:john.doe@Contoso.onmicrosoft.com`。
- UserPrincipalName （UPN）：用户的登录地址。
- 主 SMTP 地址：Exchange 收件人对象的主电子邮件地址，包括 SMTP 协议前缀。 例如，`SMTP:john.doe@Contoso.com`。
- 辅助 SMTP 地址：Exchange 收件人对象的一个或多个附加电子邮件地址。 例如，`smtp:john.doe@Contoso.com`。
- 邮件属性：保留用户的主电子邮件地址，而不保留 SMTP 协议前缀。 例如，`john.doe@Contoso.com`。
- MailNickName 属性：保留 Exchange 收件人对象的别名。 例如，`john.doe`。

## 方案 1：用户没有邮件、mailNickName 或 proxyAddresses 属性集

已创建具有以下属性集的本地用户对象：

```
AD:mail              : \<not set>
AD:mailNickName      : \<not set>
AD:proxyAddresses    : {\<not set>}
AD:userPrincipalName : user1upn@Contoso.com
```

接下来，将其同步到 Microsoft Entra ID，并且仅使用 UPN 的前缀来填充 mailNickName 属性，因为该属性是必需的：

```
AAD:mailNickName      : user1upn
AAD:UserPrincipalName : user1upn@Contoso.com
```

然后，它分配了 Exchange Online 许可证。 在此场景中，作为代理计算的结果，将执行以下操作：

- 使用 UPN 值在 proxyAddresses 属性中设置主 SMTP 地址。
- 使用主 SMTP 地址填充邮件属性。
- 使用 mailNickName@初始域 的格式，在 proxyAddresses 属性中将 MOERA 添加为辅助 SMTP 地址。

以下属性在具有 Exchange Online 许可证的同步用户对象上Microsoft Entra ID 中设置：

```
AAD:mail              : user1upn@Contoso.com
AAD:mailNickName      : user1upn
AAD:proxyAddresses    : {smtp:user1upn@Contoso.onmicrosoft.com; SMTP:user1upn@Contoso.com}
AAD:userPrincipalName : user1upn@Contoso.com
```

注意

如果用户分配了 Exchange 许可证，或者用户是 Exchange Online 收件人（例如共享邮箱），则 `userPrincipalName` 始终添加为代理地址。

## 方案 2：用户没有 mailNickName 或 proxyAddresses 属性集

创建具有以下属性集的本地用户对象：

```
AD:mail              : user2mail@Contoso.com
AD:mailNickName      : \<not set>
AD:proxyAddresses    : {\<not set>}
AD:userPrincipalName : user2upn@Contoso.com
```

接下来，它会与 Microsoft Entra ID 同步，并基于代理计算结果执行以下操作：

- 使用邮件属性的相同值设置主 SMTP。
- 使用主 SMTP 地址前缀填充 mailNickName 属性。
- 使用主 SMTP 地址填充邮件属性。

初始用户预配时，以下属性在 Microsoft Entra ID 中设置：

```
AAD:mail              : user2mail@Contoso.com
AAD:mailNickName      : user2mail
AAD:proxyAddresses    : {SMTP:user2mail@Contoso.com}
AAD:userPrincipalName : user2upn@Contoso.com
```

然后，它分配了 Exchange Online 许可证。 在此方案中，由于代理计算，将执行以下操作：

- 将 UPN 添加为 proxyAddresses 属性中的辅助 smtp 地址。
- 使用 mailNickName@初始域 的格式，在 proxyAddresses 属性中将 MOERA 添加为辅助 SMTP 地址。

以下属性是在 Microsoft Entra ID 中为具有 Exchange Online 许可证的已同步用户对象设置的：

```
AAD:mail              : user2mail@Contoso.com
AAD:mailNickName      : user2mail
AAD:proxyAddresses    : {smtp:user2upn@Contoso.com; smtp:user2mail@Contoso.onmicrosoft.com; SMTP:user2mail@Contoso.com}
AAD:userPrincipalName : user2upn@Contoso.com
```

## 方案 3：更改本地用户的 proxyAddresses 属性值

创建具有以下属性集的本地用户对象：

```
AD:mail              : \<not set>
AD:mailNickName      : \<not set>
AD:proxyAddresses    : {smtp:user3pa3@Fabrikam.microsoftonline.com, smtp:user3pa2@Contoso.onmicrosoft.com, SMTP:user3pa1@Contoso.com}
AD:userPrincipalName : user3upn@Contoso.com
```

接下来，它会同步到Microsoft Entra ID 并分配 Exchange Online 许可证。 在此方案中，由于代理计算，将执行以下操作：

- 放弃具有保留域后缀的地址。 在此示例中，跳过以下地址：
  - `smtp:user3pa2@Contoso.onmicrosoft.com`
  - `smtp:user3pa3@Fabrikam.microsoftonline.com`
- 使用本地 proxyAddresses 属性中指定的同一地址设置主 SMTP。
- 使用主 SMTP 地址前缀填充 mailNickName 属性。
- 使用主 SMTP 地址填充邮件属性。
- 使用 mailNickName@初始域 的格式，在 proxyAddresses 属性中将 MOERA 添加为辅助 SMTP 地址。
- 将 UPN 添加为 proxyAddresses 属性中的辅助 smtp 地址。

以下属性在同步用户对象的Microsoft Entra ID 中设置：

```
AAD:mail              : user3pa1@Contoso.com
AAD:mailNickName      : user3pa1
AAD:proxyAddresses    : {smtp:user3upn@Contoso.com; smtp:user3pa1@Contoso.onmicrosoft.com; SMTP:user3pa1@Contoso.com}
AAD:userPrincipalName : user3upn@Contoso.com
```

然后，将本地 proxyAddresses 属性的值更改为以下值：

```
AD:mail              : \<not set>
AD:mailNickName      : \<not set>
AD:proxyAddresses    : {smtp:user3new3@Fabrikam.microsoftonline.com, smtp:user3new2@Contoso.onmicrosoft.com, SMTP:user3new1@Contoso.com}
AD:userPrincipalName : user3upn@Contoso.com
```

在此方案中，由于代理计算，将执行以下操作：

- 放弃具有保留域后缀的地址。 例如，将跳过以下地址：
  - `smtp:user3new2@Contoso.onmicrosoft.com`
  - `smtp:user3new3@Fabrikam.microsoftonline.com`
- 替换 proxyAddresses 属性中指定的新主 SMTP 地址。
- 使用 proxyAddresses 属性中指定的新主 SMTP 地址的值更新邮件属性。
- 保留旧的 mailNickName，因为本地未设置 mailNickName，且其值也未发生更改。
- 将旧的 MOERA 保留为 proxyAddresses 属性中的辅助 smtp 地址。
- 将 UPN 保留为 proxyAddresses 属性中的辅助 SMTP 地址。

以下属性在同步用户对象的Microsoft Entra ID 中设置：

```
AAD:mail              : user3new1@Contoso.com
AAD:mailNickName      : user3pa1
AAD:proxyAddresses    : {SMTP:user3new1@Contoso.com; smtp:user3upn@Contoso.com; smtp:user3pa1@Contoso.onmicrosoft.com}
AAD:userPrincipalName : user3upn@Contoso.com
```

## 方案 4：删除 Exchange Online 许可证

创建具有以下属性集的本地用户对象：

```
AD:mail              : \<not set>
AD:mailNickName      : \<not set>
AD:proxyAddresses    : {\<not set>}
AD:userPrincipalName : user4upn@Contoso.com
```

接下来，它会同步到Microsoft Entra ID 并分配 Exchange Online 许可证。 在此方案中，由于代理计算，将执行以下操作：

- 使用 UPN 值在 proxyAddresses 属性中设置主 SMTP 地址。
- 使用主 SMTP 地址前缀填充 mailNickName 属性。
- 使用主 SMTP 地址填充邮件属性。
- 使用 mailNickName@初始域 的格式，在 proxyAddresses 属性中将 MOERA 添加为辅助 SMTP 地址。

以下属性在同步用户对象的Microsoft Entra ID 中设置：

```
AAD:mail              : user4upn@Contoso.com
AAD:mailNickName      : user4upn
AAD:proxyAddresses    : {smtp:user4upn@Contoso.onmicrosoft.com; SMTP:user4upn@Contoso.com}
AAD:userPrincipalName : user4upn@Contoso.com
```

然后，删除 Exchange Online 许可证，并执行以下操作作为代理计算的结果：

- 删除与 UPN 值对应的 proxyAddresses 属性中的主 SMTP 地址。
- 将 MOERA 从辅助地址提升到 proxyAddresses 属性中的主 SMTP 地址。
- 在 proxyAddresses 属性（MOERA）中使用主 SMTP 地址更新邮件属性。

```
AAD:mail              : user4upn@Contoso.onmicrosoft.com
AAD:mailNickName      : user4upn
AAD:proxyAddresses    : {SMTP:user4upn@Contoso.onmicrosoft.com}
AAD:userPrincipalName : user4upn@Contoso.com
```

然后，在本地 proxyAddresses 属性中添加辅助 smtp 地址：

```
AD:mail              : \<not set>
AD:mailNickName      : \<not set>
AD:proxyAddresses    : {smtp:user4new@Contoso.com}
AD:userPrincipalName : user4upn@Contoso.com
```

当对象同步到 Microsoft Entra ID 时，将执行以下操作作为代理计算的结果：

- 在 proxyAddresses 属性中添加辅助 smtp 地址。
- 将 UPN 添加为 proxyAddresses 属性中的辅助 smtp 地址。

在 Microsoft Entra ID 中为已同步的用户对象设置的以下属性：

```
AAD:mail              : user4upn@Contoso.onmicrosoft.com
AAD:mailNickName      : user4upn
AAD:proxyAddresses    : {smtp:user4upn@Contoso.com; smtp:user4new@Contoso.com; SMTP:user4upn@Contoso.onmicrosoft.com}
AAD:userPrincipalName : user4upn@Contoso.com
```

## 方案 5：mailNickName 属性值已更改

创建具有以下属性集的本地用户对象：

```
AD:mail              : \<not set>
AD:mailNickName      : \<not set>
AD:proxyAddresses    : {\<not set>}
AD:userPrincipalName : user5upn@Contoso.com
```

接下来，它会同步到Microsoft Entra ID 并分配 Exchange Online 许可证。 在此方案中，由于代理计算，将执行以下操作：

- 使用 UPN 值在 proxyAddresses 属性中设置主 SMTP 地址。
- 使用主 SMTP 地址前缀填充 mailNickName 属性。
- 使用主 SMTP 地址填充邮件属性。
- 使用 mailNickName@初始域 的格式，在 proxyAddresses 属性中将 MOERA 添加为辅助 SMTP 地址。

以下属性在同步用户对象的Microsoft Entra ID 中设置：

```
AAD:mail              : user5upn@Contoso.com
AAD:mailNickName      : user5upn
AAD:proxyAddresses    : {smtp:user5upn@Contoso.onmicrosoft.com; SMTP:user5upn@Contoso.com}
AAD:userPrincipalName : user5upn@Contoso.com
```

然后，将本地 mailNickName 属性的值更改为以下内容：

```
mail              : \<not set>
AD:mailNickName      : user5new1
AD:proxyAddresses    : {\<not set>}
AD:userPrincipalName : user5upn@Contoso.com
```

在此方案中，由于代理计算，将执行以下操作：

- 使用与本地 mailNickName 属性相同的值更新 mailNickName 属性。
- 保持邮件属性不变。
- 使 proxyAddresses 属性保持不变。

以下属性在同步用户对象的Microsoft Entra ID 中设置：

```
AAD:mail              : user5upn@Contoso.com
AAD:mailNickName      : user5new1
AAD:proxyAddresses    : {smtp:user5upn@Contoso.onmicrosoft.com; SMTP:user5upn@Contoso.com}
AAD:userPrincipalName : user5upn@Contoso.com
```

## 方案 6：两个用户具有相同 mailNickName 属性

创建两个具有相同 mailNickName 值的本地用户对象：

```
AD:mail              : \<not set>
AD:mailNickName      : user6mnn
AD:proxyAddresses    : {\<not set>}
AD:userPrincipalName : user6a@Contoso.com
```

```
AD:mail              : \<not set>
AD:mailNickName      : user6mnn
AD:proxyAddresses    : {\<not set>}
AD:userPrincipalName : user6b@Contoso.com
```

接下来，它们将同步到 Office 365 并分配 Exchange Online 许可证。 在此方案中，由于代理计算，将执行以下操作：

- 使用 UPN 值在 proxyAddresses 属性中设置主 SMTP 地址。
- 使用与本地 mailNickName 属性相同的值填充 mailNickName 属性。
- 使用主 SMTP 地址填充邮件属性。
- 对于预配的第一个用户，使用 mailNickName@initial domain 格式，在 proxyAddresses 属性中将 MOERA 添加为辅助 SMTP 地址。
- 对于预配的第二个用户，MOERA 已被另一个对象使用 - 将 MOERA 添加为辅助 smtp 地址，方法是将 4 个随机数字追加到 mailNickName 作为前缀，以及 @initial 域后缀。

以下属性在同步用户对象的Microsoft Entra ID 中设置：

```
AAD:mail              : user6a@Contoso.com
AAD:mailNickName      : user6mnn
AAD:proxyAddresses    : {smtp:user6mnn@Contoso.onmicrosoft.com; SMTP:user6a@Contoso.com}
AAD:userPrincipalName : user6a@Contoso.com
```

```
AAD:mail              : user6b@Contoso.com
AAD:mailNickName      : user6mnn
AAD:proxyAddresses    : {smtp:user6mnn5236@Contoso.onmicrosoft.com; SMTP:user6b@Contoso.com}
AAD:userPrincipalName : user6b@Contoso.com
```

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/proxyaddresses-attribute-populate)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
