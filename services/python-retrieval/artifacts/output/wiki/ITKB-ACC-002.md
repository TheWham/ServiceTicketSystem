---
id: "ITKB-ACC-002"
title: "密码重置与过期处理"
category: "账号与权限问题"
department: "IT 部"
version: "v1.0"
replaces: []
entities:
- name: "AD域控制器"
  type: "系统"
- name: "自助密码重置平台"
  type: "系统"
- name: "临时密码"
  type: "账号权限"
- name: "初始密码"
  type: "账号权限"
- name: "密码复杂度"
  type: "配置项"
- name: "密码策略"
  type: "配置项"
keywords: ["忘记密码", "重置密码", "修改密码", "密码过期", "首次登录", "密码不符合要求"]
summary: "针对忘记密码、密码过期、新员工初始密码等问题，提供自助平台重置与AD域控重置临时密码的处理流程。"
meta_source: "llm"
relations:
- target: "ITKB-ACC-001"
  type: "related"
  note: "账号锁定与密码重置同属域账号问题，均需在AD域控上操作，常配合处理"
  evidence: "AD域控制器：右键用户 → 重置密码 → 设置临时密码并勾选「用户下次登录时须更改密码」"
- target: "ITKB-ACC-004"
  type: "related"
  note: "密码问题与MFA验证失败同为登录环节故障，均提供先自助后IT的处理路径"
  evidence: "用户忘记密码无法登录，或系统提示「密码已过期，请更改密码」"
- target: "ITKB-APPENDIX-1"
  type: "process_applies"
  note: "本卡设有员工自助排查步骤，遵循员工自助排查流程规范"
  evidence: "员工自助排查：步骤1：访问公司自助密码重置平台（如有），通过手机验证码或备用邮箱重置"
- target: "ITKB-APPENDIX-2"
  type: "process_applies"
  note: "本卡IT工程师进阶处理环节适用IT故障排查通用流程"
  evidence: "IT工程师进阶处理：检查密码策略GPO是否正确应用（最小长度、复杂度、历史密码数、最长使用期限）"
graph_nodes:
- kind: "symptom"
  name: "用户忘记密码无法登录"
- kind: "symptom"
  name: "密码已过期，请更改密码"
- kind: "symptom"
  name: "新员工首次登录不知初始密码是什么"
- kind: "root_cause"
  name: "公司密码策略要求定期更换（如90天），到期未更换"
- kind: "root_cause"
  name: "用户自行修改后忘记新密码"
- kind: "root_cause"
  name: "新员工入职未收到初始密码通知"
- kind: "root_cause"
  name: "密码复杂度要求（长度、大小写、数字、特殊字符）未被满足"
- kind: "tool"
  name: "自助密码重置平台"
- kind: "tool"
  name: "AD域控制器"
- kind: "tool"
  name: "密码策略GPO"
graph_meta_source: "llm"
---

# 【ACC-002】密码重置与过期处理

## 现象描述

- 用户忘记密码无法登录，或系统提示「密码已过期，请更改密码」「密码不符合复杂度要求」。新员工首次登录不知初始密码是什么。

## 常见根因

- ① 公司密码策略要求定期更换（如90天），到期未更换
- ② 用户自行修改后忘记新密码
- ③ 新员工入职未收到初始密码通知
- ④ 密码复杂度要求（长度、大小写、数字、特殊字符）未被满足

## 员工自助排查

- 步骤1：访问公司自助密码重置平台（如有），通过手机验证码或备用邮箱重置。
- 步骤2：联系直属主管或IT支持人员协助重置。
- 步骤3：新员工查收入职邮件或联系HR获取初始密码。
- 步骤4：重置后立即登录并修改为符合复杂度要求的新密码。

## IT工程师进阶处理

- 1. AD域控制器：右键用户 → 重置密码 → 设置临时密码并勾选「用户下次登录时须更改密码」。
- 2. 告知用户临时密码（建议通过当面或电话告知，避免邮件明文）。
- 3. 检查密码策略GPO是否正确应用（最小长度、复杂度、历史密码数、最长使用期限）。
- 4. 推广自助密码重置系统，减少IT人力投入。

---
> 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 条目 ACC-002 · 分类「账号与权限问题」· 由清洗流水线自动生成
