---
id: "ITKB-ACC-001"
title: "域账号锁定排查与解锁处理"
category: "账号与权限问题"
department: "IT 部"
effective_date: "2024-03-01"
effective_date_source: "demo-constructed"
version: "v1.0"
replaces: ["ITKB-LEG-ACC-001"]
entities:
- name: "AD域"
  type: "系统"
- name: "Active Directory用户和计算机"
  type: "软件"
- name: "事件ID 4740"
  type: "概念"
- name: "组策略"
  type: "概念"
- name: "账户锁定策略"
  type: "配置项"
- name: "自助密码重置平台"
  type: "系统"
- name: "安全日志"
  type: "概念"
keywords: ["账号锁定", "密码错误", "登录失败", "AD域", "账号禁用", "多次输错密码", "解锁账号"]
summary: "针对密码多次输错等原因引发的域账号锁定，提供员工自助排查步骤及IT侧AD解锁与锁定溯源流程。"
meta_source: "llm"
relations:
- target: "ITKB-LEG-ACC-001"
  type: "replaces"
  note: "本卡为现行版域账号锁定处理规范，替代已废止的旧版宽松锁定策略卡"
  evidence: "（已废止，v1.0 版 ITKB-ACC-001 为准）旧版宽松锁定策略：3 次锁定、不自动解锁，与现行 5 次/15-30分钟策略冲突。"
- target: "ITKB-ACC-002"
  type: "related"
  note: "账号锁定后需通过自助密码重置平台重置密码，与密码重置流程衔接"
  evidence: "步骤4：联系IT或通过自助密码重置平台重置密码后重试。"
- target: "ITKB-APPENDIX-1"
  type: "process_applies"
  note: "本卡设有员工自助排查步骤，员工IT故障自助排查流程适用于本卡"
  evidence: "## 员工自助排查"
- target: "ITKB-APPENDIX-2"
  type: "process_applies"
  note: "本卡IT工程师进阶处理遵循IT故障排查通用流程"
  evidence: "## IT工程师进阶处理"
- target: "ITKB-VPN-003"
  type: "related"
  note: "远程桌面等其他设备上用此账号尝试登录可能触发账号锁定"
  evidence: "有人在其他设备上用此账号尝试登录（如共享电脑、远程桌面）"
- target: "ITKB-MAIL-003"
  type: "related"
  note: "手机/平板上邮箱、企业微信等客户端保存旧密码不停重试是账号锁定根因之一"
  evidence: "检查手机/平板上是否有邮箱、企业微信等客户端还在用旧密码——先退出登录。"
- target: "ITKB-LEG-ACC-001"
  type: "replaces"
  note: "frontmatter replaces 规则迁移"
  evidence: "frontmatter:replaces"
graph_nodes:
- kind: "symptom"
  name: "账号已被锁定"
- kind: "symptom"
  name: "账号已禁用"
- kind: "symptom"
  name: "登录失败次数过多，请稍后再试"
- kind: "root_cause"
  name: "连续多次输入错误密码触发安全策略"
- kind: "root_cause"
  name: "有人在其他设备上用此账号尝试登录（如共享电脑、远程桌面）"
- kind: "root_cause"
  name: "手机/平板上的邮箱客户端保存了旧密码不停重试"
- kind: "root_cause"
  name: "账号被盗用，攻击者在暴力破解"
- kind: "tool"
  name: "Active Directory用户和计算机"
- kind: "tool"
  name: "事件ID 4740"
- kind: "tool"
  name: "自助密码重置平台"
graph_meta_source: "llm"
---

# 【ACC-001】域账号锁定排查与解锁处理

## 现象描述

- 登录时提示「账号已被锁定」「账号已禁用」「登录失败次数过多，请稍后再试」「账户已被锁定，请联系管理员」。常见于：密码输错超过5次后、离职员工账号未及时禁用被他人尝试登录。

## 常见根因

- ① 连续多次输入错误密码触发安全策略
- ② 有人在其他设备上用此账号尝试登录（如共享电脑、远程桌面）
- ③ 手机/平板上的邮箱客户端保存了旧密码不停重试
- ④ 账号被盗用，攻击者在暴力破解
- ⑤ 管理员主动禁用（离职、违规、审计需要）

## 员工自助排查

- 步骤1：等待15-30分钟，部分策略会自动解锁。
- 步骤2：确认Caps Lock（大写锁定）和Num Lock没有误开启。
- 步骤3：检查手机/平板上是否有邮箱、企业微信等客户端还在用旧密码——先退出登录。
- 步骤4：联系IT或通过自助密码重置平台重置密码后重试。
- 步骤5：如果记得正确密码，等待锁定时间后重试。

## IT工程师进阶处理

- 1. AD域控制器 → Active Directory用户和计算机 → 找到用户 → 属性 → 账户 → 解锁账户。
- 2. 检查安全日志（事件ID 4740），确认锁定来源IP和设备名。
- 3. 如果来自未知IP，可能涉及安全事件，需上报信息安全团队。
- 4. 重置密码并勾选「用户下次登录时须更改密码」。
- 5. 检查账户锁定策略（组策略 → 计算机配置 → Windows设置 → 安全设置 → 账户策略）。
- 6. 建议用户绑定手机/邮箱用于自助解锁。

---
> 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 条目 ACC-001 · 分类「账号与权限问题」· 由清洗流水线自动生成
