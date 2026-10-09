# 在 Windows Server 2019 上安装 Microsoft Entra Connect 后出现表值参数错误

## 概要

本文介绍在基于 Windows Server 2019 的服务器上安装 Microsoft Entra Connect 后出现同步错误的问题。

*原始产品版本：* Microsoft Entra ID、Windows Server 2019

## 现象

遇到一个或多个各种症状，例如密码哈希同步失败或在导入周期期间收到“暂存错误”发现错误（如以下屏幕截图所示）。

![同步服务管理器的屏幕截图，其中显示了暂存错误。](media/tvp-errors-when-aadconnect-installed-on-windows-server-2019/sync-service-manager-error.png)

出现此问题时，事件 ID 6301 记录在服务器应用程序日志中，如下所示：

> 日志名称: 应用程序  
> 源: ADSync  
> 日期：2019/8/22 下午 11：11：17  
> 事件 ID：6301  
> 任务类别：服务器  
> 级别： 错误  
> 关键字：经典  
> 用户： 空值  
> 计算机：AADConnect.contoso.com  
> 说明：服务器在同步引擎中遇到意外错误：
>
> “保释： MMS（7996）： ..\sql.cpp（7524）： 0x80004005 > （未指定错误）  
> `**`BAIL： MMS（7996）： x：\bt\1011518\repo\src\dev\sync\server\sqlstore\rcvtvp.h（158）： 0x80004005 （未指定错误）`**`  
> `**`BAIL： MMS（7996）： x：\bt\1011518\repo\src\dev\sync\server\sqlstore\rcvtvp.h（52）： 0x80004005 （未指定错误）`**`  
> 保释： MMS（7996）： ..\sproc.cpp（1124）： 0x80004005 （未指定错误）  
> 保释： MMS（7996）： ..\csobj.cpp（15789）： 0x80004005 （未指定错误）  
> 保释： MMS（7996）： ..\tower.cpp（10511）： 0x80004005 （未指定错误）  
> BAIL： MMS（7996）： x：\bt\1011518\repo\src\dev\sync\server\sqlstore\csobj.h（1379）： 0x80004005 （未指定错误）  
> 保释： MMS（7996）： ..\csobj.cpp（1368）： 0x80004005 （未指定错误）  
> 保释： MMS（7996）： ..\nscsimp.cpp（531）： 0x80004005 （未指定错误）  
> 保释： MMS（7996）： ..\syncstage.cpp（923）： 0x80004005 （未指定错误）  
> 保释： MMS（7996）： ..\syncstage.cpp（1666）：0x80004005（未指定错误）  
> 保释： MMS（7996）： ..\syncstage.cpp（414）： 0x80004005 （未指定错误）  
> Azure AD Sync 1.5.45.0”

此事件指示Microsoft Entra Connect 使用表值参数尝试对 LocalDB 数据库执行读取或写入操作时发生错误。

有关表值参数的详细信息，请参阅[使用表值参数（数据引擎）](/zh-cn/sql/relational-databases/tables/use-table-valued-parameters-database-engine?text=Table-valued%20parameters%20are%20declared,temporary%20table%20or%20many%20parameters)。

## 原因

此问题是由不支持 Unicode 的程序的不兼容语言设置引起的。

![选择了“使用 Unicode U T F 8 进行全球语言支持”选项的区域设置的屏幕截图。](media/tvp-errors-when-aadconnect-installed-on-windows-server-2019/region-settings-unicode.png)

启用服务帐户时，该服务帐户默认为 UTF-8，以支持全球语言。 Windows Server 2019 中的 LocalDB 数据库版本不支持此格式。

## 解决方法

若要解决此问题，请清除 Beta 版旁边的 **复选框：将 Unicode UTF-8 用于全球语言支持** （如上一屏幕截图所示），然后重启服务器。

若要更改设置，请执行以下步骤：

1. 在 Microsoft Entra Connect 服务器上，打开控制面板，然后选择**时钟、语言和区域**。

   ![控制面板的屏幕截图，其中选择了“时钟”、“语言”和“区域”选项。](media/tvp-errors-when-aadconnect-installed-on-windows-server-2019/control-panel-clock-language.png)
2. 选择“区域”。

   ![“时钟”、“语言”和“区域”页的屏幕截图，其中选择了“区域”项。](media/tvp-errors-when-aadconnect-installed-on-windows-server-2019/control-panel-region.png)
3. **选择“管理**”选项卡，然后选择“**更改系统区域设置**”。

   ![“区域”对话框的“管理”选项卡的屏幕截图，其中突出显示了“非 Unicode 程序的语言”区域。](media/tvp-errors-when-aadconnect-installed-on-windows-server-2019/administrative-tab.png)
4. **如果启用了“使用 Unicode UTF-8 进行全球语言支持**设置”，请清除它。

   ![未选中使用 Unicode U T F 8 进行全球语言支持的区域设置的屏幕截图。](media/tvp-errors-when-aadconnect-installed-on-windows-server-2019/clear-region-settings-unicode.png)
5. 选择“确定**”**，然后重启服务器。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/tvp-errors-when-AADConnect-installed-on-Windows-Server-2019)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
