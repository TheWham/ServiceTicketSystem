# 升级Microsoft Entra Connect 时出错：无法安装同步服务

*原始产品版本：* Office 365 标识管理，Microsoft Entra ID  
*原始 KB 数：* 4054462

## 概要

本文提供有关在尝试升级 Microsoft Entra Connect 时解决错误代码 1603 和 `Unable to install the synchronization service` 事件日志中的错误的指导。

## 现象

尝试升级 Microsoft Entra Connect 时，会收到以下错误消息：

> 从 Azure Active Directory 同步升级时出错。无法升级同步服务。 有关更多详细信息，请参阅事件日志。

详细的事件日志如下所示：

> Date/Time[ 12] [INFO ] ServiceControllerProvider： StartService status： Running Date/Time[ 12] [ERROR] sync engine upgrade 期间出错。 System.Exception：无法升级同步服务。 有关更多详细信息，请参阅事件日志。
> >--- Microsoft.Azure.ActiveDirectory.Client.Framework.ProcessExecutionFailedException：安装 msi 包“同步Service.msi”时出错。 完整日志位于“C：\ProgramData\AADConnect\Synchronization Service\_Install-DateTime.log”。
>
> 操作 startTime：DetectServiceAccount。
> CustomAction DetectServiceAccount 返回了实际错误代码 1603（请注意，如果沙盒内部发生翻译，这可能不是 100% 准确）操作结束时间：DetectServiceAccount。 返回值 3。
> Action endedTime： INSTALL. 返回值 3。
> MSI （s） （14：AC）时间：注意：1：1708 MSI（s） （s） （14：AC）时间：产品：Microsoft Entra Connect 同步服务 -- 安装操作失败。
> MSI （s） （14：AC）时间：Windows Installer 安装了该产品。 产品名称：Microsoft Entra Connect 同步服务。 产品版本：1.1.614.0。 产品语言：1033。 制造商：Microsoft公司。 安装成功或错误状态：1603。
> MSI （s） （14：AC）时间：延迟清理包/文件（如果有存在 MSI（s） （s） （14：AC）时间：MainEngineThread 返回 1603 MSI （s） （s） （14：80）时间：重启管理器：会话已关闭。

## 原因

基础服务帐户是使用用户主体名称（UPN）而不是 Domain\SamAccountName 配置的。

## 解决方法

若要解决此问题，请执行以下步骤：

1. 在 Microsoft Entra Connect 服务器上启动服务控制台。
2. **找到Microsoft Azure AD Sync** 服务，然后右键单击该服务。
3. 选择**属性**，然后选择**登录**。
4. 使用 Domain\SamAccountName 而不是使用 UPN 设置帐户。
5. 选择“**应用**”和“**确定**”。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/upgrade-fails-error-code-1603)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
