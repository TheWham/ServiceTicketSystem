# Microsoft Entra 诊断日志

*原始产品版本：* Microsoft Entra ID  
*原始 KB 数：* 4494802

若要排查与 Microsoft Entra ID 相关的问题，Microsoft 支持部门和 Microsoft Entra 工程团队可以查看和下载与 Microsoft Entra 租户和本地配置关联的诊断日志。 Microsoft 可能会访问（或临时复制）数据，以协助解决您的支持事件。

## 详细信息

下表说明了与 Microsoft Entra 租户关联的数据类型，在排查支持事件时可能会访问这些数据。 此外，您可能需要提供来自您公司的本地环境的相同类型的数据。 根据你的租户，此信息可能会自动上传到 Microsoft Entra 服务，或者由Microsoft 支持部门工程师请求，以帮助排查支持事件。

| **类型** | **描述** |
| --- | --- |
| Microsoft Entra 对象 | 在 Microsoft Entra 租户中维护或从 Active Directory 本地环境同步的信息，例如租户、用户、组、设备和相关元数据。 |
| 服务配置 | 与 Azure 租户相关的租户配置和设置 |
| Microsoft Entra 审核和登录日志 | 登录日志、审计日志、设备注册日志、之前上传的数据（如 Authenticator App 日志）以及与运行状况相关的遥测。    **注意** 系统生成的日志包含有关最终用户的可识别信息，例如用户名。 遥测主要包含假名数据，例如系统生成的唯一标识符。 这些数据本身不能识别个人。 但是，它可用于向用户提供企业服务。 |

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/ad-dmn-services/support-data-collection-diagnostic-logs)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
