# 飞行模拟器 X 停止在加载屏幕上做出响应（挂起）

本文提供了Microsoft飞行模拟器 X 停止在加载屏幕上响应的问题的解决方案。

*适用于：*Windows 10 - 所有版本  
*原始 KB 数：* 975084

## 现象

启动飞行模拟器 X 时，游戏在加载屏幕上停止响应（挂起）。

## 解决方法

若要解决此问题，请重命名Logbook.bin文件。 为此，请按照下列步骤进行操作：

1. 单击“启动”。
2. 单击“我的文档”或“**文档****”。**
3. 双击Microsoft外部测试模拟器 X 文件文件夹将其打开。
4. 右键单击Logbook.bin文件，然后单击“ **重命名**”。
5. 将文件重命名为 *Logbook.OLD*，然后按 Enter。
6. 启动外部测试模拟器 X 以创建新的 Logbook 文件。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/flight-simulator-x-stops-responding)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
