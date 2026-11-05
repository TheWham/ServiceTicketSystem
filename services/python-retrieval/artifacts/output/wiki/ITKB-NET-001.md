---
id: "ITKB-NET-001"
title: "公司WiFi连接故障排查"
category: "网络连接问题"
department: "IT 部"
version: "v1.0"
replaces: []
entities:
- name: "WiFi"
  type: "概念"
- name: "无线网卡驱动"
  type: "软件"
- name: "DHCP"
  type: "协议"
- name: "MAC地址"
  type: "概念"
- name: "AP"
  type: "设备"
- name: "ipconfig"
  type: "命令工具"
- name: "802.1X认证"
  type: "协议"
- name: "NPS服务器"
  type: "系统"
- name: "RADIUS"
  type: "协议"
- name: "AC控制器"
  type: "设备"
- name: "路由器"
  type: "设备"
- name: "设备管理器"
  type: "软件"
- name: "PoE供电"
  type: "概念"
- name: "MAC地址过滤"
  type: "配置项"
- name: "DHCP地址池"
  type: "配置项"
keywords: ["WiFi", "无线网络", "无法连接", "网络断开", "WLAN", "信号弱"]
summary: "解决电脑无法连接公司WiFi问题，提供员工自助排查步骤与IT工程师进阶处理方法。"
meta_source: "llm"
relations:
- target: "ITKB-NET-002"
  type: "related"
  note: "有线与无线接入故障排查手段相通，均涉及物理链路与DHCP排查"
  evidence: "IP地址分配冲突或DHCP租约过期"
- target: "ITKB-NET-003"
  type: "related"
  note: "本卡的AP故障/信道拥堵根因与网速慢卡的无线干扰、信道问题相互关联"
  evidence: "公司AP设备故障或信道拥堵"
- target: "ITKB-NET-004"
  type: "related"
  note: "本卡进阶处理含DNS缓存清理，WiFi连上后若DNS异常需参考DNS解析卡"
  evidence: "ipconfig /release → ipconfig /renew → ipconfig /flushdns"
- target: "ITKB-NET-005"
  type: "same_root_cause"
  note: "两卡共同涉及IP地址冲突这一根因导致的断网/无法连接"
  evidence: "IP地址分配冲突或DHCP租约过期"
- target: "ITKB-APPENDIX-1"
  type: "process_applies"
  note: "本卡设有员工自助排查步骤，遵循员工自助排查流程（重启、验证影响范围、报IT）"
  evidence: "员工自助排查"
- target: "ITKB-APPENDIX-2"
  type: "process_applies"
  note: "本卡IT工程师进阶处理按驱动、命令行、认证到物理层分层排查，符合通用排查流程"
  evidence: "物理层排查：检查AP网线、PoE供电是否正常"
- target: "ITKB-APPENDIX-3"
  type: "related"
  note: "本卡使用的ipconfig系列命令收录于常用排查命令速查表"
  evidence: "ipconfig /release → ipconfig /renew → ipconfig /flushdns"
graph_nodes:
- kind: "symptom"
  name: "无法搜索到公司WiFi信号"
- kind: "symptom"
  name: "无法连接到此网络"
- kind: "symptom"
  name: "密码错误"
- kind: "root_cause"
  name: "无线网卡驱动异常或被禁用"
- kind: "root_cause"
  name: "WiFi开关（物理开关/Fn快捷键）处于关闭状态"
- kind: "root_cause"
  name: "IP地址分配冲突或DHCP租约过期"
- kind: "root_cause"
  name: "公司AP设备故障或信道拥堵"
- kind: "root_cause"
  name: "MAC地址绑定了旧设备，新设备未注册"
- kind: "tool"
  name: "设备管理器"
- kind: "tool"
  name: "ipconfig"
graph_meta_source: "llm"
---

# 【NET-001】公司WiFi连接故障排查

## 现象描述

- 员工电脑（Windows/macOS）无法搜索到公司WiFi信号，或能搜索到但点击连接后提示「无法连接到此网络」「连接超时」「密码错误」。常见于：换新电脑后、系统更新后、长假后返岗。

## 常见根因

- ① 无线网卡驱动异常或被禁用
- ② WiFi开关（物理开关/Fn快捷键）处于关闭状态
- ③ 输入的WiFi密码有误（区分大小写）
- ④ IP地址分配冲突或DHCP租约过期
- ⑤ 公司AP设备故障或信道拥堵
- ⑥ MAC地址绑定了旧设备，新设备未注册

## 员工自助排查

- 步骤1：检查电脑侧面/键盘F区的WiFi物理开关是否打开（指示灯应为亮起状态）。
- 步骤2：按 Win+I → 网络和Internet → WLAN → 确保WLAN开关为「开」。
- 步骤3：点击系统托盘网络图标，选择公司WiFi，点击「忘记此网络」→ 重新搜索并输入密码连接。
- 步骤4：重启电脑和公司AP（如有权限），等待2分钟后重试。
- 步骤5：用手机连接同一WiFi验证是否路由器问题——如果手机也无法连接，说明是网络设备故障，需报IT。

## IT工程师进阶处理

- 1. 检查无线网卡驱动：设备管理器 → 网络适配器 → 右键更新驱动。
- 2. 命令行排查：ipconfig /release → ipconfig /renew → ipconfig /flushdns。
- 3. 登录路由器/AC控制器检查AP状态、信道利用率、DHCP地址池是否耗尽。
- 4. 查看MAC地址过滤列表，确认该设备MAC是否在白名单中。
- 5. 如为RADIUS/802.1X认证，检查NPS服务器日志。
- 6. 物理层排查：检查AP网线、PoE供电是否正常。

> 📝 备注：新员工入职时应提前登记设备MAC地址，避免入职当天无法上网。

---
> 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 条目 NET-001 · 分类「网络连接问题」· 由清洗流水线自动生成
