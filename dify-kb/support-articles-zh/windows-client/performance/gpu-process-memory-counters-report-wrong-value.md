# GPU 进程内存计数器报告不正确的值

本文讨论图形处理单元（GPU）进程内存计数器显示正在运行的应用程序的内存泄漏并报告不正确的值的问题。

*适用于：*Windows 10 - 所有版本  
*原始 KB 数：* 4490156

## 现象

图形处理单元（GPU）进程内存计数器似乎显示 Windows 10 版本 1709 及更高版本中运行应用程序的内存泄漏。 此问题会影响以下计数器：

- 性能监视器： **GPU 进程内存**
- 任务管理器， **详细信息** 窗格： **专用 GPU 内存**

  注意

  某些 GPU 不使用专用 GPU 内存。 在这些情况下， **专用 GPU 内存** 计数器不可用或值为“0”。本文介绍的问题不会发生。

### 重现问题的步骤

注意

这些步骤使用 Office 应用lication 作为示例。

1. 右键单击任务栏，然后选择“ **任务管理器**”。
2. 在任务管理器中，选择“ **详细信息**”。 在 **“详细信息** ”窗格中，右键单击列头，选择“ **显示列**”，然后选择“ **专用 GPU 内存**”。
3. 启动任何Office 应用复制，创建一个空白文档，然后将应用程序窗口最大化。
4. 启动任何其他应用程序，然后在与Office 应用复制相同的监视器中最大化该应用程序窗口（以便新应用程序隐藏Office 应用数据删除）。
5. 等待大约 30 秒，Office 应用复制进入“低资源模式”。

   注意

   在此模式下，Office 应用复制会刷新其可丢弃的缓存，包括 GPU 资源。
6. 在“任务管理器**详细信息**”窗格中，检查**专用 GPU 内存**值以获取Office 应用数据。 应注意到该值已下降约 100MB。
7. 将Office 应用复制窗口带回监视器前台。

   - **预期行为：**当Office 应用复制重新创建其资源时，其**专用 GPU 内存**值应返回与应用程序上次处于活动状态时的大致相同值。
   - **实际行为：** 在受此问题影响的系统上，新的 **专用 GPU 内存** 值比应用程序上次处于活动状态的时间要大约 100MB（或更多）。 每次隐藏Office 应用删除时，等待它刷新其缓存，然后重新激活缓存，该值将增加 100MB（或更多）。 但是，**任务管理器**性能**窗格中可见的专用 GPU 内存**值继续显示预期值。 此外，Windows 性能记录器（WPR）和 Windows 性能分析器（WPA）等工具会显示预期值。

## 详细信息

这是 Windows 10 中的已知问题。 若要监视受影响系统上的专用 GPU 内存，请使用 **任务管理器、WPR 或 WPA 的性能** 窗格。
有关 GPU 进程内存计数器的详细信息，请参阅 [任务管理器](https://devblogs.microsoft.com/directx/gpus-in-the-task-manager/)中的 GPU。
有关 WPR 和 WPA 的详细信息，请参阅 [Windows 性能工具包](/zh-cn/windows-hardware/test/wpt/)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/gpu-process-memory-counters-report-wrong-value)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
