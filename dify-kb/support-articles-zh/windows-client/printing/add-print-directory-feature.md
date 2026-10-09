# 如何向 Windows 资源管理器添加打印目录功能

本文介绍如何添加打印目录功能，以及如何从 Windows 资源管理器内部打印目录列表。

_适用于：_ &nbsp; Windows 10 - 所有版本, Windows Vista  
_原始 KB 编号：_ &nbsp; 272623

## 摘要

有关如何在 Windows XP、Windows Vista 或 Windows 7 中为文件夹添加打印目录功能的更多信息，请单击以下文章编号以查看 Microsoft 知识库中相应的文章：[321379](https://support.microsoft.com/help/321379) 如何在 Windows XP、Windows Vista 或 Windows 7 中为文件夹添加打印目录功能

## 更多信息

要向 Windows 资源管理器添加打印目录功能，请按照下列步骤操作：

### 步骤 1：创建 Printdir.bat 文件

为此，请按照下列步骤操作：

1. 单击**开始**，单击**运行**，键入 *notepad*，然后单击**确定**。
2. 将以下文本粘贴到记事本中：

    ```console
    @echo off  
    dir %1 /-p /o:gn > "%temp%\Listing"  
    start /w notepad /p "%temp%\Listing"  
    del "%temp%\Listing"  
    exit
    ```

3. 在**文件**菜单上，单击**退出**，然后单击**是**保存更改。
4. 在**另存为**对话框中，在**文件名**框中键入以下文本，然后单击**保存**：%windir%\\Printdir.bat  
> **备注**
> 如果收到对话框提示你没有权限在此位置保存，可以将文件保存到桌面。然后单击**开始**，单击**运行**，键入 *%windir%*，再单击**确定**。之后，你可以将该文件从桌面复制到此位置。

### 步骤 2：编辑注册表
> **重要**
> 本节、方法或任务包含的步骤会告诉你如何修改注册表。但是，如果修改注册表不当，可能会出现严重问题。因此，请务必仔细按照这些步骤操作。为了加强保护，请先备份注册表再进行修改。这样，如果出现问题，你可以还原注册表。有关如何备份和还原注册表的更多信息，请单击以下文章编号以查看 Microsoft 知识库中相应的文章：[322756](https://support.microsoft.com/help/322756) 如何在 Windows 中备份和还原注册表

1. 单击**开始**，单击**运行**，键入 *Notepad*，然后单击**确定**。
2. 在记事本中键入以下命令。

    ```registry
    Windows Registry Editor Version 5.00

    [HKEY_CLASSES_ROOT\Directory\Shell]
    @="none"

    [HKEY_CLASSES_ROOT\Directory\Shell\Print_Directory_Listing]
    @="Print Directory Listing"

    [HKEY_CLASSES_ROOT\Directory\shell\Print_Directory_Listing\command]
    @="Printdir.bat \"%1\""

    [HKEY_CLASSES_ROOT\SOFTWARE\Classes\Directory]
    "BrowserFlags"=dword:00000008

    [HKEY_CLASSES_ROOT\SOFTWARE\Classes\Directory\shell\Print_Directory_Listing]
    @="Print Directory Listing"

    [HKEY_CLASSES_ROOT\SOFTWARE\Classes\Directory\shell\Print_Directory_Listing\command]
    @="Printdir.bat \"%1\""

    [HKEY_CURRENT_USER\Software\Microsoft\Windows\Shell\AttachmentExecute\{0002DF01-0000-0000-C000-000000000046}]
    @=""

    [HKEY_CLASSES_ROOT\SOFTWARE\Classes\Directory]
    "EditFlags"="000001d2"
    ```

    在**文件**菜单上，单击**另存为**。
3. 在**保存位置**列表中，单击**桌面**。
4. 在**文件名**框中键入 *PrintDirectoryListing.reg*，在**保存类型**列表中单击**所有文件**，然后单击**保存**。
5. 在桌面上双击 LoggingOn.reg 文件，将注册表项添加到 Windows 注册表。
6. 在消息框中单击**确定**。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/printing/add-print-directory-feature)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权，本文档为社区中文翻译）
