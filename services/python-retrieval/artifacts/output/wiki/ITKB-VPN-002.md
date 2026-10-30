---
id: "ITKB-VPN-002"
title: "VPN连接后无法访问内网资源"
category: "VPN与远程办公"
department: "IT 部"
version: "v1.0"
replaces: []
entities:
- name: "VPN"
  type: "协议"
- name: "split tunnel"
  type: "配置项"
- name: "DNS"
  type: "协议"
- name: "路由表"
  type: "配置项"
- name: "IP段冲突"
  type: "故障现象"
- name: "Windows防火墙"
  type: "软件"
- name: "VPN客户端"
  type: "软件"
- name: "Always-On VPN"
  type: "系统"
- name: "VPN服务器"
  type: "系统"
- name: "ipconfig"
  type: "命令工具"
- name: "ping"
  type: "命令工具"
- name: "route print"
  type: "命令工具"
- name: "管理员权限"
  type: "账号权限"
- name: "VPN策略"
  type: "配置项"
- name: "DNS后缀"
  type: "配置项"
keywords: ["VPN", "内网", "无法访问", "路由", "DNS", "共享文件夹", "内网系统"]
summary: "解决VPN已连接但无法访问内网资源问题，按路由推送、DNS、IP段冲突、防火墙及客户端权限逐项排查处置。"
meta_source: "llm"
relations:
- target: "ITKB-VPN-001"
  type: "related"
  note: "同属VPN故障场景：VPN-001处理拨号/认证失败，本卡处理已连接后无法访问内网资源，前后衔接。"
  evidence: "VPN显示已连接，但无法访问公司内网资源"
- target: "ITKB-NET-004"
  type: "same_root_cause"
  note: "DNS未切换/解析异常是两卡共同根因，本卡DNS排查与NET-004的DNS解析失败处置一致。"
  evidence: "DNS未自动切换为公司内部DNS"
- target: "ITKB-NET-005"
  type: "same_root_cause"
  note: "家庭网络与公司内网IP段冲突属IP冲突类根因，与NET-005的IP地址冲突处置同源。"
  evidence: "本地网络与公司内网IP段冲突（如家里也是192.168.1.x）"
- target: "ITKB-STO-002"
  type: "related"
  note: "本卡现象含共享文件夹打不开，VPN连通后共享盘访问失败可转STO-002继续排查。"
  evidence: "共享文件夹打不开"
- target: "ITKB-APPENDIX-1"
  type: "process_applies"
  note: "本卡设有员工自助排查步骤1-5，适用员工IT故障自助排查流程规范。"
  evidence: "员工自助排查"
- target: "ITKB-APPENDIX-2"
  type: "process_applies"
  note: "本卡按路由、DNS、IP段、防火墙、权限逐项分层排查，符合IT故障排查通用流程。"
  evidence: "按路由推送、DNS、IP段冲突、防火墙及客户端权限逐项排查处置"
- target: "ITKB-APPENDIX-3"
  type: "related"
  note: "本卡排查使用ipconfig、ping、route print等命令，可对照常用排查命令速查表。"
  evidence: "检查VPN服务器推送的路由表（route print）"
graph_nodes:
- kind: "symptom"
  name: "VPN显示已连接，但无法访问公司内网资源"
- kind: "symptom"
  name: "共享文件夹打不开"
- kind: "symptom"
  name: "ping内网IP不通"
- kind: "root_cause"
  name: "VPN路由未正确推送到客户端（split tunnel配置问题）"
- kind: "root_cause"
  name: "本地网络与公司内网IP段冲突（如家里也是192.168.1.x）"
- kind: "root_cause"
  name: "DNS未自动切换为公司内部DNS"
- kind: "root_cause"
  name: "Windows防火墙阻断了VPN接口的流量"
- kind: "root_cause"
  name: "VPN客户端没有管理员权限，无法添加路由"
- kind: "tool"
  name: "ipconfig"
- kind: "tool"
  name: "route print"
graph_meta_source: "llm"
---

# 【VPN-002】VPN连接后无法访问内网资源

## 现象描述

- VPN显示已连接，但无法访问公司内网资源：共享文件夹打不开、内网系统（OA/ERP/代码库）无法访问、ping内网IP不通。

## 常见根因

- ① VPN路由未正确推送到客户端（split tunnel配置问题）
- ② 本地网络与公司内网IP段冲突（如家里也是192.168.1.x）
- ③ DNS未自动切换为公司内部DNS
- ④ Windows防火墙阻断了VPN接口的流量
- ⑤ VPN客户端没有管理员权限，无法添加路由
- ⑥ 访问的资源端口在VPN策略中未放行

## 员工自助排查

- 步骤1：VPN连接后，Win+R → cmd → ipconfig → 检查是否获取到了VPN分配的IP和DNS。
- 步骤2：ping内网服务器IP测试（如 ping 10.x.x.x），如果能通IP但打不开网页，说明是DNS问题。
- 步骤3：ping内网域名测试DNS，如果不通，手动设置DNS为公司内部DNS。
- 步骤4：以管理员身份运行VPN客户端。
- 步骤5：检查家里路由器的IP段（如192.168.1.x）是否与公司内网IP段冲突，如冲突则改家庭路由器IP段。

## IT工程师进阶处理

- 1. 检查VPN服务器推送的路由表（route print），确认内网网段是否在路由表中。
- 2. 检查DNS后缀推送配置：确保VPN连接后自动添加公司域名后缀。
- 3. 如果家庭IP段与公司冲突，指导用户更改家庭路由器LAN网段（如改为192.168.99.x）。
- 4. 在VPN策略中放行所需的内网资源IP及端口。
- 5. 考虑实施Always-On VPN或零信任方案，减少传统VPN的配置复杂度。

---
> 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 条目 VPN-002 · 分类「VPN与远程办公」· 由清洗流水线自动生成
