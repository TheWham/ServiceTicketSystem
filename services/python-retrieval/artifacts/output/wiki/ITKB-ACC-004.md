---
id: "ITKB-ACC-004"
title: "多因素认证（MFA）验证失败"
category: "账号与权限问题"
department: "IT 部"
version: "v1.0"
replaces: []
entities:
- name: "多因素认证（MFA）"
  type: "概念"
- name: "Authenticator"
  type: "软件"
- name: "短信验证码"
  type: "概念"
- name: "SIM卡"
  type: "设备"
- name: "MFA管理后台"
  type: "系统"
- name: "Azure AD MFA"
  type: "系统"
- name: "Duo"
  type: "软件"
- name: "RSA"
  type: "软件"
- name: "MFA服务器"
  type: "系统"
- name: "注册二维码"
  type: "概念"
- name: "备用验证码"
  type: "概念"
- name: "令牌"
  type: "概念"
- name: "时间校正"
  type: "配置项"
- name: "自动设置"
  type: "配置项"
keywords: ["MFA", "双重认证", "验证码", "手机令牌", "Authenticator", "二次验证", "收不到验证码"]
summary: "解决登录时MFA验证码收不到或验证失败问题：先自助校正手机时间、检查信号，再由IT重置令牌或重新绑定。"
meta_source: "llm"
relations:
- target: "ITKB-APPENDIX-1"
  type: "process_applies"
  note: "本卡员工侧处置按自助排查到联系IT的路径执行，适用于员工IT故障自助排查流程。"
  evidence: "步骤5：联系IT申请临时绕过MFA或重新绑定"
- target: "ITKB-APPENDIX-2"
  type: "process_applies"
  note: "本卡IT侧进阶处理属于故障排查处置，适用于IT故障排查通用流程。"
  evidence: "IT工程师进阶处理"
- target: "ITKB-ACC-001"
  type: "related"
  note: "与域账号锁定同属账号与权限问题，且均影响登录访问链路。"
  evidence: "分类「账号与权限问题」"
graph_nodes:
- kind: "symptom"
  name: "收不到验证码"
- kind: "symptom"
  name: "验证码错误"
- kind: "symptom"
  name: "验证失败请重试"
- kind: "root_cause"
  name: "手机时间与服务器时间不同步"
- kind: "root_cause"
  name: "手机无信号或短信被拦截"
- kind: "root_cause"
  name: "换手机后未重新绑定Authenticator"
- kind: "root_cause"
  name: "绑定的手机号已变更"
- kind: "root_cause"
  name: "MFA服务器故障"
- kind: "tool"
  name: "Authenticator"
- kind: "tool"
  name: "MFA管理后台"
graph_meta_source: "llm"
---

# 【ACC-004】多因素认证（MFA）验证失败

## 现象描述

- 登录时要求输入手机验证码或Authenticator验证码，但收不到验证码、验证码错误、或提示「验证失败请重试」。常见于：换手机后、手机时间不同步、SIM卡故障。

## 常见根因

- ① 手机时间与服务器时间不同步（Authenticator时间偏差>30秒）
- ② 手机无信号或短信被拦截
- ③ 换手机后未重新绑定Authenticator
- ④ 绑定的手机号已变更
- ⑤ MFA服务器故障

## 员工自助排查

- 步骤1：检查手机时间 → 设置 → 日期和时间 → 确保「自动设置」已开启。
- 步骤2：在Authenticator App中手动同步时间（设置 → 时间校正）。
- 步骤3：尝试短信验证码替代Authenticator（如有该选项）。
- 步骤4：检查手机信号和短信收件箱是否已满。
- 步骤5：联系IT申请临时绕过MFA或重新绑定。

## IT工程师进阶处理

- 1. 在MFA管理后台清除用户现有令牌，生成新的注册二维码。
- 2. 临时禁用MFA（需审批），让用户先登录，再重新绑定。
- 3. 更新用户绑定的手机号。
- 4. 检查MFA服务器状态（如Azure AD MFA、Duo、RSA等）。
- 5. 提供备用验证码作为短期解决方案。

---
> 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 条目 ACC-004 · 分类「账号与权限问题」· 由清洗流水线自动生成
