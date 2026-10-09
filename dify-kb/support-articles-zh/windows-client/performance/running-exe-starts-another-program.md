# 在 Windows 7 中运行 .exe 文件时，该文件可能会启动其他程序

本文提供了针对在 Windows 7 中运行 .exe 文件时，该文件可能启动其他程序的问题的解决方案。

*适用于：* Windows 7 Service Pack 1  
*原始 KB 数：* 950505

## 现象

在 Windows 7 中运行 .exe 文件时，该文件可能会启动其他程序。 此外，.exe 文件的图标可能不会按预期显示。 还可能会从 .exe 文件或从启动的程序收到其他错误。

## 解决方法

重要

此部分（或称方法或任务）介绍了修改注册表的步骤。 但是，注册表修改不当可能会出现严重问题。 因此，按以下步骤操作时请务必谨慎。 作为额外保护措施，请在修改注册表之前先将其备份。 如果之后出现问题，您就可以还原注册表。 有关如何备份和还原注册表的详细信息，请参阅：[如何备份和还原 Windows 中的注册表](https://support.microsoft.com/help/322756)。

要解决此问题，请将 .exe 文件的文件关联的注册表子项重置回默认设置。 为此，请按照下列步骤进行操作：

1. 要打开任务管理器，请按 CTRL + SHIFT + ESC。
2. 单击“文件”，按 CTRL 并同时单击“新建任务（运行...）”。 命令提示将打开。

   ![Windows 任务管理器中“文件”菜单的“新建任务（运行...）”选项的屏幕截图。](media/running-exe-starts-another-program/new-task-run-option.png)
3. 在命令提示符处，键入“记事本”，然后按 Enter。

   ![屏幕截图显示在命令提示符处键入了记事本。](media/running-exe-starts-another-program/enter-notepad.png)
4. 将以下文本粘贴到记事本中：

   ```
   Windows Registry Editor Version 5.00

   [-HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.exe][HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.exe][HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.exe\OpenWithList][HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.exe\OpenWithProgids] "exefile"=hex(0):
   ```
5. 在“文件”菜单上，单击“另存为”。

   ![“文件”菜单下“另存为”选项的屏幕截图。](media/running-exe-starts-another-program/save-as-file.png)
6. 在“另存为类型**”列表中选择“所有文件”，然后在*“文件名**”框中键入Exe.reg***。**
7. **在**编码**列表中选择 Unicode**。 保存它并记住文件位置。

   ![将记事本文件另存为 Exe.reg 文件格式的“另存为”对话框的屏幕截图。](media/running-exe-starts-another-program/save-exe-reg-file.png)
8. 返回“命令提示符”窗口，键入 `REG IMPORT <filepath> Exe.reg`，然后按 ENTER。

   ![命令提示符中 REG IMPROT 命令的屏幕截图。](media/running-exe-starts-another-program/enter-reg-import-exe-reg-file.png)

   注意

   <filepath> 是一个占位符，用于输入Exe.reg文件位置（例如 C：\Exe.reg）。
9. 单击“是”，然后单击“确定”以响应注册表提示。
10. 从帐户注销。 然后，重新登录到帐户。

注意

- 可能需要重启计算机才能将程序图标还原到其原始外观。
- 问题解决后，删除 Exe.reg 文件，以免日后错误地将其添加回注册表。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/running-exe-starts-another-program)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
