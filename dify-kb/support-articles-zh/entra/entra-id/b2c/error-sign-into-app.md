# 尝试登录到为 Azure AD B2C 设置的应用时发生错误

本文介绍尝试登录到为 Azure AD B2C 设置的应用时发生的错误。

*原始产品版本：* Microsoft Entra ID  
*原始 KB 数：* 3092587

## 现象

尝试登录到为Microsoft Azure Active Directory（AD） 企业到使用者（B2C）设置的应用时，会收到以下错误消息：

> 很抱歉，登录时遇到问题  
> 我们自动跟踪这些错误，但如果问题仍然存在，请与我们联系。 在此期间，请重试。  
> 管理员未提供任何联系人详细信息相关 ID：xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxx  
> Timestamp：yyyy-mm-dd hh：mm：ssZ  
> AADB2C：发生异常

## 原因

应用 Web.config 文件中可能缺少或不正确客户端 ID。

## 解决方法

若要解决此问题，请执行以下步骤：

1. 打开应用的 Web.config 文件。
2. 在 Web.config 文件中，找到应用密钥 **ida：ClientId**。
3. 将应用密钥的值替换为在 Azure AD B2C 管理门户中为应用提供的客户端 ID。

   文件的更改部分如下所示：

   ```
   <appSettings>
   <add key="ida:ClientId" value="**xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx**">
   </appSettings>
   ```

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/b2c/error-sign-into-app)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
