# 排查错误 SSPR\_0029：组织未正确设置密码重置本地配置

本文可帮助你排查自助密码重置（SSPR）错误“SSPR\_0029：组织尚未正确设置密码重置的本地配置”，该配置发生在用户或管理员输入并确认 SSPR 页面上的新密码。

## 现象

用户或管理员执行以下步骤，然后收到错误 `SSPR_0029` ：

1. 在域中的Microsoft帐户登录页或Microsoft Azure 登录页 <https://login.microsoftonline.com> 中，用户或管理员选择 **“无法访问你的帐户？”**、 **忘记了我的密码**或 **立即**重置。
2. 用户或管理员选择 **工作或学校帐户** 帐户类型。 然后，会重定向到 SSPR 页面 <https://passwordreset.microsoftonline.com> ，开始 **返回到帐户** 流。
3. 在 **“你是谁”** 屏幕上，用户或管理员输入其用户 ID，完成不区分大小写的 captcha 安全质询，然后选择“ **下一步**”。
4. 在**登录时遇到问题的原因？**屏幕上，用户或管理员选择“”。
5. 在 **选择新密码** 屏幕上，用户或管理员输入并确认新的密码字符串，然后选择“ **完成**”。 然后，将显示“ **我们很抱歉** ”的屏幕，并显示以下消息：

   > SSPR\_0029：组织未正确设置重置密码的本地配置。
   >
   > 如果你是管理员，可以从“排查密码写回问题”一文获取详细信息。 如果你不是管理员，可以在联系管理员时提供此信息。

## 原因 1：无法使用密码写回重置已同步 Windows Active Directory 管理员的密码

你是属于本地 Active Directory[受保护组](/zh-cn/windows-server/identity/ad-ds/plan/security-best-practices/appendix-c--protected-accounts-and-groups-in-active-directory)的已同步 Windows Active Directory 管理员，不能使用 SSPR 和密码写回重置本地密码。

### 解决方案：无（行为设计）

出于安全性考虑，本地 Active Directory 受保护组中存在的管理员帐户不能与密码写回一起使用。 管理员可以在云中更改其密码，但无法重置忘记的密码。 有关详细信息，请参阅 [自助式密码重置写回在 Microsoft Entra ID](/zh-cn/azure/active-directory/authentication/concept-sspr-writeback) 中的工作原理。

## 原因 2：AD DS 连接器帐户没有正确的 Active Directory 权限

同步的用户缺少 Active Directory 中的正确权限。

### 解决方案：解决 Active Directory 权限问题

若要解决影响 Active Directory 权限的问题，请参阅 [密码写回访问权限和权限](password-writeback-access-rights-permissions)。

### 解决方法：面向其他 Active Directory 域控制器

注意

密码写回依赖于旧版 API [NetUserGetInfo](/zh-cn/windows/win32/api/lmaccess/nf-lmaccess-netusergetinfo)。 API `NetUserGetInfo` 需要 Active Directory 中一组复杂的允许权限，这些权限可能难以识别，尤其是在域控制器上运行Microsoft Entra Connect 服务器时。 有关详细信息，请参阅 [使用 NetUserGetInfo 和类似 API 的应用程序依赖于对某些 Active Directory 对象的](../../../windows-server/identity/netuser-netgroup-fails-with-access-denied)读取访问权限。

是否有一个方案：Microsoft Entra Connect 服务器在域控制器上运行，并且无法解析 Active Directory 权限？ 在这种情况下，我们建议在成员服务器上而不是域控制器上部署 Microsoft Entra Connect 服务器。 或者，使用以下步骤将 Active Directory 连接器配置为 **仅使用首选域控制器** ：

1. 在 **“开始** ”菜单上，搜索并选择“ **同步服务管理器**”。
2. 在 **“同步服务管理器** ”窗口中，选择“ **连接器** ”选项卡。
3. 右键单击连接器列表中的 Active Directory 连接器，然后选择“ **属性**”。
4. 在**“属性**”对话框的**“连接器设计器**”窗格中，选择“**配置目录分区**”。
5. 在 **“配置目录分区** ”窗格中，选择 **“仅使用首选域控制器** ”选项，然后选择“ **配置**”。
6. 在 **“配置首选 DC** ”对话框中，添加指向本地主机不同的域控制器（或域控制器）的一个或多个服务器名称。
7. 若要保存更改并返回到主窗口，请选择“ **确定** ”三次，包括在显示高级配置免责声明的 **“警告** ”对话框中。

## 原因 3：不允许服务器对安全帐户管理器进行远程调用（SAM）

在这种情况下，将记录两个类似的应用程序错误事件：事件 ID 33004 和 6329。 事件 ID 6329 不同于 33004，因为在服务器尝试对 SAM 进行远程调用时，它包含 `ERROR_ACCESS_DENIED` 堆栈跟踪中的错误代码：

> ERR\_：MMS（####）：admaexport.cpp（2944）：无法获取用户信息：Contoso\MSOL\_############。 错误代码：ERROR\_ACCESS\_DENIED

如果 Microsoft Entra Connect 服务器或域控制器已应用或已对域组策略对象（GPO）或服务器本地安全策略应用强化安全设置，则可能会出现这种情况。 若要检查情况是否如此，请执行以下步骤：

1. 打开管理命令提示符窗口，并运行以下命令：

   ```
   md C:\Temp
   gpresult /h C:\Temp\GPreport.htm
   start C:\Temp\GPreport.htm
   ```
2. 在 *Web 浏览器中打开 C：\Temp\gpresult.htm* 文件，然后展开>> 然后，检查是否有名为 [“网络访问”的设置：限制允许对 SAM](/zh-cn/windows/security/threat-protection/security-policy-settings/network-access-restrict-clients-allowed-to-make-remote-sam-calls) 进行远程调用的客户端。
3. 若要打开本地安全策略管理单元，请选择“开始”，输入 **secpol.msc**，按 Enter，然后展开“本地策略”。
4. 在策略列表中，选择“ [网络访问：限制允许客户端对 SAM](/zh-cn/windows/security/threat-protection/security-policy-settings/network-access-restrict-clients-allowed-to-make-remote-sam-calls) 进行远程调用”。 如果未 **启用设置，则“安全设置”** 列将显示 **“未定义** ”，或者在启用设置时显示 `O:BAG:...` 安全描述符值。 如果启用此设置，还可以选择“属性”图标以查看当前应用的访问控制列表（ACL）。

   注意

   默认情况下，此策略设置处于关闭状态。 通过 GPO 或本地策略设置在设备上应用此设置时，在 HKEY\_LOCAL\_MACHINE\System\CurrentControlSet\Control\Lsa\ **注册表路径中创建**名为 **RestrictRemoteSam** 的注册表值。 但是，在定义并应用于服务器后，此注册表设置可能难以清除。 禁用组策略设置或清除 **组策略管理控制台（GPMC）中的“定义此策略设置** ”选项不会删除注册表项。 因此，服务器仍会限制允许哪些客户端对 SAM 进行远程调用。

   如何准确验证 Microsoft Entra Connect 服务器或域控制器是否仍在限制对 SAM 的远程调用？ 通过在 PowerShell 中运行 [Get-ItemProperty](/zh-cn/powershell/module/microsoft.powershell.management/get-itemproperty#example-3--get-the-value-name-and-data-of-a-registry-entry-in-a-registry-subkey) cmdlet，检查注册表项是否存在：

   ```
   Get-ItemProperty -Path HKLM:\System\CurrentControlSet\Control\Lsa -Name RestrictRemoteSam
   ```

PowerShell 输出是否显示 **RestrictRemoteSam** 注册表项仍然存在？ 如果是这样，你有两个可能的解决方案。

### 解决方案 1：将 AD DS 连接器帐户添加到允许的用户列表

**保留网络访问：限制允许客户端对已启用和应用Microsoft Entra Connect 服务器上的 SAM** 策略设置进行远程调用，但将Active Directory 域服务（AD DS）连接器帐户（*MSOL\_*帐户）添加到允许的用户列表中。 有关说明，请参阅以下步骤：

1. 如果不知道 AD DS 连接器帐户的名称，请参阅 [“标识 AD DS 连接器帐户](password-writeback-access-rights-permissions#identify-the-ad-ds-connector-account)”。
2. 在 GPMC 或本地安全策略管理单元中，返回到该策略设置的属性对话框。
3. 选择“ **编辑安全性** ”以显示 **“远程访问 SAM** 的安全设置”对话框。
4. 在**“组”或“用户名**”列表中，选择“添加**”**以显示**“选择用户或组**”对话框。 在**“输入要选择**的对象名称”框中，输入 AD DS 连接器帐户的名称（*MSOL\_*帐户），然后选择“确定**”**退出该对话框。
5. 在列表中选择 AD DS 连接器帐户。 在“帐户名称<**的权限>”下**，在“远程访问**”行中**，选择“**允许**”。
6. 选择“ **确定** ”两次以接受策略设置更改并返回到策略设置列表。
7. 打开管理命令提示符窗口，并运行 [gpupdate](/zh-cn/windows-server/administration/windows-commands/gpupdate) 命令以强制组策略更新：

   ```
   gpupdate /force
   ```

### 解决方案 2：删除 [网络访问：限制允许远程调用 SAM](/zh-cn/windows/security/threat-protection/security-policy-settings/network-access-restrict-clients-allowed-to-make-remote-sam-calls) 策略设置的客户端，然后手动删除 RestrictRemoteSam 注册表项

1. 如果从本地安全策略应用安全设置，请转到步骤 #4。
2. 从域控制器打开 GPMC 管理单元，并编辑相应的域 GPO。
3. 展开**计算机配置****>策略**>**Windows 设置****>安全设置**>**计算机配置**>**本地策略**>**安全选项。**
4. 在安全选项列表中，选择“ **网络访问：限制允许对 SAM** 进行远程调用的客户端”、“打开 **属性**”，然后禁用 **“定义此策略”设置**。
5. 打开管理命令提示符窗口，并运行 [gpupdate](/zh-cn/windows-server/administration/windows-commands/gpupdate) 命令以强制组策略更新：

   ```
   gpupdate /force
   ```
6. 若要生成新的组策略结果报告（*GPreport.htm*），请运行 [gpresult](/zh-cn/windows-server/administration/windows-commands/gpresult) 命令，然后在 Web 浏览器中打开新报表：

   ```
   md C:\Temp
   gpresult /h C:\Temp\GPreport.htm
   start C:\Temp\GPreport.htm
   ```
7. 检查报告以确保网络访问的策略设置 **：未定义允许对 SAM** 进行远程调用的客户端。
8. 打开管理 PowerShell 控制台。
9. 若要删除 **RestrictRemoteSam** 注册表项，请运行 [Remove-ItemProperty](/zh-cn/powershell/module/microsoft.powershell.management/remove-itemproperty) cmdlet：

   ```
   Remove-ItemProperty -Path HKLM:\System\CurrentControlSet\Control\Lsa -Name RestrictRemoteSam
   ```

   注意

   如果删除 **RestrictRemoteSam** 注册表项而不删除域 GPO 设置，则会在下一个组策略刷新周期中重新创建此注册表项，并且 `SSPR_0029` 错误将再次发生。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/password-writeback-error-code-sspr-0029)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
