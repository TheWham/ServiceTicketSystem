# 登录到为 Azure B2C 设置的应用时，会出现异常

*原始产品版本：* Microsoft Entra ID  
*原始 KB 数：* 3092592

## 现象

尝试注册或登录为 Microsoft Azure B2C 设置的应用时，会收到以下错误消息：

> “/” 应用程序中的服务器错误”
>
> 响应状态代码不指示成功：404（找不到）
>
> 说明：执行当前 Web 请求期间发生未经处理的异常。 请检查堆栈跟踪信息，以了解有关该错误以及代码中导致错误的出处的详细信息。
>
> 异常详细信息：System.Net.WebException：远程服务器返回错误。 404（未找到）
>
> 源错误:  
> 第 106 行： {  
> 第 107 行： ...  
> 第 108 行：OpenIdConnectConfiguration config = await mgr。GetConfigurationAsync（）;  
> 第 109 行： ...  
> 第 110 行： }

## 原因

如果 **应用的 web.config 文件中缺少或缺少密码重置或用户配置文件的策略名称** 设置，则会出现此问题。

## 解决方法

若要解决此问题，请执行以下步骤：

1. 打开应用的 web.config 文件。
2. 在此文件中，验证以下内容：

   - 存在 ida：SignInPolicyId 应用密钥，并且已将该值替换为在 Azure B2C 管理门户中提供的登录策略的名称。
   - 存在 ida：PasswordResetPolicyId 应用密钥，并且已将该值替换为在 Azure B2C 管理门户中提供的登录策略的名称。
   - ida：UserProfilePolicyId 应用密钥存在，并且已将该值替换为在 Azure B2C 管理门户中提供的登录策略的名称。

   web.config 文件应如下所示：

   ```
   <appSettings>
   ...
   <add key="ida:SignInPolicyId" value="B2C_Signin_Policy">
   <add key="ida:PasswordResetPolicyId" value="B2C_PasswordReset_Policy">
   <add key="ida:UserProfilePolicyId" value="B2C_UserProfile_Policy">
   ...
   </appSettings>
   ```

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/b2c/server-error-application-exception)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
