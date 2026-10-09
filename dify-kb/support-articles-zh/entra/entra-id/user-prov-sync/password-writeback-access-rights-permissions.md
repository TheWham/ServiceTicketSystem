# 排查密码写回访问权限问题

本文介绍域根目录、用户对象和 Active Directory 中的 Builtin 容器中所需的访问权限和权限。 它还讨论了以下各项：

- 所需的域组策略
- 如何标识Microsoft Entra Connect 使用的 Active Directory 域服务 （AD DS） 连接器帐户
- 如何检查该帐户的现有权限
- 如何避免复制问题

此信息可以帮助你解决涉及密码写回的特定问题。

## 标识 AD DS 连接器帐户

在检查密码写回权限之前，请在 Microsoft Entra Connect 中验证当前的 AD DS 连接器帐户（也称为 *MSOL\_* 帐户）。 验证此帐户有助于避免在密码写回故障排除过程中执行错误步骤。

若要标识 AD DS 连接器帐户，请执行以下操作：

1. 打开“同步服务管理器”。 为此，请选择“开始”，输入**Microsoft Entra Connect**，在*搜索结果中选择Microsoft Entra Connect*，然后选择“**同步服务**”。
2. **选择“连接器**”选项卡，然后选择适用的 Active Directory 连接器。 在**“操作**”窗格中，选择“属性**”**以打开**“属性**”对话框。
3. 在“属性”窗口的**左窗格中，选择“**连接到 Active Directory 林**”，然后复制显示为**“用户名”的帐户名称**。**

## 检查 AD DS 连接器帐户的现有权限

若要为密码写回设置正确的 Active Directory 权限， [请使用内置的 ADSyncConfig PowerShell 模块](/zh-cn/azure/active-directory/hybrid/how-to-connect-configure-ad-ds-connector-account#using-the-adsyncconfig-powershell-module)。 ADSyncConfig 模块包含一种使用 Set-ADSyncPasswordWritebackPermissions [cmdlet 设置密码写回](/zh-cn/azure/active-directory/hybrid/how-to-connect-configure-ad-ds-connector-account#permissions-for-password-writeback)[权限的方法](/zh-cn/azure/active-directory/hybrid/reference-connect-adsyncconfig#set-adsyncpasswordwritebackpermissions)。

若要检查 AD DS 连接器帐户（即 *MSOL\_* 帐户）是否具有特定用户的正确权限，请使用以下工具之一：

- Microsoft管理控制台（MMC）上的Active Directory 用户和计算机管理单元
- 命令提示符
- PowerShell

### Active Directory 用户和计算机管理单元

使用 MMC 管理单元进行Active Directory 用户和计算机。 执行以下步骤：

1. 选择“开始”，输入 *dsa.msc*，然后选择搜索结果中的Active Directory 用户和计算机管理单元。
2. 选择“**查看>高级功能”。**
3. 在控制台树中，找到并选择要检查其权限的用户帐户。
   **然后选择“属性”**图标。
4. 在帐户的 **“属性** ”对话框中，选择“ **安全** ”选项卡，然后选择“ **高级** ”按钮。
5. 在 **帐户的“高级安全设置”** 对话框中，选择“ **有效权限** ”选项卡。然后，在 **“组”或“用户名** ”部分中，选择“ **选择** ”按钮。
6. 在**“选择用户、计算机或组**”对话框中，选择“高级**>”**以显示选择列表。 在 **“搜索结果** ”框中，选择 *MSOL\_* 帐户名称。
7. 选择“**确定**”两次，返回到“高级安全设置**”对话框中的“有效权限**”选项卡。 现在，可以查看分配给用户帐户的 *MSOL\_* 帐户的有效权限列表。 本文中“用户对象[”部分的“必需权限”中显示了](#required-permissions-on-the-user-object)密码写回所需的默认权限列表。

### 命令提示符

[使用 dsacls](/zh-cn/previous-versions/windows/it-pro/windows-server-2012-r2-and-2012/cc771151(v=ws.11)) 命令显示 AD DS 连接器帐户的访问控制列表（ACL 或权限）。 以下命令将命令输出存储在文本文件中，不过你可以对其进行修改以在控制台上显示输出：

```
dsacls "CN=User01,OU=Sync,DC=Contoso,DC=com" > dsaclsDomainContoso.txt
```

可以使用此方法分析任何 Active Directory 对象的权限。 但是，比较对象之间的权限并不有用，因为文本输出未排序。

### PowerShell

[使用 Get-Acl](/zh-cn/powershell/module/microsoft.powershell.security/get-acl) cmdlet 获取 AD DS 连接器帐户权限，然后使用 Export-Clixml [cmdlet 将输出存储为 XML 文件](/zh-cn/powershell/module/microsoft.powershell.utility/export-clixml)，如下所示：

```
Set-Location AD:
Get-Acl "DC=Contoso,DC=com" | Export-Clixml aclDomainContoso.xml
```

PowerShell 方法可用于脱机分析。 它允许使用 [Import-Clixml](/zh-cn/powershell/module/microsoft.powershell.utility/import-clixml) cmdlet 导入文件。 它还保留 ACL 的原始结构及其属性。 可以使用此方法分析任何 Active Directory 对象的权限。

## 修复权限时避免复制问题

修复 Active Directory 权限时，对 Active Directory 所做的更改可能不会立即生效。 Active Directory 权限还受到林中的复制，其方式与 Active Directory 对象相同。 如何缓解 Active Directory 复制问题或延迟？ 在 Microsoft Entra Connect 中设置首选域控制器，并仅在该域控制器上进行任何更改。 使用Active Directory 用户和计算机管理单元时，右键单击控制台树中的域根目录，选择“**更改域控制器**”菜单项，然后选择相同的首选域控制器。

若要在 Active Directory 中快速进行健全性检查，请使用 [dcdiag](/zh-cn/previous-versions/windows/it-pro/windows-server-2012-r2-and-2012/cc731968(v=ws.11)) 命令运行域控制器诊断。 然后，运行 [repadmin /replsummary](/zh-cn/previous-versions/windows/it-pro/windows-server-2012-r2-and-2012/cc770963(v=ws.11)) 命令以查看复制问题的摘要。 以下命令将命令输出存储在文本文件中，不过你可以修改它们以显示控制台上的输出：

```
dcdiag > dcdiag.txt
repadmin /replsum > replsum.txt
```

## Active Directory 域根的必需权限

本部分介绍 Active Directory 域根目录上密码写回的预期 Active Directory 权限。 不要将此根目录与 Active Directory 林的根混淆。 林可以有多个 Active Directory 域。 每个域必须在其自己的根目录中设置正确的权限，以便密码写回可用于该域中的用户。

可以在域根的安全属性中查看现有的 Active Directory 权限。 执行以下步骤：

1. 打开“Active Directory 用户和计算机”管理单元。
2. 在控制台树中，找到并选择 Active Directory 域根目录，然后选择“ **属性”** 图标。
3. 在帐户的 **“属性** ”对话框中，选择“ **安全** ”选项卡。

以下每个子节都包含一个域根默认权限表。 此表显示子节标题中组或用户名所需的权限条目。 若要查看和修改当前权限条目以匹配每个组或用户名的要求，请针对每个子节执行以下步骤：

1. 在 **“安全** ”选项卡上，选择“ **高级** ”按钮以查看 **“高级安全设置”** 对话框。 “ **权限** ”选项卡显示每个 Active Directory 标识（主体）的域根权限的当前列表。
2. 将当前权限列表与每个 Active Directory 标识（主体）的默认权限列表进行比较。
3. 如有必要，请选择“ **添加”** 以添加当前列表中缺少的必需权限条目。 或者，选择权限条目，然后选择“ **编辑”** 以修改该条目以满足要求。 重复此步骤，直到当前权限项与子节表匹配。
4. 选择“确定”**以接受“高级安全设置”**对话框中的更改**，然后返回到**“属性**”**对话框。

注意

Active Directory 域根权限不会继承自任何父容器。

### AD DS 连接器帐户的根默认权限（允许）

| 权限 | 应用于 |
| --- | --- |
| 重置密码 | 后代用户对象 |
| (空白) | 子代 msDS-Device 对象 |
| 复制目录更改 | 仅此对象 |
| 复制所有目录更改 | 仅此对象 |
| 读取所有属性 | 子代 publicFolder 对象 |
| 读取/写入所有属性 | 后代 InetOrgPerson 对象 |
| 读取/写入所有属性 | 后代组对象 |
| 读取/写入所有属性 | 后代用户对象 |
| 读取/写入所有属性 | 后代联系人对象 |

### 经过身份验证的用户的根默认权限（允许）

| 权限 | 应用于 |
| --- | --- |
| 启用每个用户可逆加密的密码 | 仅此对象 |
| 未过期密码 | 仅此对象 |
| 更新密码不需要位 | 仅此对象 |
| 特殊 | 仅此对象 |
| (空白) | 此对象和所有后代对象 |

### 每个人的根默认权限（拒绝 + 允许）

| 类型 | 权限 | 应用于 |
| --- | --- | --- |
| 拒绝 | 删除所有子对象 | 仅此对象 |
| 允许 | 读取所有属性 | 仅此对象 |

### 预 Windows 2000 兼容访问的根默认权限（允许）

| 权限 | 应用于 |
| --- | --- |
| 特殊 | 后代 InetOrgPerson 对象 |
| 特殊 | 后代组对象 |
| 特殊 | 后代用户对象 |
| 特殊 | 仅此对象 |
| 列出内容 | 此对象和所有后代对象 |

### SELF 的根默认权限（允许）

| 权限 | 应用于 |
| --- | --- |
| (空白) | 此对象和所有后代对象 |
| 特殊 | 所有后代对象 |
| 验证写入计算机属性 | 后代计算机对象 |
| (空白) | 后代计算机对象 |

## 用户对象所需的权限

本部分介绍必须更新密码的目标用户对象上密码写回的预期 Active Directory 权限。 若要查看现有安全权限，请按照以下步骤显示用户对象的安全属性：

1. 返回到Active Directory 用户和计算机管理单元。
2. 使用控制台树或**“操作>查找**”菜单项选择目标用户对象，然后选择“**属性”**图标。
3. 在帐户的 **“属性** ”对话框中，选择“ **安全** ”选项卡。

以下每个子节都包含一个用户默认权限表。 此表显示子节标题中组或用户名所需的权限条目。 若要查看和修改当前权限条目以匹配每个组或用户名的要求，请针对每个子节执行以下步骤：

1. 在 **“安全** ”选项卡上，选择“ **高级** ”按钮以查看 **“高级安全设置”** 对话框。
2. 确保 **对话框底部附近显示“禁用继承** ”按钮。
   **如果改为显示“启用继承**”按钮，请选择该按钮。 启用继承功能允许此对象继承来自父容器和组织单位的所有权限。 此更改可解决此问题。
3. **在“权限**”选项卡上，将当前权限列表与每个 Active Directory 标识（主体）的默认权限列表进行比较。 “ **权限** ”选项卡显示每个 Active Directory 标识（主体）的用户权限的当前列表。
4. 如有必要，请选择“ **添加”** 以添加当前列表中缺少的必需权限条目。 或者，选择权限条目，然后选择“ **编辑”** 以修改该条目以满足要求。 重复此步骤，直到当前权限项与子节表匹配。
5. 选择“确定**”**以接受“高级安全设置”**对话框中的更改**，然后返回到**“属性**”对话框。

注意

与 Active Directory 域根不同，用户对象的所需权限通常继承自域根目录或父容器或组织单位。 直接在对象上设置的权限将指示来自 **None** 的继承。 只要类型**、**主体**、**访问**和**应用于**权限的列的值**相同，访问控制项（ACE）的继承并不重要。 但是，某些权限只能在域根目录中设置。 这些实体列在子节表中。

### AD DS 连接器帐户的用户默认权限（允许）

| 权限 | 继承自 | 应用于 |
| --- | --- | --- |
| 重置密码 | <域根> | 后代用户对象 |
| (空白) | <域根> | 子代 msDS-Device 对象 |
| 读取所有属性 | <域根> | 子代 publicFolder 对象 |
| 读取/写入所有属性 | <域根> | 后代 InetOrgPerson 对象 |
| 读取/写入所有属性 | <域根> | 后代组对象 |
| 读取/写入所有属性 | <域根> | 后代用户对象 |
| 读取/写入所有属性 | <域根> | 后代联系人对象 |

### 经过身份验证的用户的用户默认权限（允许）

| 权限 | 继承自 | 应用于 |
| --- | --- | --- |
| 阅读常规信息 | 无 | 仅此对象 |
| 读取公共信息 | 无 | 仅此对象 |
| 读取个人信息 | 无 | 仅此对象 |
| 读取 Web 信息 | 无 | 仅此对象 |
| 读取权限 | 无 | 仅此对象 |
| 读取 Exchange 信息 | <域根> | 此对象和所有后代对象 |

### 每个人的用户默认权限（允许）

| 权限 | 继承自 | 应用于 |
| --- | --- | --- |
| 更改密码 | 无 | 仅此对象 |

### 预 Windows 2000 兼容访问的用户默认权限（允许）

**此表中的特殊**权限包括**列表内容**、**读取所有属性**和**读取权限**。

| 权限 | 继承自 | 应用于 |
| --- | --- | --- |
| 特殊 | <域根> | 后代 InetOrgPerson 对象 |
| 特殊 | <域根> | 后代组对象 |
| 特殊 | <域根> | 后代用户对象 |
| 列出内容 | <域根> | 此对象和所有后代对象 |

### SELF 的用户默认权限（允许）

**此表中的特殊**权限仅包括**读取/写入专用信息**权限。

| 权限 | 继承自 | 应用于 |
| --- | --- | --- |
| 更改密码 | 无 | 仅此对象 |
| 发送为 | 无 | 仅此对象 |
| 接收为 | 无 | 仅此对象 |
| 读取/写入个人信息 | 无 | 仅此对象 |
| 读/写电话和邮件选项 | 无 | 仅此对象 |
| 读取/写入 Web 信息 | 无 | 仅此对象 |
| 特殊 | 无 | 仅此对象 |
| 验证写入计算机属性 | <域根> | 后代计算机对象 |
| (空白) | <域根> | 后代计算机对象 |
| (空白) | <域根> | 此对象和所有后代对象 |
| 特殊 | <域根> | 此对象和所有后代对象 |

## SAM 服务器对象上所需的权限

本部分介绍安全帐户管理器（SAM）服务器对象（CN=Server，CN=System，DC=Contoso，DC=com）上密码写回的预期 Active Directory 权限。 若要查找 SAM 服务器对象（samServer）的安全属性，请执行以下步骤：

1. 返回到Active Directory 用户和计算机管理单元。
2. 在控制台树中，找到并选择 **系统** 容器。
3. 找到并选择 **服务器** （samServer 对象），然后选择“ **属性”** 图标。
4. 在 **对象的“属性** ”对话框中，选择“ **安全** ”选项卡。
5. **选择“高级安全设置”**对话框。 “ **权限** ”选项卡显示每个 Active Directory 标识（主体）的 samServer 对象权限的当前列表。
6. 验证 samServer 对象的访问控制条目中是否至少列出了以下主体之一。 如果仅 **列出了预 Windows 2000 兼容访问** ，请确保 **经过身份验证的用户** 是此内置组的成员。

### 预 Windows 2000 兼容访问的权限（允许）

**特殊** 权限必须包括 **列表内容**、 **读取所有属性**和 **读取权限** 。

### 经过身份验证的用户的权限（允许）

**特殊** 权限必须包括 **列表内容**、 **读取所有属性**和 **读取权限** 。

## 对 Builtin 容器的必需权限

本部分介绍内置容器上密码写回的预期 Active Directory 权限。 若要查看现有安全权限，请按照以下步骤访问内置对象的安全属性：

1. 打开Active Directory 用户和计算机管理单元。
2. 在控制台树中，找到并选择 **Builtin** 容器，然后选择 **“属性”** 图标。
3. 在帐户的 **“属性** ”对话框中，选择“ **安全** ”选项卡。
4. 选择 **“高级** ”按钮以查看 **“高级安全设置** ”对话框。 “ **权限** ”选项卡显示每个 Active Directory 标识（主体）的内置容器权限的当前列表。
5. 将此当前权限列表与MSOL\_*帐户所需的允许权限*列表进行比较，如下所示。

   | 权限 | 继承自 | 应用于 |
   | --- | --- | --- |
   | 读取/写入所有属性 | <域根> | 后代 InetOrgPerson 对象 |
   | 读取/写入所有属性 | <域根> | 后代组对象 |
   | 读取/写入所有属性 | <域根> | 后代用户对象 |
   | 读取/写入所有属性 | <域根> | 后代联系人对象 |
6. 如有必要，请选择“ **添加”** 以添加当前列表中缺少的必需权限条目。 或者，选择权限条目，然后选择“ **编辑”** 以修改该条目以满足要求。 重复此步骤，直到当前权限项与子节表匹配。
7. 选择“确定**”**退出**“高级安全设置**”对话框，然后返回到**“属性**”对话框。

## 其他必需的 Active Directory 权限

在 **预 Windows 2000 兼容访问** 组属性中，转到 **“成员** ”选项卡，并确保 **经过身份验证的用户** 是此组的成员。 否则，可能会遇到影响 Microsoft Entra Connect 和 Active Directory 上密码写回的问题（尤其是较旧版本）。

## 所需的域组策略

若要确保具有正确的域组策略，请执行以下步骤：

1. 选择“开始”，输入 *secpol.msc*，然后在搜索结果中选择“**本地安全策略**”。
2. 在控制台树中的“安全设置”**下**，展开**“本地策略**”，然后选择“**用户权限分配**”。
3. 在策略列表中，选择身份验证后模拟客户端，然后选择**“属性”**图标。
4. 在**“属性**”对话框中，确保“本地安全设置**”选项卡上列出了**以下组：

   - 管理员
   - 本地服务
   - 网络服务
   - SERVICE

有关详细信息，请参阅[身份验证**策略**后模拟客户端的](/zh-cn/windows/security/threat-protection/security-policy-settings/impersonate-a-client-after-authentication#default-values)默认值。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/password-writeback-access-rights-permissions)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
