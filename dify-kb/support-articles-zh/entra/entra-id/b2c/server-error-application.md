# 尝试登录到为 Azure AD B2C 设置的应用时出错：“/”应用程序中的服务器错误

本文介绍尝试登录到为 Azure AD B2C 设置的应用时发生的错误。

*原始产品版本：* Microsoft Entra ID  
*原始 KB 数：* 3092588

## 现象

尝试登录到为Microsoft Azure Active Directory（AD） 企业到使用者（B2C）设置的应用时，会收到以下错误消息：

> “/” 应用程序中的服务器错误  
> 响应状态代码不指示成功：404（找不到）  
> 说明：执行当前 Web 请求期间发生未经处理的异常。 请检查堆栈跟踪信息，以了解有关该错误以及代码中导致错误的出处的详细信息。  
> 异常详细信息：System.Net.Http.HttpRequestException：响应状态代码未指示成功：404（找不到）  
> 源错误：执行当前 Web 请求期间发生未经处理的异常。 可以使用下面的异常堆栈跟踪识别有关异常的来源和位置的信息。  
> 堆栈跟踪:  
> ...  
> [IOException： 无法从： 获取文档] `https://login.microsoftonline.com/contoso.onmicrosoft.com/.well-known/openid-configuration?p=Policyname`

## 原因

应用 Web.config 文件中可能缺少或不正确注册策略名称。

## 解决方法

若要解决此问题，请执行以下步骤：

1. 打开应用的 Web.config 文件。
2. 在 Web.config 文件中，验证应用密钥 `ida:SignUpPolicyId` 是否存在。
3. 将应用密钥的值替换为在 Azure AD B2C 管理门户中提供的注册策略的名称。

   文件的更改部分如下所示：

   ```
   <appSettings>
   <add key="ida:SignUpPolicyId" value="B2C_Signup_Policy_Name">
   </appSettings>
   ```

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/b2c/server-error-application)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
