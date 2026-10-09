# 使用 64 位版本的 Windows 查看系统注册表

本文介绍如何使用 64 位版本的 Windows 查看 Windows 注册表。

*适用于：*Windows 10 - 所有版本  
*原始 KB 数：* 305097

## 总结

64 位版本的 Windows 中的注册表分为 32 位和 64 位键。 许多 32 位项的名称与 64 位项相同，反之亦然。

Windows 64 位版本的注册表编辑器（Regedit.exe）的默认 64 位版本同时显示 64 位密钥和 32 位键。 WOW64 注册表重定向程序为 32 位程序注册表项提供不同键的 32 位程序。 在注册表编辑器的 64 位版本中，32 位密钥显示在注册表项下 `HKEY_LOCAL_MACHINE\Software\WOW6432Node` 。

## 查看 64 位和 32 位注册表项

可以使用默认的 64 位版本注册表编辑器来查看或编辑 64 位和 32 位注册表项和值。 若要查看或编辑 64 位密钥，必须使用 64 位版本的注册表编辑器（Regedit.exe）。 还可以使用文件夹中的 32 位版本的注册表编辑器 `%systemroot%\Syswow64` 来查看或编辑 32 位键和值。 在 32 位版本的注册表编辑器和 64 位版本的注册表编辑器之间执行任务的方式没有差异。 若要打开 32 位版本的注册表编辑器，请执行以下步骤：

1. 单击 **“启动”** ，再单击 **“运行”** 。
2. 在“打开”框中键入 `%systemroot%\syswow64\regedit`，然后单击“确定” 。

   注意

   必须先关闭 64 位版本的注册表编辑器，然后才能打开 32 位版本（反之亦然），除非使用 `-m` 开关启动注册表编辑器的第二个实例。 例如，如果注册表编辑器的 64 位版本已在运行，请键入 `%systemroot%\syswow64\regedit -m` 步骤 2 以启动 32 位版本的注册表编辑器。

为了支持 32 位和 64 位 COM 注册和程序状态共存，WOW64 提供了注册表的备用视图的 32 位程序。 32 位程序看到一个与真正的 64 位树完全分离的 32 位`HKEY_LOCAL_MACHINE\Software``HKEY_LOCAL_MACHINE\Software`树（`HKEY_LOCAL_MACHINE\Software\WOW6432Node`）。 这会隔离 `HKEY_CLASSES_ROOT`，因为此树的每台计算机部分驻留在注册表项中 `HKEY_LOCAL_MACHINE\Software` 。

为了通过 COM 和其他机制启用 64 位/32 位程序互操作性，WOW64 使用注册表反射器来镜像 64 位和 32 位注册表视图之间的某些注册表项和值。 反射器是智能的，即仅反映 COM 激活数据。

## 反射键

WOW64 注册表反射器可以在反射过程中修改键和值的内容，以调整路径名称等。 因此，32 位和 64 位内容可能有所不同。 例如，包含 **system32** 注册表项的路径名称在注册表的 32 位部分中编写为 **SysWOW64** 。 以下键将反映：

- `HKEY_LOCAL_MACHINE\Software\Classes`
- `HKEY_LOCAL_MACHINE\Software\COM3`
- `HKEY_LOCAL_MACHINE\Software\Ole`
- `HKEY_LOCAL_MACHINE\Software\EventSystem`
- `HKEY_LOCAL_MACHINE\Software\RPC`

## 数据收集

如果需要 Microsoft 支持方面的帮助，建议按照[使用 TSS 针对与部署相关的问题收集信息](../windows-troubleshooters/gather-information-using-tss-deployment)中所述的步骤收集信息。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/view-system-registry-with-64-bit-windows)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
