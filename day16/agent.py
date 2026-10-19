# -*- coding: utf-8 -*-
"""EnterpriseReActAgent — 企业级 ReAct 智能体运行时（Function Calling 决策中枢 + 自愈反思）。

对齐讲义第四篇「ReAct 循环与 Tool Error Reflection」：大模型通过原生 `tools` 协议
识别意图、抽取参数；宿主沙箱执行物理工具（安全 Text2SQL 查真实业务库 / 工单升级协同
API）并把结果以 `role="tool"` 回传，模型据此反思、纠错、生成终答。

工程要点：
- LLM 配置唯一真源 `rag_pipeline.config.load_llm_config()`（.env 的 LLM_*），
  不硬编码 Ollama；推理默认取 `LLM_CLEAN_MODEL`（deepseek-v4-flash），可用 `DAY16_AGENT_MODEL` 覆盖；
- Text2SQL 连真实业务库 it_ticket_system（MySQL），查询工单故障流程与知识库卡片；
- 确定性沙箱兜底：未配置 LLM / 强制离线 / 调用异常时走 `_run_deterministic_mock`，
  仍直查真实库（不编造），保障断网/离线演示；
- Tool Error Reflection：工具返回「安全违规/执行异常」时把结构化错误回传模型，
  `max_steps` 硬上限防止自愈死循环。
"""

import json
from typing import Any, Dict, List, Optional

from rag_pipeline.config import load_llm_config

from . import config as dcfg
from .gateway import ExternalAPIGateway
from .prompts import AGENT_SYSTEM_PROMPT
from .schemas import SafeText2SQLInput, SubmitEscalationInput
from .text2sql import SafeText2SQLEngine


# ==============================================================================
# Agent Function Calling 工具集描述 (Tools Schema)
# ==============================================================================

AGENT_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "execute_safe_sql",
            "description": (
                "在企业只读业务库 it_ticket_system 中执行安全 SQL 查询。"
                "可用数据表及结构：\n"
                "1. ticket (工单表): ticket_id(工单号), creator_id(创建人), nature(INCIDENT/SERVICE_REQUEST), "
                "category_id(分类), title(标题), description(描述), impact_description(影响描述), "
                "urgency_description(紧急度描述), location(位置), contact(联系方式), asset_id(资产), "
                "status(状态: NEW/ASSIGNED/IN_PROGRESS/PENDING_SUPPLEMENT/PENDING_EXTERNAL/PENDING_ACCEPTANCE/COMPLETED/CANCELLED/CLOSED), "
                "priority(优先级: HIGH/MEDIUM/LOW), assignee_id(受理工程师), created_at(创建时间), completed_at(完成时间), closed_at(关闭时间), rating_score(评分)\n"
                "2. ticket_transition (工单状态流转表): ticket_id, from_status, to_status, event(事件如 TICKET_CREATE/TICKET_ASSIGN/TICKET_SUBMIT_RESOLUTION), operator_id(操作人), reason(原因), occurred_at\n"
                "3. ticket_resolution (解决方案表): ticket_id, solution(方案), verification(验证), submitted_by, submitted_at\n"
                "4. ticket_acceptance (验收表): ticket_id, result(ACCEPTED/REJECTED/AUTO_ACCEPTED), reason, operator_id, rating_score\n"
                "5. consultation (咨询会话表): session_id, creator_id, category_id, status, current_engineer_id, source, converted_ticket_id\n"
                "6. consultation_message (咨询消息表): message_id, session_id, sender_id, sender_type, content, citation_json, sent_at\n"
                "7. assignment (分派表): assignment_id, biz_type(CONSULTATION/TICKET), biz_id, engineer_id, assigned_at, responded_at\n"
                "8. sla_instance (SLA表): sla_id, ticket_id, biz_id, sla_type, status(RUNNING/MET/BREACHED), target_at, breach_at\n"
                "9. category (分类表): category_id, parent_id, name(如 硬件/软件/网络/账号权限), level, ticket_nature\n"
                "10. support_team (支持组): team_id, name, status\n"
                "11. user (用户表): user_id, employee_no, name, department_id, status\n"
                "12. knowledge_article (知识库文章表): article_id, status(DRAFT/PENDING_REVIEW/PUBLISHED/OFFLINE), current_version_id, category_id, risk_level(NORMAL/HIGH), version\n"
                "13. knowledge_version (知识库版本表): version_id, article_id, version_no, content(JSON对象，含 title/summary/keywords/body，用 JSON_UNQUOTE(JSON_EXTRACT(content,'$.title')) 取标题), author_id, reviewer_id, published_at, change_note\n"
                "⚠️ 安全硬约束：必须且只能使用 SELECT 语句，严禁使用任何 DROP/DELETE/UPDATE 等写操作！"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query_rationale": {
                        "type": "string",
                        "description": "生成该 SQL 的业务推理动机与要解决的问题"
                    },
                    "generated_sql": {
                        "type": "string",
                        "description": "严格合规的只读 SELECT SQL 语句"
                    }
                },
                "required": ["query_rationale", "generated_sql"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "submit_ticket_escalation",
            "description": (
                "向外部协同系统提交工单升级/加急申请。"
                "当工单故障影响范围大、SLA 临近超时或需更高级别介入时调用此接口。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_id": {
                        "type": "string",
                        "description": "待升级工单号，必须为 TK 开头后接数字，例如 TK202609300013"
                    },
                    "escalation_reason": {
                        "type": "string",
                        "description": "升级/加急原因，注明故障影响范围与依据"
                    },
                    "target_priority": {
                        "type": "string",
                        "description": "目标优先级：HIGH / MEDIUM / LOW"
                    },
                    "notes": {
                        "type": "string",
                        "description": "补充备注（可选）"
                    }
                },
                "required": ["ticket_id", "escalation_reason"]
            }
        }
    }
]


class EnterpriseReActAgent:
    """企业级 ReAct 智能体运行时：Function Calling 决策 + 真实库 Text2SQL + 沙箱兜底。"""

    def __init__(self, model_name: Optional[str] = None,
                 timeout: float = dcfg.LLM_TIMEOUT):
        self.db_engine = SafeText2SQLEngine()
        self.api_gateway = ExternalAPIGateway()
        self.client = None

        cfg = load_llm_config()
        self.model = model_name or dcfg.AGENT_MODEL or cfg["clean_model"]
        api_key = cfg.get("api_key", "")
        base_url = cfg.get("base_url", "")

        if (api_key and not api_key.startswith("sk-replace-") and api_key != "sk-..."
                and base_url and not dcfg.OFFLINE):
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
            except ImportError:
                print("       ⚠️ 未安装 openai 包，Function Calling 不可用，走确定性沙箱兜底")

        # 未配置 LLM / 强制离线 / 缺 openai 包 → 走沙箱
        self.use_mock = self.client is None or dcfg.OFFLINE

    @property
    def available(self) -> bool:
        return self.client is not None and not dcfg.OFFLINE

    # --------------------------------------------------------------------------
    # 物理工具调度分发（Pydantic 快速校验 Fast-Fail）
    # --------------------------------------------------------------------------
    def _execute_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if name == "execute_safe_sql":
            try:
                contract = SafeText2SQLInput(**arguments)
                return self.db_engine.execute_query(contract.generated_sql)
            except Exception as ve:  # ValidationError 等 —— 统一回传结构化错误供模型反思
                return {"success": False, "error": f"【Pydantic 参数校验失败】：{str(ve)}"}

        elif name == "submit_ticket_escalation":
            try:
                contract = SubmitEscalationInput(**arguments)
                return self.api_gateway.call_ticket_escalation_api(contract.model_dump())
            except Exception as ve:
                return {"success": False, "error": f"【Pydantic 参数校验失败】：{str(ve)}"}

        return {"success": False, "error": f"未知的工具名称: {name}"}

    # --------------------------------------------------------------------------
    # ReAct 主循环
    # --------------------------------------------------------------------------
    def run(self, user_query: str, max_steps: int = 5) -> Dict[str, Any]:
        """运行 ReAct 多轮工具决策与自愈反思主循环。

        Returns:
            {"answer": str, "mode": "llm"|"sandbox", "trajectory": [...], "success": bool}
        """
        print(f"\n{'=' * 70}")
        print(f"💬 [用户指令] {user_query}")
        print(f"🕓 [运行模式] {'确定性沙箱（离线兜底）' if self.use_mock else f'LLM Function Calling（{self.model}）'}")
        print(f"{'=' * 70}")

        if self.use_mock:
            return self._run_deterministic_mock(user_query)

        messages = [
            {"role": "system", "content": AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": user_query}
        ]
        trajectory: List[Dict[str, Any]] = []

        for step in range(1, max_steps + 1):
            print(f"\n── 智能体推理步 [{step}/{max_steps}] ──")
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=AGENT_TOOLS_SCHEMA,
                    # 不显式传 temperature，走模型默认值（保证 Function Calling 稳定）
                )
            except Exception as e:
                print(f"  ❌ 大模型调用异常: {e}")
                return {"answer": f"大模型调用异常：{e}", "mode": "llm",
                        "trajectory": trajectory, "success": False}

            msg = response.choices[0].message
            messages.append(msg)

            if msg.tool_calls:
                # 模型在调用工具前可能先输出思考内容
                if getattr(msg, "content", None):
                    print(f"  🧠 模型思考: {msg.content[:240]}")
                for tool_call in msg.tool_calls:
                    fn_name = tool_call.function.name
                    try:
                        fn_args = json.loads(tool_call.function.arguments)
                    except Exception:
                        fn_args = {}

                    tool_out = self._execute_tool(fn_name, fn_args)
                    ok = bool(tool_out.get("success"))
                    print(f"  🛠️  调用工具: [{fn_name}]")
                    print(f"      📥 入参: {json.dumps(fn_args, ensure_ascii=False)[:400]}")
                    print(f"      📤 反馈: {'✅ 成功' if ok else '🔴 拦截/失败'} "
                          f"{json.dumps(tool_out, ensure_ascii=False)[:400]}")

                    trajectory.append({
                        "step": step, "tool": fn_name, "arguments": fn_args,
                        "output": tool_out, "success": ok
                    })

                    # 回传 tool 角色消息给大模型（错误反思自愈的关键）
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_out, ensure_ascii=False)
                    })
            else:
                final_answer = (msg.content or "").strip()
                print(f"  🎯 终答（不再调用工具，直接作答）:\n{final_answer}")
                print(f"{'=' * 70}")
                return {"answer": final_answer, "mode": "llm",
                        "trajectory": trajectory, "success": True}

        print(f"  ⏱ 已达到最大自愈反思轮次上限（{max_steps} 轮），强制终止。")
        print(f"{'=' * 70}")
        return {"answer": "超出最大自愈反思轮次限制", "mode": "llm",
                "trajectory": trajectory, "success": False}

    # --------------------------------------------------------------------------
    # 确定性沙箱执行器（离线演示 / 自动化跑测：直查真实库，不编造）
    # --------------------------------------------------------------------------
    def _run_deterministic_mock(self, query: str) -> Dict[str, Any]:
        trajectory: List[Dict[str, Any]] = []

        def _record(step: int, tool: str, args: Dict[str, Any], out: Dict[str, Any]):
            ok = bool(out.get("success"))
            print(f"\n── 沙箱推理步 [{step}/1] ──")
            print(f"  🛠️  调用工具: [{tool}]")
            print(f"      📥 入参: {json.dumps(args, ensure_ascii=False)[:400]}")
            print(f"      📤 反馈: {'✅ 成功' if ok else '🔴 拦截/失败'} "
                  f"{json.dumps(out, ensure_ascii=False)[:400]}")
            trajectory.append({"step": step, "tool": tool, "arguments": args,
                               "output": out, "success": ok})

        def _finish(ans: str) -> Dict[str, Any]:
            print(f"  🎯 终答（确定性规则）:\n{ans}")
            print(f"{'=' * 70}")
            return {"answer": ans, "mode": "sandbox", "trajectory": trajectory, "success": True}

        # 恶意注入（DROP TABLE）优先于业务关键词判定——注入语句常夹带合法关键词。
        if "DROP TABLE" in query:
            bad_sql = "DROP TABLE ticket;"
            tool_out = self._execute_tool("execute_safe_sql", {"query_rationale": "恶意删库指令", "generated_sql": bad_sql})
            _record(1, "execute_safe_sql", {"generated_sql": bad_sql}, tool_out)
            ans = ("系统安全警报：检测到包含高危动词 [DROP] 的删库指令，底层安全门禁已强制拦截该请求！"
                   "只读接口拒绝执行任何数据破坏操作。")
            return _finish(ans)

        elif any(k in query for k in ("知识库", "文章", "VPN", "打印机", "WiFi")):
            sql = ("SELECT v.version_id, v.article_id, a.status, "
                   "JSON_UNQUOTE(JSON_EXTRACT(v.content, '$.title')) AS title "
                   "FROM knowledge_version v JOIN knowledge_article a ON v.article_id = a.article_id "
                   "WHERE a.status = 'PUBLISHED' ORDER BY v.article_id LIMIT 5")
            tool_out = self._execute_tool("execute_safe_sql", {"query_rationale": "查询已发布知识库卡片", "generated_sql": sql})
            _record(1, "execute_safe_sql", {"generated_sql": sql}, tool_out)
            rows = tool_out.get("data", [])
            if rows:
                titles = "、".join(f"[{r.get('title', '')}]" for r in rows[:5])
                ans = (f"经系统核查知识库，当前已发布（PUBLISHED）的知识卡片共 {len(rows)} 张，"
                       f"例如：{titles}。以上内容均来自真实知识库数据。")
            else:
                ans = "经核查，知识库中暂无已发布的相关卡片。"
            return _finish(ans)

        elif any(k in query for k in ("工单", "故障", "ticket", "派单", "状态")):
            sql = ("SELECT ticket_id, title, status, priority, category_id, created_at "
                   "FROM ticket ORDER BY created_at DESC LIMIT 5")
            tool_out = self._execute_tool("execute_safe_sql", {"query_rationale": "查询最近工单", "generated_sql": sql})
            _record(1, "execute_safe_sql", {"generated_sql": sql}, tool_out)
            rows = tool_out.get("data", [])
            if rows:
                items = "；".join(f"{r.get('ticket_id')}「{r.get('title')}」({r.get('status')})" for r in rows[:5])
                ans = (f"经系统核查工单库，最近的工单共 {len(rows)} 条：{items}。以上内容均来自真实工单数据。")
            else:
                ans = "经核查，工单库中暂无相关记录。"
            return _finish(ans)

        else:
            ans = "经核查，工单库与知识库中未记载相关信息，建议联系 IT 服务台转人工处理。"
            return _finish(ans)
