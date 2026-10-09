# 关机或重启 Windows 时 Explorer.exe 出现应用程序错误

## 症状

Windows 关机时，你会收到以下错误消息：

> explorer.exe - 应用程序错误  
位于 \<内存地址\> 的指令引用了 \<内存地址\> 的内存。该内存不能为 \<read 或 write\>。  
> 单击"确定"终止程序。

> **备注**
> 错误消息显示后，关机过程仍会继续。该错误不会对电脑造成任何损害，可以放心忽略。

当你右键单击开始按钮（或按 Windows 键 + <kbd>X</kbd>），然后使用"关机或注销"选项来关闭或重启 Windows 时，会出现此问题。

## 原因

出现此错误是因为在关机过程中，**Explorer.exe** 进程访问了已被释放的内存。

## 解决方法

要解决此问题，请使用"设置"超级按钮（Settings charm）来关闭或重启 Windows。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/application-error-explorer-shut-down)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权，本文档为社区中文翻译）
