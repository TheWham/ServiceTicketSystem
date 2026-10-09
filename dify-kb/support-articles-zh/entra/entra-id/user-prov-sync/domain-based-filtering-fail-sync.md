# 同步 Service Manager 中基于域的筛选更改无法同步

## 概要

本文介绍对 Active Directory 管理代理或 Active Directory 连接器中基于域的筛选的更改无法同步的问题。

*原始产品版本：*Microsoft Entra ID、云服务（Web 角色/辅助角色）、Microsoft Intune、Azure 备份、Office 365 标识管理  
*原始 KB 数：* 2998261

## 现象

在 Active Directory 管理代理或 Active Directory 连接器中更改基于域的筛选后，运行配置文件操作无法同步。在这种情况下，你会收到以下错误消息：

> missing-partition-for-run-step

此外，事件 ID 6020 的实例记录在事件查看器：

> 源：FIMSynchronization  
> 事件 ID：6020  
> 说明:  
> 管理代理“Active Directory 连接器”在运行配置文件“Delta Sync”上失败，因为配置中指定的分区无法找到。  
> 用户操作  
> 刷新并验证管理代理和目标分区的分区配置。

## 原因

如果未更新运行配置文件，则可能会出现此问题。

## 解决方法

### 如果要从同步过程中删除域

1. 在同步服务管理器中，选择“ **管理代理** ”选项卡或 **“连接器** ”选项卡。
2. 右键单击Active Directory 域服务的管理代理或连接器类型**，然后选择“**配置运行配置文件****”。
3. 查找包含 **字母数字字符字符串的分区** 值的步骤（例如{B3C9A66A-4C9C-457A-97B9-A0107037A416}），然后选择“ **删除步骤**”。
4. 依次选择“应用”、“确定” 。
5. 对每个运行配置文件重复步骤 3-4。
6. 再次右键单击同一管理代理或连接器，然后选择“ **运行**”。
7. 选择 **“完全同步**”，然后选择“ **确定**”。

### 如果要添加要同步的域

1. 在同步服务管理器中，选择“ **管理代理** ”选项卡或 **“连接器** ”选项卡。
2. 右键单击Active Directory 域服务的管理代理或连接器类型**，然后选择“**配置运行配置文件****”。
3. 在导航窗格中（左侧），选择管理代理运行配置文件。
4. 选择**新建步骤**。
5. 在“类型”下**，选择类似于在步骤 3 中选择的运行配置文件的选项，然后选择“**下一步**”。**
6. 在“分区**”下**，选择要添加的域，然后选择“**完成**”。
7. 为每个运行配置文件重复步骤 3-6。
8. 再次右键单击同一管理代理或连接器，然后选择“ **运行**”。
9. 选择 **“完全同步**”，然后选择“ **确定**”。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/domain-based-filtering-fail-sync)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
