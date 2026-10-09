# 如果计算机在登录到 Windows 10 后未使用，则网络会断开连接几秒钟

*适用于：*Windows 10

## 现象

登录到运行 Windows 10 的计算机并使其未使用超过 10 分钟时，网络将断开连接几秒钟。

在此期间，通过 LAN 与计算机通信的应用程序和服务将断开与计算机的连接。

注意

这是 Windows 10 IoT [中的](/zh-cn/windows/iot-core/windows-iot-enterprise#fixed-purpose-devices)常见方案。

## 原因

登录预计划任务启动ProvTool.exe文件。 此文件处理系统上的预配包。 ProvTool.exe启动进程的 DMWapPushService 服务时，将加载ndisuio.sys驱动程序。 当ndisuio.sys驱动程序绑定到网络时，现有连接将中断，并在几秒钟后恢复。

## 解决方法

### 方法 1：更改ndisuio.sys驱动程序的加载时间

下面介绍如何更改ndisuio.sys驱动程序的加载时间：

1. [打开注册表编辑器](https://support.microsoft.com/windows/how-to-open-registry-editor-in-windows-10-deab38e6-91d6-e0aa-4b7c-8878d9e07b11)。
2. 转到 `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Ndisuio`。
3. 双击“开始**”**并将值数据更改为 **1**。

   注意

   值 **1** 表示在系统启动时启动驱动程序。
4. 关闭**注册表编辑器**。
5. 重新启动系统。

### 方法 2：更改 DMWapPushSvc 服务的开始计时

下面介绍如何更改 DMWapPushSvc 服务的开始计时：

1. [打开注册表编辑器](https://support.microsoft.com/windows/how-to-open-registry-editor-in-windows-10-deab38e6-91d6-e0aa-4b7c-8878d9e07b11)。
2. 转到 `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\dmwappushservice`。
3. 双击“开始**”**并将值数据更改为 **2**。

   注意

   值 **2** 表示将服务设置为自动启动。
4. 关闭**注册表编辑器**。
5. 重新启动系统。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/network-gets-disconnected-computer-not-used-after-sign-in)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
