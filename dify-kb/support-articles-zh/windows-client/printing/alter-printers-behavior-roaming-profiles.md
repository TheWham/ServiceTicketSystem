# 如何更改随漫游配置文件漫游的打印机的行为

本文介绍如何更改随漫游配置文件漫游的打印机的行为。

_适用于：_ &nbsp; Windows 10 - 所有版本  
_原始 KB 编号：_ &nbsp; 304767
> **重要**
> 本文包含有关修改注册表的信息。在修改注册表之前，请务必备份注册表，并确保了解如何在出现问题时还原注册表。有关如何备份、还原和编辑注册表的信息，请单击以下文章编号以查看 Microsoft 知识库中相应的文章：
>
> [256986](https://support.microsoft.com/help/256986) Microsoft Windows 注册表说明

## 摘要

按照设计，当用户使用漫游配置文件时，该用户的默认打印机会随用户配置文件漫游。但是，在某些环境中这可能不是期望的行为。本文提供了可用于更改此行为的方法。

## 更多信息
> **警告**
> 注册表编辑器使用不当可能会导致严重问题，可能需要重新安装操作系统。Microsoft 无法保证可以解决因注册表编辑器使用不当而导致的问题。使用注册表编辑器的风险由你自己承担。
> **重要**
> 本文中的信息专为企业管理员设计。在你的环境中使用本文所述的任何方法之前，应在测试环境中对该方法进行充分测试。

打印机被设计为随用户的漫游配置文件漫游，这就是默认打印机存储在注册表 HKEY_CURRENT_USER 分支下的原因。要更改此行为，请使用以下任一方法。

### 方法 1

导出已安装打印机的默认打印机设置，然后在用户登录计算机时将该设置合并到用户配置文件中：

1. 使用注册表编辑器（Regedit.exe）导出以下注册表项：

    `HKEY_CURRENT_USER\Software\Microsoft\Windows NT\CurrentVersion\Windows`

2. 用文本编辑器修改你在步骤 1 中生成的注册表（.reg）文件，使该项下只保留以下注册表值名称：

    "Device"=...
> **备注**
    > 注册表文件底部应包含一个空行。
3. 使用注册表编辑器（Regedit.exe）在以下注册表项下添加新的 ResetPrinter 字符串值：

    `HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\Run`

4. ResetPrinter 值的值应类似于以下内容：

    REGEDIT.EXE -S *path*\\*File.reg*  
    其中 *File.reg* 是你用于存储默认打印机设置的文件名。

### 方法 2

如果某个特定区域的计算机具有相似的计算机名，你可以使用 .vbs 脚本文件来匹配计算机名中的特定字符集，并安装相应的打印机。本方法包含的示例代码只要求你修改 IF 行。例如，代码中的第一条 IF 语句的含义是"如果计算机名包含文本 LAB1-，则将默认打印机设置为 \\\\LAB1\\LaserJet"。完成本方法的步骤：

1. 将以下示例 VBS 代码复制到一个 .vbs 文件中，例如 Defaultprinter.vbs：

    ```vbs
    Option Explicit
    DIM RegEntry, ComputerName

    RegEntry="HKLM\SYSTEM\CurrentControlSet\Control\ComputerName\ComputerName\ComputerName" ComputerName = ReadRegValue(RegEntry)

    if InStr(1,ucase(ComputerName),"LAB1-",vbTextCompare) > 0 then call SetPrinter("\\LAB1\LaserJet")
    if InStr(1,ucase(ComputerName),"LAB2-",vbTextCompare) > 0 then call SetPrinter("\\LAB2\LaserJet")
    if InStr(1,ucase(ComputerName),"OFFICE-",vbTextCompare) > 0 then call SetPrinter("\\OFFICE\LaserJet")
    'so on and so forth.
    wscript.quit

    '*** This subroutine installs and sets the default printer
    Sub SetPrinter(ByVal PrinterPath)
        DIM WshNetwork
        Set WshNetwork = CreateObject("WScript.Network")
        WshNetwork.AddWindowsPrinterConnection(PrinterPath)
        WshNetwork.SetDefaultPrinter Printerpath
    end sub

    '**** This function returns the data in the registry value
    Function ReadRegValue(ByVal RegValue)
        DIM WSHShell
        Set WSHShell = WScript.CreateObject("WScript.Shell")
        ReadRegValue=""
        On Error Resume Next
        ReadRegValue= WSHShell.RegRead(RegValue)
    End Function
    ```

2. 根据需要修改 IF 行。IF 行中唯一需要修改的部分是双引号之间的内容。你可能需要添加额外的 IF 行。
3. 使用注册表编辑器在以下注册表项下创建 ResetPrinter 字符串值：

    `HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\Run`

4. ResetPrinter 的值应类似于以下内容：

    WSCRIPT.EXE *path*\\DefaultPrinter.vbs  
    其中 *path* 是 Defaultprinter.vbs 文件的存储位置。
> **备注**
> 也可以从登录脚本而不是 Run 项运行 Defaultprinter.vbs 文件。本文所述的两种方法都会重置用户配置文件所设置的默认打印机。此外，如果本文包含的示例脚本无法正常运行，你可能需要升级或安装 Windows Scripting Host。
>
> Microsoft 提供编程示例仅供说明之用，不作任何明示或暗示的担保。这包括但不限于对适销性或特定用途适用性的暗示担保。本文假设你熟悉所演示的编程语言以及用于创建和调试过程的工具。Microsoft 支持工程师可以帮助解释特定过程的功能，但他们不会修改这些示例来提供额外功能，也不会构建过程来满足你的特定要求。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/printing/alter-printers-behavior-roaming-profiles)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权，本文档为社区中文翻译）
