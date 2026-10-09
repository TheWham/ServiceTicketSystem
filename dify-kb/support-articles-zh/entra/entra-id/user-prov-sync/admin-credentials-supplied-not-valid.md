# 尝试运行 Azure Active Directory 同步工具配置向导时出错：你提供的企业管理员凭据无效

## 概要

本文可帮助你解决“你提供的企业管理员凭据无效”。 提供有效的凭据，然后重试。”这是您运行 Microsoft Azure Active Directory 同步工具配置向导后遇到的消息。

*原始产品版本：* 云服务（Web 角色/辅助角色）、Microsoft Entra ID、Microsoft Intune、Azure 备份、Office 365 标识管理  
*原始 KB 数：* 2386471

## 现象

尝试运行 Microsoft Azure Active Directory 同步工具配置向导时，会收到以下错误消息：

> 你提供的企业管理员凭据无效。 提供有效的凭据，然后重试。

## 原因

如果在目录同步工具配置向导的“Active Directory 凭据”页上输入了不正确的凭据，则可能会出现此问题。

## 解决方法

若要解决此问题，请执行以下步骤：

1. 请确保为具有公司本地 Active Directory 安装的企业管理员权限的帐户提供凭据。
2. 请确保为用户帐户输入正确的用户名和密码。
3. 确保安装目录同步工具配置向导的计算机可以与公司的域控制器通信，并且可以向本地 Active Directory 进行身份验证。

注意

帐户必须在运行目录同步工具配置向导的计算机加入到的 Active Directory 林中具有企业管理员权限。

若要检查帐户是否具有企业管理员权限，请执行以下步骤：

1. 在安装了 Windows Server 管理工具包的域控制器或计算机上，启动Active Directory 用户和计算机。 为此，请单击“开始”，单击“运行**”**，在**“打开**”框中键入 dsa.msc，然后单击“**确定**”。

   ![键入了 dsa.msc 的“运行”窗口的屏幕截图。](media/admin-credentials-supplied-not-valid-aad-sync/run-dsa-msc.png)
2. 右键单击域，然后单击“ **查找**”。

   ![右键单击域的屏幕截图，然后单击“查找”项。](media/admin-credentials-supplied-not-valid-aad-sync/domain-find.png)
3. 在 **“名称** ”框中，键入企业管理员，然后单击“ **立即**查找”。

   ![在“名称”框中键入企业管理员的屏幕截图，然后单击“立即查找”选项。](media/admin-credentials-supplied-not-valid-aad-sync/type-name-find-now.png)
4. 双击 **“企业管理员**”，然后单击“ **成员** ”选项卡。

   ![企业管理员属性窗口中的“成员”选项卡的屏幕截图。](media/admin-credentials-supplied-not-valid-aad-sync/enterprise-admins-properties.png)
5. 检查用户是否在“成员**”**列表中列出。 如果用户不在列表中，则此列表的成员之一必须登录并将用户添加到此列表中。 或者，此列表的成员可以在目录同步工具配置向导中使用其凭据。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/admin-credentials-supplied-not-valid)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
