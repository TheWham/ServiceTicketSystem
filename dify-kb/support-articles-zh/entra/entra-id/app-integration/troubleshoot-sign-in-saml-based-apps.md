# 登录到基于 SAML 的单一登录配置应用时出现问题

## 概要

本文提供有关解决登录到基于 SAML 的单一登录配置应用时遇到的问题的指南。

## 决议

若要排查这些登录问题，建议执行以下作来更好地诊断并自动执行解决步骤：

- 安装 [我的应用 Secure Browser 扩展](/zh-cn/azure/active-directory/manage-apps/my-apps-deployment-plan)，以帮助Microsoft Entra ID，以在Azure 门户中使用测试体验时提供更好的诊断和解决方法。
- 使用 Azure 门户的应用配置页中的测试体验重现该错误。 详细了解 [如何调试基于 SAML 的单一登录应用程序](/zh-cn/azure/active-directory/manage-apps/debug-saml-sso-issues)

如果将 Azure 门户中的测试 [体验](/zh-cn/azure/active-directory/manage-apps/debug-saml-sso-issues) 与“我的应用安全浏览器扩展”配合使用，则无需手动执行以下步骤即可打开基于 SAML 的单一登录配置页。

若要打开基于 SAML 的单一登录配置页，请执行以下作：

1. 打开[**Azure 门户**](https://portal.azure.com/)，以全局管理员**或 **Coadmin** 身份**登录。
2. **通过选择**左侧主导航菜单顶部的所有服务**，打开Microsoft Entra 扩展**。
3. **在筛选器搜索框中键入“Microsoft Entra ID”**，然后选择**Microsoft Entra ID** 项。
4. **从“Microsoft Entra 左侧导航菜单中选择企业应用程序**。
5. 选择“所有应用程序”，查看所有应用程序的列表。

   如果看不到要在此处显示的应用程序，请使用**“所有应用程序列表**”顶部的**“筛选器”**控件，并将“**显示**”选项设置为**“所有应用程序**”。
6. 选择要为单一登录配置的应用程序。
7. 加载应用程序后， **从应用程序的左侧导航菜单中选择“单一登录** ”。
8. 选择“基于 SAML 的 SSO”。

## 常规故障排除

### 自定义发送到应用程序的 SAML 声明时出现问题

若要了解如何自定义发送到应用程序的 SAML 属性声明，请参阅 [Microsoft Entra ID](/zh-cn/azure/active-directory/develop/active-directory-claims-mapping) 中的声明映射。

### 与应用配置错误相关的错误

确认门户中的配置与应用中的配置相匹配。 具体而言，比较客户端/应用程序 ID、回复 URL、客户端密码/密钥和应用 ID URI。

将在代码中请求访问的资源与“所需资源”选项卡中的已配置权限进行比较，确保仅请求已配置的资源。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/troubleshoot-sign-in-saml-based-apps)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
