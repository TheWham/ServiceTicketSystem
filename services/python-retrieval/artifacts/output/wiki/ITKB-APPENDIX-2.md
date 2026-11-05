---
id: "ITKB-APPENDIX-2"
title: "IT故障排查通用流程"
category: "附录：IT故障排查通用流程"
department: "IT 部"
version: "v1.0"
replaces: []
entities:
- name: "OSI模型"
  type: "概念"
- name: "分层排查"
  type: "概念"
- name: "事件查看器"
  type: "软件"
- name: "应用日志"
  type: "概念"
- name: "服务器日志"
  type: "概念"
- name: "排除法"
  type: "概念"
- name: "回归测试"
  type: "概念"
- name: "知识库"
  type: "系统"
keywords: []
summary: "规范IT故障排查七步流程：信息收集、复现测试、按OSI模型分层排查、日志分析、交叉验证、修复回归与知识沉淀。"
meta_source: "llm"
relations:
- target: "ITKB-APPENDIX-1"
  type: "related"
  note: "同属故障排查流程，前者面向员工自助，本卡面向IT工程师通用处置。"
  evidence: "员工IT故障自助排查五步法"
- target: "ITKB-APPENDIX-3"
  type: "related"
  note: "命令速查表用于支撑本通用流程中的快速定位与处置。"
  evidence: "支撑按通用流程快速定位与处置"
- target: "ITKB-NET-003"
  type: "process_applies"
  note: "本卡分层排查与交叉验证流程适用于网络断连与网速慢的分层处置。"
  evidence: "按带宽占用、ARP攻击、线路质量、DNS、端口协商、无线干扰分层排查处置"
- target: "ITKB-MAIL-003"
  type: "process_applies"
  note: "本卡按层定位与日志分析流程适用于IM登录及消息同步故障。"
  evidence: "按网络、代理、防火墙、账号状态分层排查处置"
- target: "ITKB-VPN-001"
  type: "process_applies"
  note: "本卡七步流程适用于VPN拨号或认证失败的分层排查。"
  evidence: "从本地网络、客户端配置到服务器与账号状态的分层排查处置方法"
- target: "ITKB-SYS-002"
  type: "process_applies"
  note: "本卡日志分析步骤适用于软件闪退与无响应故障的事件日志定位。"
  evidence: "事件日志分析分级处置"
- target: "ITKB-SYS-004"
  type: "process_applies"
  note: "本卡分层排查流程适用于电脑运行缓慢或开机极慢的分层处置。"
  evidence: "通过禁用自启程序、清理磁盘、查杀病毒及升级内存/SSD进行分层排查处置"
graph_nodes:
- kind: "tool"
  name: "OSI模型"
- kind: "tool"
  name: "事件查看器"
- kind: "tool"
  name: "应用日志"
- kind: "tool"
  name: "服务器日志"
- kind: "tool"
  name: "知识库"
graph_meta_source: "llm"
---

# IT故障排查通用流程

第1步【信息收集】：确认问题现象、发生时间、影响范围（单用户/部门/全员）、用户操作步骤。

第2步【复现测试】：在安全环境下尝试复现问题。判断是偶发性还是可稳定复现。

第3步【分层排查】：按OSI模型由下而上排查——物理层（线缆/电源）→ 网络层（IP/路由）→ 传输层（端口/防火墙）→ 应用层（软件/配置）。

第4步【日志分析】：查看系统事件查看器、应用日志、服务器日志，定位异常事件。

第5步【交叉验证】：排除法——更换设备/线缆/账号/网络环境，逐一排除变量。

第6步【修复实施】：根据定位的根因执行修复方案，修复后进行回归测试。

第7步【知识沉淀】：将问题和解决方案更新到本知识库，供后续检索使用。

---
> 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 条目 APPENDIX-2 · 分类「附录：IT故障排查通用流程」· 由清洗流水线自动生成
