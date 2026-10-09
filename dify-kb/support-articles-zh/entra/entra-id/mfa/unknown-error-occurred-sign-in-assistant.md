# 运行 Azure Active Directory 同步工具配置向导时出错：Microsoft Online Services 登录助手出现未知错误

## 概要

本文可帮助你解决在运行 Azure Active Directory 同步工具配置向导后，遇到的“Microsoft Online Services 登录助手”未知错误。

*原始产品版本：* 云服务（Web 角色/辅助角色）、Microsoft Entra ID、Microsoft Intune、Azure 备份、Office 365 标识管理  
*原始 KB 数：* 2502710

## 现象

运行 Microsoft Azure Active Directory 同步工具配置向导时，会收到以下错误消息：

> Microsoft Online Services 登录助手发生未知错误。 请联系支持人员。

## 解决方法

若要解决此问题，请执行以下步骤：

1. 选择“开始”**，键入，然后按 `appwiz.cpl` 打开**控制面板**中的**“程序和功能**”**项。
2. 卸载 Microsoft Online Services 登录助手。
3. 卸载 Azure Active Directory 同步工具。
4. 重新安装 Azure Active Directory 同步工具。 有关如何执行此操作的详细信息，请转到 [“安装或升级目录同步”工具](https://technet.microsoft.com/library/jj151800.aspx)。
5. 检查是否解决了问题。 如果在执行步骤 1 到 4 后仍发生此错误，请确保启动 Microsoft Online Services 登录助手服务。 为此，请按照下列步骤进行操作：

   1. 选择“开始”，键入，然后按 `services.msc`。
   2. 在服务列表中，确保启动 Microsoft Online Services 登录助手**的**“状态**”列中**的条目。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/mfa/unknown-error-occurred-sign-in-assistant)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
