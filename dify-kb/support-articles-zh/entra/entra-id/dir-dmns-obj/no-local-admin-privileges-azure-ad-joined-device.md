# Microsoft已加入 Entra 的设备上没有本地管理员组特权

本文介绍如何解决为用户分配或激活已加入 Azure AD 的设备本地管理员角色的方案，但在用户登录到已加入 Microsoft Entra 的设备后，用户不会收到本地管理员组权限。

## 原因 1：用户在使用缓存的 PRT 时分配了已加入 Azure AD 的设备本地管理员角色

已将已加入 Azure AD 的设备本地管理员角色分配给仍在其本地设备上使用缓存的主刷新令牌（PRT）的用户。

#### 检查是否存在 PRT

若要检查活动 [PRT](/zh-cn/azure/active-directory/devices/concept-primary-refresh-token) 是否存在，请在命令提示符处运行以下 [dsregcmd](/zh-cn/azure/active-directory/devices/troubleshoot-device-dsregcmd) 命令：

```
dsregcmd /status
```

在命令输出中 [，找到 SSO 状态](/zh-cn/azure/active-directory/devices/troubleshoot-device-dsregcmd#sso-state) 部分。 （`SSO` 表示“单一登录”。以前更新 PRT 的时间显示在 `AzureAdPrtUpdateTime` 字段中。

## 原因 2：已为缓存 PRT 的用户激活 Privileged Identity Management （PIM）

你使用 [Privileged Identity Management](/zh-cn/azure/active-directory/privileged-identity-management/pim-configure) （PIM） 将用户激活到已加入 Microsoft Entra 的设备本地管理员角色，但他们在本地设备上具有缓存的 PRT。

有关确定 PRT 是否处于活动状态的说明，请参阅 [检查是否存在 PRT](#check-for-the-presence-of-a-prt)。

## 解决方案 1：等待 PRT 续订

云身份验证提供程序（CloudAP）插件每四小时续订一次 PRT。 如果用户在 CloudAP 插件续订 PRT 之前等待长达四个小时的时间间隔，则可以按预期登录并接收本地管理员组权限。

## 解决方案 2：获取新的 PRT

如果要立即修复缺少的权限问题，以便用户无需等待，请使用新的 PRT。 获取新的 PRT 是一个多部分过程。

注意

如果缺少的权限问题是由显式分配角色而不是激活 PIM 引起的，请跳过第 1 部分。 相反，请从第 2 部分开始 [：检查本地管理员权限](#part-2-check-for-local-administrator-permissions)。

### 第 1 部分：（仅 PIM 用户）激活 PIM 并验证角色激活是否已完成

按照 PIM [中“激活Microsoft Entra 角色”中的](/zh-cn/azure/active-directory/privileged-identity-management/pim-how-to-activate-role)说明为用户激活[已加入 Azure AD 的设备本地管理员](/zh-cn/azure/active-directory/roles/permissions-reference#azure-ad-joined-device-local-administrator)角色。 然后，按照Azure 门户中的以下步骤验证该用户的角色激活是否已完成：

1. 在[Azure 门户](https://portal.azure.com)中，搜索并选择Microsoft **Entra Privileged Identity Management**。
2. 在 PIM 导航窗格中，找到 **“任务”** 标题，然后选择“ **我的角色**”。
3. 在“我的角色” **中 |Microsoft“条目角色** ”页，选择“ **活动分配** ”选项卡。
4. 在 **“角色** ”列中，确保 **显示“已加入 Azure AD 的设备本地管理员** ”角色。

### 第 2 部分：检查本地管理员权限

让用户按照以下步骤检查本地管理员权限：

1. 登录到 Windows 客户端计算机。
2. 选择“开始”，输入 *cmd*，然后在搜索结果中选择**命令提示符**。
3. 运行以下 [whoami](/zh-cn/windows-server/administration/windows-commands/whoami) 命令：

   ```
   whoami /all
   ```
4. 在命令输出中 `GROUP INFORMATION` ，找到该节，然后检查该组是否 `BUILTIN\Administrators` 显示在 `Group Name` 列中。 以下示例输出未在组信息中列出此组。 这意味着在 PIM 激活或显式分配 **已加入 Azure AD 的设备本地管理员** 角色之前获取缓存的 PRT。

   ```
   USER INFORMATION
   ----------------

   User Name             SID
   ===================== ==================================================
   someuser\contoso.corp S-1-12-3687709483-1112055202-2756941246-4106396469

   GROUP INFORMATION
   -----------------

   Group Name                                Type             SID          Attributes
   ========================================= ================ ============ ==================================================
   Mandatory Label\Medium Mandatory Level    Label            S-1-16-8192
   Everyone                                  Well-known group S-1-1-0      Mandatory group, Enabled by default, Enabled group
   BUILTIN\Remote Desktop Users              Alias            S-1-5-32-555 Mandatory group, Enabled by default, Enabled group
   BUILTIN\Users                             Alias            S-1-5-32-545 Mandatory group, Enabled by default, Enabled group
   NT AUTHORITY\REMOTE INTERACTIVE LOGON     Well-known group S-1-5-14     Mandatory group, Enabled by default, Enabled group
   NT AUTHORITY\INTERACTIVE                  Well-known group S-1-5-4      Mandatory group, Enabled by default, Enabled group
   NT AUTHORITY\Authenticated Users          Well-known group S-1-5-11     Mandatory group, Enabled by default, Enabled group
   NT AUTHORITY\This Organization            Well-known group S-1-5-15     Mandatory group, Enabled by default, Enabled group
   LOCAL                                     Well-known group S-1-2-0      Mandatory group, Enabled by default, Enabled group
   NT AUTHORITY\Cloud Account Authentication Well-known group S-1-5-64-36  Mandatory group, Enabled by default, Enabled group

   PRIVILEGES INFORMATION
   ----------------------

   Privilege Name                Description                          State
   =======================       ==================================== ========
   SeShutdownPrivilege           Shut down the system                 Disabled
   SeChangeNotifyPrivilege       Bypass traverse checking             Enabled
   SeUndockPrivilege             Remove computer from docking station Disabled
   SeIncreaseWorkingSetPrivilege Increase a process working set       Disabled
   SeTimeZonePrivilege           Change the time zone                 Disabled
   ```

   `BUILTIN\Administrators`如果组缺失，请继续第 3 部分以刷新 PRT。

### 第 3 部分：刷新 PRT 并验证是否收到预期角色

让用户按照以下步骤刷新 PRT 并验证他们现在是否具有预期角色：

1. 通过运行以下命令 `dsregcmd` 计划 PRT 的刷新：

   ```
   dsregcmd /refreshprt
   ```

   以下消息将出现：

   > `PRT refresh scheduled. Check AAD event logs for details.`
2. 等待一到两分钟，以刷新令牌。
3. 注销 Windows 会话，然后重新登录。
4. 运行以下 `whoami` 命令：

   ```
   whoami /groups
   ```
5. 检查该组是否 `BUILTIN\Administrators` 显示在 `Group Name` 列中。 如以下示例输出所示，该组现在应显示在组列表中：

   ```
   GROUP INFORMATION
   -----------------

   Group Name                                Type             SID                                                 Attributes
   ========================================= ================ =================================================== ==================================================
   Mandatory Label\Medium Mandatory Level    Label            S-1-16-8192
   Everyone                                  Well-known group S-1-1-0                                             Mandatory group, Enabled by default, Enabled group
   BUILTIN\Remote Desktop Users              Alias            S-1-5-32-555                                        Mandatory group, Enabled by default, Enabled group
   BUILTIN\Users                             Alias            S-1-5-32-545                                        Mandatory group, Enabled by default, Enabled group
   BUILTIN\Administrators                    Alias            S-1-5-32-544                                        Group used for deny only
   NT AUTHORITY\REMOTE INTERACTIVE LOGON     Well-known group S-1-5-14                                            Mandatory group, Enabled by default, Enabled group
   NT AUTHORITY\INTERACTIVE                  Well-known group S-1-5-4                                             Mandatory group, Enabled by default, Enabled group
   NT AUTHORITY\Authenticated Users          Well-known group S-1-5-11                                            Mandatory group, Enabled by default, Enabled group
   NT AUTHORITY\This Organization            Well-known group S-1-5-15                                            Mandatory group, Enabled by default, Enabled group
   LOCAL                                     Well-known group S-1-2-0                                             Mandatory group, Enabled by default, Enabled group
                                             Unknown SID type S-1-12-1-788341310-1134859379-3309005462-3346259773 Mandatory group, Enabled by default, Enabled group
   NT AUTHORITY\Cloud Account Authentication Well-known group S-1-5-64-36                                         Mandatory group, Enabled by default, Enabled group
   ```

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/dir-dmns-obj/no-local-admin-privileges-azure-ad-joined-device)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
