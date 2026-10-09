# Microsoft：创建无线配置文件时缺少受保护的 EAP （PEAP） 选项

本文提供了Microsoft：在某些情况下缺少受保护的 EAP （PEAP） 选项的问题的解决方案。

*适用于：* Windows 7 Service Pack 1  
*原始 KB 数：* 2699785

## 现象

此问题存在多个症状：

- Microsoft：在客户端上创建无线配置文件时，可能缺少受保护的 EAP （PEAP） 选项。
- Microsoft：使用窗口简易传输向导启动文件传输后，受保护的 EAP （PEAP） 选项可能会丢失。
- 远程访问连接管理器未启动。

## 原因

文件的默认位置SymRasMan.dll为 %SystemRoot%\System32\rastls.dll。 在安装 Symantec 防病毒或 Symantec Endpoint Protection 时，默认位置会在注册表中更改为 C：\Program Files\ Symantec\Symantec\Symantec Endpoint Protection \SymRasMan.dll。 卸载后，此位置不会撤消。 出现此问题的原因是注册表项在删除 Symantec Endpoint Protection 11.0 后，注册表值中指示的默认值或.dll文件不存在。

这 2 个注册表配置单元受到影响：

- `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\RasMan\PPP\EAP\25`
- `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\RasMan\PPP\EAP\13`

EAP 下以下键的值从 C：\System32\rastls.dll 修改为 C：\Program Files\Symantec\Symantec Endpoint Protection\SymRasMan.dll。

- ConfigUiPath
- IdentityPath
- InteractiveUIPath
- 路径

创建其值为 C：\Windows\ System32\rastls.dll的 4 个新注册表项。

- ConfigUiPathBack
- IdentityPathBack
- InteractiveUIPathBack
- PathBack

## 解决方法

重要

此部分（或称方法或任务）介绍了修改注册表的步骤。 但是，注册表修改不当可能会出现严重问题。 因此，按以下步骤操作时请务必谨慎。 作为额外保护措施，请在修改注册表之前先将其备份。 如果之后出现问题，您就可以还原注册表。

若要解决此问题，请修改注册表以更正 ConfigUiPath、IdentityPath、InteractiveUIPath 和 Path 的值。 为此，请按照下列步骤进行操作：

1. 单击“**开始**”，再单击“**运行**”，键入“*regedit&* ”，然后单击“**确定**”。
2. 找到并单击注册表子项：`HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\RasMan\PPP\EAP\13`。
3. 选择文件夹 13。
4. 将密钥的值更改为：ConfigUiPath、IdentityPath、InteractiveUIPath 和 Path 更改为：C：\Windows\ System32\rastls.dll
5. 导航到 `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\RasMan\PPP\EAP\25`。
6. 选择文件夹 25。
7. 将密钥的值更改为：ConfigUiPath、IdentityPath、InteractiveUIPath 和 Path to： C：\Windows\ System32\rastls.dll。
8. 删除文件夹 13 和 25 下的以下密钥。

   位置：

   - `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\RasMan\PPP\EAP\13`
   - `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\RasMan\PPP\EAP\25`

   注册表项：

   - ConfigUiPathBack
   - IdentityPathBack
   - InteractiveUIPathBack
   - PathBack
9. 存在注册表编辑器，然后重新启动计算机。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/microsoft-protected-eap-option-missing)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
