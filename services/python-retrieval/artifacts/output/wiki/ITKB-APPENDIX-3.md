---
id: "ITKB-APPENDIX-3"
title: "常用排查命令速查表"
category: "附录：IT故障排查通用流程"
department: "IT 部"
version: "v1.0"
replaces: []
entities:
- name: "ipconfig"
  type: "命令工具"
- name: "ping"
  type: "命令工具"
- name: "tracert"
  type: "命令工具"
- name: "nslookup"
  type: "命令工具"
- name: "netstat"
  type: "命令工具"
- name: "sfc"
  type: "命令工具"
- name: "DISM"
  type: "命令工具"
- name: "chkdsk"
  type: "命令工具"
- name: "mdsched.exe"
  type: "命令工具"
- name: "msinfo32"
  type: "命令工具"
- name: "eventvwr.msc"
  type: "命令工具"
- name: "taskmgr"
  type: "命令工具"
- name: "DNS"
  type: "协议"
- name: "DHCP"
  type: "协议"
- name: "工单系统"
  type: "系统"
keywords: []
summary: "为IT故障排查提供常用命令速查，支撑按通用流程快速定位与处置。"
meta_source: "llm"
relations:
- target: "ITKB-APPENDIX-2"
  type: "process_applies"
  note: "本命令速查表归属并支撑IT故障排查通用流程，供按流程排查时快速调用命令"
  evidence: "分类「附录：IT故障排查通用流程」"
- target: "ITKB-NET-003"
  type: "related"
  note: "ping与tracert命令可用于网络断连与网速慢故障的连通性与链路排查"
  evidence: "ping 目标IP -t | 测试到目标的连通性和延迟；tracert 目标IP | 查看数据包经过的每一跳路由"
- target: "ITKB-NET-004"
  type: "related"
  note: "刷新DNS缓存与nslookup命令直接支撑DNS解析失败故障的清缓存与解析测试"
  evidence: "ipconfig /flushdns | 清除DNS解析缓存；nslookup 域名 | 测试DNS解析是否正常"
- target: "ITKB-NET-005"
  type: "related"
  note: "释放/续租IP命令对应IP地址冲突处置中的重新获取IP操作"
  evidence: "ipconfig /release && ipconfig /renew | DHCP重新获取IP"
- target: "ITKB-SYS-001"
  type: "related"
  note: "内存诊断、磁盘检查与系统文件修复命令支撑蓝屏死机故障的内存/硬盘/系统文件排查"
  evidence: "mdsched.exe | 重启后进行内存诊断；chkdsk C: /f | 检查并修复C盘文件系统错误；sfc /scannow | 扫描并修复系统文件"
- target: "ITKB-SYS-002"
  type: "related"
  note: "事件查看器命令支撑软件闪退故障的事件日志分析"
  evidence: "eventvwr.msc | 打开事件查看器"
- target: "ITKB-SYS-003"
  type: "related"
  note: "DISM与sfc命令对应Windows更新失败处理中的修复组件环节"
  evidence: "DISM /Online /Cleanup-Image /RestoreHealth | 修复系统映像组件"
- target: "ITKB-SYS-004"
  type: "related"
  note: "启动项管理命令支撑电脑开机慢故障的禁用自启程序排查"
  evidence: "taskmgr → 启动 | 管理开机自启动程序"
graph_nodes:
- kind: "tool"
  name: "ipconfig /all"
- kind: "tool"
  name: "ipconfig /release && ipconfig /renew"
- kind: "tool"
  name: "ipconfig /flushdns"
- kind: "tool"
  name: "ping 目标IP -t"
- kind: "tool"
  name: "tracert 目标IP"
- kind: "tool"
  name: "nslookup 域名"
- kind: "tool"
  name: "netstat -ano"
- kind: "tool"
  name: "sfc /scannow"
- kind: "tool"
  name: "DISM /Online /Cleanup-Image /RestoreHealth"
- kind: "tool"
  name: "chkdsk C: /f"
graph_meta_source: "llm"
---

# 常用排查命令速查表

— 文档结束 —

维护说明：本知识库由IT部门定期更新维护。
新增或修正条目请联系IT支持团队，将问题和解决方案提交至工单系统 → 知识库更新。

| 场景 | 命令 | 说明 |
| --- | --- | --- |
| 查看IP配置 | ipconfig /all | 查看所有网卡的IP、网关、DNS |
| 释放/续租IP | ipconfig /release && ipconfig /renew | DHCP重新获取IP |
| 刷新DNS缓存 | ipconfig /flushdns | 清除DNS解析缓存 |
| 网络连通测试 | ping 目标IP -t | 测试到目标的连通性和延迟 |
| 路由跟踪 | tracert 目标IP | 查看数据包经过的每一跳路由 |
| DNS查询 | nslookup 域名 | 测试DNS解析是否正常 |
| 查看网络连接 | netstat -ano | 查看所有活动的网络连接及对应PID |
| 系统文件修复 | sfc /scannow | 扫描并修复系统文件 |
| 系统映像修复 | DISM /Online /Cleanup-Image /RestoreHealth | 修复系统映像组件 |
| 磁盘检查 | chkdsk C: /f | 检查并修复C盘文件系统错误 |
| 内存诊断 | mdsched.exe | 重启后进行内存诊断 |
| 查看系统信息 | msinfo32 | 查看系统硬件和软件详细信息 |
| 查看事件日志 | eventvwr.msc | 打开事件查看器 |
| 查看启动项 | taskmgr → 启动 | 管理开机自启动程序 |

---
> 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 条目 APPENDIX-3 · 分类「附录：IT故障排查通用流程」· 由清洗流水线自动生成
