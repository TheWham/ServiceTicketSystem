# 联盟域中的用户在 Office 2013 应用程序中看到黄色感叹号

## 概要

本文介绍联合域中未同步到 Microsoft Entra ID 的用户在 Office 2013 应用程序中看到黄色感叹号的问题。

*原始产品版本：* Microsoft Entra ID、Office Professional 2013、Office Standard 2013  
*原始 KB 数：* 3158020

## 现象

当处于联合域中但未同步到 Microsoft Entra ID 的用户打开 Office 2013 应用程序时，他们会看到黄色感叹号。

## 原因

默认情况下，Office 2013 使用 Microsoft Online Services 登录助手（也称为 IDCRL）。 IDCRL 检测到用户的域是联合的，因此尝试对用户进行身份验证以Microsoft Entra ID。 由于用户未同步到 Microsoft Entra ID，因此用户不存在于 Microsoft Entra ID 中，这会触发 Office 2013 应用程序中的黄色感叹号。

## 解决方法

执行以下操作之一。

### 将 SignInOptions 注册表项值设置为 3

重要

请认真遵循本部分所述的步骤。 如果注册表修改不正确，可能会发生严重问题。 在修改注册表之前，请[备份注册表](https://support.microsoft.com/help/322756)，以便在出现问题时可以还原。

注意

仅将此过程用于未同步到 Microsoft Entra ID 的用户。 对同步用户使用此过程可能会导致这些用户遇到登录失败。

若要仅针对未同步到 Microsoft Entra ID 的用户解决此问题，请执行以下步骤：

1. 依次选择“开始”、“运行”，键入 **regedit**，然后选择“确定”。
2. 找到以下注册表子项： `HKEY_CURRENT_USER\Software\Microsoft\Office\15.0\Common\SignIn\`
3. 右键单击 **SignInOptions** 注册表项，选择“修改**”**，**在**“值”数据**框中键入 3**，然后选择“**确定**”。
4. 退出注册表编辑器。 将 **SignInOptions** 注册表项设置为 **3** 会强制 Office 2013 仅针对用户的本地 Active Directory 服务进行身份验证，而不是尝试将用户登录到 Microsoft Entra ID。

### 使用 Office 2016

Office 2016 应用程序中未显示黄色感叹号。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/yellow-exclamation-mark-office2013)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
