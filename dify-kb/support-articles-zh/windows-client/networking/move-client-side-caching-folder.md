# 将客户端缓存 （CSC） 文件夹移动到 Windows 中的新位置

本文介绍如何在 Windows 中移动 CSC 文件夹。 它还介绍如何在将 CSC 缓存文件夹移动到新位置后删除旧缓存文件夹。

*适用于：* Windows 10 版本 2004、Windows 10 版本 1909、Windows 10 版本 1709、Windows 7 Service Pack 1  
*原始 KB 编号：* 942960

重要

本文包含有关如何修改注册表的信息。 修改注册表之前，一定要先对其进行备份。 并且一定要知道在发生问题时如何还原注册表。 有关如何备份、还原和修改注册表的详细信息，请参阅[如何在 Windows 中备份和还原注册表](https://support.microsoft.com/help/322756)。

## 为何无法使用Cachemov.exe

Windows Vista 和更高版本的 Windows 不支持Cachemov.exe工具。 尝试使用 Cachemov.exe 工具在 Windows Vista 和更高版本的 Windows 中移动 CSC 文件夹时，可能会收到以下错误消息：

> cachemov.exe - 找不到序号  
> 序号 51 不能位于动态链接库CSCDLL.dll

注意

CSC 文件夹是 Windows Vista 存储脱机文件的文件夹。

Cachemov.exe工具用于在包含以下操作系统之一的计算机上移动 CSC 文件夹：

- Windows Server 2003
- Windows XP
- Windows 2000 Server

## 移动 CSC 文件夹

通常，脱机文件缓存位于以下目录中： `%systemroot%\CSC`

若要将 CSC 缓存文件夹移动到 Windows Vista、Windows 7、Windows 8.1 和 Windows 10 中的另一个位置，请执行以下步骤：

1. 打开权限提升的命令提示符。 选择“**启动****>所有程序**>**附件**”，右键单击命令提示符，然后选择“**以管理员**身份运行”。

   如果系统提示输入管理员密码或进行确认，请键入密码或选择“允许”。
2. 键入以下命令，然后按 Enter：

   ```
   REG ADD "HKLM\System\CurrentControlSet\Services\CSC\Parameters" /v MigrationParameters /t REG_DWORD /d 1 /f
   ```
3. 键入以下命令，然后按 Enter：

   ```
   c:\windows\system32\migwiz\migwiz.exe
   ```

   注意

   可能需要根据情况替换其他驱动器号。
4. 在 Windows 简易传输向导中，选择以下选项：

   1. 选择“ **启动新传输**”。
   2. 选择 **“我的旧计算机**”。
   3. 选择“ **使用 CD、DVD 或其他可移动媒体**”。
   4. 选择“外部硬盘” **或“网络位置**”。
   5. 键入要在其中保存 Savedata.mig 文件的路径，然后选择“ **下一步**”。
   6. 选择“高级选项”。
   7. 在 **“选择要传输** 的用户帐户、文件和设置”对话框中，执行以下步骤：

      1. 清除所有复选框。
      2. 在 **“系统和程序设置”下**，展开 **“Windows 设置**>**网络和 Internet**”，然后选择“ **脱机文件** ”复选框。
      3. 对页面上列出的每个用户重复上一步。
      4. 选择“下一步**”**开始传输过程。

## 更改注册表设置

警告

如果使用注册表编辑器或使用其他方法错误地修改了注册表，则可能会发生严重问题。 这些问题可能需要重新安装操作系统才能解决。 Microsoft 不能保证可以解决这些问题。 您应自行承担修改注册表的风险。

按照以下步骤检查计算机上使用的缓存大小：

1. 在**控制面板**中，选择“网络”和“**Internet>****脱机文件**”。
2. 在**“脱机文件**”框中选择“磁盘使用情况**”选项卡**。

如果缓存大小为零，则必须仅更改以下列表中的注册表设置。 或者，如果缓存大小设置为某个值，请执行所有步骤。

1. 选择“开始”**，在“搜索**”框中键入 regedit*，然后按 Enter。*****
2. 找到以下注册表子项，然后右键单击它： `HKEY_LOCAL_MACHINE\System\CurrentControlSet\Services\CSC`
3. 右键单击 **CSC**，指向“新建**”**，然后选择“**密钥**”。
4. *在名称框中键入参数*。
5. 右键单击“参数**”，指向“新建**”**，然后选择“**字符串值**”。**
6. 若要命名新值，请键入 *CacheLocation*，然后按 Enter。
7. 右键单击 **CacheLocation**，然后选择“ **修改**”。
8. 在 **“值”数据** 框中，键入要在其中创建缓存的新文件夹的名称。

   注意

   对文件夹名称使用 Microsoft Windows NT 格式。 例如，如果希望缓存位置为 `d:\csc`，请键入 `\??\d:\csc`。
9. 退出 **注册表编辑器**，然后重新启动计算机。

## 继续传输过程

1. 在提升的命令提示符下，键入以下命令，然后按 Enter： `c:\windows\system32\migwiz\migwiz.exe`
2. 在 Windows 简易传输向导中，选择以下选项：

   1. 选择“ **继续正在进行的**传输”。
   2. 选择“ **否”，我已将文件和设置复制到 CD、DVD 或其他可移动媒体**。
   3. 在外部硬盘或网络位置**上选择**。
   4. 在“移动 CSC 文件夹[”部分的步骤 4e](#move-the-csc-folder) 中创建的 Savedata.mig 文件的路径。
   5. 将旧计算机上的用户帐户映射到新计算机上的相应用户帐户。
   6. 选择“**下一次>传输”。**
   7. 重新启动计算机。

## 删除旧缓存

移动所有文件后，请按照以下步骤从 Windows Vista 候选版本 1 （RC1） 生成中删除旧缓存：

1. 在提升的命令提示符下，键入 `takeown /r /f c:\windows\csc` 命令，然后按 Enter。
2. 在提升的命令提示符下，键入 `rd /s c:\windows\csc` 命令，然后按 Enter。

注意

此方法删除旧缓存的限制是，Takeown.exe只能处理不超过 `MAX_PATH` （路径的最大长度）的路径。 路径的最大长度为 260 个字符。 如果此路径长度超过 `MAX_PATH`该长度，则 takeown 命令将失败。

## 参考

有关如何更改 CSC 文件夹的位置的详细信息，请参阅 [如何在 Windows Vista](https://support.microsoft.com/help/937475) 中配置 CacheLocation 注册表值来更改 CSC 文件夹的位置。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/move-client-side-caching-folder)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
