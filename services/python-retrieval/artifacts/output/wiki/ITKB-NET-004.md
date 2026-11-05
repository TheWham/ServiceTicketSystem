---
id: "ITKB-NET-004"
title: "DNS解析失败故障排查与处置"
category: "网络连接问题"
department: "IT 部"
effective_date: "2024-03-01"
effective_date_source: "demo-constructed"
version: "v1.0"
replaces: ["ITKB-LEG-NET-004"]
entities:
- name: "DNS"
  type: "协议"
- name: "DHCP"
  type: "协议"
- name: "UDP 53端口"
  type: "概念"
- name: "阿里DNS"
  type: "系统"
- name: "DNS服务器"
  type: "系统"
- name: "防火墙"
  type: "系统"
- name: "VPN/代理软件"
  type: "软件"
- name: "nslookup"
  type: "命令工具"
- name: "ipconfig /flushdns"
  type: "命令工具"
- name: "ping"
  type: "命令工具"
- name: "ncpa.cpl"
  type: "命令工具"
- name: "hosts文件"
  type: "配置项"
- name: "Internet协议版本4"
  type: "配置项"
- name: "DNS_PROBE_FINISHED_NXDOMAIN"
  type: "故障现象"
- name: "ERR_NAME_NOT_RESOLVED"
  type: "故障现象"
keywords: ["DNS", "打不开网页", "QQ能上", "域名解析", "nslookup", "DNS_PROBE_FINISHED"]
summary: "解决DNS解析失败致网页无法打开（QQ等正常）的问题：清缓存、改DNS、查hosts与代理，并排查公司DNS/DHCP/防火墙。"
meta_source: "llm"
relations:
- target: "ITKB-LEG-NET-004"
  type: "replaces"
  note: "本卡为现行版DNS解析故障处置规范，替代已废止的旧版强制内网DNS方案"
  evidence: "（已废止，v1.0 版 ITKB-NET-004 为准）旧版强制统一使用内网 10.0.0.1 并禁用公共 DNS 的处置方法。"
- target: "ITKB-APPENDIX-1"
  type: "process_applies"
  note: "员工IT故障自助排查五步法适用于本卡的员工自助排查环节"
  evidence: "提供员工IT故障自助排查五步法：重启、确认影响范围、收集错误信息、搜索知识库、提交IT工单。"
- target: "ITKB-APPENDIX-2"
  type: "process_applies"
  note: "IT故障排查七步通用流程（含OSI分层排查）适用于本卡DNS故障的分层排查处置"
  evidence: "规范IT故障排查七步流程：信息收集、复现测试、按OSI模型分层排查、日志分析、交叉验证、修复回归与知识沉淀。"
- target: "ITKB-APPENDIX-3"
  type: "related"
  note: "本卡使用的nslookup、ipconfig /flushdns等排查命令可由常用命令速查表支撑"
  evidence: "为IT故障排查提供常用命令速查，支撑按通用流程快速定位与处置。"
- target: "ITKB-NET-003"
  type: "related"
  note: "DNS异常也是网络断连与网速慢故障的分层排查因素之一，两卡排查面存在交叉"
  evidence: "按带宽占用、ARP攻击、线路质量、DNS、端口协商、无线干扰分层排查处置"
- target: "ITKB-VPN-002"
  type: "related"
  note: "VPN/代理软件残留的DNS配置可致解析失败，VPN后无法访问内网资源的排查同样涉及DNS环节"
  evidence: "⑤ 代理/VPN软件残留的DNS配置"
- target: "ITKB-STO-002"
  type: "related"
  note: "共享盘无法访问的排查链路中包含DNS环节，与本卡根因存在交叉"
  evidence: "按网络、凭据、DNS、SMB和服务器状态排查并重映射"
- target: "ITKB-SYS-005"
  type: "related"
  note: "浏览器页面加载失败与本卡网页打不开现象相似，且两卡均涉及代理因素，需相互鉴别"
  evidence: "解决浏览器白屏、错乱或加载失败，按缓存、扩展、时间、代理与杀毒扫描排查"
- target: "ITKB-LEG-NET-004"
  type: "replaces"
  note: "frontmatter replaces 规则迁移"
  evidence: "frontmatter:replaces"
graph_nodes:
- kind: "symptom"
  name: "无法访问此网站"
- kind: "symptom"
  name: "DNS_PROBE_FINISHED_NXDOMAIN"
- kind: "symptom"
  name: "ping IP地址通，ping域名不通"
- kind: "root_cause"
  name: "DNS服务器地址配置错误或被篡改"
- kind: "root_cause"
  name: "公司DNS服务器故障或过载"
- kind: "root_cause"
  name: "DNS缓存污染"
- kind: "root_cause"
  name: "hosts文件被恶意修改"
- kind: "root_cause"
  name: "代理/VPN软件残留的DNS配置"
- kind: "tool"
  name: "nslookup www.baidu.com"
- kind: "tool"
  name: "ipconfig /flushdns"
graph_meta_source: "llm"
---

# 【NET-004】DNS解析失败故障排查与处置

## 现象描述

- 浏览器访问任何网页均提示「无法访问此网站」「DNS_PROBE_FINISHED_NXDOMAIN」或「ERR_NAME_NOT_RESOLVED」。但企业微信/QQ等即时通讯软件可以正常收发消息。ping IP地址通，ping域名不通。

## 常见根因

- ① DNS服务器地址配置错误或被篡改
- ② 公司DNS服务器故障或过载
- ③ DNS缓存污染
- ④ hosts文件被恶意修改
- ⑤ 代理/VPN软件残留的DNS配置

## 员工自助排查

- 步骤1：Win+R → cmd → 输入 nslookup www.baidu.com，观察能否返回IP地址。
- 步骤2：ipconfig /flushdns 清除DNS缓存。
- 步骤3：Win+R → ncpa.cpl → 右键网卡 → 属性 → Internet协议版本4 → DNS改为223.5.5.5（阿里DNS）或公司内部DNS。
- 步骤4：检查 C:\Windows\System32\drivers\etc\hosts 文件，删除可疑条目。
- 步骤5：关闭VPN/代理软件后重试。
- 步骤6：重启电脑。

## IT工程师进阶处理

- 1. 检查公司DNS服务器是否正常运行（nslookup 使用公司 DNS 测试）。
- 2. 检查DHCP下发的DNS地址是否正确。
- 3. 查防火墙是否拦截了DNS（UDP 53端口）。
- 4. 如近期做过DNS迁移，检查旧DNS是否已从所有DHCP作用域中移除。
- 5. 检查是否存在DNS劫持或中间人攻击。

---
> 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 条目 NET-004 · 分类「网络连接问题」· 由清洗流水线自动生成
