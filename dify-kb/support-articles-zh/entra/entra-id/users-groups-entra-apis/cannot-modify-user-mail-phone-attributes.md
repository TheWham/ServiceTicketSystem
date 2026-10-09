# 无法修改用户邮件或电话号码信息

本文提供了一个解决方案，用于解决无法修改其他用户的特定个人信息（如邮件和电话号码）的问题。

## 症状

不能修改其他用户的以下用户属性：

- `mobilePhone`
- `businessPhones`/`telephoneNumber`
- `otherMails`

遇到此问题的大多数用户是服务主体（Microsoft Graph 方案）或使用客户端凭据授予类型的 Microsoft Entra 用户。 此外，他们会收到 403 错误。

## 原因

由于权限不足，因此会出现此问题。 对于 Microsoft Entra 用户， `User.ReadWrite.All` 权限可以更改用户配置文件，但三个用户属性除外。 对于服务主体（Microsoft Graph 方案），拥有 `Directory.ReadWrite.All` 权限不足以修改三个用户属性。

## 解决方案

若要解决此问题，请将支持管理员、用户管理员或全局管理员角色分配给更改三个属性的服务主体或用户，具体取决于尝试修改角色的用户。 只有三个管理员角色才能更改三个属性。

谨慎

将这三个管理员角色之一分配给服务主体或用户时，可以让他们在该级别执行任务。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/users-groups-entra-apis/cannot-modify-user-mail-phone-attributes)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
