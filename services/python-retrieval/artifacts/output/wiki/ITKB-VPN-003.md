---
id: "ITKB-VPN-003"
title: "远程桌面(RDP)连接失败排查"
category: "VPN与远程办公"
department: "IT 部"
version: "v1.0"
replaces: []
entities:
- name: "远程桌面(RDP)"
  type: "协议"
- name: "mstsc"
  type: "命令工具"
- name: "VPN"
  type: "系统"
- name: "TCP 3389"
  type: "概念"
- name: "Windows防火墙"
  type: "软件"
- name: "组策略"
  type: "配置项"
- name: "ping"
  type: "命令工具"
- name: "ipconfig"
  type: "命令工具"
- name: "DHCP"
  type: "协议"
- name: "Remote Desktop Connection Manager"
  type: "软件"
- name: "ToDesk"
  type: "软件"
- name: "TeamViewer"
  type: "软件"
- name: "AD账号"
  type: "账号权限"
keywords: ["远程桌面", "RDP", "远程连接", "MSTSC", "3389", "内网机器", "凭据错误"]
summary: "解决远程桌面连接内网电脑失败问题，按开机状态、远程桌面开关、VPN与防火墙、NLA凭据、IP变更逐步排查处置。"
meta_source: "llm"
relations:
- target: "ITKB-VPN-001"
  type: "related"
  note: "VPN拨号/认证失败导致VPN未连接，是本卡RDP连接失败的根因之一"
  evidence: "网络层面：VPN未连接或未授权访问3389端口"
- target: "ITKB-VPN-002"
  type: "related"
  note: "VPN已连接但无法访问内网资源时同样表现为ping不通目标电脑，与本卡场景衔接"
  evidence: "步骤3：确认VPN已连接并能ping通目标电脑IP。"
- target: "ITKB-APPENDIX-1"
  type: "process_applies"
  note: "本卡包含员工自助排查六个步骤，适用员工IT故障自助排查流程"
  evidence: "员工自助排查"
- target: "ITKB-APPENDIX-2"
  type: "process_applies"
  note: "本卡按分层逐步排查并设IT工程师进阶处理，遵循IT故障排查通用流程"
  evidence: "按开机状态、远程桌面开关、VPN与防火墙、NLA凭据、IP变更逐步排查处置"
- target: "ITKB-HW-001"
  type: "related"
  note: "目标电脑未开机是RDP失败的首要根因，与无法开机/黑屏故障卡相关"
  evidence: "① 目标电脑未开机或处于休眠/睡眠状态"
- target: "ITKB-ACC-002"
  type: "related"
  note: "密码过期或输错会表现为RDP登录提示凭据无效"
  evidence: "「凭据无效」"
- target: "ITKB-ACC-001"
  type: "related"
  note: "域账号锁定同样会导致RDP凭据验证失败"
  evidence: "「凭据无效」"
- target: "ITKB-NET-005"
  type: "related"
  note: "DHCP分配变化/异常导致目标电脑IP变更，与IP地址冲突及DHCP异常处置相关"
  evidence: "⑥ 目标电脑IP地址变更（DHCP分配变化）"
graph_nodes:
- kind: "symptom"
  name: "远程桌面无法连接到远程计算机"
- kind: "symptom"
  name: "凭据无效"
- kind: "root_cause"
  name: "目标电脑未开机或处于休眠/睡眠状态"
- kind: "root_cause"
  name: "目标电脑远程桌面功能未开启"
- kind: "root_cause"
  name: "VPN未连接或未授权访问3389端口"
- kind: "root_cause"
  name: "防火墙（Windows防火墙/公司防火墙）拦截"
- kind: "root_cause"
  name: "NLA（网络级身份验证）导致凭据传递失败"
- kind: "root_cause"
  name: "目标电脑IP地址变更（DHCP分配变化）"
- kind: "tool"
  name: "mstsc"
- kind: "tool"
  name: "ipconfig"
graph_meta_source: "llm"
---

# 【VPN-003】远程桌面(RDP)连接失败排查

## 现象描述

- 使用远程桌面（mstsc）连接公司内网电脑时，提示「远程桌面无法连接到远程计算机」「凭据无效」「内部错误」等。常见于：在家访问工位电脑、IT远程协助用户。

## 常见根因

- ① 目标电脑未开机或处于休眠/睡眠状态
- ② 目标电脑远程桌面功能未开启
- ③ 网络层面：VPN未连接或未授权访问3389端口
- ④ 防火墙（Windows防火墙/公司防火墙）拦截
- ⑤ NLA（网络级身份验证）导致凭据传递失败
- ⑥ 目标电脑IP地址变更（DHCP分配变化）

## 员工自助排查

- 步骤1：确认目标电脑已开机且未休眠（可请同事帮忙查看）。
- 步骤2：Win+I → 系统 → 远程桌面 → 确保远程桌面开关为「开」。
- 步骤3：确认VPN已连接并能ping通目标电脑IP。
- 步骤4：检查Windows防火墙：允许应用通过防火墙 → 确保「远程桌面」已勾选。
- 步骤5：连接时输入完整凭据：域名\用户名 格式。
- 步骤6：如果使用IP连接，确认IP地址没有变化（目标电脑 ipconfig 查看）。

## IT工程师进阶处理

- 1. 检查目标电脑电源管理设置：关闭睡眠和休眠，关闭网卡节能模式。
- 2. 组策略：计算机配置 → 管理模板 → Windows组件 → 远程桌面服务 → 启用远程桌面。
- 3. 防火墙规则：开放TCP 3389，如改端口则需要查当前端口。
- 4. 检查NLA设置：系统属性 → 远程 → 取消勾选「仅允许运行使用网络级别身份验证…」。
- 5. 使用 Remote Desktop Connection Manager 或远程协助工具（如ToDesk/TeamViewer）作为备选。
- 6. 检查AD账号是否在目标电脑的 Remote Desktop Users 组中。

---
> 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 条目 VPN-003 · 分类「VPN与远程办公」· 由清洗流水线自动生成
