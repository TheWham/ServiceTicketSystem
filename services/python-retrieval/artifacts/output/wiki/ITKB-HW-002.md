---
id: "ITKB-HW-002"
title: "打印机无法打印故障处置"
category: "硬件与外设故障"
department: "IT 部"
version: "v1.0"
replaces: []
entities:
- name: "打印机"
  type: "设备"
- name: "网络打印机"
  type: "设备"
- name: "共享打印机"
  type: "设备"
- name: "打印服务器"
  type: "系统"
- name: "打印机驱动"
  type: "软件"
- name: "打印服务（Print Spooler）"
  type: "软件"
- name: "打印队列"
  type: "概念"
- name: "脱机使用打印机"
  type: "配置项"
- name: "卡纸"
  type: "故障现象"
- name: "缺墨"
  type: "故障现象"
- name: "services.msc"
  type: "命令工具"
- name: "control printers"
  type: "命令工具"
- name: "USB"
  type: "协议"
- name: "C:\\Windows\\System32\\spool\\PRINTERS"
  type: "配置项"
- name: "NVRAM"
  type: "配置项"
keywords: ["打印机", "无法打印", "打印队列", "脱机", "卡纸", "缺墨", "驱动", "打印服务"]
summary: "用于打印机无响应或任务卡住，按电源连接、队列、脱机、服务、驱动及耗材卡纸排查恢复。"
meta_source: "llm"
relations:
- target: "ITKB-APPENDIX-1"
  type: "process_applies"
  note: "本卡的员工侧处置按自助排查步骤展开，适用于员工IT故障自助排查流程。"
  evidence: "员工自助排查"
- target: "ITKB-APPENDIX-2"
  type: "process_applies"
  note: "本卡的IT侧进阶处置符合通用故障排查与修复沉淀流程。"
  evidence: "IT工程师进阶处理"
- target: "ITKB-APPENDIX-3"
  type: "related"
  note: "本卡使用打印机管理与服务等常用命令入口，可由命令速查表支撑。"
  evidence: "Win+R → services.msc → 找到 Print Spooler → 右键重启。"
- target: "ITKB-NET-002"
  type: "related"
  note: "网络打印机需确认IP与在线状态，有线链路异常可能导致打印故障表象。"
  evidence: "网络打印机：打印配置页检查IP地址是否正确，确认打印机在线。"
graph_nodes:
- kind: "symptom"
  name: "发送打印任务后打印机无反应"
- kind: "symptom"
  name: "打印机报红灯、面板显示错误代码"
- kind: "root_cause"
  name: "打印机未开机或USB/网线松动"
- kind: "root_cause"
  name: "打印机设置为「脱机使用打印机」"
- kind: "root_cause"
  name: "打印队列中有卡住的任务阻塞后续任务"
- kind: "root_cause"
  name: "驱动程序损坏或版本不匹配"
- kind: "root_cause"
  name: "打印服务（Print Spooler）停止"
- kind: "root_cause"
  name: "纸张耗尽 / 墨粉耗尽 / 卡纸 / 废粉盒满"
- kind: "tool"
  name: "control printers"
- kind: "tool"
  name: "services.msc"
graph_meta_source: "llm"
---

# 【HW-002】打印机无法打印故障处置

## 现象描述

- 发送打印任务后打印机无反应，打印队列中任务状态显示「错误」「已暂停」「脱机」。或打印机报红灯、面板显示错误代码（如卡纸、缺墨、废粉盒满）。

## 常见根因

- ① 打印机未开机或USB/网线松动
- ② 打印机设置为「脱机使用打印机」
- ③ 打印队列中有卡住的任务阻塞后续任务
- ④ 驱动程序损坏或版本不匹配
- ⑤ 打印服务（Print Spooler）停止
- ⑥ 纸张耗尽 / 墨粉耗尽 / 卡纸 / 废粉盒满

## 员工自助排查

- 步骤1：检查打印机是否开机、是否连接到电脑（USB）或网络（网络打印）。
- 步骤2：Win+R → control printers → 右键打印机 → 查看正在打印 → 取消所有文档。
- 步骤3：确认打印机没有设为「脱机使用打印机」——右键打印机，取消勾选。
- 步骤4：Win+R → services.msc → 找到 Print Spooler → 右键重启。
- 步骤5：检查打印机面板是否有错误提示（缺纸、卡纸、缺墨粉）→ 添加纸张/更换墨粉。
- 步骤6：重启打印机和电脑。

## IT工程师进阶处理

- 1. 停止 Print Spooler → 清空 C:\Windows\System32\spool\PRINTERS → 重启服务。
- 2. 卸载打印机驱动 → 从官网下载最新驱动重新安装。
- 3. 网络打印机：打印配置页检查IP地址是否正确，确认打印机在线。
- 4. 卡纸处理：按打印机手册指示取出卡纸（注意方向，避免碎片残留）。
- 5. 重置打印机NVRAM（恢复出厂设置），重新配置网络。
- 6. 如为共享打印机故障，重建打印服务器上的打印机共享。

---
> 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 条目 HW-002 · 分类「硬件与外设故障」· 由清洗流水线自动生成
