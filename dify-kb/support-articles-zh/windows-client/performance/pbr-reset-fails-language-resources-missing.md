# 由于缺少语言资源，按钮重置失败

本文介绍一个问题：由于缺少语言资源，因此按下按钮重置失败，并提供了此问题的解决方法。

*适用于：*Windows 10 教育版版本 2004

## 现象

按钮重置（PBR）失败，用户收到错误消息， **重置电脑时出现问题。ErrorCode 0x80041002，WBEM\_E\_NOT\_FOUND**。

将个人计算机（PC）空闲并执行 PBR 重置命令后，会出现此问题。 执行 **SilentCleanup** 任务后，也可能出现此问题。 出现此问题的电脑具有多种语言资源。

## 原因

此错误是一个已知问题。 如果 PBR 在早期阶段失败并回滚，回滚过程会将 Windows 恢复环境（WinRE）启动配置数据（BCD）设置为默认 BCD 条目，但无法将默认 BCD 条目还原到操作系统（OS）。 将默认 BCD 条目更改为 WinRE 条目将导致 PBR 成功删除 WinRE 条目，并禁用 WinRE BCD。

以下步骤重现此错误：

1. 设置电脑而不包括语言资源 2020.8B。
2. 手动执行 SilentCleanupTask。
3. 将语言资源 2020.8B 应用于电脑。
4. 执行 PBR 重置/刷新。 PBR 失败并显示错误消息， **重置电脑**时出现问题。

此问题将在下一个 Windows OS 升级版本中得到解决。

## 解决方法

### 使用 Internet 的用户的解决方法

对于可以访问 Internet 的用户：

当问题重现时，WinRE 会正确安装，但其 BCD 条目被意外删除。 若要更正此问题，请从管理员命令提示符运行 `Reagentc /enable` 该命令两次。

首次 `Reagentc /enable` 运行时，它会询问 WinRE 的状态，并检测当前的 WinRE 状态。 虽然 `Reagentc /enable` 无法解决此问题，但它将执行清理，并将完全卸载 WinRE。 WinRE 文件仍然存在（复制到暂存位置），以便将来启用该文件。

第二次 `Reagentc /enable` 运行时，将清除 WinRE 文件。 然后，可以针对 OS 安装它，并在没有问题的情况下运行。

注意

`Reagentc /enable`首次运行时，它将报告错误消息，**无法更新启动配置数据**。

第 `Reagentc /enable` 二次运行时，将启用 WinRE。

### 没有 Internet 访问权限的用户的解决方法

对于无法访问 Internet 的用户：

1. 应用语言资源 2020.8B。
2. 运行 `Dism /online /cleanup-image /restorehealth`。
3. 运行 **PBR 重置/刷新**。
4. 尝试 PBR。
5. 重新运行 **PBR 重置/刷新**。
6. 运行 `reagentc /enable` 两次。
7. **运行 PBR 重置/刷新**。

注意

目前有一种正在调查的情况，其中 `Reagentc /enable` 不会修复之前讨论的问题。 如果暂存位置与 WinRE 的位置相同，则当前逻辑 `Reagentc /enable` 将不起作用。 Microsoft正在更新逻辑 `Reagentc /enable`，并将作为最新累积更新（LCU）的一部分释放更新的命令。

## 详细信息

- [一键重置](/zh-cn/windows-hardware/manufacture/desktop/push-button-reset-overview)
- [按钮重置的工作原理](/zh-cn/windows-hardware/manufacture/desktop/how-push-button-reset-features-work)
- [Windows 恢复环境 (Windows RE)](/zh-cn/windows-hardware/manufacture/desktop/windows-recovery-environment--windows-re--technical-reference)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/pbr-reset-fails-language-resources-missing)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
