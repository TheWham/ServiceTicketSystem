# 尝试删除 Microsoft Entra ID 中的 B2C 目录时出错：无法删除“<contoso>”

本文介绍尝试在 Microsoft Entra ID 中删除 B2C 目录时发生错误的问题。

*原始产品版本：* Microsoft Entra ID  
*原始 KB 数：* 3112170

## 现象

在Microsoft Entra 环境中，设置 B2C 目录，然后尝试删除它。 但是，你会收到以下错误消息：

> 无法删除“<contoso>”  
> 以下问题阻止删除目录：  
> 目录包含由用户或管理员添加的一个或多个应用程序

## 原因

如果现有的 B2C 应用程序服务主体（例如 CPIM、Ibiza 门户和 SSPR）阻止删除，则会出现此问题。

## 解决方法

若要解决此问题，请使用Azure 门户。

### 步骤 1：删除 Azure AD B2C 仪表板中列出的所有应用

为此，请按照下列步骤进行操作：

1. 以有权访问 Azure AD B2C 目录的管理员身份登录[Azure 门户](https://portal.azure.com/)。
2. 在右上角选择显示名称，然后选择 B2C 目录的目录。

   注意

   如果只有一个目录，则已选择 Azure AD B2C 目录。
3. 若要查找 Azure AD B2C 边栏选项卡，请选择左下角的“更多服务**”>**按钮，然后搜索“B2C”。
4. 选择 **Azure AD B2C**。
5. 选择 **“所有设置”**，然后选择“ **应用程序**”。

   ![应用程序设置的屏幕截图。](media/cannot-delete-directory/applications-in-azure-ad-b2c.png)
6. 删除所有应用程序。 为此，请选择应用程序，选择“属性**”**，然后选择“**删除**”按钮。

   ![屏幕截图显示如何删除应用。](media/cannot-delete-directory/delete-applications.png)

### 步骤 2：删除 Azure AD B2C 租户

为此，请按照下列步骤进行操作：

1. 在 Azure AD B2C 目录中，找到并选择**Azure 门户中的Microsoft Entra ID** 边栏选项卡。
2. 在“ **概述** ”菜单上，选择“ **删除目录**”。
3. 按照门户中的说明操作。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/b2c/cannot-delete-directory)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
