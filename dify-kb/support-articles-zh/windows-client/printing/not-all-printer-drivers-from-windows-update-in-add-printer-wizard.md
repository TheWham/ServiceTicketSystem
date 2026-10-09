# 添加打印机向导中未列出从Windows 更新下载的所有打印机驱动程序

本文提供了一种解决方法，其中并非所有从Windows 更新下载的打印机驱动程序都列在“添加打印机”向导中。

*原始 KB 数：* 4508350

## 现象

在运行 Windows 10 版本 1803、Windows Server 版本 1803 或更高版本的 Windows 的计算机上，执行以下操作：

1. 选择“开始**”**，键入*控制面板*，然后按 Enter。
2. 在控制面板中，选择“查看设备和打印机**”**项。

   ![控制面板中“查看设备和打印机”项的屏幕截图。](media/not-all-printer-drivers-from-windows-update-in-add-printer-wizard/view-devices-and-printers-option.png)
3. 选择窗口顶部的“ **添加打印机** ”。

   ![“设备和打印机”窗口的“添加打印机”选项的屏幕截图。](media/not-all-printer-drivers-from-windows-update-in-add-printer-wizard/add-printer.png)
4. 向导启动后，选择 **“我想要的打印机”未列出**。
5. 选择 **“添加具有手动设置**的本地打印机或网络打印机”，然后选择“ **下一步**”。
6. 在 **“选择打印机端口** ”页上，选择所需的端口，然后选择“ **下一步**”。
7. 在**“安装打印机驱动程序**”页上，选择**Windows 更新**。
8. 更新**的打印机**列表从Windows 更新显示。 例如，如果选择“制造商”**下的 **KONICA MINOLTA**，则**“打印机”**列表如下所示。**

   ![“安装打印机驱动程序”对话框中 KONICA MINOLTA 的打印机列表的屏幕截图。](media/not-all-printer-drivers-from-windows-update-in-add-printer-wizard/printer-list.png)

在此方案中，并非所有已注册的驱动程序都显示。

例如，“KONICA MINOLTA PS BW 激光类驱动程序”和“KONICA MINOLTA PS 颜色激光类驱动程序”未按预期显示。

## 解决方法

若要解决此问题，请手动下载并安装要从Windows 更新目录中安装的打印机驱动程序。 在“症状”部分中提到的驱动程序示例中，请根据以下过程进行安装。

1. 转到[Windows 更新目录](https://www.catalog.update.microsoft.com/home.aspx)。
2. 在搜索框中，输入要下载的驱动程序的关键字，例如“Windows 10 KONICA MINOLTA PS BW 激光类驱动程序”，然后选择“ **搜索**”。
3. 显示列表后，选择 **目标驱动程序的“下载** ”按钮，并将其保存到任何文件夹。

   ![Microsoft更新目录中 Windows 10 KONICA MINOLTA PS BW 激光类驱动程序的搜索结果的屏幕截图。](media/not-all-printer-drivers-from-windows-update-in-add-printer-wizard/microsoft-update-catelog.png)
4. 将保存.cab文件解压缩到任何文件夹中。
5. 执行 [“症状](#symptoms) ”部分中的步骤 1 到 6。
6. 在 **“安装打印机驱动程序** ”屏幕上，选择“ **有磁盘**”。

   ![具有磁盘的屏幕截图...“添加打印机向导”对话框中的“仅泛型/文本仅打印机”选项。](media/not-all-printer-drivers-from-windows-update-in-add-printer-wizard/select-have-disk-button.png)
7. 浏览到步骤 4 中提取的文件夹，然后选择“ **确定**”。

   ![复制制造商的文件的屏幕截图：“从磁盘安装”对话框中的输入框。](media/not-all-printer-drivers-from-windows-update-in-add-printer-wizard/browse-disk.png)
8. 显示打印机驱动程序列表后，选择目标驱动程序，然后选择“下一步**”**以完成其余向导步骤并完成所有安装任务。 请联系打印机供应商，了解有关必须为正在使用的打印机下载哪些打印机驱动程序的详细信息。

   ![“安装打印机驱动程序”对话框中打印机驱动程序列表的屏幕截图。](media/not-all-printer-drivers-from-windows-update-in-add-printer-wizard/install-printer-driver.png)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/printing/not-all-printer-drivers-from-windows-update-in-add-printer-wizard)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
