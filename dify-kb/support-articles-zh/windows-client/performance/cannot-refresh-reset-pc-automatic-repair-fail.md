# Windows 8 中自动修复失败后无法"刷新"或"重置"电脑

本文解决自动修复失败后无法刷新或重置电脑的问题。

_适用于：_ &nbsp; Windows 8  
_原始 KB 编号：_ &nbsp; 2823223

## 症状

考虑以下场景：

- 你的电脑上安装了 Windows 8 或 Windows 8 Pro。
- 电脑无法正常启动进入 Windows，于是启动"自动修复"尝试修复 Windows。
- 自动修复无法修复你的电脑，你选择**高级选项**。
- 选择**疑难解答**后，你选择**"刷新你的电脑"**或**"重置你的电脑"**。

在此场景下，恢复可能会失败，你会被退回到 WinRE 主界面。

## 原因

如果 System 或 Software 注册表配置单元（registry hive）损坏，则可能会出现此问题。

## 解决方法

请按以下步骤尝试解决此问题。

> **备注**
> 仅当系统已无法启动、你正尝试在 Windows RE 中使用**"刷新你的电脑"**或**"重置你的电脑"**选项时，才应使用这些步骤。

1. 自动修复无法修复你的电脑后，选择**高级选项**，然后选择**疑难解答**。
2. 选择**高级选项**，然后选择"命令提示符"。
3. 如果系统提示，请输入该用户名的密码。
4. 在命令提示符下，通过键入以下命令转到 \windows\system32\config 文件夹：

    ```console
    cd %windir%\system32\config
    ```

5. 使用以下命令将 System 和 Software 注册表配置单元重命名为 System.001 和 Software.001：

    ```console
    ren system system.001  
    ren software software.001
    ```
> **备注**
    > 重命名 Software 配置单元会导致无法使用"刷新你的电脑"选项。如果要使用"刷新你的电脑"选项，请只重命名 System 配置单元。如果 Software 配置单元也已损坏，则可能无法使用"刷新你的电脑"选项。
6. 键入 exit（不带引号）退出命令提示符，并将电脑重启回"自动修复"界面。
7. 选择**高级选项**，然后选择**疑难解答**，接着选择**"刷新你的电脑"**或**"重置你的电脑"**。

## 更多信息

使用**"重置你的电脑"**选项将删除硬盘上的所有文件，并将电脑恢复到 OEM 在电脑上预装的 Windows 8 版本。购买电脑后安装的所有新应用程序都需要重新安装。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/cannot-refresh-reset-pc-automatic-repair-fail)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权，本文档为社区中文翻译）
