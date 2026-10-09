# 无法设置 MFA，因为已注册五台设备以使用验证器应用

本文讨论如何解决无法设置多重身份验证（MFA）的方案，因为你已经注册了五台设备以使用验证器应用。

## 现象

尝试设置 MFA 时，会收到以下错误消息：

> 不能有 5 个以上的硬件令牌或验证器应用。 请删除一个或多个验证器应用，然后添加新的验证器应用。 如果需要删除硬件令牌，请联系管理员。 禁用硬件令牌将不允许添加新的验证器应用。
>
> 注册的设备过多。

## 原因

你以前使用验证器应用设置五个不同的手机或其他设备，以注册 MFA。 因此，允许的最大设备令牌数（5）已保留在目录用户对象的属性中 `StrongAuthenticationPhoneAppDetail` 。

## 解决方案 1：直接在 Web 浏览器中删除登录方法

若要删除设备令牌，可以直接在 Web 浏览器中从安全设置中删除登录方法。 但是，如果你不是管理员，或者你不是Microsoft Entra ID 的唯一管理员，则必须首先让其他人（管理员或其他管理员用户）设置在以下部分中重新注册 MFA 的要求。

### 第 1 部分：让管理员或其他管理员用户设置 MFA 重新注册要求

注意

如果你是Microsoft Entra ID 的唯一管理员，则不需要此过程。

1. 在 [Azure 门户](https://portal.azure.com)中，搜索并选择“Microsoft Entra ID”。
2. 在“Microsoft Entra 导航窗格中，找到 **”管理** “标题，然后选择” **用户**”。
3. 在Microsoft Entra 用户列表中，选择 **用户的显示名称** 。
4. 在Microsoft Entra 用户的导航窗格中，找到 **“管理** ”标题，然后选择“ **身份验证方法**”。
5. 在Microsoft Entra 用户菜单中，选择“ **要求重新注册多重身份验证**”。

### 第 2 部分：删除部分或全部登录方法

可以通过删除相应的登录方法来删除设备令牌。 执行以下步骤：

1. 若要查看登录方法，请转到 <https://aka.ms/mysecurityinfo>。

   例如，登录方法列表可能包括与电话号码关联的电话方法，以及与特定设备关联的验证器应用方法。 有关详细信息，请参阅 [Microsoft Entra ID 中提供了哪些身份验证和验证方法？](/zh-cn/azure/active-directory/authentication/concept-authentication-methods)
2. 删除列出的任意或全部五个登录方法。

   警告

   如果尝试删除 [无密码登录方法](/zh-cn/azure/active-directory/authentication/concept-authentication-passwordless)，会在包含 **“登录** 和 **取消** ”按钮的对话框中收到以下错误消息：

   > **删除验证器应用**
   >
   > 若要删除此验证器应用，需要使用双重身份验证登录。

   若要能够删除无密码登录方法，请事先设置另一种双重身份验证方法（例如电话呼叫或短信）。 然后，当你重试删除无密码登录方法时，请使用该双重身份验证方法登录。

## 解决方案 2：使用 Microsoft Graph 删除验证器应用

全局管理员可以使用 Microsoft 图形 API 删除用户的验证器应用。 在某些情况下，Microsoft图形 API 是唯一可用的解决方案（例如，如果使用安全默认值）。 若要使用此解决方案，你或全局管理员应以全局管理员身份登录到 [Graph 资源管理器](https://developer.microsoft.com/graph/graph-explorer) ，然后执行以下步骤：

1. 在 [Graph 资源管理器](/zh-cn/graph/graph-explorer/graph-explorer-features#query-area)的查询区域中，执行以下操作：

   1. 在 **HTTP 方法** 列表中，选择 **GET**。
   2. 在查询框中，输入 `https://graph.microsoft.com/beta/users/<user-principal-name>/authentication/microsoftAuthenticatorMethods`。 将用户主体名称[（UPN）的](/zh-cn/azure/active-directory/hybrid/connect/howto-troubleshoot-upn-changes)占位符替换为必须删除其身份验证应用的用户的 UPN。
   3. **选择“运行查询**”按钮。

      警告

      如果在运行查询时遇到权限错误，请按照以下步骤获取必要的权限：

      1. **选择“修改权限**”选项卡。
      2. **选择“打开权限面板**”链接。
      3. 在权限面板中，展开 **UserAuthenticationMethod** 节点，然后选择 **UserAuthenticationMethod.ReadWrite.All** 权限。
      4. 选择“ **同意** ”按钮。

      完成这些步骤后，请重试运行查询。

      在响应窗格中，“ **响应标头** ”选项卡显示显示验证器方法信息的 JSON 代码。 在以下示例代码片段中，用户与一个验证器方法的总数相关联：

   ```
   {
     "@odata.context": "https://graph.microsoft.com/beta/$metadata#users('user%40contoso.com')/authentication/microsoftAuthenticatorMethods",
     "value": [
       {
         "id": "01234567-89ab-cdef-0123-456789abcdef",
         "displayName": "SM-G973F",
         "deviceTag": "SoftwareTokenActivated",
         "phoneAppVersion": "6.2102.0762",
         "createdDateTime": null
       }
     ]
   }
   ```
2. 在响应窗格的 **“响应标头** ”选项卡中，复制并保存 `id` 要删除的每个验证器方法的属性（GUID）。
3. 在查询区域中，将 HTTP 方法设置为  输入 UPN 和验证器 GUID 以替换占位符值。
4. **选择“运行查询**”按钮。 如果此删除查询成功删除验证器应用，将显示状态消息“无内容 - 204 - <查询执行时间>”。
5. 对要删除的每个验证器应用重复步骤 2-4。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/mfa/cant-set-up-mfa-five-devices-registered)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
