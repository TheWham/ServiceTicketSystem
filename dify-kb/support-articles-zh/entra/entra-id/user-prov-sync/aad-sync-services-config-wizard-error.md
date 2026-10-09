# 错误：运行 Azure Active Directory 同步服务配置向导时80070005

## 概要

本文提供有关在运行 Azure Active Directory 同步服务配置向导时解决错误80070005的指导。

*原始产品版本：*Microsoft Entra ID、Microsoft Intune、Azure 备份、Office 365 标识管理  
*原始 KB 数：* 2988408

## 现象

运行 Azure Active Directory Sync （Azure AD Sync） 服务配置向导时，会收到以下消息：

> 从计算机中检索具有 CSLID {...} 的远程组件的 COM 类工厂...由于出现以下错误，失败：80070005

## 原因

如果不是本地计算机上的 ADSyncAdmins **组的成员**，或者刚刚安装了 Azure AD 同步服务，则可能会出现此问题。

## 解决方法

若要解决此问题，请注销，然后登录到计算机。 如果问题仍然存在，请执行以下步骤：

1. 选择“开始**”**，在`compmgmt.msc`搜索框中键入，然后按 Enter 打开计算机管理。
2. 在“计算机管理”下**，展开**“本地用户和组**”，然后展开“**组**”。**
3. 确保 **ADSyncAdmins** 组存在。 如果缺少此组，请创建新组并将其命名为 **ADSyncAdmins**。
4. 将自己添加到 **ADSyncAdmins** 组。
5. 注销，然后再次登录到计算机。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/aad-sync-services-config-wizard-error)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
