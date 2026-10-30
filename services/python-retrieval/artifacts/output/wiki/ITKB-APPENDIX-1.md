---
id: "ITKB-APPENDIX-1"
title: "员工IT故障自助排查流程"
category: "附录：IT故障排查通用流程"
department: "IT 部"
version: "v1.0"
replaces: []
entities:
- name: "重启"
  type: "命令工具"
- name: "设备"
  type: "设备"
- name: "软件"
  type: "软件"
- name: "服务端"
  type: "系统"
- name: "网络故障"
  type: "故障现象"
- name: "错误提示"
  type: "故障现象"
- name: "截图"
  type: "概念"
- name: "错误关键词"
  type: "概念"
- name: "内部知识库"
  type: "系统"
- name: "公司Wiki"
  type: "系统"
- name: "IT工单"
  type: "概念"
keywords: []
summary: "提供员工IT故障自助排查五步法：重启、确认影响范围、收集错误信息、搜索知识库、提交IT工单。"
meta_source: "llm"
relations:
- target: "ITKB-APPENDIX-2"
  type: "related"
  note: "本卡为员工侧自助排查流程，自助无效后提交工单，转入IT侧通用排查流程（APPENDIX-2）"
  evidence: "如果以上步骤无法解决，提交工单并附上截图和操作描述。"
- target: "ITKB-APPENDIX-3"
  type: "related"
  note: "同属附录「IT故障排查通用流程」体系，命令速查表支撑按流程快速定位处置"
  evidence: "分类「附录：IT故障排查通用流程」"
- target: "ITKB-NET-001"
  type: "process_applies"
  note: "WiFi连接故障卡含员工自助排查步骤，本卡自助五步法适用于该卡先行自查"
  evidence: "如果大家都有，可能是服务端/网络故障。"
- target: "ITKB-ACC-001"
  type: "process_applies"
  note: "域账号锁定先由员工自助排查，无法解决再提工单由IT侧解锁，与本卡流程衔接"
  evidence: "如果以上步骤无法解决，提交工单并附上截图和操作描述。"
- target: "ITKB-ACC-004"
  type: "process_applies"
  note: "MFA验证失败先由员工自助处理（校正时间、查信号），对应本卡自助排查先行原则"
  evidence: "重启出问题的设备和软件。很多偶发性问题重启即解决。"
- target: "ITKB-STO-003"
  type: "process_applies"
  note: "云盘同步异常卡提供员工自助排查手段，本卡五步自助流程适用"
  evidence: "在本文档或公司Wiki中搜索错误关键词。"
graph_nodes:
- kind: "symptom"
  name: "错误提示"
- kind: "root_cause"
  name: "服务端/网络故障"
- kind: "tool"
  name: "公司Wiki"
- kind: "tool"
  name: "IT工单"
graph_meta_source: "llm"
---

# 员工IT故障自助排查流程

第1步【重启大法】：重启出问题的设备和软件。很多偶发性问题重启即解决。

第2步【确认范围】：是只有自己有问题，还是同事也有？如果大家都有，可能是服务端/网络故障。

第3步【收集信息】：记录错误提示的完整文字（截图）、发生时间、做了什么操作后出现的。

第4步【搜索内部知识库】：在本文档或公司Wiki中搜索错误关键词。

第5步【提交IT工单】：如果以上步骤无法解决，提交工单并附上截图和操作描述。

---
> 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 条目 APPENDIX-1 · 分类「附录：IT故障排查通用流程」· 由清洗流水线自动生成
