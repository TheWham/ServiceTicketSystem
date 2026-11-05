---
id: "ITKB-MAIL-001"
title: "邮件无法发送处置指南"
category: "邮件与通讯问题"
department: "IT 部"
version: "v1.0"
replaces: []
entities:
- name: "Outlook"
  type: "软件"
- name: "网页邮箱"
  type: "系统"
- name: "SMTP"
  type: "协议"
- name: "退信"
  type: "故障现象"
- name: "Exchange"
  type: "软件"
- name: "反垃圾邮件网关"
  type: "设备"
- name: "OneDrive"
  type: "软件"
- name: "脱机工作"
  type: "配置项"
- name: "邮箱配额"
  type: "配置项"
- name: "白名单"
  type: "配置项"
- name: "SPF/DKIM/DMARC"
  type: "协议"
- name: "DNS"
  type: "协议"
- name: "MXToolbox"
  type: "命令工具"
- name: "防火墙"
  type: "设备"
- name: "配置文件"
  type: "配置项"
keywords: ["邮件", "Outlook", "发送失败", "退信", "SMTP", "发送报告", "邮件在发件箱", "无法送达"]
summary: "解决邮件发送失败或退信问题，按地址、附件、客户端、配额及反垃圾策略排查。"
meta_source: "llm"
relations:
- target: "ITKB-MAIL-002"
  type: "related"
  note: "邮件发送与接收为姊妹问题，共用网页邮箱测试、邮箱配额与垃圾拦截等排查手段"
  evidence: "邮箱已满（达到存储配额上限）"
- target: "ITKB-APPENDIX-1"
  type: "process_applies"
  note: "本卡设有员工自助排查六个步骤，遵循员工IT故障自助排查流程规范"
  evidence: "员工自助排查"
- target: "ITKB-APPENDIX-2"
  type: "process_applies"
  note: "IT工程师进阶处理包含日志分析与分层定位，符合IT故障排查通用七步流程"
  evidence: "检查邮件服务器SMTP日志，定位拒绝原因"
- target: "ITKB-NET-004"
  type: "related"
  note: "外发邮件到达率依赖DNS的SPF/DKIM/DMARC记录配置，与DNS解析排查相关"
  evidence: "检查DNS的SPF/DKIM/DMARC记录配置是否正确（影响外发邮件到达率）"
- target: "ITKB-STO-003"
  type: "related"
  note: "附件超过大小限制时建议改用OneDrive或公司内部云盘链接替代发送"
  evidence: "超过限制的用云盘链接替代（如 OneDrive / 公司内部云盘）"
graph_nodes:
- kind: "symptom"
  name: "邮件停留在发件箱无法发出"
- kind: "symptom"
  name: "收到退信通知"
- kind: "root_cause"
  name: "收件人邮箱地址写错"
- kind: "root_cause"
  name: "附件超过大小限制"
- kind: "root_cause"
  name: "SMTP服务器无响应或被防火墙拦截"
- kind: "root_cause"
  name: "邮箱已满（达到存储配额上限）"
- kind: "root_cause"
  name: "邮件被反垃圾邮件策略拦截"
- kind: "root_cause"
  name: "Outlook离线模式误开启"
- kind: "tool"
  name: "Exchange管理后台"
- kind: "tool"
  name: "MXToolbox查询"
graph_meta_source: "llm"
---

# 【MAIL-001】邮件无法发送处置指南

## 现象描述

- 在Outlook或网页邮箱中点击发送后，邮件停留在发件箱无法发出，或收到退信通知。退信常见提示：「550 Mailbox not found」「552 Message size exceeds」「554 Rejected」。

## 常见根因

- ① 收件人邮箱地址写错（拼写错误、用户不存在）
- ② 附件超过大小限制（公司邮箱通常限制20-50MB）
- ③ SMTP服务器无响应或被防火墙拦截
- ④ 邮箱已满（达到存储配额上限）
- ⑤ 邮件被反垃圾邮件策略拦截（内容含敏感词或可疑链接）
- ⑥ Outlook离线模式误开启

## 员工自助排查

- 步骤1：检查收件人地址拼写，确认无误后重发。
- 步骤2：检查附件大小，超过限制的用云盘链接替代（如 OneDrive / 公司内部云盘）。
- 步骤3：Outlook → 发送/接收 → 确认「脱机工作」未被选中。
- 步骤4：登录网页版邮箱测试发送是否正常——如果网页版正常，说明是Outlook客户端问题。
- 步骤5：清理邮箱，删除不需要的旧邮件，清空已删除邮件和垃圾邮件文件夹。
- 步骤6：暂时关闭杀毒软件邮件扫描功能测试。

## IT工程师进阶处理

- 1. 检查邮件服务器SMTP日志，定位拒绝原因。
- 2. 检查用户邮箱配额：Exchange管理后台 → 邮箱使用情况 → 提高配额或归档旧邮件。
- 3. 反垃圾邮件网关：检查该邮件是否被误判为垃圾邮件，添加到白名单。
- 4. 检查DNS的SPF/DKIM/DMARC记录配置是否正确（影响外发邮件到达率）。
- 5. Outlook配置修复：控制面板 → 邮件 → 配置文件 → 重建Outlook配置文件。
- 6. 检查公网IP是否在黑名单中（MXToolbox查询），如被列入需申请移出。

---
> 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 条目 MAIL-001 · 分类「邮件与通讯问题」· 由清洗流水线自动生成
