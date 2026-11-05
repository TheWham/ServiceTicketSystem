---
id: "ITKB-STO-002"
title: "共享盘无法访问排查"
category: "数据存储与备份"
department: "IT 部"
version: "v1.0"
replaces: []
entities:
- name: "共享盘"
  type: "概念"
- name: "文件服务器"
  type: "设备"
- name: "网络驱动器"
  type: "概念"
- name: "SMB"
  type: "协议"
- name: "SMBv1"
  type: "协议"
- name: "DNS"
  type: "协议"
- name: "VPN"
  type: "概念"
- name: "找不到网络路径"
  type: "故障现象"
- name: "凭据管理器"
  type: "软件"
- name: "control keymgr.dll"
  type: "命令工具"
- name: "PowerShell"
  type: "命令工具"
- name: "Get-SmbConnection"
  type: "命令工具"
- name: "组策略"
  type: "软件"
- name: "共享权限"
  type: "账号权限"
- name: "NTFS权限"
  type: "账号权限"
keywords: ["共享盘", "文件服务器", "NAS", "盘符丢失", "网络驱动器", "无法连接", "SMB"]
summary: "处置共享盘无法访问，按网络、凭据、DNS、SMB和服务器状态排查并重映射。"
meta_source: "llm"
relations:
- target: "ITKB-NET-004"
  type: "same_root_cause"
  note: "DNS解析文件服务器主机名失败是共享盘无法访问的根因之一，与DNS解析失败故障同源"
  evidence: "DNS解析文件服务器主机名失败"
- target: "ITKB-ACC-002"
  type: "related"
  note: "用户改密后凭据管理器旧密码未更新会导致共享盘访问失败，与密码重置/过期处理相关联"
  evidence: "用户密码变更后凭据管理器中的旧密码未更新"
- target: "ITKB-ACC-003"
  type: "related"
  note: "共享盘提示「拒绝访问」时需核查共享权限与NTFS权限，与文件夹访问被拒绝处置相通"
  evidence: "检查文件服务器磁盘状态、共享权限、NTFS权限"
- target: "ITKB-VPN-002"
  type: "related"
  note: "VPN/网络未就绪时持久映射的共享盘会断开，与VPN已连接但无法访问内网资源场景相关"
  evidence: "网络驱动器映射使用持久连接但VPN/网络未就绪"
- target: "ITKB-APPENDIX-1"
  type: "process_applies"
  note: "本卡设有员工自助排查五个步骤，遵循员工IT故障自助排查流程"
  evidence: "员工自助排查"
- target: "ITKB-APPENDIX-2"
  type: "process_applies"
  note: "本卡IT工程师进阶处理按服务、协议、DNS、权限分层展开，遵循IT故障排查通用流程"
  evidence: "IT工程师进阶处理"
- target: "ITKB-APPENDIX-3"
  type: "related"
  note: "排查中使用ping、Get-SmbConnection等命令，可对照常用排查命令速查表"
  evidence: "PowerShell → Get-SmbConnection"
graph_nodes:
- kind: "symptom"
  name: "共享盘显示红叉（盘符断开）"
- kind: "symptom"
  name: "找不到网络路径"
- kind: "symptom"
  name: "拒绝访问"
- kind: "root_cause"
  name: "网络驱动器映射使用持久连接但VPN/网络未就绪"
- kind: "root_cause"
  name: "SMB协议版本不兼容"
- kind: "root_cause"
  name: "DNS解析文件服务器主机名失败"
- kind: "root_cause"
  name: "用户密码变更后凭据管理器中的旧密码未更新"
- kind: "root_cause"
  name: "文件服务器脱机或文件共享服务停止"
- kind: "tool"
  name: "Get-SmbConnection"
- kind: "tool"
  name: "control keymgr.dll"
graph_meta_source: "llm"
---

# 【STO-002】共享盘无法访问排查

## 现象描述

- 开机后共享盘显示红叉（盘符断开），双击提示「无法访问」「找不到网络路径」「拒绝访问」。或共享盘完全消失不见。常见于：周一早上开机、网络切换后。

## 常见根因

- ① 网络驱动器映射使用持久连接但VPN/网络未就绪
- ② SMB协议版本不兼容（如服务器SMBv1已禁用但客户端仅支持v1）
- ③ DNS解析文件服务器主机名失败
- ④ 用户密码变更后凭据管理器中的旧密码未更新
- ⑤ 文件服务器脱机或文件共享服务停止

## 员工自助排查

- 步骤1：Win+R → 输入 \\fileserver（替换为实际服务器名）→ 看能否打开共享列表。
- 步骤2：如果能打开但盘符断开 → 断开旧盘符（右键 → 断开）→ 重新映射。
- 步骤3：Win+R → control keymgr.dll → Windows凭据 → 删除文件服务器相关凭据 → 重新映射并输入密码。
- 步骤4：重启电脑。
- 步骤5：ping文件服务器IP和主机名，检查DNS解析是否正常。

## IT工程师进阶处理

- 1. 检查文件服务器状态：Server服务、Workstation服务是否运行。
- 2. 检查SMB协议版本：PowerShell → Get-SmbConnection，确保客户端和服务端版本兼容。
- 3. 在客户端启用不安全的访客登录（如因SMB签名策略导致）：组策略 → 计算机配置 → 管理模板 → 网络 → Lanman工作站。
- 4. 检查DNS记录，确认文件服务器主机名能被正确解析。
- 5. 检查文件服务器磁盘状态、共享权限、NTFS权限。

---
> 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 条目 STO-002 · 分类「数据存储与备份」· 由清洗流水线自动生成
