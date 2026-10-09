# 如何读取 Windows 创建的小型内存转储文件（如果发生崩溃）

本文介绍如何检查小型内存转储文件。 小型内存转储文件可以帮助你确定计算机失败的原因。

*适用于* 所有受支持的 Windows 客户端和 Windows Server 版本

*原始 KB 数：* 315263

注意

如果要查找 Windows 8 或更高版本的调试信息，请参阅[适用于 Windows 的调试工具（WinDbg、KD、CDB、NTSD）。](/zh-cn/windows-hardware/drivers/debugger/)
有关小型内存转储的详细信息，请参阅 [小型内存转储](/zh-cn/windows-hardware/drivers/debugger/small-memory-dump)。

## 小型内存转储文件

如果计算机失败，如何确定发生的情况、修复问题并阻止它再次发生？ 在这种情况下，你可能会发现小型内存转储文件很有用。 小型内存转储文件包含最少的有用信息，可帮助确定计算机失败的原因。 内存转储文件包含以下信息：

- Stop 消息、其参数和其他数据
- 已加载驱动程序的列表
- 已停止的处理器的处理器上下文 （PRCB）
- 停止的进程的进程信息和内核上下文 （EPROCESS）
- 停止的线程的进程信息和内核上下文 （ETHREAD）
- 停止的线程的内核模式调用堆栈

若要创建内存转储文件，Windows 需要启动卷上的分页文件，该文件至少为 2 MB。 在运行Microsoft Windows 2000 或更高版本的 Windows 的计算机上，每次发生计算机故障时都会创建一个新的内存转储文件。 这些文件的历史记录存储在文件夹中。 如果出现第二个问题，如果 Windows 创建第二个小内存转储文件，Windows 将保留以前的文件。 Windows 为每个文件提供一个不同的日期编码文件名。 例如， *Mini022900-01.dmp* 是 2000 年 2 月 29 日生成的第一个内存转储文件。 Windows 保留 %SystemRoot%\Minidump *文件夹中所有小型内存转储文件*的列表。

如果硬盘空间有限，小型内存转储文件可能很有用。 但是，由于包含的信息有限，因此无法通过分析此文件发现未直接由问题时运行的线程引起的错误。

## 配置转储类型

若要配置启动和恢复选项以使用小型内存转储文件，请执行以下步骤。

注意

根据你的 Windows 版本，你的计算机上以下步骤可能有所不同。 如果它们不同，请参阅产品文档以完成这些步骤。

1. 选择“开始”>“控制面板”。
2. 双击“系统”，然后选择“**高级系统设置**>**”。**
3. 在“启动和恢复**”下**，选择“**设置**”。
4. 在**“写入调试信息**”列表中，选择“**小型内存转储”（256k）。**

   ![启动和恢复窗口中“写入调试信息”列表中的“小型内存转储”选项（256k）选项的屏幕截图。](media/read-small-memory-dump-file/small-memory-dump-option.gif)

若要更改小型内存转储文件的文件夹位置，请在“转储文件**”框中或**“小型转储目录**”框中键入新路径**（具体取决于 Windows 的版本）。

## 用于读取小型内存转储文件的工具

使用转储检查实用工具（*Dumpchk.exe*）读取内存转储文件或验证文件是否已正确创建。

注意

转储检查实用工具不需要访问调试符号。 符号文件保存运行二进制文件时实际不需要的各种数据。 但是，此数据在调试中非常有用。

有关如何在 Windows NT、Windows 2000、Windows Server 2003 或 Windows Server 2008 中使用转储检查实用工具的详细信息，请参阅 [“使用Dumpchk.exe检查内存转储文件](../../windows-server/performance/use-dumpchk-to-check-memory-dump-file)。

有关如何在 Windows XP、Windows Vista 或 Windows 7 中使用转储检查实用工具的详细信息，请参阅 [如何使用Dumpchk.exe来检查内存转储文件](https://support.microsoft.com/topic/how-to-use-dumpchk-exe-to-check-a-memory-dump-file-0d766a2d-efaf-cf41-989e-fa3169869abb)。

或者，可以使用 Windows 调试器（*WinDbg.exe*）工具或内核调试器（*KD.exe*）工具来读取小型内存转储文件。  WinDbg.exe和*KD.exe*包含在最新版本的 Windows 调试工具包中。

若要安装调试工具，请参阅适用于 Windows [网页的](/zh-cn/windows-hardware/drivers/debugger/debugger-download-tools)下载和安装调试工具。 **选择典型**安装。 默认情况下，安装程序会在以下文件夹中安装调试工具：

*C：\Program Files\Debugging Tools for Windows*

该工具网页还提供对适用于 Windows 的可下载符号包的访问权限。 有关 Windows 符号的详细信息，请参阅 [“使用符号](/zh-cn/windows/win32/dxtecharts/debugging-with-symbols)进行调试”和“ [下载 Windows 符号包](/zh-cn/windows-hardware/drivers/debugger/debugger-download-symbols) ”网页。

有关 Windows 中的转储文件选项的详细信息，请参阅 [Windows](../../windows-server/performance/memory-dump-file-options) 内存转储文件选项概述。

## 打开转储文件

若要在安装完成后打开转储文件，请执行以下步骤：

1. 选择“**开始>****运行”**，键入`cmd`，然后选择“**确定”。**
2. 更改为 *Windows* 调试工具文件夹。 为此，请在命令提示符处键入以下内容，然后按 Enter：

   ```
   cd C:\Program Files\Debugging Tools For Windows
   ```
3. 若要将转储文件加载到调试器中，请键入以下命令之一，然后按 Enter：

   ```
   windbg -y SymbolPath -i ImagePath -z DumpFilePath
   ```

   ```
   kd -y SymbolPath -i ImagePath -z DumpFilePath
   ```

下表说明了这些命令中使用的占位符的使用。

| 占位符 | 解释 |
| --- | --- |
| **SymbolPath** | 下载符号文件的本地路径或符号服务器路径，包括缓存文件夹。 由于小型内存转储文件包含有限的信息，因此必须将实际的二进制文件与符号一起加载，以便正确读取转储文件。 |
| **ImagePath** | 这些文件的路径。 这些文件包含在 Windows XP CD-ROM 上的 I386 文件夹中。 例如，路径可以是 `C:\Windows\I386`. |
| **DumpFilePath** | 要检查的转储文件的路径和文件名。 |

### 示例命令

可以使用以下示例命令打开转储文件。 这些命令假定为以下内容：

- Windows CD-ROM 上的 I386 *文件夹的内容*将*复制到 C：\Windows\I386* 文件夹。
- 转储文件名为 *C：\Windows\Minidump\Minidump.dmp*。

示例 1 （命令行）：

```
kd -y srv*C:\Symbols*https://msdl.microsoft.com/download/symbols -i C:\Windows\i386 -z C:\Windows\Minidump\minidump.dmp
```

示例 2（图形 UI）。 如果更喜欢调试器的图形版本而不是命令行版本，请改为键入以下命令：

```
windbg -y srv*C:\Symbols*https://msdl.microsoft.com/download/symbols -i C:\Windows\i386 -z C:\Windows\Minidump\minidump.dmp
```

## 检查转储文件

可以使用多个命令来收集转储文件中的信息，包括以下命令：

- 该 `!analyze -show` 命令显示“停止”错误代码及其参数。 停止错误代码也称为 bug 检查代码。
- 该 `!analyze -v` 命令显示详细输出。
- 该 `lm N T` 命令列出指定的已加载模块。 输出包括模块的状态和路径。

注意

在旧版本的 Windows（预约会 Windows XP）中 `!drivers` ，扩展命令显示目标计算机上加载的所有驱动程序的列表，以及有关其内存使用的摘要信息。 但是，扩展 `!drivers` 命令在 Windows XP 和更高版本中已过时。 若要显示有关加载的驱动程序和其他模块的信息，请使用 `lm` 该命令。 该 `lm N T` 命令以类似于旧 `!drivers` 扩展的格式显示信息。

有关其他命令和完整命令语法的帮助，请参阅调试工具帮助文档。 可以在以下位置找到调试工具帮助文档：

*C：\Program Files\Debugging Tools for Windows\Debugger.chm*

注意

如果存在与符号相关的问题，请使用 Symchk 实用工具验证是否正确加载了正确的符号。 有关如何使用 Symchk 的详细信息，请参阅 [使用符号](/zh-cn/windows/win32/dxtecharts/debugging-with-symbols)进行调试。

### 使用批处理文件简化命令

确定必须用于加载内存转储的命令后，可以创建批处理文件来检查转储文件。 例如，创建批处理文件并将其命名 *为Dump.bat*。 将其保存在安装调试工具的文件夹中。 在批处理文件中键入以下文本：

```
cd "C:\Program Files\Debugging Tools for Windows"

kd -y srv*C:\Symbols*https://msdl.microsoft.com/download/symbols -i C:\Windows\i386 -z %1
```

如果要检查转储文件，请键入以下命令，将转储文件路径传递给批处理文件：

```
dump C:\Windows\Minidump\minidump.dmp
```

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/read-small-memory-dump-file)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
