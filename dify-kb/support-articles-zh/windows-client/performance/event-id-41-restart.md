# 事件 ID 41 的高级故障排除：“系统已重新启动，无需先完全关闭”

注意

家庭用户：本文适用于支持代理和 IT 专业人员。 如果要查找有关蓝屏错误消息的详细信息，请访问 [“排查蓝屏错误](https://support.microsoft.com/help/14238/windows-10-troubleshoot-blue-screen-errors)”。

关闭 Windows 的首选方法是选择“开始**”**，然后选择一个选项来关闭或关闭计算机。 使用此标准方法时，操作系统会关闭所有文件并通知正在运行的服务和应用程序，以便它们可以将任何未保存的数据写入磁盘并刷新任何活动缓存。

如果计算机意外关闭，Windows 会在下次启动计算机时记录事件 ID 41。 事件文本类似于以下信息：

```
Event ID: 41  
Description: The system has rebooted without cleanly shutting down first.
```

此事件指示某些意外活动阻止 Windows 正确关闭。 此类关闭可能是电源中断或停止错误造成的。 如果可行，Windows 会记录关闭时的任何错误代码。 在下 [一个 Windows 启动的内核阶段](windows-boot-issues-troubleshooting#troubleshoot-issues-in-the-kernel-phase) ，Windows 会检查这些代码，并在事件 ID 41 的事件数据中包含任何现有代码。

```
EventData  
BugcheckCode 159  
BugcheckParameter1 0x3  
BugcheckParameter2 0xfffffa80029c5060  
BugcheckParameter3 0xfffff8000403d518  
BugcheckParameter4 0xfffffa800208c010  
SleepInProgress false  
PowerButtonTimestamp 0Converts to 0x9f (0x3, 0xfffffa80029c5060, 0xfffff8000403d518, 0xfffffa800208c010)
```

## 排查意外关闭或重启问题时如何使用事件 ID 41

事件 ID 41 本身可能不包含足够的信息来显式定义所发生的情况。 通常，还必须考虑意外关闭时发生的情况（例如电源出现故障）。 使用本文中的信息来确定适合你的情况的故障排除方法：

- [方案 1](#scenario-1-the-computer-restarts-because-of-a-stop-error-and-event-id-41-contains-a-stop-error-bug-check-code)：计算机因停止错误而重启，事件 ID 41 包含“停止”错误（bug 检查）代码
- [方案 2](#scenario-2-the-computer-restarts-because-you-pressed-and-held-the-power-button)：计算机会重启，因为你按下并按住电源按钮
- [方案 3](#scenario-3-the-computer-is-unresponsive-or-randomly-restarts-and-event-id-41-isnt-recorded-or-the-event-id-41-entry-or-lists-error-code-values-of-zero)：计算机无响应或随机重启，未记录事件 ID 41，或者事件 ID 41 条目列出错误代码值为零

## 方案 1：计算机因停止错误而重启，事件 ID 41 包含“停止”错误（bug 检查）代码

当计算机因停止错误而关闭或重新启动时，Windows 会将事件 ID 41 中的“停止”错误数据作为更多事件数据的一部分包含在事件 ID 41 中。 此信息包括停止错误代码（也称为 bug 检查代码），如以下示例所示：

```
EventData  
BugcheckCode 159  
BugcheckParameter1 0x3  
BugcheckParameter2 0xfffffa80029c5060  
BugcheckParameter3 0xfffff8000403d518  
BugcheckParameter4 0xfffffa800208c010
```

注意

事件 ID 41 包含小数格式的 bug 检查代码。 大多数描述 bug 检查代码的文档将代码称为十六进制值而不是十进制值。 若要将十进制转换为十六进制，请执行以下步骤：

1. 选择“开始”**，在“搜索**”框中键入计算*，然后选择“**计算器**”。*****
2. 在**“计算器**”窗口中，选择“**查看>程序员”。**
3. 在计算器左侧，验证 12 月是否突出显示。
4. 使用键盘输入 bug 检查代码的十进制值。
5. 在计算器左侧，选择 **十六进制**。  
   计算器显示的值现在是十六进制代码。

将 bug 检查代码转换为十六进制格式时，请验证“0x”指定是否后跟八位数字（即，“x”后面的代码部分包含足够的零来填写八位数字）。 例如，通常将0x9F记录为0x0000009f，0xA记录为0x0000000A。 对于本文中的示例事件数据，“159”转换为0x0000009f。

标识十六进制值后，使用以下引用继续进行故障排除：

- [停止错误或蓝屏错误问题高级疑难解答](stop-error-or-blue-screen-error-troubleshooting)。
- [Bug 检查代码参考](/zh-cn/windows-hardware/drivers/debugger/bug-check-code-reference2)。 此页面列出了指向不同 bug 检查代码的文档的链接。
- [如何调试内核模式蓝屏崩溃（适合初学者](/zh-cn/archive/blogs/askcore/how-to-debug-kernel-mode-blue-screen-crashes-for-beginners)）。

## 方案 2：计算机会重启，因为你按下并按住电源按钮

由于重启计算机的此方法会干扰 Windows 关闭操作，因此建议仅在你没有选择的情况下使用此方法。 例如，如果计算机未响应，可能需要使用此方法。 通过按住电源按钮重启计算机时，计算机会记录一个事件 ID 41，其中包含 **PowerButtonTimestamp** 条目的非零值。

```
<EventData>
<Data Name="BugcheckCode">0</Data>
<Data Name="BugcheckParameter1">0x0</Data>
<Data Name="BugcheckParameter2">0x0</Data>
<Data Name="BugcheckParameter3">0x0</Data>
<Data Name="BugcheckParameter4">0x0</Data>
<Data Name="SleepInProgress">0</Data>
<Data Name="PowerButtonTimestamp">131728546170882432</Data>
<Data Name="BootAppStatus">0</Data>
</EventData>
```

有关对无响应计算机进行故障排除时的帮助，请参阅 [Windows 帮助](https://support.microsoft.com//windows/troubleshooting-windows-unexpected-restarts-and-stop-code-errors-60b01860-58f2-be66-7516-5c45a66ae3c6)。 请考虑使用“挂起”、“响应”或“空白屏幕”等关键字搜索帮助。

## 方案 3：计算机无响应或随机重启，未记录事件 ID 41 或事件 ID 41 条目或列出错误代码值为零

此方案包括以下情况：

- 关闭无响应计算机的电源，然后重新启动计算机。  
  若要验证计算机是否无响应，请按 `键盘上的 Caps 锁定` 键。
  `如果按下 Caps 锁键时键盘上的 Caps 锁`灯不会更改，则计算机可能无响应（也称为硬挂起）。
- 计算机会重启，但不会生成事件 ID 41。
- 计算机重启并生成事件 ID 41，但 **BugcheckCode** 和 **PowerButtonTimestamp** 值为零。

在这种情况下，某些内容会阻止 Windows 生成错误代码或将错误代码写入磁盘。 某些内容可能会阻止对磁盘的写入访问（如无响应计算机的情况），或者计算机可能会关闭太快，无法编写错误代码，甚至检测到错误。

事件 ID 41 中的信息提供了一些指示开始检查问题的位置：

- 未记录事件 ID 41 或 bug 检查代码为零。 此行为可能表示电源问题。 如果计算机电源中断，计算机可能会关闭，而不会生成“停止”错误。 如果它确实生成了“停止”错误，则可能无法完成将错误代码写入磁盘。 下次计算机启动时，它可能不会记录事件 ID 41。 或者，如果这样做，bug 检查代码为零。 以下情况可能是原因：

  - 对于便携式计算机，电池已移除或耗尽。
  - 对于台式计算机，计算机被拔出或遇到停电。
  - 电源不足或故障。
- PowerButtonTimestamp 值为零。 如果将电源与未响应输入的计算机断开连接，则可能会发生此行为。 以下情况可能是原因：

  - Windows 进程阻止了对磁盘的写入访问，你通过按下电源按钮至少四秒关闭计算机。
  - 你断开了对无响应计算机的电源。
- 写入转储文件失败，所有值均为零。 例如：

  ```
  <EventData>
  <Data Name="BugcheckCode">0</Data>
  <Data Name="BugcheckParameter1">0x0</Data>
  <Data Name="BugcheckParameter2">0x0</Data>
  <Data Name="BugcheckParameter3">0x0</Data>
  <Data Name="BugcheckParameter4">0x0</Data>
  <Data Name="SleepInProgress">0</Data>
  <Data Name="PowerButtonTimestamp">0</Data>
  <Data Name="BootAppStatus">0</Data>
  </EventData>
  ```

  但是，volmgr 记录的事件日志 ID 为 46： **崩溃转储初始化失败！**。 如果计算机在没有配置的转储文件的情况下启动，则可能会发生此事件。 默认转储文件是页面文件。

  ![事件日志的屏幕截图。](media/event-id-41-restart.md/event-id-screenshot.png)

  因此，如果出现意外重启的情况，并且事件 ID 41 的所有值都为 **0**，请检查是否有事件 ID 46 by volmgr。 如果是，请检查页面文件配置。 bug 检查仍可能导致意外重启，但系统无法在事件 ID 41 中编写 bug 检查类型，也无法生成内存转储。 启动计算机时，请参阅 [事件 ID 46](../../windows-server/performance/event-id-46-start-a-computer)

通常，此方案中描述的症状表示硬件问题。 若要帮助隔离问题，请执行以下步骤：

- 禁用超锁。 如果计算机已启用超锁，请禁用它。 验证系统是否以正确的速度运行时出现问题。
- 检查内存。 使用内存检查器确定内存运行状况和配置。 验证所有内存芯片是否以相同的速度运行，并且系统中是否已正确配置每个芯片。
- 检查电源。 验证电源是否有足够的瓦数来适当处理已安装的设备。 如果添加了内存、安装了较新的处理器、安装了更多驱动器或添加了外部设备，则此类设备可能需要比当前电源持续提供更多的能量。 如果计算机记录的事件 ID 41 是因为计算机的电源中断，请考虑获取不间断电源（UPS），例如电池备份电源。
- 检查过热情况。 检查硬件的内部温度，并检查是否有任何过热的组件。
- 如果计算机是物理机，自动服务器恢复（ASR）软件可能检测到该计算机没有响应，并已将其重新启动。
- 如果系统在 Hyper-V 虚拟机（VM）中运行，并且不属于集群环境，则系统可能已由 Hyper-V 心跳功能重新启动。 如果启用此功能，并且主机未检测到来自 VM 的心跳信号（可能是因为它没有响应），Hyper-V 将重新启动该 VM。
- 如果在 Hyper-V 群集环境中出现问题，则此问题可能与虚拟机**选项的“启用检测信号监视”相关**。 尝试从群集环境中[运行的虚拟机获取完整内存转储文件时，请参阅](../../windows-server/high-availability/corrupted-memory-dump-file)损坏的内存转储文件。
- 如果 VMWare VM 出现问题，则它可能与 VMWare 中的检测信号功能相关，或者 VM 是某些第三方群集的一部分。
- 在应用程序日志和系统日志中检查关闭时间（从事件 ID 6008 获取）之前是否有任何可疑事件。

如果执行这些检查，但仍无法隔离问题，请将系统设置为其默认配置，并验证问题是否仍然存在。

注意

如果看到包含 bug 检查代码的“停止”错误消息，但事件 ID 41 不包括该代码，请更改计算机的重启行为。 为此，请按照下列步骤进行操作：

1. 右键单击“**我的计算机**”，然后选择“**属性****>高级系统设置**>**高级**”。
2. 在 **“启动和恢复** ”部分中，选择“ **设置**”。
3. 清除“ **自动重启** ”复选框。

## 详细信息

### 有关事件 ID 41 的详细信息

当计算机意外关闭或重启时，会发生内核 Power 事件 ID 41 错误。 当基于 Windows 的计算机启动时，将执行检查以确定计算机是否已完全关闭。 否则，将生成内核 Power 事件 ID 41 消息。

事件 ID 41 用于报告导致 Windows 无法正确关闭的意外事件。 可能没有足够的信息来显式定义所发生的事情。 有关详细信息，请参阅 [内核电源事件 ID 41](https://social.technet.microsoft.com/wiki/contents/articles/14246.kernel-power-event-id-41.aspx)。

- 日志名称：系统
- 产品：Windows 操作系统
- ID：41
- 源：Microsoft-Windows-Kernel-Power
- 级别：严重
- 版本：6.1
- 消息：系统已重新启动，无需先完全关闭。 如果系统停止响应、崩溃或意外断电，则可能导致此错误。

注意

.evtx 文件中显示的时间调整为系统的时间。 检查服务器的时区。

- 事件 ID 41：此事件指示 Windows 在未完全关闭的情况下重启。
- 事件 ID 1074：当应用程序负责系统关闭或重启时，将记录此事件。 它还指示用户使用“开始”**菜单或按 Ctrl+Alt+Del 重新启动或关闭系统**。
- 事件 ID 6006：此事件指示 Windows 已完全关闭。
- 事件 ID 6008：此事件指示不正确或脏关闭。 如果最近关闭是意外的，会记录该事件。

在计算机关闭之前，使用 `shutdown.exe` Source=User32 和事件 ID 1074 记录 Windows 系统日志中的关闭事件以及任何自定义消息和原因代码。

事件日志是指示从 `shutdown.exe` 中触发的重新启动处于挂起状态的唯一方法。 该事件还会记录用户名以及发出命令的 `shutdown` 日期和时间。

使用 `shutdown.exe` 重启服务器时，关闭过程通常允许 30 秒，以确保每个正在运行的服务都有时间停止。 服务按字母顺序关闭。 按特定顺序 `NET STOP` 手动停止服务，或者 `SC` 可能会稍微快一些。

### 启动状态文件（来自 Windows 内部 6 日）

Windows 使用启动状态文件（*%SystemRoot%\Bootstat.dat*）来记录它已经历系统生命周期的各个阶段（包括启动和关闭）的事实。

这样，启动管理器、Windows 加载程序和启动修复工具就可以检测异常关闭或故障完全关闭，以提供用户恢复和诊断启动选项，例如“上次已知良好和安全模式”。 此二进制文件包含系统报告系统生命周期以下阶段成功的信息：

- 启动（成功启动的定义与用于确定上次已知良好状态的定义相同，前面所述）
- 关机
- 从休眠状态恢复或挂起

启动状态文件还指示用户上次尝试启动操作系统时是否检测到问题，以及显示的恢复选项，表明用户已收到问题警报并采取了措施。 ntdll.dll中的运行时库 API（Rtl）包含 Windows 用于读取和写入文件的专用接口。 与 BCD 一样，用户无法对其进行编辑。

### 关于关闭

启动关闭后，Windows 会将WM\_QUERYENDSESSION消息发送到具有用户界面（UI）线程的所有正在运行的应用程序。 此消息要求应用程序保存任何未保存的数据并正常终止。 如果应用程序未在特定的时间限制内响应消息，Windows 会将WM\_ENDSESSION消息发送到应用程序，该应用程序会立即终止该应用程序。

如果所有应用程序都响应WM\_QUERYENDSESSION消息并正常终止，Windows 会在系统事件日志中记录干净关闭事件。 如果有任何应用程序未响应系统消息或异常终止，Windows 会在系统事件日志中记录一个非正常关机事件。

意外关闭主要是由操作系统外部的组件引起的。

脏关机是在计算机系统关闭而不经历正确的关闭过程时。 当电源突然关闭或计算机被迫关闭电源按钮时，可能会发生这种情况。 脏关闭可能会导致数据丢失或损坏，也可能导致启动问题。

脏关机计数是 Windows 注册表中的一个注册表键，用于跟踪计算机系统在不经过正常的关机过程时关机的次数。 排查启动问题时，此密钥非常有用，以确定系统是否未正确关闭。

还可以清除以下注册表项中的所有值（如 DirtyShutdown、LastAliveStamp、TimeStampInterval）： `Computer\HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Reliability` 这有助于防止关闭事件跟踪器在意外关闭后出现。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/event-id-41-restart)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
