# 审核报告中的未知参与者

## 总结

下面是可以在 Microsoft Entra 审核日志中找到的一些 Microsoft 第一方服务主体角色的常见示例，包括这些角色可能对您的租户中的 Microsoft Entra 对象执行的操作的说明。

本文中找不到你在审核日志中看到的许多第一方服务主体参与者，因为它仅列出了一些示例。

## 未知参与者

| 参与者名称 | 服务 | 说明 |
| --- | --- | --- |
| Azure 凭据配置端点服务 | 身份验证方法注册 | 注册身份验证方法[时](/zh-cn/entra/identity/authentication/howto-mfa-userdevicesettings#add-authentication-methods-for-a-user)使用。 启用合并注册时，它可以在审核日志中显示为参与者。 |
| cxpweb\_service@support.onmicrosoft.com | CXP | 此帐户来自我们内部的 Microsoft 支持租户环境。 它用于促进客户租户的管理和维护。 Microsoft 支持部门目前正在过渡到统一的平台，用于客户支持和案例管理。 对于所涉及的更改，帐户会在租户设置标志以开始将客户支持案例迁移到统一平台。 此更改不会直接影响您的租户上的任何设置，也不会影响现有或将来的支持请求。 |
| DaRT 团队 | 合作伙伴中心 | “设置伙伴关系”操作意味着 DAP 由Microsoft终止。 此情景预计将成为由Microsoft主导的DAP弃用的一部分。 |
| fim\_password\_service@support.onmicrosoft.com | 自助密码重置 | 用于为最终用户执行自助密码重置操作。 |
| Microsoft审批管理 | 自助服务组管理服务 | 自助服务组管理服务（SSGM）用于Microsoft Entra ID [动态组](/zh-cn/azure/active-directory/enterprise-users/groups-create-rule)和 Office 365 组过期策略操作。 |
| Microsoft Azure AD 内部 - 即时预配 | Microsoft Entra ID | 当自动创建或更新Microsoft服务的服务主体时使用，通常是为了响应订阅中所做的更改。 这些自动服务主体更新有时通过后台异步过程进行。 它们不一定在订阅事件或更改后立即发生。 |
| Microsoft Azure 管理 | ARM | 如果目录还没有服务管理员的帐户，则“Windows Azure 服务管理 API”ARM 服务主体将向 Azure 订阅列表的服务管理员发送和兑换邀请。 此过程可确保订阅的服务管理员可以在门户中访问和查看订阅。 |
| Microsoft Entra 订阅生命周期过程 | 许可证管理器服务 | 许可证管理器服务用于在订阅过期或订阅状态更改时从 Microsoft Entra ID 中删除许可证和订阅。 |
| Microsoft Exchange 在线保护 | 安全与合规中心 | 由 Exchange Online Protection 用来写入对 Microsoft Entra ID 的更改。 例如，MIP 标签只能在安全和合规中心（SCC）中修改。 SCC 日志包含用户角色。 然后，SCC 将这些标签离线推送到 Microsoft Entra，于是没有用户上下文。 |
| Microsoft托管策略管理器 | Microsoft 条件访问托管 | 用于创建和管理 [Microsoft托管的条件访问策略](/zh-cn/entra/identity/conditional-access/managed-policies)。 |
| Microsoft基底管理 | 交流 | Exchange Online 在并行写入操作期间用于 Microsoft Entra ID。 当 Exchange Online 中的对象写入到 Microsoft Entra 身份验证 ID 时，该主体会显示为 Microsoft Entra 审核日志中的执行者。 有关双重写入操作的详细信息，请参阅 [Exchange Online 改进，以加速将更改复制到 Microsoft Entra ID](https://techcommunity.microsoft.com/t5/exchange-team-blog/exchange-online-improvements-to-accelerate-replication-of/ba-p/837218)。 |
| MS-CE-CXG-MAC-AadShadowRoleWriter | 许可证管理服务，购买服务，市场平台 | 商业平台用于将Microsoft 365商务角色权限分配给Microsoft Entra ID。 此服务将添加的角色示例是新式商务管理员。   - [参考 1 - Microsoft Entra 内置角色](/zh-cn/azure/active-directory/roles/permissions-reference#modern-commerce-administrator)  - [参考 2 - 谁可以通过自助购买？](/zh-cn/microsoft-365/commerce/subscriptions/self-service-purchase-faq#who-can-buy-through-self-service-purchase) |
| 注册 | 商业授权（LMS） | 在自助订阅注册期间由商业许可服务使用。 有关自助服务订阅的详细信息，请参阅 [管理自助注册订阅](/zh-cn/microsoft-365/commerce/subscriptions/manage-self-service-signup-subscriptions)。 |
| spo\_service@support.onmicrosoft.com | SharePoint Online | 此帐户用于创建 Azure 访问控制 服务（ACS）原则。 安装 SharePoint 应用（加载项）需要满足这些要求。 |
| Windows Azure 服务管理 API | Azure Resource Manager | 由 Azure 资源管理器 （ARM） 服务使用。 此服务主体可用于维护对 Azure 订阅和资源的适当访问权限所需的任何Microsoft Entra 操作，例如确保订阅的服务管理员在租户中具有Microsoft Entra 帐户。 当客户在其租户中的 Azure 订阅中注册资源提供程序时，可以看到此参与者。 有关此参与者出现的方式和原因的详细信息，请参阅 [资源提供程序和类型](/zh-cn/azure/azure-resource-manager/management/resource-providers-and-types)。 超过 1,000 个应用 ID 连接到资源提供程序，并定期添加新 ID。 REST API 可用于动态返回应用 ID。 |

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/governance/unknown-actors-in-audit-reports)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
