# 排查Microsoft 365 管理中心中的管理员密码重置问题

本文介绍管理员在Microsoft 365 管理中心中重置用户密码后发生的密码写回问题。

## 现象

最近有管理员重置其密码的用户无法使用新密码登录到本地 Active Directory。 此外，以前的密码可能仍然有效。

## 原因

管理员已重置Microsoft 365 管理中心[用户](https://admin.microsoft.com)的密码。 尽管用户可以使用新密码联机登录，但新密码不会同步回本地 Active Directory。

目前，Microsoft 365 管理中心不使用自助密码重置（SSPR）和密码写回库。 当管理员在Microsoft 365 管理中心中重置用户密码时，密码会重置为 Microsoft Entra ID，但在本地 Active Directory中不会更新新密码。 因此，用户密码现在在 本地 Active Directory 与 Microsoft Entra ID 之间处于同步状态。

## 解决方案

若要确保密码写回更新本地 Active Directory中的新密码，更改或重置密码的管理员必须使用[Azure 门户](https://portal.azure.com)而不是[Microsoft 365 管理中心](https://admin.microsoft.com)。

有关详细信息，请参阅 [自助式密码重置写回在 Microsoft Entra ID 中的工作原理？](/zh-cn/azure/active-directory/authentication/concept-sspr-writeback)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/password-writeback-microsoft-365-admin-center)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
