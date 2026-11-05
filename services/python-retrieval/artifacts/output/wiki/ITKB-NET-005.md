---
id: "ITKB-NET-005"
title: "IP地址冲突处置"
category: "网络连接问题"
department: "IT 部"
version: "v1.0"
replaces: []
entities:
- name: "IP地址冲突"
  type: "故障现象"
- name: "IP地址"
  type: "概念"
- name: "DHCP"
  type: "协议"
- name: "DHCP服务器"
  type: "系统"
- name: "DHCP池"
  type: "概念"
- name: "DHCP Snooping"
  type: "概念"
- name: "静态IP"
  type: "概念"
- name: "ARP"
  type: "协议"
- name: "MAC地址"
  type: "概念"
- name: "交换机"
  type: "设备"
- name: "路由器"
  type: "设备"
- name: "虚拟机"
  type: "软件"
- name: "cmd"
  type: "命令工具"
- name: "ipconfig /release"
  type: "命令工具"
- name: "ipconfig /renew"
  type: "命令工具"
keywords: ["IP冲突", "黄色感叹号", "IP地址重复", "DHCP", "静态IP", "网络受限"]
summary: "处置IP地址冲突断网，重获IP并排查静态IP、DHCP异常或私接路由。"
meta_source: "llm"
relations:
- target: "ITKB-APPENDIX-1"
  type: "process_applies"
  note: "本卡设有员工自助排查环节，步骤与员工自助排查五步法（重启、收集信息、提交IT）一致"
  evidence: "员工自助排查：步骤3：重启电脑；步骤4：如果仍不行，联系IT告知你的IP地址和工位号"
- target: "ITKB-APPENDIX-2"
  type: "process_applies"
  note: "本卡IT侧处理遵循通用排查流程的分层排查与修复规范"
  evidence: "IT工程师进阶处理"
- target: "ITKB-APPENDIX-3"
  type: "related"
  note: "本卡自助步骤使用的ipconfig释放/更新命令可在命令速查表中查证"
  evidence: "ipconfig /release 然后 ipconfig /renew"
- target: "ITKB-NET-002"
  type: "related"
  note: "同为接入层网络故障，均涉及交换机端口与DHCP分配排查"
  evidence: "通过MAC地址表追踪到冲突设备所在的交换机端口"
- target: "ITKB-NET-003"
  type: "related"
  note: "IP冲突引发的间歇性断网与网络断连故障症状重叠，需相互鉴别"
  evidence: "同一局域网内两台或多台设备间歇性断网"
- target: "ITKB-NET-001"
  type: "related"
  note: "WiFi连接场景同样可能出现IP冲突导致的黄色感叹号与无Internet访问"
  evidence: "电脑右下角网络图标显示黄色感叹号"
- target: "ITKB-VPN-002"
  type: "related"
  note: "VPN已连接但无法访问内网的排查项包含IP段冲突，与本卡主题呼应"
  evidence: "手动设置了与DHCP池重叠的静态IP"
graph_nodes:
- kind: "symptom"
  name: "网络图标显示黄色感叹号"
- kind: "symptom"
  name: "提示「IP地址冲突」「网络上已有重复的名称」"
- kind: "symptom"
  name: "间歇性断网"
- kind: "root_cause"
  name: "手动设置了与DHCP池重叠的静态IP"
- kind: "root_cause"
  name: "DHCP服务器故障，重复分配同一IP"
- kind: "root_cause"
  name: "有员工私自接入路由器并开启了DHCP服务"
- kind: "root_cause"
  name: "虚拟机网卡桥接模式占用了宿主机IP"
- kind: "tool"
  name: "ipconfig /release 然后 ipconfig /renew"
- kind: "tool"
  name: "在交换机上查看ARP表"
- kind: "tool"
  name: "DHCP Snooping"
graph_meta_source: "llm"
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
