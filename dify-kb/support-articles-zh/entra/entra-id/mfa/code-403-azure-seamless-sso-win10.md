# 在 Windows 10 上使用 Azure 无缝单一登录时出现代码 403（禁止）

本文可以帮助你解决在 Windows 10 上使用 Azure 无缝单一登录时收到代码 403（禁止）的问题。

*原始产品版本：* Microsoft Entra ID、Windows 10  
*原始 KB 数：* 4135083

## 现象

升级到 Windows 10 后，Azure 无缝单一登录身份验证不起作用。 出现此问题时，你可能会收到以下错误消息：

> 集成 Windows 身份验证失败，状态代码 403（禁止）。

## 解决方法

若要解决该问题，请执行以下步骤：

1. 检查下列组策略对象，并确保将其设置为“未定义”：

   **网络安全：配置 Kerberos 允许的加密类型**

   如果更新组策略设置，请运行 `gpupdate /force` 将更改推送到设备。
2. 启动注册表编辑器，浏览到以下子项：

   `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System\kerberos\parameters`
3. 删除 `supportedencryptiontypes` DWORD 条目（如果存在）。
4. 重启设备。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/mfa/code-403-azure-seamless-sso-win10)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
