# 映射的网络驱动器可能无法在 Windows 10 版本 1809 中重新连接

本文提供了一种解决方法，说明映射的网络驱动器可能无法在 Windows 10 版本 1809 中重新连接的问题。

*适用于：* Windows 10 版本 1809  
*原始 KB 数：* 4471218

## 现象

在 Windows 10 版本 1809 中遇到以下问题：

- 在 Windows 资源管理器中，映射的网络驱动器上会显示一个红色 X。
- 在命令提示符下运行以下命令时，映射的网络驱动器显示为`net use`。
- 在通知区域中，通知显示以下消息：
  > 无法重新连接所有网络驱动器。

## 解决方法

Microsoft正在研究一项决议，预计解决方案将在 2018 年 11 月底之前提供。 监视 Windows 10 1809 更新历史记录 KB [4464619](https://support.microsoft.com/help/4464619/windows-10-update-history)中的映射驱动器主题。 目前，可以通过运行脚本在登录设备时自动重新连接映射的网络驱动器来解决此问题。 为此，请创建两个脚本文件，然后根据需要使用其中一种解决方法。

### 创建名为MapDrives.cmd的脚本文件

该文件应在常规运行，但不应在提升的命令提示符下运行，因为它应以与 Windows 资源管理器相同的权限运行：

```
PowerShell -Command "Set-ExecutionPolicy -Scope CurrentUser Unrestricted" >> "%TEMP%\StartupLog.txt" 2>&1
PowerShell -File "%SystemDrive%\Scripts\MapDrives.ps1" >> "%TEMP%\StartupLog.txt" 2>&1
```

### 创建名为 MapDrives.ps1 的脚本文件

该文件应在常规运行，但不应在提升的命令提示符下运行，因为它应以与 Windows 资源管理器相同的权限运行：

```
$i=3
while($True){
    $error.clear()
    $MappedDrives = Get-SmbMapping |where -property Status -Value Unavailable -EQ | select LocalPath,RemotePath
    foreach( $MappedDrive in $MappedDrives)
    {
        try {
            New-SmbMapping -LocalPath $MappedDrive.LocalPath -RemotePath $MappedDrive.RemotePath -Persistent $True -ErrorAction Stop
        } catch {
            Write-Host "There was an error mapping $($MappedDrive.RemotePath) to $($MappedDrive.LocalPath)"
        }
    }
    $i = $i - 1
    if($error.Count -eq 0 -Or $i -eq 0) {break}

    Start-Sleep -Seconds 30
}
```

### 解决方法

所有解决方法都应在标准用户安全上下文中执行。 在提升的安全上下文中执行脚本将阻止映射驱动器在标准用户上下文中可用。

#### 解决方法 1：创建启动项

注意

此解决方法仅适用于登录时具有网络访问权限的设备。 如果在登录时设备尚未建立网络连接，启动脚本将不会自动重新连接网络驱动器。

1. 将脚本文件 **MapDrives.cmd** 复制到以下位置：  
   **%ProgramData%\Microsoft\Windows\Start Menu\Programs\StartUp**
2. 将脚本文件 **MapDrives.ps1** 复制到以下位置： **%SystemDrive%\Scripts\**。
3. %TEMP% **\** 文件夹中创建日志文件 **StartupLog.txt**。
4. 退出登录后，再登录设备以打开映射的驱动器。

#### 解决方法 2：创建计划任务

注意

计划任务运行时，PowerShell 窗口会闪烁。

1. 将脚本文件 **MapDrives.ps1** 复制到以下位置： **%SystemDrive%\Scripts\**。
2. 在**任务计划程序**中，选择“**操作>创建任务”。**
3. 在“**创建任务**”对话框中的“**常规**”选项卡上，键入名称（如**映射网络驱动器**）和任务说明。
4. 选择“更改用户或组**”**，选择本地用户或组（例如 **LocalComputer\Users**），然后选择“**确定**”。
5. 在**“触发器**”选项卡上，选择“新建**”**，然后选择“**开始任务**”域的“登录****时”。
6. 在**“操作**”选项卡上，选择“新建**”**，然后选择“操作”字段的“**启动程序**”。
7. 为 **Program/script** 字段键入**Powershell.exe**。
8. 在 **“添加参数”（可选）** 字段中，键入以下内容：  
   **-windowstyle 隐藏 -command 。 >>\MapDrives.ps1 %TEMP%\StartupLog.txt 2>&1**
9. 在“ **开始”（可选）** 字段中，键入脚本文件的位置： **%SystemDrive%\Scripts\**。
10. **在“条件**”选项卡上，**仅当以下网络连接可用**选项时，选择“开始”，选择“**任何连接**”，然后选择“**确定**”。
11. 退出登录，然后重新登录设备以运行计划任务。

#### 解决方法 3：为 VPN 连接事件 ID 20225 创建计划任务

注意

事件 ID 20225 指示已成功建立虚拟专用网络（VPN）连接。

1. 将脚本文件 **MapDrives.ps1** 复制到以下位置： **%SystemDrive%\Scripts\**。
2. 在**任务计划程序**中，选择“**操作>创建任务”。**
3. 在“**创建任务**”对话框中的“**常规**”选项卡上，键入名称（如**映射网络驱动器**）和任务说明。
4. 选择“更改用户或组**”**，选择本地用户或组（例如 **LocalComputer\Users**），然后选择“**确定**”。
5. 在“**触发器**”选项卡上，选择“**新建**”，然后在“**开始任务**”域选择“**事件时触发**”。
6. 从**“日志**”下拉列表中选择**“应用程序**”，在**“源**”字段中键入 **RasClient**，并在**“事件 ID**”字段中键入 **20225**。 然后，选择“**确定**”。
7. 在**“操作**”选项卡上，选择“新建**”**，然后选择“操作”字段的“**启动程序**”。
8. 为 **Program/script** 字段键入**Powershell.exe**。
9. 在 **“添加参数”（可选）** 字段中，键入以下内容：  
   **-windowsstyle 隐藏 -command 。 >>\MapDrives.ps1 %TEMP%\StartupLog.txt 2>&1**
10. 在“ **开始”（可选）** 字段中，键入脚本文件的位置： **%SystemDrive%\Scripts\**。
11. **在“条件**”选项卡上，**仅当以下网络连接可用**选项时，选择“开始”，选择“**任何连接**”，然后选择“**确定**”。
12. 注销，再重新登录设备，以运行计划任务。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/mapped-network-drive-fail-reconnect)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
