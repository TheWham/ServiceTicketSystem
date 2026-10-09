# 尝试运行适用于 Windows PowerShell cmdlet 的 Azure Active Directory 模块时出错：无法识别术语 <cmdlet 名称>

*原始产品版本：* 云服务（Web 角色/辅助角色）、Microsoft Entra ID、Microsoft Intune、Azure 备份、Office 365 标识管理  
*原始 KB 编号：*2669552

## 症状

尝试运行适用于 Windows PowerShell cmdlet 的 Microsoft Azure Active Directory 模块时，会收到以下错误消息：

> 无法将 <cmdlet name> 项识别为 cmdlet、函数、脚本文件或可运行程序的名称。 检查名称的拼写，或者是否包含路径，验证路径是否正确，然后重试。

例如，你可能会看到类似下面的错误消息：

> 无法将“Get-ADForest”项识别为 cmdlet、函数、脚本文件或可运行程序的名称。 检查名称的拼写，或者是否包含路径，验证路径是否正确，然后重试。  
> 在第 1 行第 20 个字符处  
> + Connect-MsolService <<<<  
> + CategoryInfo : ObjectNotFound : (Connect-MsolService : String) [], CommandNotFoundException  
> + FullyQualifiedErrorId ：CommandNotFoundException

## 原因

如果未正确加载适用于 Windows PowerShell 的 Azure Active Directory 模块，则可能会出现此问题。

## 解决方案

若要解决此问题，请按照下列步骤操作。

1. 在计算机上安装适用于 Windows PowerShell 的 Azure Active Directory 模块（如果尚未安装）。 要安装适用于 Windows PowerShell 的 Azure Active Directory 模块，请参阅[使用 Windows PowerShell 管理 Microsoft Entra ID](/zh-cn/previous-versions/azure/jj151815(v=azure.100)?redirectedfrom=MSDN)。
2. 选择“启动”>“所有程序”，选择“Windows Azure Active Directory”，然后选择“适用于 Windows PowerShell 的 Windows Azure Active Directory 模块”。
3. 在 Windows PowerShell 命令提示符处，键入 `Get-Module`，然后按 Enter。
4. 在输出中，检查 `MSOnline` 模块是否存在。 输出应该与以下示例相似：

   ```
   Module Type Name Exported Commands
   -------------- -------- ----------------
   Binary MSOnline {Add-MsolRoleMember, Remove-MsolContact...
   ```

   如果 `MSOnline` 模块不存在，请使用 Windows PowerShell 导入 `MSOnline` 模块。 要执行此操作，请执行以下步骤：

   1. 通过使用远程 PowerShell 连接到 Exchange Online。 有关如何执行此操作的详细信息，请参阅[使用远程 PowerShell 连接到 Exchange Online](/zh-cn/powershell/exchange/connect-to-exchange-online-powershell?redirectedfrom=MSDN&view=exchange-ps&preserve-view=true)。
   2. 键入以下 cmdlet，然后按 Enter：

      ```
      Import-Module MSOnline
      ```

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/dir-dmns-obj/term-cmdlet-name-not-recognized-aad-cmdlet)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
