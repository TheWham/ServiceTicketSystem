# 使用 Connect Health 了解 Microsoft Entra ID 中的 AD FS 登录事件

使用 Microsoft Entra Connect Health，可以将 Active Directory 联合身份验证服务 （AD FS） 登录事件集成到 Microsoft Entra 登录报告中。 Microsoft Entra 登录报告包含有关以下类型的实体何时登录到 Microsoft Entra ID 和访问资源的信息：

- 用户
- 应用程序
- 托管的资源

本文介绍如何使用适用于 AD FS 代理、Azure Monitor 和 Log Analytics 的 Connect Health 关联和分析 AD FS 登录数据。

## 先决条件

- [Microsoft已安装并升级到最新版本（3.1.95.0 或更高版本）的 Entra Connect Health](/zh-cn/azure/active-directory/hybrid/connect/how-to-connect-health-agent-install) for AD FS。
- 用于 [查看Microsoft Entra 登录的全局管理员](/zh-cn/azure/active-directory/roles/permissions-reference#global-administrator) 或 [报告读取者](/zh-cn/azure/active-directory/roles/permissions-reference#reports-reader) 角色。
- 第一个 Connect Health 代理至少有一个Microsoft Entra ID P1 或 P2 许可证。
- 对于每个额外的注册代理，25 个额外的Microsoft Entra ID P1 或 P2 许可证。
- 与在所有受监视角色（AD FS、Microsoft Entra Connect 和 Active Directory 域服务）中注册的代理总数相等的代理计数。
- 有效Microsoft Entra Connect Health 许可证的必需数目。 （无需向特定用户分配许可证。

## 登录数据报告

适用于 AD FS 的 Connect Health 代理将 AD FS 中的许多事件 ID 关联在一起，以提供有关登录请求的信息，以及请求失败时的错误详细信息。 请求信息与 Microsoft Entra 登录报表架构相关。 此信息可以显示在 Microsoft Entra 登录报表用户界面中。 除了报表之外，AD FS 数据还提供新的 Azure Monitor 工作簿模板和新的 Azure Log Analytics 流。 对于方案，可以使用和修改工作簿模板进行深入分析，例如：

- AD FS 帐户锁定。
- 密码尝试失败。
- 意外登录尝试的峰值。

可用数据镜像可用于 Microsoft Entra 登录的相同数据。有信息的五个选项卡可用，具体取决于登录类型：

- Microsoft Entra ID
- AD FS

Connect Health 关联 AD FS 中的事件，具体取决于服务器版本。 然后，它将事件与 AD FS 架构匹配。 有关详细信息，请参阅 [报表中显示的数据？](/zh-cn/azure/active-directory/hybrid/how-to-connect-health-ad-fs-sign-in#what-data-is-displayed-in-the-report)

## 配置

基本配置是自动的。 功能推出后，数据会馈送到报表中，并满足先决条件。

可以为 AD FS 登录启用 Log Analytics，并将其与任何其他 Log Analytics 集成组件（如 Microsoft Sentinel）一起使用。 有关详细信息，请参阅 [启用 Log Analytics 和 Azure Monitor](/zh-cn/azure/active-directory/hybrid/how-to-connect-health-ad-fs-sign-in#enabling-log-analytics-and-azure-monitor)。

## 基本故障排除

有关当前已知问题和限制，请参阅 [常见问题解答](/zh-cn/azure/active-directory/hybrid/how-to-connect-health-ad-fs-sign-in#frequently-asked-questions)。

### Kusto 日志记录

若要从 AD FS 登录收集登录事件，请在 Log Analytics 中运行以下 Kusto 查询。

```
unioncluster('Idsharedweu').database('ADFSConnectHealth').SignInEvent,  
cluster('Idsharedwus').database('ADFSConnectHealth').SignInEvent 
| where env_time > ago(2d)
| where tenantId == "00000000-0000-0000-0000-000000000000"
| take 15
```

## 后续步骤

阅读有关使用 Connect Health [的 Microsoft Entra ID 中的 AD FS 登录的详细信息](/zh-cn/azure/active-directory/hybrid/how-to-connect-health-ad-fs-sign-in)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/ad-dmn-services/understand-ad-fs-sign-in-events-azure-ad-connect-health)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
