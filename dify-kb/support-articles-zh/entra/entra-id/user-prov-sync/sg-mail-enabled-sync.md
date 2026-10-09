# 通过本地 AD 中的同步禁用安全组后，仍启用邮件

## 概要

本文提供有关解决安全组在通过本地 AD 中的同步禁用邮件后保持启用邮件的问题的信息。

*原始产品版本：* Microsoft Entra ID  
*原始 KB 数：* 4096314

## 现象

假设出现了下面这种情景：

- 你有一个安全组，其中包含本地 Active Directory（本地 AD）中指定的电子邮件地址。
- 安全组同步到 Microsoft Entra ID。
- 从本地 AD 中的安全组中删除电子邮件地址。
- 运行同步。
  在此方案中，安全组将保持启用邮件状态，并且它仍具有Microsoft Entra ID 中分配给它的原始电子邮件地址。

## 原因

当启用邮件的安全组同步到Microsoft Entra ID 时，使用原始域（`onmicrosoft.com`）的电子邮件地址将追加到组作为辅助电子邮件地址。 如果删除主电子邮件地址，具有原始域的电子邮件地址将成为主电子邮件地址。

以下是此问题的影响：

- 本地用户的全局地址列表（GAL）中不存在受影响的组，因此用户在发送电子邮件时无法选择“发件人**”中的组**。
- 对于 Exchange Online 用户，可以在 GAL 中找到受影响的组以供选择。 但是，由于组的邮件地址已更改为 `alias@contoso.onmicrosoft.com`，因此电子邮件不会到达收件人。
- 本地用户无法使用受影响的组来设置权限，例如对共享日历的访问权限。
- 对于 Exchange Online 用户，受影响的组可用于设置对日历的访问权限。

## 解决方法

若要解决此问题，请使用以下某种方法：

- 从管理门户删除安全组，然后再次运行同步。
- 将安全组移动到尚未同步的另一个组织单位（OU）（已筛选掉）。 执行此操作时，将从云中删除该组。 然后，将组移回原始 OU。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/sg-mail-enabled-sync)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
