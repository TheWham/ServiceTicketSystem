# 无法在适用于 Windows PowerShell 的 Azure Active Directory 模块中运行脚本

## 概要

本文介绍尝试在适用于 Windows PowerShell 的 Azure Active Directory 模块中运行脚本时收到错误消息的问题。

*原始产品版本：*Microsoft Entra ID、Microsoft Intune、Azure 备份、Office 365 用户和域管理、Office 365 标识管理  
*原始 KB 数：* 2411920

## 现象

尝试在适用于 Windows PowerShell 的 Azure Active Directory 模块Microsoft运行脚本时，会收到以下错误消息之一：

> 无法加载文件 C：\my\_script.ps1。 在此系统上禁用脚本的执行。 有关详细信息，请参阅“获取帮助about\_signing”。

> 无法加载文件 C：\Desktop\myscript.ps1，因为在此系统上禁用了正在运行的脚本。 有关详细信息，请参阅about\_Execution\_Policies。`http://go.microsoft.com/fwlink/?LinkID=135170`

> 无法加载文件 C：\my\_script.ps1。 文件 C：\my\_script.ps1 未进行数字签名。 脚本不会在系统上执行。 有关详细信息，请参阅about\_Execution\_Policies。`http://go.microsoft.com/fwlink/?LinkID=135170`

## 原因

如果以下因素之一为 true，则可能会出现此问题：

- 使用的 PowerShell 版本高于 5.1。 Azure Active Directory 模块仅适用于 PowerShell 3 到 5.1。
- 执行策略设置为 **“受限**”。 如果策略太受限，则某些 Windows PowerShell cmdlet 无法运行。

## 解决方法

若要解决此问题，请执行以下步骤：

1. 通过运行 `$PSVersionTable`来标识 PowerShell 版本。
2. 以管理员身份运行适用于 Windows PowerShell 的 Azure Active Directory 模块。 为此，请选择“开始”**，选择“**所有程序**”，选择**“Windows Azure Active Directory”，右键单击 **Windows PowerShell** 的 Windows Azure Active Directory** 模块，然后选择“**以管理员**身份**运行”。
3. 将执行策略设置为“无限制”。 若要执行此操作，请键入以下 cmdlet，然后按 Enter：

   ```
   Set-ExecutionPolicy Unrestricted
   ```
4. 运行所需的 Windows PowerShell cmdlet。
5. 将执行策略设置为 **“受限**”。 若要执行此操作，请键入以下 cmdlet，然后按 Enter：

   ```
   Set-ExecutionPolicy Restricted
   ```

## 详细信息

为了帮助提供更安全的命令行管理体验，Windows PowerShell 使用“执行策略”来控制 Windows PowerShell 的使用方式。 执行策略定义 Windows PowerShell 加载文件以供执行和配置的限制。 默认情况下，Windows PowerShell 在受限执行策略中运行。 此模式是其最安全的模式。 在此模式下，Windows PowerShell 仅作为交互式 shell 运行。

四个执行策略如下所示：

- 受限是默认执行策略。 此策略不运行脚本，并且仅交互。
- AllSigned 策略运行脚本。 所有脚本和配置文件必须由你信任的发布者签名。 确认你信任发布者后，此策略将打开运行已签名但恶意脚本的风险。
- 远程签名策略运行脚本。 从通信应用程序下载的所有脚本和配置文件必须由你信任的发布者签名。 这些通信应用程序包括Microsoft Outlook、Windows Internet Explorer、Outlook Express 和 Windows Messenger。 此策略可让你面临运行未从这些应用程序下载的恶意脚本的风险。 在这种情况下，系统不会提示你。
- 不受限制的策略运行脚本。 确认文件源自 Internet 后，从通信应用程序下载的所有脚本和配置文件都会运行。 这些通信应用程序包括 Outlook、Internet Explorer、Outlook Express 和 Windows Messenger。 无需数字签名。 此策略将打开运行从这些应用程序下载的未签名恶意脚本的风险。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/cannot-run-scripts-powershell)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
