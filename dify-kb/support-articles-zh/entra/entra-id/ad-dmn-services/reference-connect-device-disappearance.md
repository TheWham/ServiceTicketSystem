# 了解 Microsoft Entra Connect 1.4.xx.x 和设备消失

随着 Microsoft Entra Connect 版本 1.4.xx.x 的实现，客户可能会看到部分或全部 Windows 设备从 Microsoft Entra ID 中消失。 这不是问题的原因，因为条件访问*授权期间*Microsoft Entra ID 不使用这些设备标识。 此更改不会删除Microsoft Entra 混合联接Microsoft Entra ID 正确注册的任何 Windows 设备。

如果在 Microsoft Entra ID 中看到设备对象的删除超出了 *导出删除阈值*，则允许删除操作完成。
[如何：允许删除在超出删除阈值时流式删除](/zh-cn/azure/active-directory/hybrid/how-to-connect-sync-feature-prevent-accidental-deletes)

## 背景

注册为 Microsoft Entra 混合联接的 Windows 设备以Microsoft Entra ID 表示为设备对象，可用于条件访问。 Windows 10 设备通过 Microsoft Entra Connect 同步到云，而下层 Windows 设备则使用 Active Directory 联合身份验证服务 （AD FS） 或无缝单一登录直接注册。

## Windows 10 设备

只有具有由 Microsoft Entra 混合联接配置的特定 *userCertificate* 属性值的 Windows 10 设备应通过 Microsoft Entra Connect 同步到云。 在早期版本的 Microsoft Entra Connect 中，此要求未严格强制实施，并将不必要的设备对象添加到 Microsoft Entra ID。 Microsoft Entra ID 中的此类设备始终处于“挂起”状态，因为这些设备不应注册到 Microsoft Entra ID。

此版本的 Microsoft Entra Connect 只会同步正确配置为Microsoft Entra 混合联接的 Windows 10 设备。 不带 Microsoft Entra 联接特定 userCertificate 的 Windows 10 设备对象将从 Microsoft Entra ID 中删除。

## 下层 Windows 设备

Microsoft Entra Connect 绝不应同步 [下层 Windows 设备](/zh-cn/azure/active-directory/devices/hybrid-azuread-join-plan#windows-down-level-devices)。 Microsoft Entra ID 之前未正确同步的任何设备都将从 Microsoft Entra ID 中删除。 如果Microsoft Entra Connect 尝试删除[下层 Windows 设备](/zh-cn/azure/active-directory/devices/hybrid-azuread-join-plan#windows-down-level-devices)，则设备不是为非 Windows 10 计算机 MSI [Microsoft Workplace Join 创建的](https://www.microsoft.com/download/details.aspx?id=53554)设备，它不能由任何其他Microsoft Entra 功能使用。

某些客户可能需要重新访问 [操作方法：规划Microsoft Entra 混合联接实现](/zh-cn/azure/active-directory/devices/hybrid-azuread-join-plan) 以正确注册其 Windows 设备，并确保这些设备能够参与基于设备的条件访问。

## 如何通过此更新验证已删除哪些设备？

若要验证已删除哪些设备，请使用 PowerShell 证书报表脚本中的 [PowerShell 脚本](#powershell-certificate-report-script)。

此脚本生成有关存储在 Active Directory 计算机*对象中的*证书的报告，特别是由 Microsoft Entra 混合联接功能颁发的证书。

该脚本还会检查 AD 中 Computer 对象的 UserCertificate 属性中存在的证书。 对于存在的每个未过期证书，脚本将验证是否已为 Microsoft Entra 混合联接功能颁发证书;例如， `Subject Name matches CN={ObjectGUID}`.

在此更新之前，Microsoft Entra Connect 将同步到包含至少一个有效证书的任何计算机Microsoft Entra。 从 Microsoft Entra Connect 版本 1.4 开始，同步引擎标识Microsoft Entra 混合联接证书，并使用 *cloudfilter* 筛选器来防止计算机对象同步到 Microsoft Entra ID，除非有有效的Microsoft Entra 混合联接证书。

Microsoft以前同步到 AD 但没有有效的Microsoft Entra 混合联接证书的 Entra 设备，将使用筛选器 `CloudFiltered=TRUE`删除同步引擎。

## PowerShell 证书报告脚本

```
<#

Filename:    Export-ADSyncToolsHybridAzureADjoinCertificateReport.ps1.

DISCLAIMER:
Copyright (c) Microsoft Corporation. All rights reserved. This script is made available to you without any express, implied or statutory warranty, not even the implied warranty of  merchantability or fitness for a particular purpose, or the warranty of title or non-infringement. The entire risk of the use or the results from the use of this script remains with you.
.Synopsis
This script generates a report about certificates stored in Active Directory Computer objects, specifically, 
certificates issued by the Microsoft Entra hybrid join feature.
.DESCRIPTION
It checks the certificates present in the UserCertificate property of a Computer object in AD and, for each 
non-expired certificate present, validates if the certificate was issued for the Microsoft Entra hybrid join feature 
(i.e. Subject Name matches CN={ObjectGUID}).
Before, Microsoft Entra Connect would synchronize to Microsoft Entra ID any Computer that contained at least one valid 
certificate but starting on Microsoft Entra Connect version 1.4, the sync engine can identify Hybrid 
Microsoft Entra join certificates and will 'cloudfilter' the computer object from synchronizing to Microsoft Entra ID unless 
there's a valid Microsoft Entra hybrid join certificate.
Microsoft Entra Device objects that were already synchronized to AD but do not have a valid Microsoft Entra hybrid join 
certificate will be deleted (CloudFiltered=TRUE) by the sync engine.
.EXAMPLE
.\Export-ADSyncToolsHybridAzureADjoinCertificateReport.ps1 -DN 'CN=Computer1,OU=SYNC,DC=Fabrikam,DC=com'
.EXAMPLE
.\Export-ADSyncToolsHybridAzureADjoinCertificateReport.ps1 -OU 'OU=SYNC,DC=Fabrikam,DC=com' -Filename "MyHybridAzureADjoinReport.csv" -Verbose

#>
   [CmdletBinding()]
   Param
   (
       # Computer DistinguishedName
       [Parameter(ParameterSetName='SingleObject',
               Mandatory=$true,
               ValueFromPipelineByPropertyName=$true,
               Position=0)]
       [String]
       $DN,

       # AD OrganizationalUnit
       [Parameter(ParameterSetName='MultipleObjects',
               Mandatory=$true,
               ValueFromPipelineByPropertyName=$true,
               Position=0)]
       [String]
       $OU,

       # Output CSV filename (optional)
       [Parameter(Mandatory=$false,
               ValueFromPipelineByPropertyName=$false,
               Position=1)]
       [String]
       $Filename

   )

   # Generate Output filename if not provided
   If ($Filename -eq "")
   {
       $Filename = [string] "$([string] $(Get-Date -Format yyyyMMddHHmmss))_ADSyncAADHybridJoinCertificateReport.csv"
   }
   Write-Verbose "Output filename: '$Filename'"
   
   # Read AD object(s)
   If ($PSCmdlet.ParameterSetName -eq 'SingleObject')
   {
       $directoryObjs = @(Get-ADObject $DN -Properties UserCertificate)
       Write-Verbose "Starting report for a single object '$DN'"
   }
   Else
   {
       $directoryObjs = Get-ADObject -Filter { ObjectClass -like 'computer' } -SearchBase $OU -Properties UserCertificate
       Write-Verbose "Starting report for $($directoryObjs.Count) computer objects in OU '$OU'"
   }

   Write-Host "Processing $($directoryObjs.Count) directory object(s). Please wait..."
   # Check Certificates on each AD Object
   $results = @()
   ForEach ($obj in $directoryObjs)
   {
       # Read UserCertificate multi-value property
       $objDN = [string] $obj.DistinguishedName
       $objectGuid = [string] ($obj.ObjectGUID).Guid
       $userCertificateList = @($obj.UserCertificate)
       $validEntries = @()
       $totalEntriesCount = $userCertificateList.Count
       Write-verbose "'$objDN' ObjectGUID: $objectGuid"
       Write-verbose "'$objDN' has $totalEntriesCount entries in UserCertificate property."
       If ($totalEntriesCount -eq 0)
       {
           Write-verbose "'$objDN' has no Certificates - Skipped."
           Continue
       }

       # Check each UserCertificate entry and build array of valid certs
       ForEach($entry in $userCertificateList)
       {
           Try
           {
               $cert = [System.Security.Cryptography.X509Certificates.X509Certificate2] $entry
           }
           Catch
           {
               Write-verbose "'$objDN' has an invalid Certificate!"
               Continue
           }
           Write-verbose "'$objDN' has a Certificate with Subject: $($cert.Subject); Thumbprint:$($cert.Thumbprint)."
           $validEntries += $cert

       }
       
       $validEntriesCount = $validEntries.Count
       Write-verbose "'$objDN' has a total of $validEntriesCount certificates (shown above)."
       
       # Get non-expired Certs (Valid Certificates)
       $validCerts = @($validEntries | Where-Object {$_.NotAfter -ge (Get-Date)})
       $validCertsCount = $validCerts.Count
       Write-verbose "'$objDN' has $validCertsCount valid certificates (not-expired)."

       # Check for Microsoft Entra hybrid join Certificates
       $hybridJoinCerts = @()
       $hybridJoinCertsThumbprints = [string] "|"
       ForEach ($cert in $validCerts)
       {
           $certSubjectName = $cert.Subject
           If ($certSubjectName.StartsWith($("CN=$objectGuid")) -or $certSubjectName.StartsWith($("CN={$objectGuid}")))
           {
               $hybridJoinCerts += $cert
               $hybridJoinCertsThumbprints += [string] $($cert.Thumbprint) + '|'
           }
       }

       $hybridJoinCertsCount = $hybridJoinCerts.Count
       if ($hybridJoinCertsCount -gt 0)
       {
           $cloudFiltered = 'FALSE'
           Write-verbose "'$objDN' has $hybridJoinCertsCount Microsoft Entra hybrid join Certificates with Thumbprints: $hybridJoinCertsThumbprints (cloudFiltered=FALSE)"
       }
       Else
       {
           $cloudFiltered = 'TRUE'
           Write-verbose "'$objDN' has no Microsoft Entra hybrid join Certificates (cloudFiltered=TRUE)."
       }
       
       # Save results
       $r = "" | Select ObjectDN, ObjectGUID, TotalEntriesCount, CertsCount, ValidCertsCount, HybridJoinCertsCount, CloudFiltered
       $r.ObjectDN = $objDN
       $r.ObjectGUID = $objectGuid
       $r.TotalEntriesCount = $totalEntriesCount
       $r.CertsCount = $validEntriesCount
       $r.ValidCertsCount = $validCertsCount
       $r.HybridJoinCertsCount = $hybridJoinCertsCount
       $r.CloudFiltered = $cloudFiltered
       $results += $r
   }

   # Export results to CSV
   Try
   {        
       $results | Export-Csv $Filename -NoTypeInformation -Delimiter ';'
       Write-Host "Exported Hybrid Microsoft Entra Domain Join Certificate Report to '$Filename'.`n"
   }
   Catch
   {
       Throw "There was an error saving the file '$Filename': $($_.Exception.Message)"
   }
```

## 后续步骤

- [Microsoft Entra Connect 版本历史记录](/zh-cn/azure/active-directory/hybrid/reference-connect-version-history)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/ad-dmn-services/reference-connect-device-disappearance)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
