# 无法在 S 模式下从恢复驱动器启动 Windows 11

S 模式下的 Windows 11 具有安全策略，可确保系统安全运行。 尝试从恢复驱动器在 S 模式下启动 Windows 11 时，由于缺少策略，系统可能无法启动。 若要解决此问题，可以使用以下方法之一将策略文件复制到驱动器的指定位置。

## 从恢复驱动器复制策略文件

按照以下步骤检查恢复驱动器是否包含策略文件，然后将该文件复制到驱动器的指定位置。

1. 插入或连接恢复驱动器到计算机。
2. 打开**文件资源管理器**，转到<*恢复驱动器>：\EFI\Microsoft\Boot* 文件夹，并检查 winsipolicy.p7b *文件是否*在文件夹中。
3. *如果 winsipolicy.p7b* 文件位于文件夹中，请将该文件*<复制到恢复驱动器>：\EFI\Boot* 文件夹。

## 从另一台 Windows 计算机复制策略文件

如果恢复驱动器不包含策略文件，请从另一台 Windows 计算机复制该文件。

1. 插入或将恢复驱动器连接到另一台 Windows 计算机。
2. 打开**文件资源管理器，转到 *C：\Windows\Boot\EFI* 文件夹，并将 winsipolicy.p7b *文件复制到<**恢复驱动器>：\EFI\Boot* 文件夹。**

## Status

此问题将在将来的 Windows 服务更新中得到解决，本文将在发布服务更新时更新。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/cannot-start-windows-11-s-mode-recovery-drive)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
