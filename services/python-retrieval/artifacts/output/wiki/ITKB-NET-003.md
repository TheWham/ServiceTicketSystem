---
id: "ITKB-NET-003"
title: "网络断连与网速慢故障排查"
category: "网络连接问题"
department: "IT 部"
version: "v1.0"
replaces: []
entities:
- name: "ping"
  type: "命令工具"
- name: "ARP攻击"
  type: "故障现象"
- name: "广播风暴"
  type: "故障现象"
- name: "DNS"
  type: "协议"
- name: "交换机端口协商"
  type: "配置项"
- name: "Wireshark"
  type: "软件"
- name: "WiFi Analyzer"
  type: "软件"
- name: "上网行为管理"
  type: "系统"
- name: "任务管理器"
  type: "软件"
- name: "cmd"
  type: "命令工具"
- name: "show interface"
  type: "命令工具"
- name: "交换机"
  type: "设备"
- name: "防火墙"
  type: "设备"
- name: "AP"
  type: "设备"
- name: "限速策略"
  type: "配置项"
keywords: ["网速慢", "卡顿", "网络不稳定", "丢包", "延迟高", "ping不通", "断流"]
summary: "解决网络间歇断连、网速慢问题，按带宽占用、ARP攻击、线路质量、DNS、端口协商、无线干扰分层排查处置。"
meta_source: "llm"
relations:
- target: "ITKB-NET-004"
  type: "related"
  note: "本卡将DNS响应慢列为网速慢根因之一，改DNS处置与DNS解析失败卡相互衔接"
  evidence: "④ DNS服务器响应慢；更换DNS为内部DNS服务器或公共DNS（223.5.5.5 / 114.114.114.114）"
- target: "ITKB-NET-001"
  type: "related"
  note: "本卡无线信道干扰与切换5G频段的处置与WiFi连接故障卡相关"
  evidence: "⑥ 无线2.4G频段信道干扰严重；WiFi用户尝试切换到5G频段，或靠近AP"
- target: "ITKB-NET-002"
  type: "related"
  note: "本卡网线质量与端口协商异常的排查与有线网络物理链路排查相关"
  evidence: "③ 网线质量问题（五类线跑千兆、网线过长>100米）"
- target: "ITKB-NET-005"
  type: "related"
  note: "ARP攻击导致的断连需与IP地址冲突断网场景相互鉴别"
  evidence: "② ARP攻击或广播风暴导致局域网拥堵"
- target: "ITKB-SYS-004"
  type: "related"
  note: "网速慢、视频会议卡顿需与电脑本身运行缓慢导致的卡顿相鉴别"
  evidence: "网页加载极慢、视频会议卡顿、文件传输速度远低于正常水平"
- target: "ITKB-APPENDIX-1"
  type: "process_applies"
  note: "本卡员工自助排查五步骤遵循员工IT故障自助排查流程规范"
  evidence: "员工自助排查 步骤1：打开任务管理器 → 性能 → 查看网络占用"
- target: "ITKB-APPENDIX-2"
  type: "process_applies"
  note: "本卡按带宽、ARP、线路、DNS、端口、无线分层排查，符合IT故障排查通用流程"
  evidence: "按带宽占用、ARP攻击、线路质量、DNS、端口协商、无线干扰分层排查处置"
- target: "ITKB-APPENDIX-3"
  type: "related"
  note: "本卡使用ping等常用命令测延迟与丢包，与命令速查表互证"
  evidence: "ping 114.114.114.114 -t，观察是否稳定（正常应<50ms且不丢包）"
graph_nodes:
- kind: "symptom"
  name: "网络间歇性断开"
- kind: "symptom"
  name: "网页加载极慢、视频会议卡顿"
- kind: "root_cause"
  name: "带宽被占用"
- kind: "root_cause"
  name: "ARP攻击或广播风暴"
- kind: "root_cause"
  name: "网线质量问题"
- kind: "root_cause"
  name: "DNS服务器响应慢"
- kind: "root_cause"
  name: "交换机端口协商异常"
- kind: "root_cause"
  name: "无线2.4G频段信道干扰"
- kind: "tool"
  name: "Wireshark"
- kind: "tool"
  name: "WiFi Analyzer"
graph_meta_source: "llm"
---

# 【NET-003】网络断连与网速慢故障排查

## 现象描述

- 网络间歇性断开（几秒到几分钟后自动恢复），或网页加载极慢、视频会议卡顿、文件传输速度远低于正常水平。ping网关或外网出现大量超时或延迟波动（>100ms）。

## 常见根因

- ① 带宽被占用（大文件下载、视频流、Windows更新后台下载）
- ② ARP攻击或广播风暴导致局域网拥堵
- ③ 网线质量问题（五类线跑千兆、网线过长>100米）
- ④ DNS服务器响应慢
- ⑤ 交换机端口协商异常（半双工/10Mbps）
- ⑥ 无线2.4G频段信道干扰严重

## 员工自助排查

- 步骤1：打开任务管理器 → 性能 → 查看网络占用，关闭高带宽后台程序。
- 步骤2：打开浏览器访问公司内网页面，如果内网正常外网慢，可能是出口带宽或DNS问题。
- 步骤3：Win+R → cmd → ping 114.114.114.114 -t，观察是否稳定（正常应<50ms且不丢包）。
- 步骤4：重启路由器/交换机（如有权限），等待2分钟。
- 步骤5：WiFi用户尝试切换到5G频段，或靠近AP。

## IT工程师进阶处理

- 1. 流量分析：在核心交换机上查看各端口流量，定位带宽占用源头。
- 2. Wireshark抓包分析是否存在ARP攻击、环路或广播风暴。
- 3. 检查交换机端口协商速率与双工模式（show interface）。
- 4. 更换DNS为内部DNS服务器或公共DNS（223.5.5.5 / 114.114.114.114）。
- 5. 防火墙/上网行为管理检查：是否对该IP做了限速策略。
- 6. 无线环境：用WiFi Analyzer扫描信道占用，调整AP信道。

---
> 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 条目 NET-003 · 分类「网络连接问题」· 由清洗流水线自动生成
