# Day16 演示页面 → 代码位置对照表（演讲速查）

> 按讲解顺序排列。启动：`python -m day16` → 浏览器开 `http://127.0.0.1:8321/`

## ① 提问框 + 三个预置用例按钮（页面顶部）

- **前端**：预置用例定义 `api.py:20` `PRESET_CASES` → 按钮渲染 `api.py` `renderPresets()` → 点击 `askPreset()`
- **后端接口**：`api.py` `POST /api/v1/agent/chat` → 进 `agent.py` `run()`

## ② 最终答复 + Function Calling 工具轨迹 —— 核心

- **前端渲染**：`api.py` `render()`；轨迹卡片（工具名/入参/反馈/成功或拦截）在 `api.py` 内嵌 JS 的 `render()` 里
- **决策中枢**：`agent.py:AGENT_TOOLS_SCHEMA`（两个工具契约）+ `agent.py:run()`（ReAct 主循环）
- **物理工具派发**：`agent.py:_execute_tool()`（Pydantic Fast-Fail 校验后分发）
- **系统提示词**：`prompts.py:AGENT_SYSTEM_PROMPT`（客观第三人称 / 封闭世界 / 错误反思三军规）

## ③ 安全 Text2SQL 五重防线（恶意注入演示的拦截逻辑）

- **拦截器**：`text2sql.py:SafeText2SQLEngine.validate_sql()` ——
  分号拦截 → 危险动词扫描 → SELECT 开头 → 真实表白名单 → 强制 LIMIT 50（讲点：5 道门在 `cursor.execute` 之前，查询对象是企业真实工单库）

## ④ 外部 API 网关（工单升级协同的重试韧性）

- **网关**：`gateway.py:ExternalAPIGateway.call_ticket_escalation_api()` ——
  超时硬约束 + 指数退避 + 抖动 + 熔断降级（讲点：15% 概率模拟首轮 504，观察重试）

## ⑤ 确定性沙箱兜底（断网离线演示）

- **沙箱**：`agent.py:_run_deterministic_mock()` —— 工单 / 知识库 / DROP TABLE 三路 + 默认拒答（直查真实库）
- **判定顺序**：恶意注入（DROP TABLE）优先于实体匹配（讲点：注入语句夹带合法实体名也能正确拦截）

---

## 主链路核心逻辑 `run()`（agent.py，一句话指路）

| 步骤 | 位置 | 一句话 |
|---|---|---|
| LLM 装配 | `agent.py:__init__` | `load_llm_config()` 读 .env，未配置落沙箱 |
| ReAct 循环 | `agent.py:run()` | `chat.completions.create(tools=...)`，deepseek-v4-flash 不显式传 temperature |
| 工具派发 | `agent.py:_execute_tool()` | Pydantic 校验 → text2sql / gateway |
| 错误回传 | `agent.py:run()` | `role="tool"` 注入执行结果（自愈反思） |
| 沙箱兜底 | `agent.py:_run_deterministic_mock()` | 断网/离线确定性作答，绝不编造 |

## 一句话回答"代码在哪"

- **前端页面**：`day16/api.py`（HTML/CSS/JS 全内嵌）
- **决策中枢**：`day16/agent.py`（`run()` 主循环 + `AGENT_TOOLS_SCHEMA`）
- **安全 SQL**：`day16/text2sql.py`（五重门禁）
- **API 网关**：`day16/gateway.py`（重试韧性）
- **防幻觉规则**：`day16/prompts.py`
- **模型配置**：不在 day16，复用 `rag_pipeline/config.py:load_llm_config()`（读 `.env`）
