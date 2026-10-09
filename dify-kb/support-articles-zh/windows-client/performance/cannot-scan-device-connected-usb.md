# 无法从通过 USB 连接到 USB 零客户端工作站的扫描设备扫描

## 症状

考虑以下场景：

- 你的服务器运行的是 Windows Multipoint Server 2011。
- 一台扫描设备通过 USB 连接到 USB 零客户端工作站。
- 你在某个扫描应用程序（如 Microsoft "画图"）中选择"从扫描仪或照相机扫描"。

在此场景下，你会收到类似以下内容的错误消息：

> 无法从设备读取图片。请确认设备已正确连接，然后重试。

此外，如果扫描设备直接连接到服务器上的 USB 端口，Windows Multipoint Server 可能会因 Stop 0x3B 错误意外重启。此时，事件查看器的 **Windows 日志** > **系统** 下会记录类似以下的事件：

```output
事件 ID: 1001
级别: 错误
描述: 计算机已从检查错误(bugcheck)重新启动。检查错误为: 0x0000003b (0x00000000c0000005, 0xfffff8800247e447, 0xfffff88004385cc0, 0x0000000000000000)。转储已保存于: C:\Windows\MEMORY.DMP。报告 ID: 030614-19375-01。
```

## 解决方法

要解决此问题，请使用注册表编辑器从 `UpperFilters` 注册表值中删除 `WmsImageFilter`。操作步骤如下：

1. 打开注册表编辑器。
2. 找到并选中以下注册表子项：

    `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Class\{6BDD1FC6-810F-11D0-BEC7-08002BE2092F}`
3. 在右侧窗格中，右键单击名为 `UpperFilters` 的多字符串值，然后选择"修改…"。
4. 在"数值数据"框的列表中找到 `WmsImageFilter`，并将其从列表中删除。
5. 选择"确定"保存更改，然后关闭注册表编辑器。

> **备注**
> 本方法适用于运行 Windows Multipoint Server 2011 的场景。修改注册表前请先备份：`UpperFilters` 下如有其他值，只删除 `WmsImageFilter` 一项，切勿清空整个值。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/cannot-scan-device-connected-usb)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权，本文档为社区中文翻译）
