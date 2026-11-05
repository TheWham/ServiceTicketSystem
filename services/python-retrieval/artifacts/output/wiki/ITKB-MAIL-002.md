---
id: "ITKB-MAIL-002"
title: "邮件接收失败处理"
category: "邮件与通讯问题"
department: "IT 部"
version: "v1.0"
replaces: []
entities:
- name: "Outlook"
  type: "软件"
- name: "网页版邮箱（OWA）"
  type: "系统"
- name: "Exchange"
  type: "系统"
- name: "POP3/IMAP"
  type: "协议"
- name: "垃圾邮件过滤器"
  type: "软件"
- name: "邮箱存储配额"
  type: "配置项"
- name: "反垃圾邮件网关"
  type: "系统"
- name: "邮件追踪（Message Trace）"
  type: "命令工具"
- name: "阻止发件人列表"
  type: "配置项"
- name: "安全发件人列表"
  type: "配置项"
- name: "Outlook规则"
  type: "配置项"
- name: "传输规则（Transport Rule）"
  type: "配置项"
- name: "Exchange Online"
  type: "系统"
- name: "Exchange Server"
  type: "系统"
- name: "Outlook配置文件"
  type: "配置项"
keywords: ["邮件", "收不到", "接收失败", "Outlook同步", "垃圾邮件", "白名单", "收件箱"]
summary: "处理邮件无法接收，通过网页邮箱、垃圾拦截、规则和配额排查账户同步问题。"
meta_source: "llm"
relations:
- target: "ITKB-ACC-002"
  type: "related"
  note: "密码变更后Outlook未更新保存密码是邮件接收失败的常见根因，需参考密码重置流程"
  evidence: "① 密码变更后Outlook未更新保存的密码"
- target: "ITKB-MAIL-003"
  type: "related"
  note: "同属邮件与通讯问题分类，IM登录/同步与邮件接收故障排查思路相近"
  evidence: "分类「邮件与通讯问题」"
- target: "ITKB-APPENDIX-1"
  type: "process_applies"
  note: "本卡员工自助排查环节遵循员工IT故障自助排查流程"
  evidence: "员工自助排查"
- target: "ITKB-APPENDIX-2"
  type: "process_applies"
  note: "本卡IT工程师进阶处理遵循IT故障排查通用流程的分层排查与日志分析规范"
  evidence: "IT工程师进阶处理"
graph_nodes:
- kind: "symptom"
  name: "Outlook或其他邮件客户端无法接收新邮件，刷新后无新邮件出现"
- kind: "symptom"
  name: "特定发件人的邮件总是收不到，但其他人发送的邮件正常"
- kind: "root_cause"
  name: "密码变更后Outlook未更新保存的密码"
- kind: "root_cause"
  name: "邮箱存储配额已满，无法接收新邮件"
- kind: "root_cause"
  name: "邮件被垃圾邮件过滤器误拦截"
- kind: "root_cause"
  name: "邮箱规则错误地将邮件移到了其他文件夹"
- kind: "root_cause"
  name: "POP3/IMAP协议设置不正确"
- kind: "root_cause"
  name: "发件人被加入了阻止发件人列表"
- kind: "tool"
  name: "网页版邮箱（OWA）"
- kind: "tool"
  name: "邮件追踪（Message Trace）"
graph_meta_source: "llm"
---

# 【MAIL-002】邮件接收失败处理

## 现象描述

- Outlook或其他邮件客户端无法接收新邮件，刷新后无新邮件出现。或特定发件人的邮件总是收不到，但其他人发送的邮件正常。常见于：Outlook更新后、密码变更后。

## 常见根因

- ① 密码变更后Outlook未更新保存的密码
- ② 邮箱存储配额已满，无法接收新邮件
- ③ 邮件被垃圾邮件过滤器误拦截
- ④ 邮箱规则错误地将邮件移到了其他文件夹
- ⑤ POP3/IMAP协议设置不正确
- ⑥ 发件人被加入了阻止发件人列表

## 员工自助排查

- 步骤1：登录网页版邮箱（OWA），检查是否能收到新邮件——能收到说明是客户端问题。
- 步骤2：检查垃圾邮件文件夹，是否有被误判的邮件。
- 步骤3：Outlook → 文件 → 账户设置 → 修复账户。
- 步骤4：检查Outlook规则（文件 → 管理规则和通知），删除可疑的移动规则。
- 步骤5：检查邮箱存储使用率（网页版 → 设置 → 常规 → 存储），清理到80%以下。
- 步骤6：将发件人添加到安全发件人列表（白名单）。

## IT工程师进阶处理

- 1. Exchange管理后台 → 邮件追踪（Message Trace），查询该邮件是否到达服务器。
- 2. 检查反垃圾邮件网关的隔离区，查找被误拦截的邮件并放行。
- 3. 提高用户邮箱配额。
- 4. 重建Outlook配置文件，或重新创建邮件账户。
- 5. 检查传输规则（Transport Rule），看是否有规则拦截了特定发件人。
- 6. 升级到Exchange Online或更新Exchange Server补丁。

---
> 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 条目 MAIL-002 · 分类「邮件与通讯问题」· 由清洗流水线自动生成
