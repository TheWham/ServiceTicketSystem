# 一个或多个Microsoft Entra Connect 服务未启动

## 概要

本文介绍阻止Microsoft Entra Connect 服务启动的问题。

*原始产品版本：* Microsoft Entra ID、Office 365 标识管理  
*原始 KB 数：* 2995030

## 症状

你发现一个或多个 Microsoft Entra Connect 服务未启动。 例如，Microsoft Azure AD Sync 服务（ADSync）不会启动。

## 解决方案 1：在组策略中设置用户权限分配权限

如有必要，请进行组策略更改，以便 ADSync 服务帐户可以本地、作为服务登录，以及作为批处理作业登录。 由于域组策略优先于本地组策略，因此需要检查这两种类型的组策略的设置。

1. 选择“开始”，在搜索框中输入“gpedit.msc”，然后按 Enter 打开“本地组策略编辑器”管理单元。
2. 在控制台树中的“计算机配置”下，展开“Windows 设置”“安全设置”“本地策略”，然后选择“用户权限分配” 。
3. 验证是否已为以下策略设置添加了 ADSync 服务帐户：

   - **允许本地登录**
   - **作为批处理作业登录**
   - **作为服务登录**
4. 对于域组策略，请打开管理命令提示符。
5. 运行以下 [gpresult](/zh-cn/windows-server/administration/windows-commands/gpresult) 命令，该命令生成组策略报告：

   ```
   gpresult /H gpresult.htm
   ```
6. 打开生成的组策略报告 (gpresult.htm)。
7. 如果通过任何域组策略对象 (GPO) 应用“用户权限分配”设置，请使用域控制器中的“组策略管理”控制台 (gpmc.msc) 执行以下操作之一 ：

   - 从 **获奖 GPO** 中删除以下策略设置：

     - **允许本地登录**
     - **作为批处理作业登录**
     - **作为服务登录**
   - 更新 **获奖 GPO** 以包含 ADSync 服务帐户。
8. 如果对本地组策略或域组策略进行了任何更改，请重启计算机来应用更改。

## 解决方案 2：使用 事件查看器排查错误消息

还可以尝试通过扫描**事件查看器中的应用程序和**系统**日志来查找和**修复问题，以获取目录同步事件。 有关详细信息，请参阅[其他错误消息的疑难解答](installation-configuration-wizard-errors#troubleshoot-other-error-messages)。

## 解决方案 3：检查 Microsoft Entra ID Sync （ADSync） 服务帐户

如果解决方案 1 和 2 无法解决问题，请验证自定义 ADSync 服务帐户的状态。 确保帐户未过期或已禁用，否则 **用户必须在下次登录** 选项时更改密码，并且其密码未过期。 如果密码已更改，请使用 **Services.msc** 控制台更新 ADSync 服务帐户密码。

有关其他类型的 Windows 服务帐户的详细信息，请参阅 [ADSync 服务帐户](/zh-cn/entra/identity/hybrid/connect/concept-adsync-service-account)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/services-sync-not-start)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
