# DirectAccess 客户端可能无法连接并出现错误0x80092013

本文有助于解决 DirectAccess 客户端无法使用基于安全超文本传输协议（IP-HTTPS）连接的 Internet 协议连接到 DirectAccess 服务器的问题。

*原始 KB 数：* 2980672

## 现象

由于吊销检查失败，DirectAccess 客户端可能无法使用 IP 通过 IP-HTTPS 连接连接到 DirectAccess 服务器。

命令 netsh 接口 http show 接口的输出将显示以下错误：

> 错误：0x80092013
>
> 转换为：CRYPT\_E\_REVOCATION\_OFFLINE  
> # 吊销函数无法检查吊销，因为吊销服务器处于脱机状态。

## 原因

此错误可能由于以下原因之一而发生：

1. CRL 位置（CDP）无法访问。
2. CRL 位置（CDP）未发布。
3. CRL 已过期，未发布新的 CRL。
4. CRL 可访问，但客户端正在从旧缓存中选取。

## 解决方法

如果 CRL 位置（CDP）无法访问，请按照以下步骤验证 CRL 是否可从系统上下文下载：

1. 确定连接问题是否是由代理设置引起的。 若要确定这一点，可以使用以下注册表值进行查询：

   - cmd.exe /c reg 查询  
     `HKEY_USERS\.DEFAULT\Software\Microsoft\Windows\CurrentVersion\Internet Settings` /v ProxyEnable
   - cmd.exe /c reg 查询  
     `HKEY_USERS\.DEFAULT\Software\Microsoft\Windows\CurrentVersion\Internet Settings` /v ProxyServer
   - cmd.exe /c reg 查询  
     `HKEY_USERS\.DEFAULT\Software\Microsoft\Windows\CurrentVersion\Internet Settings` /v ProxyOverride
   - cmd.exe /c reg 查询  
     `HKEY_USERS\.DEFAULT\Software\Microsoft\Windows\CurrentVersion\Internet Settings` /v AutoConfigURL
   - cmd.exe /c reg 查询  
     `HKEY_USERS\S-1-5-18\Software\Microsoft\Windows\CurrentVersion\Internet Settings` /v ProxyEnable
   - cmd.exe /c reg 查询  
     `HKEY_USERS\S-1-5-18\Software\Microsoft\Windows\CurrentVersion\Internet Settings` /v ProxyServer
   - cmd.exe /c reg 查询  
     `HKEY_USERS\S-1-5-18\Software\Microsoft\Windows\CurrentVersion\Internet Settings` /v ProxyOverride
   - cmd.exe /c reg 查询  
     `HKEY_USERS\S-1-5-18\Software\Microsoft\Windows\CurrentVersion\Internet Settings` /v AutoConfigURL
   1. **如果 ProxyEnable** 值在任一中等于 1。 默认或 S-1-5-18，则表示不 **自动检测设置**。 这意味着，仅使用 ProxyServer **或 **AutoConfigURL** 中**定义的代理进行连接。
   2. 如果 ProxyEnable 值等于 0，则表示 **自动检测设置**。 因此，无法更改注册表中的值以使 DA 正常工作，因为 HKU\<UserSID> 配置单元是 HKCU 配置单元的转储。 每次系统服务**处于活动状态时**，都会覆盖对 HKU 所做的任何更改。 若要更改此设置，必须在系统帐户**（NT AUTHORITY\System）下**启动 Internet Explorer 或CMD.exe。 为此，请从提升的 **命令提示符** 运行：
   - psexec.exe -s -s -i cmd.exe /c reg add `HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings` /v ProxyEnable /t REG\_DWORD /d 0 /f
     - CRL 位置可能由于以下原因之一而无法访问：
     1. 系统上下文代理已应用，但无法访问，需要用户身份验证。
     2. 热点登录挂起。
     3. CRL 位置在 Internet 上不可用。
     4. 在授予访问权限之前，CRL 位置需要身份验证。
     5. CRL 位置可访问。 但不允许提供 CRL 文件。
     - 在这种情况下，请检查 **CRL 和 Delta CRL 文件的文件系统权限** 。
     - 确保 **为 CDP 位置启用了 DoubleEscaping** ：
       - Set-WebConfiguration -Filter system.webServer/security/requestFiltering -PSPath 'IIS：\Sites<SiteName> -Value @{allowDoubleEscaping=$true}
2. 如果未发布 CRL 位置（CDP），请执行以下步骤：

   1. 单击“开始**”**，指向**“管理工具**”，然后单击“**证书颁发机构**”。
   2. 在控制台树中，右键单击 **corp-DC1-CA**，然后单击“ **属性**”。
   3. **单击“扩展”选项卡**，然后单击“**添加**”。
   4. 在 **“位置”**中，键入 `http://\<Public-IIS-URL>/crld/` （需要 Internet 访问的 WAN URL）
   5. 在“变量**”中**，单击<“CAName>”，然后单击“**插入**”。
   6. 在变量**中**，单击 <CRLNameSuffix>，然后单击“**插入**”。
   7. 在变量**中**，单击 <DeltaCRLAllowed>，然后单击“**插入**”。
   8. 在 **Location** 中，键入位置字符串末尾的 .crl，然后单击“ **确定**”。
   9. 选择 **CRL 中的“包括** ”。 客户端使用此位置查找 Delta CRL 位置。 在 **颁发的证书的 CDP 扩展中选择“包括** ”，然后单击“ **确定**”。 然后单击“添加” 。
   10. 在 **Location** 中，键入 \<IIS-ServerName>\crldist$\ （证书颁发机构用于发布到客户端和由 IIS 用于为客户端提供服务的内部位置）。
   11. 在“变量**”中**，单击<“CAName>”，然后单击“**插入**”。
   12. 在变量中，单击 <CRLNameSuffix>，然后单击“ **插入**”。
   13. 在变量中，单击 <DeltaCRLAllowed>，然后单击“ **插入**”。
   14. 在 Location 中，键入字符串末尾的 .crl，然后单击“ **确定**”。
   15. 选择“ **将 CRL** 发布到此位置”， **然后将增量 CRL** 发布到此位置，然后单击“ **确定**”。
   16. 单击“是”重启 Active Directory 证书服务。
   17. 关闭证书颁发机构控制台。
3. 如果 CRL 已过期，请执行以下步骤：

   - 重新发布 CRL
     - Certutil -crl
4. 如果 CRL 可访问，但客户端正在从旧缓存中选取，请执行以下步骤：

   清除客户端缓存

   1. TVO （时间验证的对象）
      - Certutil -setreg chain\ChainCacheResyncFiletime @now
   2. URL 缓存
      - Certutil -urlcache \* delete

## 详细信息

DirectAccess 连接方法

DirectAccess 客户端使用多种方法连接到 DirectAccess 服务器。 这样就可以访问内部资源。 客户端可以选择使用 Teredo、6to4 或 IP-HTTPS 连接到 DirectAccess。 这也取决于 DirectAccess 服务器的配置方式。

当 DirectAccess 客户端具有公共 IPv4 地址时，它将尝试使用 6to4 接口进行连接。 但是，某些 ISP 提供公共 IP 地址的错觉。 他们向最终用户提供的内容是伪公共 IP 地址。 这意味着 DirectAccess 客户端（数据卡或 SIM 连接）收到的 IP 地址可能是来自公共地址空间的 IP，但实际上位于一个或多个 NAT 后面。

当客户端位于 NAT 设备后面时，它将尝试使用 Teredo。 许多企业（如酒店、机场和咖啡店）不允许 Teredo 流量穿过防火墙。 在这种情况下，客户端将故障转移到 IP-HTTPS。 IP-HTTPS 是基于 SSL （TLS） TCP 443 的连接生成的。 SSL 出站流量很可能在所有网络上都允许。

考虑到这一点，IP-HTTPS 已生成，以提供可靠且始终可访问的备份连接。 当其他方法（如 Teredo 或 6to4）失败时，DirectAccess 客户端将使用此客户端。

有关转换技术的详细信息，请参阅 [IPv6 转换技术](https://technet.microsoft.com/library/bb726951.aspx)。

证书吊销列表

证书吊销列表（CRL）用于向尝试验证证书有效性的个人、计算机和应用程序分发有关吊销证书的信息。 CRL 是已吊销的未过期证书的完整数字签名列表。 CRL 由客户端检索，这些客户端随后可以缓存 CRL（基于 CRL 配置的生存期），并使用它来验证提供的证书以供使用。 默认情况下，CRL 由Microsoft企业 CA 在两个位置发布：

- `http://CAName/certenroll/CRLName`
- LDAP:///CN=CAName,CN=CAComputerName,CN=CDP,CN=PublicKeyServices,CN=Services,CN=Configuration,DC=ForestRootDomain,DC=TLD

基本证书链验证

当 CryptoAPI 生成并验证证书链时，会出现三个不同的阶段：

1. 所有可能的证书链都是使用本地缓存证书生成的。 如果自签名证书中没有任何证书链结束，则 CryptoAPI 会选择最佳链，并尝试检索颁发者证书（在颁发机构信息访问扩展中指定的颁发者证书）以完成链。 此过程将重复，直到生成自签名证书的链。
2. 对于在受信任的根存储中以自签名证书结尾的每个链，将执行吊销检查。
3. 吊销检查从根 CA 证书向下执行到评估的证书。

有关证书吊销列表（CRL）分发点的详细信息，请参阅 [“指定 CRL 分发点”](https://technet.microsoft.com/library/cc753296.aspx)

证书吊销检查和 CRL 分发点

DirectAccess 客户端和 DirectAccess 服务器之间的 IP-HTTPS 连接需要证书吊销检查。 如果证书吊销检查失败，DirectAccess 客户端无法与 DirectAccess 服务器建立基于 IP 的 HTTPS 连接。 因此，基于 Internet 的 CRL 分发点位置必须存在于 IP-HTTPS 证书中，并且可用于连接到 Internet 的 DirectAccess 客户端。

DirectAccess 客户端与网络位置服务器之间基于 IP-HTTPS 的连接需要认证吊销检查。 如果证书吊销检查失败，DirectAccess 客户端无法访问网络位置服务器上的基于 IP-HTTPS 的 URL。 因此，基于 Intranet 的 CRL 分发点位置必须存在于网络位置服务器证书中，并且可用于连接到 Intranet 的 DirectAccess 客户端，即使名称解析策略表 （NRPT） 中存在 DirectAccess 规则也是如此。

DirectAccess 客户端和 DirectAccess 服务器之间的 IPsec 隧道需要认证吊销检查。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/directaccess-clients-unable-connect-error-0x80092013)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
