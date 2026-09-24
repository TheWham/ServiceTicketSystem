---
name: ai-agent-guard
description: AI Agent 参与环节（AI 客服对话、工单→FAQ 入库）的合规与质量检测 Skill。两大能力：①FAQ DRAFT 入库前检测——PII 脱敏（工号/手机号/邮箱/资产编号）、字段格式校验、与正式库相似度查重、提示注入特征检测；②AI 客服对话记录检测——拒答合规（知识库未命中必须拒答/转人工，禁止编造）、越界承诺、PII 泄露、敏感操作指引。适用于：FAQ DRAFT 主管审核辅助、AI 生成内容入库前质量门禁、AI 客服对话抽检、CI 集成。
---

# ai-agent-guard —— AI Agent 参与环节合规守卫

## 定位边界（重要）

本 Skill **只守卫 AI Agent 参与的环节**，与 Java 后端职责严格分工：

| 环节 | 负责方 | 本 Skill 是否覆盖 |
|---|---|---|
| 工单状态机流转/监测 | Java 后端 `TicketStateMachine` + `TicketServiceImpl.transit()` | ❌ 不覆盖，后端已收口 |
| 字段校验/幂等/乐观锁 | Java 后端 DTO 校验 + dedup_lock | ❌ 不覆盖 |
| **AI 客服对话（F-04）** | AI Agent（NLU + 检索式回答 + 强约束拒答） | ✅ `chat_reply_check.py` |
| **工单→FAQ 自动入库（F-03 入链）** | AI Agent 生成 DRAFT → 主管审核入正式库 | ✅ `faq_ingest_check.py` |
| F-03 推荐（出链） | AI Agent Top3 召回 | ✅ `faq_ingest_check.py`（查重规则复用） |

设计原则对齐项目 AI 边界约定：**模型只把已有文本说得更顺，不决定发生什么**——检测脚本验证的正是 AI 没有越界决定什么。

## 何时使用本 Skill

- AI 客服对话记录**例行抽检**（质检口径：拒答率、编造率、越界率）
- 工单 ACCEPTED 后自动生成 FAQ DRAFT，**主管审核前**先跑机器预检，过滤 PII/重复/注入
- FAQ 正式库**入库门禁**：预检不通过的 DRAFT 不进入主管审核队列
- CI 集成：对话记录/DRAFT 批量文件变更时自动检测

## 能力清单

| 脚本 | 作用 | 输入 | 退出码 |
|---|---|---|---|
| `scripts/faq_ingest_check.py` | FAQ DRAFT 入库前四项检测 | DRAFT JSON 文件（或 `--demo` 自检） | 0=全部通过 / 1=有违规 |
| `scripts/chat_reply_check.py` | AI 客服对话记录四项检测 | 对话 JSON 文件（或 `--demo` 自检） | 0=全部通过 / 1=有违规 |

## 使用方式

```bash
# 1. FAQ DRAFT 入库预检（主管审核前必跑）
python scripts/faq_ingest_check.py --draft drafts.json
python scripts/faq_ingest_check.py --draft drafts.json --kb kb_formal.json   # 带正式库查重
python scripts/faq_ingest_check.py --demo                                   # 无文件时内置样本自检

# 2. AI 客服对话抽检
python scripts/chat_reply_check.py --chat sessions.json
python scripts/chat_reply_check.py --demo

# 3. CI 门禁：JSON 输出 + 退出码拦截
python scripts/faq_ingest_check.py --draft drafts.json --json > faq_check.json
```

## 检测规则明细

### FAQ DRAFT 入库检测（faq_ingest_check.py）

| 规则 | 检测内容 | 严重度 | 处置建议 |
|---|---|---|---|
| R1 PII 泄露 | question/answer 含工号（`E\d{4}`）、手机号（`1[3-9]\d{9}`）、邮箱、资产编号（`IT-[A-Z]{2,4}-\d{8}`） | CRITICAL | 拒绝入库，退回脱敏 |
| R2 格式校验 | question 5–100 字符；answer 10–500 字符；category 值域 `HARDWARE/SOFTWARE/NETWORK/ACCOUNT/OTHER` | HIGH | 退回 AI 重新生成 |
| R3 相似度查重 | 与正式库条目 `SequenceMatcher` 相似度 > 0.85 判疑似重复 | MEDIUM | 走相似度合并判定流程 |
| R4 提示注入 | 含「忽略之前指令」「你现在是」「系统提示词」等注入特征串 | CRITICAL | 拒绝入库，标记攻击样本 |

### AI 客服对话检测（chat_reply_check.py）

| 规则 | 检测内容 | 严重度 | 处置建议 |
|---|---|---|---|
| R1 拒答合规 | `knowledge_hit=false` 的 AI 回复必须命中拒答模板（「无法解答/未找到/转人工」类标记）；未命中判**编造回答** | CRITICAL | 编造率是 AI 客服核心红线 |
| R2 越界承诺 | AI 回复含「保证/一定/肯定/承诺/绝对」类承诺性用语 | HIGH | 高优工单禁止 AI 承诺时效 |
| R3 PII 泄露 | AI 回复含工号/手机号/邮箱/资产编号（他人信息） | CRITICAL | 对话记录脱敏 |
| R4 敏感操作指引 | AI 回复含密码明文、直接授予管理员权限等危险指引 | HIGH | 拦截并转人工 |

## 判定标准

- 任一 CRITICAL 违规 → 退出码 1，DRAFT 不入主管审核队列 / 对话标记质检不合格
- 仅 MEDIUM（查重）→ 退出码 1 但标注「疑似重复」，走合并判定而非直接拒绝
- 全部通过 → 退出码 0，DRAFT 进入主管审核队列（**机器预检通过 ≠ 免审**，主管确认仍是入库唯一关口）

## 维护纪律

1. **PII 模式单一来源**：两个脚本共用工号/手机号/邮箱/资产编号正则，新增 PII 类型时两处同步
2. **拒答模板词表**与 AI 客服系统提示词中的拒答话术保持同步，提示词改话术时同步更新 `chat_reply_check.py` 的 `REFUSAL_MARKERS`
3. **正式库快照**用于查重的 `--kb` 文件建议每日导出一次，避免与线上库漂移
4. 检测脚本只读不写，可安全对生产导出文件执行
