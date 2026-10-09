# 丢失手机或手机号码更改后无法使用 Azure 多重身份验证登录到云服务

*原始产品版本：* 云服务（Web 角色/辅助角色）、Microsoft Entra ID、Microsoft Intune、Azure 备份、Office 365 标识管理  
*原始 KB 数：* 2834954

## 现象

假设你是已启用 Azure 多重身份验证Microsoft Microsoft云服务管理员。 如果丢失手机或电话号码已更改，则无法登录到云服务帐户（如 Office 365、Azure 或 Microsoft Intune），因为未从多重身份验证服务收到短信或语音呼叫。

## 解决方法

请让另一个云服务管理员重置多重身份验证设置。 为此，管理员应执行以下步骤：

1. 以管理员身份登录到云服务门户。
2. 转到 <https://account.activedirectory.windowsazure.com/usermanagement/multifactorverification.aspx>。
3. 选中要重置其多重身份验证设置的管理员帐户的复选框。
4. 选择“管理用户设置”。
5. **选中“要求所选用户再次**提供联系人方法”复选框，然后选择“**保存**”。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/mfa/cannot-use-mfa-signin-lose-phone)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
