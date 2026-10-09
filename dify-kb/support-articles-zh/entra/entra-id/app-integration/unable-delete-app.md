# 由于禁用了“删除”按钮，无法删除应用程序

## 概要

在 Microsoft Entra ID 中删除应用时，在某些情况下可能会禁用“删除”按钮。 这些方案包括：

- 对于企业应用程序下的应用程序，如果没有以下角色之一，将禁用“删除”按钮：全局管理员、云应用程序管理员、应用程序管理员或服务主体的所有者。
- 对于Microsoft应用程序，无论角色如何，都无法从 UI 中删除它们。
- 对于与托管标识对应的服务主体，无法在“企业应用”边栏选项卡中删除服务主体。 需要转到 Azure 资源来管理它。 若要了解有关托管标识的详细信息，请参阅托管标识[一文](/zh-cn/azure/active-directory/managed-identities-azure-resources/overview)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/unable-delete-app)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
