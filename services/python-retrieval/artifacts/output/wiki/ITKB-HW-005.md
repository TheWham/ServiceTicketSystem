---
id: "ITKB-HW-005"
title: "键盘鼠标失灵及反应异常处理"
category: "硬件与外设故障"
department: "IT 部"
version: "v1.0"
replaces: []
entities:
- name: "键盘"
  type: "设备"
- name: "鼠标"
  type: "设备"
- name: "USB接收器"
  type: "设备"
- name: "蓝牙"
  type: "协议"
- name: "触摸板"
  type: "设备"
- name: "电池"
  type: "设备"
- name: "驱动程序"
  type: "软件"
- name: "设备管理器"
  type: "软件"
- name: "Keyboard Test Utility"
  type: "软件"
- name: "BIOS"
  type: "系统"
- name: "USB Legacy Support"
  type: "配置项"
- name: "双击速度"
  type: "配置项"
keywords: ["键盘", "鼠标", "失灵", "按键没反应", "光标乱跳", "双击", "无线", "蓝牙", "驱动"]
summary: "解决键盘鼠标失灵、光标异常问题，通过换电池、重插接收器、重新配对及重装驱动分层排查处置。"
meta_source: "llm"
relations:
- target: "ITKB-APPENDIX-1"
  type: "process_applies"
  note: "本卡设有员工自助排查六个步骤，应用员工IT故障自助排查流程"
  evidence: "员工自助排查"
- target: "ITKB-APPENDIX-2"
  type: "process_applies"
  note: "本卡设有IT工程师进阶处理环节，遵循IT故障排查通用流程的分层处置规范"
  evidence: "IT工程师进阶处理"
- target: "ITKB-HW-004"
  type: "related"
  note: "均涉及USB设备连接异常排查，本卡USB接收器接触不良及换USB口测试与U盘/移动硬盘不识别处置相关"
  evidence: "USB接收器松动或接触不良"
- target: "ITKB-SYS-001"
  type: "related"
  note: "驱动程序异常为两卡共同排查方向，均通过设备管理器卸载重装驱动处置"
  evidence: "驱动程序异常"
graph_nodes:
- kind: "symptom"
  name: "键盘部分或全部按键无反应"
- kind: "symptom"
  name: "鼠标光标不动"
- kind: "root_cause"
  name: "无线键鼠电池耗尽"
- kind: "root_cause"
  name: "USB接收器松动或接触不良"
- kind: "root_cause"
  name: "蓝牙连接被干扰或距离过远"
- kind: "root_cause"
  name: "键盘进水/进异物导致按键短路"
- kind: "root_cause"
  name: "触摸板误触（笔记本）"
- kind: "root_cause"
  name: "驱动程序异常"
- kind: "tool"
  name: "设备管理器"
- kind: "tool"
  name: "Keyboard Test Utility"
graph_meta_source: "llm"
---

# 【HW-005】键盘鼠标失灵及反应异常处理

## 现象描述

- 键盘部分或全部按键无反应，鼠标光标不动、左键变右键、单击变双击、光标自己移动。无线键鼠突然断开连接或反应延迟明显。

## 常见根因

- ① 无线键鼠电池耗尽
- ② USB接收器松动或接触不良
- ③ 蓝牙连接被干扰或距离过远
- ④ 键盘进水/进异物导致按键短路
- ⑤ 触摸板误触（笔记本）
- ⑥ 驱动程序异常

## 员工自助排查

- 步骤1：无线键鼠：更换电池，重新插拔USB接收器。
- 步骤2：有线键鼠：换一个USB口测试。
- 步骤3：蓝牙键鼠：Win+I → 蓝牙和其他设备 → 删除设备后重新配对。
- 步骤4：笔记本：检查触摸板是否误触（Fn+触摸板禁用快捷键）。
- 步骤5：用另一台电脑测试键鼠是否正常（区分设备问题还是电脑问题）。
- 步骤6：重启电脑。

## IT工程师进阶处理

- 1. 设备管理器 → 键盘/鼠标 → 卸载设备 → 扫描检测硬件改动。
- 2. 检查BIOS中USB Legacy Support是否开启（影响BIOS阶段键鼠可用性）。
- 3. 键盘：用 Keyboard Test Utility 检测所有按键响应。
- 4. 鼠标双击问题：调整双击速度（控制面板 → 鼠标 → 双击速度滑块）。
- 5. 检查是否有键鼠管理软件冲突（如罗技Options/G HUB、雷云等）。
- 6. 如为硬件故障，直接更换（键盘鼠标属低值易耗品）。

---
> 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 条目 HW-005 · 分类「硬件与外设故障」· 由清洗流水线自动生成
