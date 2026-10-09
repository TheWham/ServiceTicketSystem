# 打开位于远程网络计算机上的共享文件夹中的文件时网络性能降低

本文有助于修复在远程网络计算机上打开位于共享文件夹中的文件时可能出现的网络性能缓慢问题。

*适用于：* Windows 7 Service Pack 1  
*原始 KB 编号：* 829700

## 现象

使用 Windows 资源管理器连接到网络上远程计算机上的共享文件夹时，双击该共享文件夹中的某个文件将其打开，可能需要比预期打开该文件的时间更长。 例如，当通过慢速连接打开Microsoft 办公室文档时可能会遇到此问题，例如广域网（WAN）上的 64 千比特/秒（kbps）集成服务数字网络（ISDN）连接）。

## 原因

出现此问题的原因是 Windows 资源管理器尝试获取有关远程共享的详细信息以及打开的文件。 此操作在连接缓慢时可能需要很长时间。

## 解决方法

重要

此部分（或称方法或任务）介绍了修改注册表的步骤。 但是，注册表修改不当可能会出现严重问题。 因此，按以下步骤操作时请务必谨慎。 作为额外保护措施，请在修改注册表之前先将其备份。 如果之后出现问题，您就可以还原注册表。 有关如何备份和还原注册表的详细信息，请单击以下文章编号以查看Microsoft知识库中的文章： [322756](https://support.microsoft.com/help/322756) 如何在 Windows 中备份和还原注册表

1. 将 **SuppressionPolicy** DWORD 值添加到以下注册表项： `HKEY_CLASSES_ROOT\*\Shellex\PropertySheetHandlers\CryptoSignMenu`  
   为此，请执行以下操作：

   1. 单击“开始”**，然后单击“运行”**。
   2. 在“打开”框中，键入“regedit”，然后单击“确定”。
   3. 找到并单击以下注册表项： `HKEY_CLASSES_ROOT\*\Shellex\PropertySheetHandlers\CryptoSignMenu`
   4. 在“编辑”菜单上，指向“新建”，然后单击“DWORD 值”。
   5. 键入 SuppressionPolicy，然后按 Enter。
   6. 在 **“编辑** ”菜单上，单击“ **修改**”。
   7. 单击 **“十六进制**”，在 **“值”数据** 框中键入 100000，然后单击“ **确定**”。
2. 将 **SuppressionPolicy** DWORD 值添加到以下注册表项： **HKEY\_CLASSES\_ROOT\\*\Shellex\PropertySheetHandlers\{3EA48300-8CF6-101B-84FB-666CCB9BCD32}**  
   为此，请执行以下操作：

   1. 在注册表编辑器中，找到并单击以下注册表项： **HKEY\_CLASSES\_ROOT\\*\Shellex\PropertySheetHandlers\{3EA48300-8CF6-101B-84FB-666CCB9BCD32}**
   2. 在“编辑”菜单上，指向“新建”，然后单击“DWORD 值”。
   3. 键入 SuppressionPolicy，然后按 Enter。
   4. 在 **“编辑** ”菜单上，单击“ **修改**”。
   5. 单击 **“十六进制**”，在 **“值”数据** 框中键入 100000，然后单击“ **确定**”。
3. 将 **SuppressionPolicy** DWORD 值添加到以下注册表项： **HKEY\_CLASSES\_ROOT\\*\Shellex\PropertySheetHandlers\{883373C3-BF89-11D1-BE35-080036B11A03}**  
   为此，请执行以下操作：

   1. 在注册表编辑器中，找到并单击以下注册表项： **HKEY\_CLASSES\_ROOT\\*\Shellex\PropertySheetHandlers\{883373C3-BF89-11D1-BE35-080036B11A03}**
   2. 在“编辑”菜单上，指向“新建”，然后单击“DWORD 值”。
   3. 键入 SuppressionPolicy，然后按 Enter。
   4. 在 **“编辑** ”菜单上，单击“ **修改**”。
   5. 单击 **“十六进制**”，在 **“值”数据** 框中键入 100000，然后单击“ **确定**”。
4. 将 **Flags** DWORD 值添加到以下注册表项： `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\SCAPI`  
   为此，请执行以下操作：

   1. 在注册表编辑器中，找到并单击以下注册表项： `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\SCAPI`
   2. 在“编辑”菜单上，指向“新建”，然后单击“DWORD 值”。
   3. 键入标志，然后按 Enter。
   4. 在 **“编辑** ”菜单上，单击“ **修改**”。
   5. 单击 **“十六进制**”，在 **“值”数据** 框中键入 00100c02，然后单击“ **确定**”。
   6. 退出注册表编辑器。

### 添加组策略

除了“更改注册表”部分中介绍的直接注册表修改之外，还可以使用组策略解决此问题。 管理员可以使用 **批准的** 密钥和 EnforceShellExtensionSecurity 策略来控制哪些 shell 扩展可以运行。 SuppressionPolicy 值绑定到 EnforceShellExtensionSecurity 策略。 可以添加此策略以启用修改后的 shell 行为。

为此，请按照下列步骤进行操作：

1. 单击“**开始**”，单击“运行**”**，键入 Gpedit.msc，然后单击“**确定**”。
2. 在左窗格中的“用户配置”下**，展开**“管理模板**”，展开**“Windows 组件**”，然后单击“**Windows 资源管理器**”。**
3. 在右窗格中，双击**“仅允许每个用户或批准的 shell 扩展**”，单击“已启用**”**，然后单击“**确定**”。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/slow-network-performance-remote-computer)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
