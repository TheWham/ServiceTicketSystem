# 用于排查 802.1X 身份验证问题的数据收集

[试用虚拟代理](https://vsa.services.microsoft.com/v1.0/?partnerId=7d74cf73-5217-4008-833f-87a1a278f2cb&flowId=DMC&initialQuery=31806441) - 它可以帮助你快速识别和修复常见的无线技术问题。

使用以下步骤收集可用于排查 802.1X 身份验证问题的数据。 收集数据后，请参阅 [高级故障排除 802.1X 身份验证](802-1x-authentication-issues-troubleshooting)。

*适用于：*Windows 10

## 捕获无线/有线功能日志

使用以下步骤在 Windows 和 Windows Server 上收集无线和有线日志：

1. 在客户端计算机上创建 *C：\MSLOG* 以存储捕获的日志。
2. 在客户端计算机上启动提升的命令提示符，并运行以下命令以启动 RAS 跟踪日志和无线/有线方案日志。

   无线 Windows 8.1、Windows 10 和 Windows 11：

   ```
   netsh ras set tracing * enabled
   netsh trace start scenario=wlan,wlan_wpp,wlan_dbg,wireless_dbg globallevel=0xff capture=yes maxsize=1024 tracefile=C:\MSLOG\%COMPUTERNAME%_wireless_cli.etl
   ```

   无线 Windows 7 和 Windows 8：

   ```
   netsh ras set tracing * enabled
   netsh trace start scenario=wlan,wlan_wpp,wlan_dbg globallevel=0xff capture=yes maxsize=1024 tracefile=C:\MSLOG\%COMPUTERNAME%_wireless_cli.etl
   ```

   有线客户端，无论版本如何

   ```
   netsh ras set tracing * enabled
   netsh trace start scenario=lan globallevel=0xff capture=yes maxsize=1024 tracefile=C:\MSLOG\%COMPUTERNAME%_wired_cli.etl
   ```
3. 运行以下命令以启用 CAPI2 日志记录并增加大小：

   ```
   wevtutil.exe sl Microsoft-Windows-CAPI2/Operational /e:true
   wevtutil sl Microsoft-Windows-CAPI2/Operational /ms:104857600
   ```
4. 在 NPS 上创建 *C：\MSLOG* 以存储捕获的日志。
5. 在 NPS 服务器上启动提升的命令提示符，并运行以下命令以启动 RAS 跟踪日志和无线/有线方案日志：

   Windows Server 2012 R2、Windows Server 2016 无线网络：

   ```
   netsh ras set tracing * enabled
   netsh trace start scenario=wlan,wlan_wpp,wlan_dbg,wireless_dbg globallevel=0xff capture=yes maxsize=1024 tracefile=C:\MSLOG\%COMPUTERNAME%_wireless_nps.etl
   ```

   Windows Server 2008 R2、Windows Server 2012 无线网络

   ```
   netsh ras set tracing * enabled
   netsh trace start scenario=wlan,wlan_wpp,wlan_dbg globallevel=0xff capture=yes maxsize=1024 tracefile=C:\MSLOG\%COMPUTERNAME%_wireless_nps.etl
   ```

   有线网络

   ```
   netsh ras set tracing * enabled
   netsh trace start scenario=lan globallevel=0xff capture=yes maxsize=1024 tracefile=C:\MSLOG\%COMPUTERNAME%_wired_nps.etl
   ```
6. 运行以下命令以启用 CAPI2 日志记录并增加大小：

   ```
    wevtutil.exe sl Microsoft-Windows-CAPI2/Operational /e:true
    wevtutil sl Microsoft-Windows-CAPI2/Operational /ms:104857600
   ```
7. 从客户端计算机上的命令提示符运行以下命令，并启动 PSR 以捕获屏幕图像：

   注意

   单击鼠标按钮时，光标在捕获屏幕图像时将闪烁为红色。

   ```
   psr /start /output c:\MSLOG\%computername%_psr.zip /maxsc 100
   ```
8. 重现遇到的问题。
9. 在客户端电脑上运行以下命令以停止 PSR 捕获：

   ```
   psr /stop
   ```
10. 从 NPS 服务器上的命令提示符运行以下命令。

    - 停止 RAS 跟踪日志和无线方案日志：

      ```
      netsh trace stop
      netsh ras set tracing * disabled
      ```
    - 禁用和复制 CAPI2 日志：

      ```
      wevtutil.exe sl Microsoft-Windows-CAPI2/Operational /e:false
      wevtutil.exe epl Microsoft-Windows-CAPI2/Operational C:\MSLOG\%COMPUTERNAME%_CAPI2.evtx
      ```
11. 在客户端电脑上运行以下命令。

    - 停止 RAS 跟踪日志和无线方案日志：

      ```
      netsh trace stop
      netsh ras set tracing * disabled
      ```
    - 若要禁用和复制 CAPI2 日志，请执行以下操作：

      ```
      wevtutil.exe sl Microsoft-Windows-CAPI2/Operational /e:false
      wevtutil.exe epl Microsoft-Windows-CAPI2/Operational C:\MSLOG\%COMPUTERNAME%_CAPI2.evtx
      ```
12. 在客户端和 NPS 上保存以下日志：

    客户端

    - *C：\MSLOG\%computername%\_psr.zip*
    - *C：\MSLOG\%COMPUTERNAME%\_CAPI2.evtx*
    - *C：\MSLOG\%COMPUTERNAME%\_wireless\_cli.etl*
    - *C：\MSLOG\%COMPUTERNAME%\_wireless\_cli.cab*
    - %Systemroot%\Tracing 中的所有 *日志文件和文件夹*

    NPS

    - *C\MSLOG\%COMPUTERNAME%\_CAPI2.evtx*
    - *C：\MSLOG\%COMPUTERNAME%\_wireless\_nps.etl（*%COMPUTERNAME%\_wired\_nps.etl** for wired scenario）
    - *C：\MSLOG\%COMPUTERNAME%\_wireless\_nps.cab* （*有线方案的%COMPUTERNAME%\_wired\_nps.cab* ）
    - %Systemroot%\Tracing 中的所有 *日志文件和文件夹*

## 保存环境和配置信息

### 在 Windows 客户端上

1. 创建 *C：\MSLOG* 以存储捕获的日志。
2. 以管理员身份启动命令提示符。
3. 运行以下命令。

   - 环境信息和组策略应用程序状态

     ```
     gpresult /H C:\MSLOG\%COMPUTERNAME%_gpresult.htm
     msinfo32 /report c:\MSLOG\%COMPUTERNAME%_msinfo32.txt
     ipconfig /all > c:\MSLOG\%COMPUTERNAME%_ipconfig.txt
     route print > c:\MSLOG\%COMPUTERNAME%_route_print.txt
     ```
   - 事件日志

     ```
     wevtutil epl Application c:\MSLOG\%COMPUTERNAME%_Application.evtx
     wevtutil epl System c:\MSLOG\%COMPUTERNAME%_System.evtx
     wevtutil epl Security c:\MSLOG\%COMPUTERNAME%_Security.evtx
     wevtutil epl Microsoft-Windows-GroupPolicy/Operational C:\MSLOG\%COMPUTERNAME%_GroupPolicy_Operational.evtx
     wevtutil epl "Microsoft-Windows-WLAN-AutoConfig/Operational" c:\MSLOG\%COMPUTERNAME%_Microsoft-Windows-WLAN-AutoConfig-Operational.evtx
     wevtutil epl "Microsoft-Windows-Wired-AutoConfig/Operational" c:\MSLOG\%COMPUTERNAME%_Microsoft-Windows-Wired-AutoConfig-Operational.evtx
     wevtutil epl Microsoft-Windows-CertificateServicesClient-CredentialRoaming/Operational c:\MSLOG\%COMPUTERNAME%_CertificateServicesClient-CredentialRoaming_Operational.evtx
     wevtutil epl Microsoft-Windows-CertPoleEng/Operational c:\MSLOG\%COMPUTERNAME%_CertPoleEng_Operational.evtx
     ```
   - 对于 Windows 8 及更高版本，还针对事件日志运行以下命令：

     ```
     wevtutil epl Microsoft-Windows-CertificateServicesClient-Lifecycle-System/Operational c:\MSLOG\%COMPUTERNAME%_CertificateServicesClient-Lifecycle-System_Operational.evtx
     wevtutil epl Microsoft-Windows-CertificateServicesClient-Lifecycle-User/Operational c:\MSLOG\%COMPUTERNAME%_CertificateServicesClient-Lifecycle-User_Operational.evtx
     wevtutil epl Microsoft-Windows-CertificateServices-Deployment/Operational c:\MSLOG\%COMPUTERNAME%_CertificateServices-Deployment_Operational.evtx
     ```
   - 证书存储信息：

     ```
     certutil -v -silent -store MY > c:\MSLOG\%COMPUTERNAME%_cert-Personal-Registry.txt
     certutil -v -silent -store ROOT > c:\MSLOG\%COMPUTERNAME%_cert-TrustedRootCA-Registry.txt
     certutil -v -silent -store -grouppolicy ROOT > c:\MSLOG\%COMPUTERNAME%_cert-TrustedRootCA-GroupPolicy.txt
     certutil -v -silent -store -enterprise ROOT > c:\MSLOG\%COMPUTERNAME%_TrustedRootCA-Enterprise.txt
     certutil -v -silent -store TRUST > c:\MSLOG\%COMPUTERNAME%_cert-EnterpriseTrust-Reg.txt
     certutil -v -silent -store -grouppolicy TRUST > c:\MSLOG\%COMPUTERNAME%_cert-EnterpriseTrust-GroupPolicy.txt
     certutil -v -silent -store -enterprise TRUST > c:\MSLOG\%COMPUTERNAME%_cert-EnterpriseTrust-Enterprise.txt
     certutil -v -silent -store CA > c:\MSLOG\%COMPUTERNAME%_cert-IntermediateCA-Registry.txt
     certutil -v -silent -store -grouppolicy CA > c:\MSLOG\%COMPUTERNAME%_cert-IntermediateCA-GroupPolicy.txt
     certutil -v -silent -store -enterprise CA > c:\MSLOG\%COMPUTERNAME%_cert-Intermediate-Enterprise.txt
     certutil -v -silent -store AuthRoot > c:\MSLOG\%COMPUTERNAME%_cert-3rdPartyRootCA-Registry.txt
     certutil -v -silent -store -grouppolicy AuthRoot > c:\MSLOG\%COMPUTERNAME%_cert-3rdPartyRootCA-GroupPolicy.txt
     certutil -v -silent -store -enterprise AuthRoot > c:\MSLOG\%COMPUTERNAME%_cert-3rdPartyRootCA-Enterprise.txt
     certutil -v -silent -store SmartCardRoot > c:\MSLOG\%COMPUTERNAME%_cert-SmartCardRoot-Registry.txt
     certutil -v -silent -store -grouppolicy SmartCardRoot > c:\MSLOG\%COMPUTERNAME%_cert-SmartCardRoot-GroupPolicy.txt
     certutil -v -silent -store -enterprise SmartCardRoot > c:\MSLOG\%COMPUTERNAME%_cert-SmartCardRoot-Enterprise.txt
     certutil -v -silent -store -enterprise NTAUTH > c:\MSLOG\%COMPUTERNAME%_cert-NtAuth-Enterprise.txt
     certutil -v -silent -user -store MY > c:\MSLOG\%COMPUTERNAME%_cert-User-Personal-Registry.txt
     certutil -v -silent -user -store ROOT > c:\MSLOG\%COMPUTERNAME%_cert-User-TrustedRootCA-Registry.txt
     certutil -v -silent -user -store -enterprise ROOT > c:\MSLOG\%COMPUTERNAME%_cert-User-TrustedRootCA-Enterprise.txt
     certutil -v -silent -user -store TRUST > c:\MSLOG\%COMPUTERNAME%_cert-User-EnterpriseTrust-Registry.txt
     certutil -v -silent -user -store -grouppolicy TRUST > c:\MSLOG\%COMPUTERNAME%_cert-User-EnterpriseTrust-GroupPolicy.txt
     certutil -v -silent -user -store CA > c:\MSLOG\%COMPUTERNAME%_cert-User-IntermediateCA-Registry.txt
     certutil -v -silent -user -store -grouppolicy CA > c:\MSLOG\%COMPUTERNAME%_cert-User-IntermediateCA-GroupPolicy.txt
     certutil -v -silent -user -store Disallowed > c:\MSLOG\%COMPUTERNAME%_cert-User-UntrustedCertificates-Registry.txt
     certutil -v -silent -user -store -grouppolicy Disallowed > c:\MSLOG\%COMPUTERNAME%_cert-User-UntrustedCertificates-GroupPolicy.txt
     certutil -v -silent -user -store AuthRoot > c:\MSLOG\%COMPUTERNAME%_cert-User-3rdPartyRootCA-Registry.txt
     certutil -v -silent -user -store -grouppolicy AuthRoot > c:\MSLOG\%COMPUTERNAME%_cert-User-3rdPartyRootCA-GroupPolicy.txt
     certutil -v -silent -user -store SmartCardRoot > c:\MSLOG\%COMPUTERNAME%_cert-User-SmartCardRoot-Registry.txt
     certutil -v -silent -user -store -grouppolicy SmartCardRoot > c:\MSLOG\%COMPUTERNAME%_cert-User-SmartCardRoot-GroupPolicy.txt
     certutil -v -silent -user -store UserDS > c:\MSLOG\%COMPUTERNAME%_cert-User-UserDS.txt
     ```
   - 无线 LAN 客户端信息：

     ```
     netsh wlan show all > c:\MSLOG\%COMPUTERNAME%_wlan_show_all.txt
     netsh wlan export profile folder=c:\MSLOG\
     ```
   - 有线 LAN 客户端信息

     ```
     netsh lan show interfaces > c:\MSLOG\%computername%_lan_interfaces.txt
     netsh lan show profiles > c:\MSLOG\%computername%_lan_profiles.txt
     netsh lan show settings > c:\MSLOG\%computername%_lan_settings.txt
     netsh lan export profile folder=c:\MSLOG\
     ```
4. 保存存储在 C：\MSLOG *中的*日志。

### 在 NPS 上

1. 创建 *C：\MSLOG* 以存储捕获的日志。
2. 以管理员身份启动命令提示符。
3. 运行以下命令。

   - 环境信息和组策略应用程序状态：

     ```
     gpresult /H C:\MSLOG\%COMPUTERNAME%_gpresult.txt
     msinfo32 /report c:\MSLOG\%COMPUTERNAME%_msinfo32.txt
     ipconfig /all > c:\MSLOG\%COMPUTERNAME%_ipconfig.txt
     route print > c:\MSLOG\%COMPUTERNAME%_route_print.txt
     ```
   - 事件日志：

     ```
     wevtutil epl Application c:\MSLOG\%COMPUTERNAME%_Application.evtx
     wevtutil epl System c:\MSLOG\%COMPUTERNAME%_System.evtx
     wevtutil epl Security c:\MSLOG\%COMPUTERNAME%_Security.evtx
     wevtutil epl Microsoft-Windows-GroupPolicy/Operational c:\MSLOG\%COMPUTERNAME%_GroupPolicy_Operational.evtx
     wevtutil epl Microsoft-Windows-CertificateServicesClient-CredentialRoaming/Operational c:\MSLOG\%COMPUTERNAME%_CertificateServicesClient-CredentialRoaming_Operational.evtx
     wevtutil epl Microsoft-Windows-CertPoleEng/Operational c:\MSLOG\%COMPUTERNAME%_CertPoleEng_Operational.evtx
     ```
   - 在 Windows Server 2012 及更高版本上运行以下命令：

     ```
     wevtutil epl Microsoft-Windows-CertificateServicesClient-Lifecycle-System/Operational c:\MSLOG\%COMPUTERNAME%_CertificateServicesClient-Lifecycle-System_Operational.evtx
     wevtutil epl Microsoft-Windows-CertificateServicesClient-Lifecycle-User/Operational c:\MSLOG\%COMPUTERNAME%_CertificateServicesClient-Lifecycle-User_Operational.evtx
     wevtutil epl Microsoft-Windows-CertificateServices-Deployment/Operational c:\MSLOG\%COMPUTERNAME%_CertificateServices-Deployment_Operational.evtx
     ```
   - 证书存储信息

     ```
     certutil -v -silent -store MY > c:\MSLOG\%COMPUTERNAME%_cert-Personal-Registry.txt
     certutil -v -silent -store ROOT > c:\MSLOG\%COMPUTERNAME%_cert-TrustedRootCA-Registry.txt
     certutil -v -silent -store -grouppolicy ROOT > c:\MSLOG\%COMPUTERNAME%_cert-TrustedRootCA-GroupPolicy.txt
     certutil -v -silent -store -enterprise ROOT > c:\MSLOG\%COMPUTERNAME%_TrustedRootCA-Enterprise.txt
     certutil -v -silent -store TRUST > c:\MSLOG\%COMPUTERNAME%_cert-EnterpriseTrust-Reg.txt
     certutil -v -silent -store -grouppolicy TRUST > c:\MSLOG\%COMPUTERNAME%_cert-EnterpriseTrust-GroupPolicy.txt
     certutil -v -silent -store -enterprise TRUST > c:\MSLOG\%COMPUTERNAME%_cert-EnterpriseTrust-Enterprise.txt
     certutil -v -silent -store CA > c:\MSLOG\%COMPUTERNAME%_cert-IntermediateCA-Registry.txt
     certutil -v -silent -store -grouppolicy CA > c:\MSLOG\%COMPUTERNAME%_cert-IntermediateCA-GroupPolicy.txt
     certutil -v -silent -store -enterprise CA > c:\MSLOG\%COMPUTERNAME%_cert-Intermediate-Enterprise.txt
     certutil -v -silent -store AuthRoot > c:\MSLOG\%COMPUTERNAME%_cert-3rdPartyRootCA-Registry.txt
     certutil -v -silent -store -grouppolicy AuthRoot > c:\MSLOG\%COMPUTERNAME%_cert-3rdPartyRootCA-GroupPolicy.txt
     certutil -v -silent -store -enterprise AuthRoot > c:\MSLOG\%COMPUTERNAME%_cert-3rdPartyRootCA-Enterprise.txt
     certutil -v -silent -store SmartCardRoot > c:\MSLOG\%COMPUTERNAME%_cert-SmartCardRoot-Registry.txt
     certutil -v -silent -store -grouppolicy SmartCardRoot > c:\MSLOG\%COMPUTERNAME%_cert-SmartCardRoot-GroupPolicy.txt
     certutil -v -silent -store -enterprise SmartCardRoot > c:\MSLOG\%COMPUTERNAME%_cert-SmartCardRoot-Enterprise.txt
     certutil -v -silent -store -enterprise NTAUTH > c:\MSLOG\%COMPUTERNAME%_cert-NtAuth-Enterprise.txt
     certutil -v -silent -user -store MY > c:\MSLOG\%COMPUTERNAME%_cert-User-Personal-Registry.txt
     certutil -v -silent -user -store ROOT > c:\MSLOG\%COMPUTERNAME%_cert-User-TrustedRootCA-Registry.txt
     certutil -v -silent -user -store -enterprise ROOT > c:\MSLOG\%COMPUTERNAME%_cert-User-TrustedRootCA-Enterprise.txt
     certutil -v -silent -user -store TRUST > c:\MSLOG\%COMPUTERNAME%_cert-User-EnterpriseTrust-Registry.txt
     certutil -v -silent -user -store -grouppolicy TRUST > c:\MSLOG\%COMPUTERNAME%_cert-User-EnterpriseTrust-GroupPolicy.txt
     certutil -v -silent -user -store CA > c:\MSLOG\%COMPUTERNAME%_cert-User-IntermediateCA-Registry.txt
     certutil -v -silent -user -store -grouppolicy CA > c:\MSLOG\%COMPUTERNAME%_cert-User-IntermediateCA-GroupPolicy.txt
     certutil -v -silent -user -store Disallowed > c:\MSLOG\%COMPUTERNAME%_cert-User-UntrustedCertificates-Registry.txt
     certutil -v -silent -user -store -grouppolicy Disallowed > c:\MSLOG\%COMPUTERNAME%_cert-User-UntrustedCertificates-GroupPolicy.txt
     certutil -v -silent -user -store AuthRoot > c:\MSLOG\%COMPUTERNAME%_cert-User-3rdPartyRootCA-Registry.txt
     certutil -v -silent -user -store -grouppolicy AuthRoot > c:\MSLOG\%COMPUTERNAME%_cert-User-3rdPartyRootCA-GroupPolicy.txt
     certutil -v -silent -user -store SmartCardRoot > c:\MSLOG\%COMPUTERNAME%_cert-User-SmartCardRoot-Registry.txt
     certutil -v -silent -user -store -grouppolicy SmartCardRoot > c:\MSLOG\%COMPUTERNAME%_cert-User-SmartCardRoot-GroupPolicy.txt
     certutil -v -silent -user -store UserDS > c:\MSLOG\%COMPUTERNAME%_cert-User-UserDS.txt
     ```
   - NPS 配置信息：

     ```
     netsh nps show config > C:\MSLOG\%COMPUTERNAME%_nps_show_config.txt
     netsh nps export filename=C:\MSLOG\%COMPUTERNAME%_nps_export.xml exportPSK=YES
     ```
4. 执行以下步骤保存 NPS 会计日志。

   1. 打开**管理工具>网络策略服务器。**
   2. 在网络策略服务器管理工具上，选择 **左窗格中的“** 会计”。
   3. 选择“ **更改日志文件属性**”。
   4. 在**“日志文件**”选项卡上，记下日志文件命名约定，该约定显示为**“名称**”和“目录**”框中显示的**日志文件位置。
   5. 将日志文件复制到 *C：\MSLOG*。
5. 保存存储在 C：\MSLOG *中的*日志。

## 证书颁发机构 （CA） （可选）

1. 在 CA 上，以管理员身份启动命令提示符。 创建 *C：\MSLOG* 以存储捕获的日志。
2. 运行以下命令。

   - 环境信息和组策略应用程序状态

     ```
     gpresult /H C:\MSLOG\%COMPUTERNAME%_gpresult.txt
     msinfo32 /report c:\MSLOG\%COMPUTERNAME%_msinfo32.txt
     ipconfig /all > c:\MSLOG\%COMPUTERNAME%_ipconfig.txt
     route print > c:\MSLOG\%COMPUTERNAME%_route_print.txt
     ```
   - 事件日志

     ```
     wevtutil epl Application c:\MSLOG\%COMPUTERNAME%_Application.evtx
     wevtutil epl System c:\MSLOG\%COMPUTERNAME%_System.evtx
     wevtutil epl Security c:\MSLOG\%COMPUTERNAME%_Security.evtx
     wevtutil epl Microsoft-Windows-GroupPolicy/Operational c:\MSLOG\%COMPUTERNAME%_GroupPolicy_Operational.evtx
     wevtutil epl Microsoft-Windows-CertificateServicesClient-CredentialRoaming/Operational c:\MSLOG\%COMPUTERNAME%_CertificateServicesClient-CredentialRoaming_Operational.evtx
     wevtutil epl Microsoft-Windows-CertPoleEng/Operational c:\MSLOG\%COMPUTERNAME%_CertPoleEng_Operational.evtx
     ```
   - 在 Windows 2012 及更新上运行以下行

     ```
     wevtutil epl Microsoft-Windows-CertificateServicesClient-Lifecycle-System/Operational c:\MSLOG\%COMPUTERNAME%_CertificateServicesClient-Lifecycle-System_Operational.evtx
     wevtutil epl Microsoft-Windows-CertificateServicesClient-Lifecycle-User/Operational c:\MSLOG\%COMPUTERNAME%_CertificateServicesClient-Lifecycle-User_Operational.evtx
     wevtutil epl Microsoft-Windows-CertificateServices-Deployment/Operational c:\MSLOG\%COMPUTERNAME%_CertificateServices-Deployment_Operational.evtx
     ```
   - 证书存储信息

     ```
     certutil -v -silent -store MY > c:\MSLOG\%COMPUTERNAME%_cert-Personal-Registry.txt
     certutil -v -silent -store ROOT > c:\MSLOG\%COMPUTERNAME%_cert-TrustedRootCA-Registry.txt
     certutil -v -silent -store -grouppolicy ROOT > c:\MSLOG\%COMPUTERNAME%_cert-TrustedRootCA-GroupPolicy.txt
     certutil -v -silent -store -enterprise ROOT > c:\MSLOG\%COMPUTERNAME%_TrustedRootCA-Enterprise.txt
     certutil -v -silent -store TRUST > c:\MSLOG\%COMPUTERNAME%_cert-EnterpriseTrust-Reg.txt
     certutil -v -silent -store -grouppolicy TRUST > c:\MSLOG\%COMPUTERNAME%_cert-EnterpriseTrust-GroupPolicy.txt
     certutil -v -silent -store -enterprise TRUST > c:\MSLOG\%COMPUTERNAME%_cert-EnterpriseTrust-Enterprise.txt
     certutil -v -silent -store CA > c:\MSLOG\%COMPUTERNAME%_cert-IntermediateCA-Registry.txt
     certutil -v -silent -store -grouppolicy CA > c:\MSLOG\%COMPUTERNAME%_cert-IntermediateCA-GroupPolicy.txt
     certutil -v -silent -store -enterprise CA > c:\MSLOG\%COMPUTERNAME%_cert-Intermediate-Enterprise.txt
     certutil -v -silent -store AuthRoot > c:\MSLOG\%COMPUTERNAME%_cert-3rdPartyRootCA-Registry.txt
     certutil -v -silent -store -grouppolicy AuthRoot > c:\MSLOG\%COMPUTERNAME%_cert-3rdPartyRootCA-GroupPolicy.txt
     certutil -v -silent -store -enterprise AuthRoot > c:\MSLOG\%COMPUTERNAME%_cert-3rdPartyRootCA-Enterprise.txt
     certutil -v -silent -store SmartCardRoot > c:\MSLOG\%COMPUTERNAME%_cert-SmartCardRoot-Registry.txt
     certutil -v -silent -store -grouppolicy SmartCardRoot > c:\MSLOG\%COMPUTERNAME%_cert-SmartCardRoot-GroupPolicy.txt
     certutil -v -silent -store -enterprise SmartCardRoot > c:\MSLOG\%COMPUTERNAME%_cert-SmartCardRoot-Enterprise.txt
     certutil -v -silent -store -enterprise NTAUTH > c:\MSLOG\%COMPUTERNAME%_cert-NtAuth-Enterprise.txt
     certutil -v -silent -user -store MY > c:\MSLOG\%COMPUTERNAME%_cert-User-Personal-Registry.txt
     certutil -v -silent -user -store ROOT > c:\MSLOG\%COMPUTERNAME%_cert-User-TrustedRootCA-Registry.txt
     certutil -v -silent -user -store -enterprise ROOT > c:\MSLOG\%COMPUTERNAME%_cert-User-TrustedRootCA-Enterprise.txt
     certutil -v -silent -user -store TRUST > c:\MSLOG\%COMPUTERNAME%_cert-User-EnterpriseTrust-Registry.txt
     certutil -v -silent -user -store -grouppolicy TRUST > c:\MSLOG\%COMPUTERNAME%_cert-User-EnterpriseTrust-GroupPolicy.txt
     certutil -v -silent -user -store CA > c:\MSLOG\%COMPUTERNAME%_cert-User-IntermediateCA-Registry.txt
     certutil -v -silent -user -store -grouppolicy CA > c:\MSLOG\%COMPUTERNAME%_cert-User-IntermediateCA-GroupPolicy.txt
     certutil -v -silent -user -store Disallowed > c:\MSLOG\%COMPUTERNAME%_cert-User-UntrustedCertificates-Registry.txt
     certutil -v -silent -user -store -grouppolicy Disallowed > c:\MSLOG\%COMPUTERNAME%_cert-User-UntrustedCertificates-GroupPolicy.txt
     certutil -v -silent -user -store AuthRoot > c:\MSLOG\%COMPUTERNAME%_cert-User-3rdPartyRootCA-Registry.txt
     certutil -v -silent -user -store -grouppolicy AuthRoot > c:\MSLOG\%COMPUTERNAME%_cert-User-3rdPartyRootCA-GroupPolicy.txt
     certutil -v -silent -user -store SmartCardRoot > c:\MSLOG\%COMPUTERNAME%_cert-User-SmartCardRoot-Registry.txt
     certutil -v -silent -user -store -grouppolicy SmartCardRoot > c:\MSLOG\%COMPUTERNAME%_cert-User-SmartCardRoot-GroupPolicy.txt
     certutil -v -silent -user -store UserDS > c:\MSLOG\%COMPUTERNAME%_cert-User-UserDS.txt
     ```
   - CA 配置信息

     ```
     reg save HKLM\System\CurrentControlSet\Services\CertSvc c:\MSLOG\%COMPUTERNAME%_CertSvc.hiv
     reg export HKLM\System\CurrentControlSet\Services\CertSvc c:\MSLOG\%COMPUTERNAME%_CertSvc.txt
     reg save HKLM\SOFTWARE\Microsoft\Cryptography c:\MSLOG\%COMPUTERNAME%_Cryptography.hiv
     reg export HKLM\SOFTWARE\Microsoft\Cryptography c:\MSLOG\%COMPUTERNAME%_Cryptography.txt
     ```
3. 将以下文件（如果存在）复制到 *C：\MSLOG： %windir%\CAPolicy.inf*
4. 登录到域控制器并创建 *C：\MSLOG* 以存储捕获的日志。
5. 以管理员身份启动 Windows PowerShell。
6. 运行以下 PowerShell cmdlet。 替换“;..”中的域名。 ，DC=test，DC=local“;具有适当的域名。 该示例显示“;test.local“;域。

   ```
   Import-Module ActiveDirectory
   Get-ADObject -SearchBase ";CN=Public Key Services,CN=Services,CN=Configuration,DC=test,DC=local"; -Filter * -Properties * | fl * > C:\MSLOG\Get-ADObject_$Env:COMPUTERNAME.txt
   ```
7. 保存以下日志。

   - CA 上 C：\MSLOG *中的所有文件*
   - 域控制器上 *C：\MSLOG* 中的所有文件

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/data-collection-for-troubleshooting-802-1x-authentication-issues)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
