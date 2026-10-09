# 用户显示为已禁用或启用Microsoft Azure 多重身份验证，但行为相反

*原始产品版本：* Active Directory  
*原始 KB 数：* 2934588

本文提供了一个解决方案，其中用户显示为已禁用或启用Microsoft Azure 多重身份验证，但行为相反。 这是预期的行为。

## 现象

### 问题 1

Microsoft启用 Azure 多重身份验证后，即使用户的行为处于启用状态，用户也可能显示为已禁用。

### 问题 2

禁用 azure 多重身份验证Microsoft时，即使用户的行为为已禁用，用户也可能显示为已启用

## 原因

如果将用户作为来宾用户添加到另一个目录中，则会出现此问题。 请考虑以下示例：

用户 John （`John@contoso.com`） 是在 . 中创建的 `contoso.onmicrosoft.com`。 这是他的主目录。 然后，John 作为来宾用户添加到来宾目录中 `fabrikam.onmicrosoft.com` 。 当检查来宾用户的管理员 `fabrikam.onmicrosoft.com` 时，该用户显示为已禁用多重身份验证。

## 解决方法

此行为是特意这样设计的。 多重身份验证行为始终基于用户的主目录状态。 如果要更改所需的多重身份验证行为，你或管理员应从用户的主目录进行此更改。

## 详细信息

来宾用户是添加到另一个目录的目录中的用户。 例如，可将来自 `contoso.onmicrosoft.com` 的用户添加到 `fabrikam.onmicrosoft.com`。 在这种情况下，用户仍使用用户主目录中定义的设置（`contoso.onmicrosoft.com`）进行身份验证。

注意

若要快速检查用户是否为来宾用户，请注意“管理多重身份验证”屏幕上用户旁边的复选框是否灰显。 灰色复选框指示用户是来宾用户。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/mfa/user-displayed-disabled-or-enabled-mfa)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
