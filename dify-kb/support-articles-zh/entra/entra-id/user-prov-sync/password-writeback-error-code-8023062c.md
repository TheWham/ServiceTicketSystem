# 排查错误代码 8023062C：不安全的密码重置或更改

本文介绍如何排查Microsoft Entra Connect 尝试在不安全的配置中更改密码或重置密码时发生的密码写回错误。 这种情况特别发生在Microsoft Entra Connect 尝试进行密码更改或重置，而无需建立 128 位传输层安全性（TLS）或安全套接字层（SSL）连接。

## 现象

当用户或管理员尝试在 Microsoft Entra ID 中更改或重置密码时，本地目录的密码写回将失败，并返回“8023062C（0x8023062c）”错误代码和以下错误消息：

> 无法设置密码，因为服务器未配置为不安全的密码设置，或者需要 128 位 TLS 或 SSL 连接。

## 原因

[Microsoft Entra Connect](/zh-cn/azure/active-directory/hybrid/how-to-connect-install-roadmap) 已配置为不要求对轻型目录访问协议（LDAP）流量进行签名和加密。

## 解决方案

按照以下步骤在 **Synchronization Service Manager 中的三个位置启用“签名和加密 LDAP 流量** ”设置：

1. 打开“同步服务管理器”。 为此，请打开 **“开始** ”菜单，转到 **“Microsoft Entra Connect** 组，然后选择” **同步服务**”。
2. **选择“连接器**”选项卡，然后选择适用的 Active Directory 连接器。 在**操作**窗格中，选择**属性**。
3. 在“属性**”对话框左侧**，选择“**连接到 Active Directory 林**”，然后选择“**选项”**按钮。 在 **“连接选项** ”对话框中，打开“ **登录和加密 LDAP 流量**”，然后选择“ **确定**”。
4. 在“属性**”对话框左侧**，选择“**配置目录分区**”。 然后，在 **“配置目录分区** ”窗格中，从列表中选择目录分区。
5. 在 **域控制器连接设置** 组中，选择“ **选项”** 按钮。 在 **“连接选项** ”对话框中，打开“ **登录和加密 LDAP 流量**”，然后选择“ **确定**”。
6. 在**“凭据**”组中，检查是否选择了此目录分区**选项的**备用凭据。 如果未选择该选项，请转到步骤 8。 否则，请选择“**设置凭据”按钮，然后在“凭据****”对话框中选择“**选项****”。
7. 在 **“连接选项** ”对话框中，打开“ **登录和加密 LDAP 流量**”，然后选择“ **确定** ”两次以返回到 **“属性** ”对话框。
8. 选择“确定**”**保存更改并返回到 Synchronization Service Manager。
9. 选择“开始”，输入 *services.msc*，然后选择“服务**”**管理单元。
   **从服务列表中选择Microsoft Azure AD Sync**，然后选择“重启服务**”**图标。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/password-writeback-error-code-8023062c)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
