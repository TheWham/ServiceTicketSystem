# Microsoft Entra Connect 从其组成员身份中排除用户的主要组

*原始产品版本：* Microsoft Entra ID  
*原始 KB 数：* 4014115

## 总结

Microsoft Entra Connect 不支持主组功能。 因此，它不会查询 **PrimaryGroupID** 属性以生成用户的组成员身份。 这可能会导致仍在使用主组功能的用户出现问题。

![屏幕截图显示，Microsoft Entra Connect 不支持主组功能。](media/aad-connect-exclude-user-primary-group/primary-group.png)

为用户设置主组时，该用户将从 Active Directory 中的相应组成员身份中排除。
**而是使用该组设置 PrimaryGroupID** 属性。

例如：

1. User1 属于 Group1，这意味着 Group1 具有 User1 作为成员。
2. 主组在 User1 上从域用户更改为 Group1：
   1. User1 已从 Group1 成员中排除。
   2. User1 将添加为域管理员的成员（因为它不再是主组）。
   3. 使用 Group1 引用设置 User1 **PrimaryGroupID** 属性。

需要查询组以授予基于组成员身份的用户访问权限的程序还应查询 **PrimaryGroupID** 属性。 但是，由于组成员身份同步的复杂性，Microsoft Entra Connect 不支持 **PrimaryGroupID** 。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/exclude-user-primary-group)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
