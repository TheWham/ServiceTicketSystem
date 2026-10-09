# 你未收到包含Microsoft Entra 多重身份验证的验证码的文本或语音呼叫

*原始产品版本：* 云服务（Web 角色/辅助角色）、Microsoft Entra ID、Microsoft Intune、Azure 备份、Office 365 标识管理  
*原始 KB 数：* 2834956

## 现象

假设出现了下面这种情景：

- 你是启用了 Microsoft Entra 多重身份验证（MFA）的全局管理员
- 你未收到包含验证码的短信或语音呼叫。

在此方案中，无法登录到工作或学校帐户，例如 Office 365、Azure 或 Microsoft Intune。

## 解决方法

若要解决此问题，请执行下列步骤：

1. 如果已设置其他安全验证选项，请选择 **“其他验证选项**”，然后通过选择其他选项重试。 此外，请确保用户帐户设置中的电话号码正确无误。
2. 要求另一个全局管理员确认你的电话号码是否已在用户设置中正确设置。

如果步骤 1 和步骤 2 无法解决问题，则可能阻止用户帐户使用 Microsoft Entra 多重身份验证。 若要检查用户帐户是否被阻止，请向全局管理员请求Microsoft云服务执行以下步骤：

如果有Microsoft Entra 多重身份验证或Microsoft Entra ID P1 或 P2 订阅

1. 转到[Azure 门户](https://portal.azure.com)，然后打开**Microsoft Entra ID**。
2. 如果要更改默认 Active Directory，请单击“管理租户**”**，选择该 Active Directory，然后单击“**切换**”。
3. 选择“ **用户**”，打开有问题的用户的配置文件。
4. 检查是否 **启用了阻止登录** 。 如果是，请禁用该选项。

如果你有 Office 365 且没有Microsoft Entra 多重身份验证或Microsoft Entra ID P1 或 P2 订阅，请联系 Office 365 支持部门。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/mfa/text-voice-call-verification-code-mfa-not-send)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
