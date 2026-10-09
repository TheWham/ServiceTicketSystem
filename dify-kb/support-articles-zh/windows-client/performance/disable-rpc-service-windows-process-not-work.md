# 如果禁用远程过程调用服务，某些 Windows 过程不起作用

本文提供了一个解决方案，其中某些 Windows 过程在禁用远程过程调用 （RPC） 服务时不起作用。

*原始 KB 数：* 830071

重要

本文包含有关修改注册表的信息。 在修改注册表之前，请务必备份注册表并确保您知晓如何在出现问题时还原注册表。 有关如何备份、还原和编辑注册表的详细信息，请参阅 [适用于高级用户的 Windows 注册表信息](https://support.microsoft.com/help/256986)。

## 现象

重启运行 Microsoft Windows NT 4.0、Microsoft Windows 2000、Microsoft Windows Server 2003 或 Microsoft Windows XP 的计算机时，可能会出现以下情况：

- 不能在桌面上移动图标。
- 无法查看事件日志条目。
- 可以打开服务Microsoft管理控制台（MMC），但看不到列出的任何服务。

## 原因

如果禁用 RPC 服务，可能会出现此问题。 许多 Windows 操作系统过程依赖于 RPC 服务。

Microsoft建议不要禁用 RPC 服务。

## 解决方法

警告

如果注册表编辑器使用不当，则可能会产生严重问题，导致重新安装操作系统。 Microsoft 无法保证可以解决因注册表编辑器使用不当而造成的问题。 请慎用注册表编辑器，风险自负。

若要解决该问题，请执行以下步骤：

1. 单击“**开始”，**单击“运行**”**，键入 *regedt32*，然后单击“**确定**”。
2. 展开注册表项 `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\RpcSs\`。
3. 双击“开始”，在**“编辑 DWORD 值**”对话框中键入 2，然后单击“**确定**”。
4. 关闭注册表编辑器，然后重新启动计算机。

如果计算机无法正确启动，可以使用恢复控制台重新启用 RPC 服务。 若要使用恢复控制台，请执行以下步骤：

1. 将计算机启动到恢复控制台。
2. 在恢复控制台命令提示符处，键入 `Enable RPCSS Service_Auto_Start` 该命令，然后按 Enter。
3. 在恢复控制台命令提示符处，键入 `EXIT`，然后按 Enter。
4. 重新启动计算机。

## 详细信息

以下服务依赖于 RPC 服务：

- 后台智能传输服务
- COM+ 事件系统
- 分布式链接堆栈客户端
- 分布式事务处理协调器
- 传真服务
- 索引服务
- IPSec 策略代理
- 信使
- 网络连接
- 打印后台处理程序
- 受保护的存储
- 可移动存储
- 路由信息协议 （RIP） 侦听器
- 路由和远程访问
- 任务计划程序
- 电话服务
- Telnet
- Windows Installer
- Windows Management Instrumentation

## 参考

有关如何在 Windows XP、Windows 2000 或 Windows Server 2003 中使用恢复控制台的详细信息，请参阅 [Windows 中的系统恢复选项是什么？](https://support.microsoft.com/windows/bd88ffdf-1e8e-34a0-d76f-39a71fb4ed4d)[以及如何在基于 Windows Server 2003 的基于 Windows Server 2003 的计算机上](https://support.microsoft.com/help/326215)使用恢复控制台。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/disable-rpc-service-windows-process-not-work)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
