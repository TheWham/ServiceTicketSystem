# 在 Windows Defender 攻击防护中使用 VPN 丢失 Internet 连接 - 网络保护

本文提供了在审核模式或阻止模式和虚拟专用网络（VPN）中使用 Windows Defender 攻击防护中的网络保护功能时发生的错误的解决方案。

*适用于：*Windows 10 - 所有版本  
*原始 KB 数：* 4560203

## 现象

在审核模式或阻止模式和虚拟专用网络（VPN）中使用 Windows Defender 攻击防护中的网络保护功能时，会在 ping IP 地址时丢失网络连接并收到 **常规故障** 错误消息。

## 原因

出现此问题的原因是缺少支持网络保护功能的当前 （4.12.x.x） 反恶意软件平台更新。

## 解决方案

安装最新的 （4.18.x.x） 反恶意软件平台更新，如下所述：

- [Windows Defender 反恶意软件平台](https://support.microsoft.com/help/4052623)的更新。
- [管理 Windows Defender 防病毒更新并应用基线](/zh-cn/windows/security/threat-protection/windows-defender-antivirus/manage-updates-baselines-windows-defender-antivirus#released-platform-and-engine-versions)。
- [SCCM-Endpoint Protection：通过 SCCM ADR 为 Microsoft Defender AV 启用“平台更新”（第 4 部分）。](https://yongrhee.wordpress.com/2020/02/22/sccm-endpoint-protection-enabling-platform-update-for-microsoft-defender-av-via-sccm-adr-part-4/)

## 解决方法

将以下组策略设置为 **“未配置**”：

计算机配置 > 管理模板 > Windows 组件 > Windows Defender 防病毒 > Windows Defender 攻击防护 > 网络保护 > 阻止用户和应用访问危险网站

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/network-connectivity-lost)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
