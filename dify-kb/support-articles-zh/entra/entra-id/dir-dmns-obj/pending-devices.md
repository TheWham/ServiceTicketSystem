# Microsoft Entra ID 中的挂起设备

注意

本文有帮助吗? 你的输入对我们很重要。 请使用此页上的 **“反馈** ”按钮告诉我们本文为你工作得有多好，或者我们如何改进它。

## 总结

本文介绍设备为何在Microsoft Entra ID 中处于挂起状态，以及如何排查和解决与挂起设备相关的问题。

挂起的设备是从本地 Active Directory 同步到 Microsoft Entra ID 的设备，这些设备没有通过 Microsoft Entra 设备注册服务完成注册。 当设备注册状态挂起时，设备无法完成任何授权或身份验证请求，例如请求主刷新令牌[进行单一](/zh-cn/azure/active-directory/devices/concept-primary-refresh-token)登录，或应用[基于设备的条件访问策略](/zh-cn/mem/intune/protect/create-conditional-access-intune)。

注意

待处理状态仅适用于 Microsoft Entra 混合联接设备。

## 为什么设备可能处于挂起状态

为本地设备在 Microsoft Entra Connect Sync 中配置 **Microsoft Entra 混合加入** 任务时，该任务会将设备对象同步到 Microsoft Entra ID，并在设备完成设备注册之前临时将设备的注册状态设置为“挂起”。 此状态存在，因为必须先将设备添加到 Microsoft Entra 目录，然后才能注册它。 有关设备注册过程的详细信息，请参阅[工作流程：设备注册](/zh-cn/azure/active-directory/devices/device-registration-how-it-works#hybrid-azure-ad-joined-in-managed-environments)。

有关如何对挂起的设备进行故障排除的详细信息，请参阅以下视频：

## 设备如何卡在挂起状态

两种情况可能使设备处于挂起状态。

### 将新加入本地域的设备同步到 Microsoft Entra ID

如果无法完成设备注册过程，新的本地设备可能会停滞在挂起状态。 多种因素可能会导致此问题，例如设备未连接到注册服务。

若要排查设备注册问题，请参阅：

- [对 Microsoft Entra 混合加入的设备进行故障排除](/zh-cn/azure/active-directory/devices/troubleshoot-hybrid-join-windows-current)
- [测试设备注册连接](/zh-cn/samples/azure-samples/testdeviceregconnectivity/testdeviceregconnectivity/)

### 已注册设备的状态更改为挂起

此问题可能发生在以下方案中：

1. 将设备对象移动到Microsoft Entra Connect Sync 中不在同步范围内的另一个组织单位（OU）。
2. Microsoft Entra Connect Sync 会将此更改识别为在本地 Active Directory中删除的设备对象。 因此，它会删除Microsoft Entra ID 中的设备。
3. 将设备对象移回同步范围内的 OU。
4. Microsoft Entra Connect Sync 在 Microsoft Entra ID 中为此设备创建待处理的设备对象。
5. 设备无法完成设备注册过程，因为它以前已注册。

若要解决此问题，请在提升的命令提示符下运行 `dsregcmd /leave` 以注销设备，然后重启设备。 设备通过计划的任务重新初始化设备注册过程。 对于基于 Windows 10 的设备，计划任务位于“Microsoft 任务计划程序库”“Microsoft”>“Windows”“工作区加入”>“自动设备加入任务”下>>。

## 获取待处理设备列表

1. 安装 [Microsoft Graph PowerShell SDK](/zh-cn/powershell/microsoftgraph/installation?view=graph-powershell-1.0&preserve-view=true) 以运行 Microsoft Graph PowerShell 命令。
2. 请使用 `Connect-MgGraph` 命令登录到 Microsoft Entra 租户。 有关详细信息，请参阅 [Microsoft Graph PowerShell SDK](/zh-cn/powershell/microsoftgraph/get-started?view=graph-powershell-1.0&preserve-view=true) 入门。
3. 对所有挂起的设备进行计数：

   ```
   (Get-MgDevice -All -Filter "TrustType eq 'ServerAd'" | Where-Object{((-not $_.AlternativeSecurityIds))}).count
   ```

   还可以将返回的数据保存在 CSV 文件中：

   ```
   Get-MgDevice -All -Filter "TrustType eq 'ServerAd'" | Where-Object{(-not $_.AlternativeSecurityIds)} | select-object -Property AccountEnabled, Id, DeviceId, DisplayName, OperatingSystem, OperatingSystemVersion, TrustType | export-csv pendingdevicelist-summary.csv -NoTypeInformation
   ```

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/dir-dmns-obj/pending-devices)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
