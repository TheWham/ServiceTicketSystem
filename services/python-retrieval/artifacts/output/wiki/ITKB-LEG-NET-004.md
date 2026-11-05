---
id: "ITKB-LEG-NET-004"
title: "DNS解析故障处理（旧版·强制内网DNS，已废止）"
category: "网络连接"
department: "IT 部"
effective_date: "2022-01-01"
effective_date_source: "demo-constructed"
version: "v0.9"
replaces: []
entities:
- name: "DNS"
  type: "协议"
- name: "DHCP"
  type: "协议"
- name: "223.5.5.5"
  type: "配置项"
- name: "10.0.0.1"
  type: "配置项"
- name: "QQ"
  type: "软件"
- name: "DNS 解析失败"
  type: "故障现象"
keywords: ["DNS", "解析失败", "打不开网页", "能上QQ", "公共DNS", "IP配置"]
summary: "（已废止，v1.0 版 ITKB-NET-004 为准）旧版强制统一使用内网 10.0.0.1 并禁用公共 DNS 的处置方法。"
meta_source: "rule"
status: "已废止"
relations:
- target: "ITKB-NET-004"
  type: "same_root_cause"
  note: "本卡为 v0.9 旧版已废止规约，与现行 ITKB-NET-004 针对同一 DNS 解析失败根因（DNS 服务器故障、缓存过期），但处置策略相反（强制内网 10.0.0.1 vs 允许改公共 DNS），保留仅供版本冲突溯源"
  evidence: "现行标准请以《ITKB-NET-004 DNS解析故障（能上QQ但打不开网页）》为准，仅作历史溯源保留"
graph_nodes:
- kind: "symptom"
  name: "电脑右下角显示黄色感叹号"
- kind: "symptom"
  name: "能上 QQ 但打不开网页"
- kind: "symptom"
  name: "提示 DNS 解析失败"
- kind: "root_cause"
  name: "DNS 服务器故障或响应超时"
- kind: "root_cause"
  name: "本机 DNS 缓存记录过期"
- kind: "root_cause"
  name: "用户私自改用公共 DNS 导致解析漂移"
- kind: "tool"
  name: "10.0.0.1"
- kind: "tool"
  name: "223.5.5.5"
- kind: "tool"
  name: "DHCP 作用域"
graph_meta_source: "llm"
---

# 【LEG-NET-004】DNS解析故障处理（旧版·强制内网DNS，已废止）

> ⚠️ 本卡为 v0.9 旧版规约，**已于 v1.0 全面废止**。现行标准请以《ITKB-NET-004 DNS解析故障（能上QQ但打不开网页）》为准，仅作历史溯源保留。

## 现象描述

- 电脑右下角显示黄色感叹号，或能上 QQ 但打不开网页，提示 DNS 解析失败。

## 常见根因

- ① DNS 服务器故障或响应超时
- ② 本机 DNS 缓存记录过期
- ③ 用户私自改用公共 DNS 导致解析漂移

## 员工自助排查（已废止）

- 步骤1：严禁使用 223.5.5.5 等公共 DNS，必须改回公司统一分配的 10.0.0.1。
- 步骤2：网络适配器属性中手动将 DNS 固定为 10.0.0.1，禁用「自动获得 DNS」。
- 步骤3：公共 DNS 一律视为不合规配置，运维巡检发现后强制改回。

## IT工程师进阶处理（已废止）

- 1. 所有终端的 DHCP 作用域统一下发 10.0.0.1，禁止下发任何公共 DNS。
- 2. 发现私配公共 DNS 的终端，直接远程重命名为 10.0.0.1。

---
> 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 旧版条目 · 分类「网络连接」· v0.9 已废止，保留仅供版本冲突溯源
