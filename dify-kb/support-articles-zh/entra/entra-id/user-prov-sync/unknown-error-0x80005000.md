# 运行 Azure Active Directory 同步工具配置向导时出错：未知错误（0x80005000）

## 概要

本文提供了解决运行 Azure Active Directory 同步工具配置向导时收到错误消息的问题的解决方法。

*原始产品版本：*Office 365 标识管理、Microsoft Entra ID、云服务（Web 角色/辅助角色），Microsoft Intune，Azure 备份  
*原始 KB 数：* 3003331

## 现象

运行 Azure Active Directory 同步工具配置向导时，该工具将失败，并收到以下错误消息：

> 错误  
> 未知错误（0x80005000）

## 原因

如果 Azure Active Directory 同步工具配置向导无法配置域，则会出现此问题。

## 解决方法

若要解决此问题，请确保所有域控制器都处于正常状态。 若要确定哪个域或域控制器导致问题，请执行以下步骤：

1. 在安装 Azure Active Directory 同步工具的服务器上，启动 Windows PowerShell。
2. 运行以下命令：

   ```
   $Forest = [System.DirectoryServices.ActiveDirectory.Forest]::GetCurrentForest().domains
   ```

   ```
   $Forest
   ```
3. 检查输出中的信息。

   在以下示例中， `dev.contoso.com` 无法访问域。 你可以确定这一点，因为输出中缺少有关域的信息，如以下示例所示。

   ```
   Forest : contoso.com
   DomainControllers : {ContosoDC01.contoso.com}
   Children : {dev.contoso.com}
   DomainMode : Windows2008R2Domain
   Parent :
   PdcRoleOwner : ContosoDC01.contoso.com
   RidRoleOwner : ContosoDC01.contoso.com
   InfrastructureRoleOwner : ContosoDC01.contoso.com
   Name : contoso.com

   Forest :
   DomainControllers :
   Children :
   DomainMode :
   Parent :
   PdcRoleOwner :
   RidRoleOwner :
   InfrastructureRoleOwner :
   Name : dev.contoso.com
   ```
4. 调查并解决问题。 最有可能的是，托管域的域控制器未运行或不在网络中。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/unknown-error-0x80005000)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
