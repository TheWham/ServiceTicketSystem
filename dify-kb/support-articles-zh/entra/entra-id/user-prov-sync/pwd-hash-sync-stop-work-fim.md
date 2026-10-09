# 在 FIM 中更新 Microsoft Entra 凭据后，密码哈希同步停止工作

## 概要

本文介绍密码哈希同步在 Azure 环境中停止工作的问题。 在 Microsoft Forefront Identity Manager（FIM）中更新全局管理员凭据后，将发生这种情况。

*原始产品版本：*Microsoft Entra ID、云服务（Web 角色/辅助角色）、Microsoft Intune、Azure 备份、Office 365 标识管理  
*原始 KB 数：* 2962509

## 现象

在 FIM 中更新全局管理员凭据进行目录同步后，密码哈希同步将停止工作。 此外，以下事件之一可能会在应用程序日志中记录事件查看器：

| 事件 ID | Source | Level | 说明 |
| --- | --- | --- | --- |
| 115 | 目录同步 | 信息 | 错误说明：拒绝访问 Windows Azure Active Directory。 请与技术支持部门联系。 |
| 0 | 目录同步 | 错误 | 用户名或密码不正确。 验证用户名，然后再次键入密码。 |
| 655 | 目录同步 | 错误 | 用户名或密码不正确。 验证用户名，然后再次键入密码。 |
| 6900 | FIMSynchronizationService | 错误 | 服务器在处理密码更改通知时遇到意外的错误： 用户名或密码不正确”的错误。 验证用户名，然后再次键入密码。 |

## 解决方法

若要解决此问题，请运行 Azure Active Directory 同步工具配置向导。 有关如何执行此操作的详细信息，请参阅 [“同步目录](/zh-cn/azure/active-directory/hybrid/whatis-hybrid-identity)”。

## 详细信息

或者，可以重启 Forefront Identity Manager 同步服务。 为此，请按照下列步骤进行操作：

1. 单击“开始**”**，指向**“管理工具**”，然后单击“**服务**”。
2. 在服务列表中，右键单击 **Forefront Identity Manager 同步服务**，然后单击“ **停止**”。
3. 右键单击 **Forefront Identity Manager 同步服务**，然后单击“ **启动**”。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/pwd-hash-sync-stop-work-fim)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
