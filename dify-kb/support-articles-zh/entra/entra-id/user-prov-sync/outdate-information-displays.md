# Microsoft Entra Connect Health 显示有关本地 Microsoft Entra Connect 服务器的旧信息

## 概要

本文讨论Microsoft Entra Connect Health 显示有关本地 Microsoft Entra Connect 服务器的过时信息的问题。

*原始产品版本：* Microsoft Entra ID  
*原始 KB 数：* 4053427

## 现象

Microsoft Entra Connect Health 边栏选项卡不再显示有关本地 Microsoft Entra Connect 服务器的最新信息（例如同步错误）。 在某些情况下，在 Microsoft Entra Connect 服务器上运行的 Microsoft Entra Connect Health Insight Service 崩溃并生成以下 Windows 应用程序事件：

> 日志名称: 应用程序  
> 源：应用程序错误  
> 日期：2017/10/19 上午 8：03：19  
> 事件 ID：1000  
> 任务类别：（100）  
> 级别：错误  
> 关键字：经典  
> 用户：无  
> 计算机：XXXXXXX  
> 说明：故障应用程序名称：Microsoft.Identity.AadConnect.Health.AadSync.Host.exe，版本：3.0.68.0， 时间戳：0x5965450e故障模块名称：ntdll.dll，版本：6.3.9600.18696，时间戳：0x59153753异常代码：0xc0000374故障偏移量：0x00000000000f1c00故障进程 ID：0x624故障应用程序开始时间：0x01d348d2403fcb09故障应用程序路径：C：\Program Files\Microsoft Azure AD Connect Health Sync Agent\Insights\Microsoft.Identity.AadConnect.Health.AadSync.Host.exe 故障模块路径：C：\Windows\SYSTEM32\ntdll.dll 报告 ID： 7eb31450-b4c5-11e7-80cb-005056ba3ca2 故障包全名：故障包相对应用程序 ID：

## 原因

如果 Microsoft Entra Connect Synchronization Service 与 Microsoft Entra Connect Health for Sync 应用程序之间存在版本不匹配，则会出现此问题。 如果在上次Microsoft Entra Connect 升级或自动升级期间，任一组件未成功升级，则可能会出现此问题。

若要验证现有Microsoft Entra Connect 服务器在两个应用程序之间是否存在版本兼容性问题，请执行以下步骤：

1. 从控制面板中的**“程序”**项获取应用程序的版本。

   ![显示版本信息的“程序”窗口的屏幕截图。](media/outdate-information-displays/synchronization-service-version.png)
2. 将版本信息与以下兼容性表进行比较：

   | 同步服务版本 | 兼容的运行状况代理版本 |
   | --- | --- |
   | 1.1.614.0（或更早版本） | 3.0.68.0 （或更早版本） 3.0.127.0 |
   | 1.1.647.0（或更高版本） | 3.0.103.0 3.0.129.0 |

## 解决方法

若要解决此问题，请使用以下任一方法。

### 方法 1

手动将 Microsoft Entra Connect 服务器升级到版本 1.1.649.0 或更高版本。 在手动升级期间，这两个应用程序都将升级到彼此兼容的版本。

有关如何升级 Microsoft Entra Connect 服务器的详细信息，请参阅以下 Azure 文章：Microsoft Entra Connect： [从以前的版本升级到最新版本](/zh-cn/azure/active-directory/connect/active-directory-aadconnect-upgrade-previous-version)

### 方法 2

将 Health Agent for Sync 手动重新安装到与安装在 Microsoft Entra Connect 服务器上的同步服务版本兼容的版本。 例如，你有一个现有的 Microsoft Entra Connect 服务器，该服务器具有同步服务版本 1.1.647.0 和 Health Agent for Sync 版本 3.0.68.0。 若要解决不兼容问题，可以重新安装 Health Agent for Sync 版本 3.0.129.0。

若要重新安装 Health Agent for Sync，请执行以下操作：

1. 确定与已安装的 Microsoft Entra Connect 同步服务版本兼容的 Health 代理版本。 如果Microsoft Entra Connect Synchronization Service 版本 1.1.647.0 或更高版本，请使用 Health Agent 版本 3.0.129.0。
2. 从以下Microsoft下载中心网站下载运行状况代理安装程序（AadConnectHealthAadSyncSetup.exe）的副本：

   [下载并安装 Microsoft Entra Connect Health 代理](/zh-cn/azure/active-directory/hybrid/how-to-connect-install-roadmap#download-and-install-azure-ad-connect-health-agent)
3. 使用具有本地管理员权限的帐户登录到 Microsoft Entra Connect 服务器。
4. 若要卸载现有版本的 Health 代理，请执行以下步骤：

   1. 转到 **控制面板>Program 和功能。** 选择 **Microsoft Entra Connect Health Agent for Sync**，然后选择“ **卸载**”。

      注意

      这将打开运行状况代理的设置窗口。
   2. 在运行状况代理的设置窗口中，选择“ **卸载**”。
   3. 卸载过程完成后，选择“ **关闭**”。
5. 若要安装兼容版本的 Health 代理，请执行以下操作：

   1. 双击下载的可执行文件。
   2. 在 **“安装”** 屏幕上，选择“ **安装**”。
   3. 安装完成后，选择“关闭” 。

      重要

      请勿选择“ **配置**”。
   4. 启动新的 PowerShell 会话。 通过运行以下 cmdlet，将已安装的 Health 代理注册到 Microsoft Entra ID：

      ```
      Register-AzureADConnectHealthSyncAgent -AttributeFiltering:$false -StagingMode:$false
      ```
   5. 系统提示输入凭据时，请提供Microsoft Entra 全局管理员凭据。
   6. 等待大约两个小时，然后验证运行状况面板是否显示有关同步的最新信息。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/outdate-information-displays)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
