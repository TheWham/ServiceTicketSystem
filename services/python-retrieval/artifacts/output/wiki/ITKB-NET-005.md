---
id: "ITKB-NET-005"
title: "IP地址冲突处置"
category: "网络连接问题"
department: "IT 部"
version: "v1.0"
replaces: []
entities: ["IP地址", "DHCP", "静态IP", "ARP", "MAC地址", "交换机", "路由器", "DHCP Snooping"]
keywords: ["IP冲突", "黄色感叹号", "IP地址重复", "DHCP", "静态IP", "网络受限"]
summary: "处置IP地址冲突断网，重获IP并排查静态IP、DHCP异常或私接路由。"
meta_source: "llm"
---

# 【NET-005】IP地址冲突处置

## 现象描述

- 电脑右下角网络图标显示黄色感叹号，提示「IP地址冲突」「网络上已有重复的名称」或「无Internet访问」。同一局域网内两台或多台设备间歇性断网。

## 常见根因

- ① 手动设置了与DHCP池重叠的静态IP
- ② DHCP服务器故障，重复分配同一IP
- ③ 有员工私自接入路由器并开启了DHCP服务
- ④ 虚拟机网卡桥接模式占用了宿主机IP

## 员工自助排查

- 步骤1：Win+R → cmd → ipconfig /release 然后 ipconfig /renew，重新获取IP。
- 步骤2：如果公司要求自动获取IP，检查是否手工设置了静态IP——改为「自动获得IP地址」。
- 步骤3：重启电脑。
- 步骤4：如果仍不行，联系IT告知你的IP地址和工位号。

## IT工程师进阶处理

- 1. 在交换机上查看ARP表，定位冲突IP对应的两个MAC地址。
- 2. 通过MAC地址表追踪到冲突设备所在的交换机端口。
- 3. 扫描局域网内是否有人私接路由器（检测DHCP Server）。
- 4. 规范IP分配策略：DHCP保留区与静态IP区严格分开。
- 5. 在核心交换机启用DHCP Snooping，防止私接DHCP服务器。

---
> 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 条目 NET-005 · 分类「网络连接问题」· 由清洗流水线自动生成
