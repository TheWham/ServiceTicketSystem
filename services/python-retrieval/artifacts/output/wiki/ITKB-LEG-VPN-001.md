---
id: "ITKB-LEG-VPN-001"
title: "VPN连接失败处理（旧版·PPTP，已废止）"
category: "VPN与远程办公"
department: "IT 部"
effective_date: "2022-01-01"
effective_date_source: "demo-constructed"
version: "v0.9"
replaces: []
entities:
- name: "VPN"
  type: "概念"
- name: "SSL VPN"
  type: "系统"
- name: "PPTP"
  type: "协议"
- name: "GRE"
  type: "协议"
- name: "防火墙"
  type: "设备"
- name: "NAT 设备"
  type: "设备"
- name: "PPTP 服务器"
  type: "系统"
- name: "1723 端口"
  type: "配置项"
- name: "VPN连接失败"
  type: "故障现象"
- name: "认证失败"
  type: "故障现象"
keywords: ["VPN", "远程办公", "拨号", "连接失败", "认证失败", "L2TP", "SSL VPN", "穿透性"]
summary: "（已废止，v1.0 版 ITKB-VPN-001 为准）旧版推荐 PPTP 协议连接并限制 SSL VPN 的处置方法。"
meta_source: "rule"
status: "已废止"
relations:
- target: "ITKB-VPN-001"
  type: "replaces"
  note: "本卡为v0.9旧版PPTP规约，已被ITKB-VPN-001全面废止并替代"
  evidence: "已于 v1.0 全面废止。现行标准请以《ITKB-VPN-001 VPN连接失败（拨号/认证失败）》为准"
graph_nodes:
- kind: "symptom"
  name: "连接失败"
- kind: "symptom"
  name: "无法建立VPN连接"
- kind: "symptom"
  name: "认证失败"
- kind: "root_cause"
  name: "PPTP 协议未启用或被运营商封锁"
- kind: "root_cause"
  name: "防火墙未放行 TCP 1723 端口和 GRE 47 协议"
- kind: "tool"
  name: "PPTP"
- kind: "tool"
  name: "SSL VPN"
graph_meta_source: "llm"
---

# 【LEG-VPN-001】VPN连接失败处理（旧版·PPTP，已废止）

> ⚠️ 本卡为 v0.9 旧版规约，**已于 v1.0 全面废止**。现行标准请以《ITKB-VPN-001 VPN连接失败（拨号/认证失败）》为准，仅作历史溯源保留。

## 现象描述

- 在家/出差期间连接公司VPN时，提示「连接失败」「无法建立VPN连接」「认证失败」。

## 常见根因

- ① PPTP 协议未启用或被运营商封锁
- ② 防火墙未放行 TCP 1723 端口和 GRE 47 协议

## 员工自助排查（已废止）

- 步骤1：推荐使用 PPTP 协议连接，配置最简单。
- 步骤2：防火墙需放行 TCP 1723 端口和 GRE 47 协议。
- 步骤3：不建议使用 SSL VPN，旧版评估其不稳定。

## IT工程师进阶处理（已废止）

- 1. 排查 PPTP 服务器的 1723 端口监听状态与 GRE 协议转发。
- 2. 确认 NAT 设备支持 GRE 穿越。

---
> 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 旧版条目 · 分类「VPN与远程办公」· v0.9 已废止，保留仅供版本冲突溯源
