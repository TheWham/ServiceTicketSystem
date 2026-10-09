# Microsoft Graph PowerShell 引发错误“IDX14102：无法解码标头”

本文提供了使用 Microsoft Graph PowerShell 时出现的错误“IDX14102：无法解码标头”的解决方案。

## 症状

运行 Microsoft Graph PowerShell 命令 `Connect-MgGraph -AccessToken $token`时，会收到以下错误：

> IDX14102：无法解码标头

## 原因

发生此错误的原因是将无效的访问令牌传递给 `AccessToken` cmdlet 的参数 `Connect-MgGraph` 。 当令牌通过 Azure PowerShell 的 `Get-AzAccessToken` cmdlet 获取并作为一个 `SecureString`传递时，通常会发生此问题。 从版本 5.0.0 开始，这一行为在 `Az.Accounts` 模块中被观察到。 从 Microsoft Graph PowerShell 版本 2.28.0 开始，该 `Connect-MgGraph` 命令仅接受纯字符串作为 `AccessToken` 参数。

## 解决方案

下面是用于解决此问题的两种解决方案：

- 确保传递给 `AccessToken` cmdlet 参数 `Connect-MgGraph` 的访问令牌有效。

  有关访问令牌的详细信息，请参阅 [Microsoft标识平台中的访问令牌](/zh-cn/entra/identity-platform/access-tokens)。
- 如果使用 `Get-AzAccessToken` cmdlet 获取访问令牌，请使用以下方法之一：

  - 将 `Az.Accounts` 降级到版本 4.2.0，以避免令牌被返回为 `SecureString`。
  - 将令牌从 `SecureString` 转换为 `String`：

    ```
    $microsoftGraphToken = Get-AzAccessToken -ResourceUrl "https://graph.microsoft.com"

    Connect-MgGraph -AccessToken (ConvertFrom-SecureString -SecureString $microsoftGraphToken.Token -AsPlainText)
    ```

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/users-groups-entra-apis/unable-to-decode-header-error)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
