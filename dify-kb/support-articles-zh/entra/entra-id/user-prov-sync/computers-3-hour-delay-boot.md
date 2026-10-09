# Microsoft已加入 Entra 的计算机在启动期间遇到三个小时的延迟

## 概要

本文描述了当工作组名称与本地 Active Directory 域的 NetBIOS 名称相同时，启动过程中会出现三小时的延迟，并说明如何解决此问题。

*原始产品版本：* Microsoft Entra ID  
*原始 KB 数：* 4565997

## 现象

假设出现了下面这种情景：

1. 使用 Microsoft Entra Connect 将联合用户从本地 Active Directory域同步到 Microsoft Entra ID。
2. 计算机Microsoft已加入 Entra，工作组名称与本地域的 NetBIOS 名称相同。
3. 已使用联合用户至少登录此计算机一次。

在这种情况下，重启 OS 时，计算机需要大约三个小时才能进入登录屏幕。 在此期间，你将看到一个黑屏，显示活动图标（旋转圆点）。 启动后大约三个小时，启动过程完成，并显示交互式登录屏幕，用户可以登录时不会出现问题。

这种缓慢的启动体验不依赖于硬件配置。 具有“优秀”硬件规格的计算机也可能会遇到此问题。

## 原因

出现此问题的原因是 Windows 意外地评估了启动 10,000 秒的等待时间的条件。 此超时条件显示为三小时的启动延迟。

注意

有关参考，10,000 秒 = 167 分钟 = 2 小时 47 分钟。

## 解决方法

若要解决此问题，请使用与本地域的 NetBIOS 名称不匹配的工作组名称。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/computers-3-hour-delay-boot)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
