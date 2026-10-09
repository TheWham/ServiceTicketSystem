# 运行 Azure Active Directory 同步工具配置向导时出错：用户名或密码不正确

*原始产品版本：*云服务（Web 角色/辅助角色）、Microsoft Entra ID、Microsoft Intune、Office 365 标识管理  
*原始 KB 数：* 2965539

## 现象

运行 Azure Active Directory 同步工具配置向导时，会收到以下错误消息：

> 用户名或密码不正确。

![Windows Azure 目录同步工具配置向导中错误消息的屏幕截图。](media/user-name-pwd-incorrect/user-name-pwd-incorrect-error.png)

此外，事件 ID 611 记录到应用程序日志事件查看器：

> 事件 ID：611  
> 级别：信息  
> 源：目录同步  
> 说明:  
> 域的密码同步失败： `ChildDomain.Contoso.Com`。 详细信息：Microsoft.Online.PasswordSynchronization.SynchronizationManagerException：无法打开与域的连接： `ChildDomain.Contoso.Com`。 错误：尝试查找域 `ChildDomain.Contoso.Com`的域控制器时发生异常。
> >--- Microsoft.Online.PasswordSynchronization.DirectoryReplicationServices.DrsCommunicationException：尝试查找域`ChildDomain.Contoso.Com`域控制器时发生异常。
> >--- System.Security.Authentication.AuthenticationException：用户名或密码不正确。  
> >--- System.Runtime.InteropServices.COMException：用户名或密码不正确。

## 原因

如果向导中指定的企业管理员帐户凭据在 Active Directory 林中不唯一，则会出现此问题。 多域林中两个或多个同名帐户之间的密码不匹配可能会导致向导失败。

请考虑以下示例场景：

- Contoso\admin 是在 Azure Active Directory 同步工具配置向导中指定的企业管理员帐户。
- Contoso\admin 和 Fabrikam\admin 是两个具有相同名称但存在于不同域中的帐户。
- 每个帐户都有不同的密码。

在此方案中，Contoso\admin 的密码用于配置过程中 Active Directory 林中的所有域。 例如，如果密码为“Password1”，则“Password1”用于 Fabrikam\admin。这会导致向导失败。

## 解决方法

若要解决此问题，请执行下列操作之一：

- 创建一个企业管理员帐户，其中 sAMAccountName 属性的值是唯一的，并且不存在于每个域中。
- 更新所有具有相同名称的帐户的密码，以便所有这些帐户的密码相同。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/mfa/user-name-pwd-incorrect)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
