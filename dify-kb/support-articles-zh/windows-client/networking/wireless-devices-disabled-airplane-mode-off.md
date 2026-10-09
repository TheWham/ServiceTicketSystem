# 关闭飞行模式后禁用无线设备

本文提供了在关闭飞行模式后禁用无线设备的问题的解决方案。

*适用于：*Windows 10 - 所有版本  
*原始 KB 数：* 2826798

## 现象

假设出现了下面这种情景：

- 你有一台运行 Windows 8.1 或 Windows 8 的计算机。
- 打开飞行模式以禁用所有无线通信。
- 将计算机置于睡眠或休眠模式，或者关闭计算机。
- 从睡眠或休眠模式唤醒计算机，或重新启动计算机。
- 关闭飞行模式以启用所有无线通信。

在此方案中，如果在初始化无线设备之前关闭飞行模式，即使飞行模式处于关闭状态，设备也会保持关闭状态。

## 原因

出现此问题的原因是飞机模式设置在配置无线设备之前发生更改。 因此，系统无法将飞行模式设置中继到设备。

## 解决方法

若要解决此问题，请执行以下步骤：

1. 从屏幕右边缘轻扫，或按 Windows 徽标键 + C。
2. 点击或单击“设置”。
3. 点击或单击“ **更改电脑设置**”。
4. 点击或单击“ **无线**”。
5. 点击或单击受影响的设备以再次打开它。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/wireless-devices-disabled-airplane-mode-off)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
