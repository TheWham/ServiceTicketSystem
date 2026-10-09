# 如何确定计算机上提供和配置硬件 DEP

本文介绍如何确定计算机上提供和配置硬件 DEP。

*原始 KB 数：* 912923

## 简介

数据执行防护（DEP）是一组硬件和软件技术，用于对内存执行额外检查，以帮助防范恶意代码攻击。

硬件强制执行的 DEP 会将进程中的所有内存位置标记为非可执行文件，除非该位置显式包含可执行代码。 恶意代码攻击尝试从非可执行内存位置插入和运行代码。 DEP 通过截获这些攻击并引发异常来帮助防止这些攻击。

本文介绍使用硬件强制 DEP 的要求。 本文还介绍如何确认硬件 DEP 在 Windows 中正常工作。

## 详细信息

### 使用硬件强制 DEP 的要求

若要使用硬件强制执行的 DEP，必须满足以下所有条件：

1. 计算机的处理器必须支持硬件强制执行的 DEP。

   许多最新的处理器支持硬件强制执行的 DEP。 高级微型设备（AMD）和 Intel Corporation 都定义了并交付了与 DEP 兼容的 Windows 兼容体系结构。 此处理器支持可能称为 NX（无执行）或 XD （执行禁用） 技术。 若要确定计算机的处理器是否支持硬件强制执行的 DEP，请联系计算机的制造商。
2. 必须在 BIOS 中启用硬件强制执行的 DEP。

   在某些计算机上，可以在 BIOS 中禁用对硬件强制实施 DEP 的处理器支持。 无法禁用此支持。 根据计算机制造商，禁用此支持的选项可能标记为“数据执行防护”、“XD”、“执行禁用”或“NX”。
3. 计算机必须安装了 Service Pack 2 或安装了 Service Pack 1 的 Windows Server 2003。

   注意

   32 位版本和 64 位版本的 Windows 都支持硬件强制实施 DEP。 Windows XP Media Center Edition 2005 和 Microsoft Windows XP Tablet PC Edition 2005 包括 Windows XP SP2 的所有功能和组件。
4. 必须为计算机上的程序启用硬件强制执行的 DEP。

   在 64 位版本的 Windows 中，始终为 64 位本机程序启用硬件强制 DEP。 但是，根据配置，32 位程序可能会禁用硬件强制实施 DEP。

有关如何使用 Service Pack 2 在 Windows XP 中配置内存保护的信息，请访问以下Microsoft网站：  
<https://technet.microsoft.com/library/cc700810.aspx>

### 如何确认硬件 DEP 在 Windows 中正常工作

若要确认硬件 DEP 在 Windows 中正常工作，请使用以下方法之一。

#### 方法 1：使用 `Wmic` 命令行工具

可以使用 `Wmic` 命令行工具检查 DEP 设置。 若要确定硬件强制 DEP 是否可用，请执行以下步骤：

1. 单击“**开始”，单击“运行**”**，在**“打开**”框中键入 cmd，然后单击“**确定****”。
2. 在命令提示符下，键入以下命令，然后按 Enter：

   ```
   wmic OS Get DataExecutionPrevention_Available
   ```

如果输出为“TRUE”，则硬件强制执行的 DEP 可用。

若要确定当前的 DEP 支持策略，请执行以下步骤。

1. 单击“**开始”，单击“运行**”**，在**“打开**”框中键入 cmd，然后单击“**确定****”。
2. 在命令提示符下，键入以下命令，然后按 Enter：

   ```
   wmic OS Get DataExecutionPrevention_SupportPolicy
   ```

   返回的值将为 0、1、2 或 3。 此值对应于下表中所述的 DEP 支持策略之一。

   | DataExecutionPrevention\_SupportPolicy属性值 | 策略级别 | 说明 |
   | --- | --- | --- |
   | 2 | OptIn （默认配置） | 只有 Windows 系统组件和服务应用 DEP |
   | 3 | OptOut | 为所有进程启用 DEP。 管理员可以手动创建未应用 DEP 的特定应用程序的列表 |
   | 1 | AlwaysOn | 为所有进程启用 DEP |
   | 0 | AlwaysOff | 未为任何进程启用 DEP |

   注意

   若要验证 Windows 是否在启用了硬件 DEP 的情况下运行，请检查Win32\_OperatingSystem类的DataExecutionPrevention\_Drivers属性。 在某些系统配置中，可以使用 Boot.ini 文件中的 /nopae 或 /execute 开关禁用硬件 DEP。 若要检查此属性，请在命令提示符处键入以下命令：  
   wmic OS 获取DataExecutionPrevention\_Drivers

#### 方法 2：使用图形用户界面

若要使用图形用户界面来确定 DEP 是否可用，请执行以下步骤：

1. 单击“**开始**”，单击“运行**”**，键入`wbemtest`“**打开**”框，然后单击“**确定**”。
2. 在“Windows Management Instrumentation 测试器”  对话框中，单击“连接” 。
3. 在“连接**”对话框顶部**的框中，键入 root\cimv2，然后单击“**连接**”。
4. 单击 **枚举实例**。
5. 在**“类信息**”对话框中，在 Enter 超级类名称**框中键入Win32\_OperatingSystem**，然后单击“**确定**”。
6. 在 **“查询结果** ”对话框中，双击顶部项。

   注意

   此项以“Win32\_OperatingSystem.Name=Microsoft...”开头
7. 在**“对象编辑器**”对话框中，找到“属性**”区域中的DataExecutionPrevention\_Available属性**。
8. 双击 **DataExecutionPrevention\_Available**。
9. 在**“属性编辑器**”对话框中，记下“值**”框中的值**。  
   如果值为 TRUE，则硬件 DEP 可用。

注意

- 若要确定运行 DEP 的模式，请检查Win32\_OperatingSystem类的DataExecutionPrevention\_SupportPolicy属性。 方法 1 末尾的表描述了每个支持策略值。
- 若要验证是否在 Windows 中启用了硬件 DEP，请检查Win32\_OperatingSystem类的DataExecutionPrevention\_Drivers属性。 在某些系统配置中，可以使用 Boot.ini 文件中的 /nopae 或 /execute 开关禁用硬件 DEP。

本文中提到的第三方产品由 Microsoft 以外的其他公司提供。 对于这些产品的性能或可靠性，Microsoft 不作任何暗示保证或其他形式的保证。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/determine-hardware-dep-available)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
