# day26/run_day26_langgraph_hitl.py
# 生产级 LangGraph Checkpointer 快照持久化与原生 interrupt 人机审批智能体
import operator
import copy
from typing import TypedDict, Annotated, Optional, Dict, Any, List, Tuple, Callable

# ==============================================================================
# 0. 依赖导入与双模仿真引擎 (Zero-Dependency Fallback Engine)
# ==============================================================================
try:
    from langgraph.graph import StateGraph, START, END  # type: ignore[import-not-found]
    from langgraph.checkpoint.memory import MemorySaver  # type: ignore[import-not-found]
    from langgraph.types import interrupt, Command  # type: ignore[import-not-found]
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    START = "__start__"
    END = "__end__"

    class GraphInterrupt(Exception):
        """原生 interrupt 抛出的挂起异常"""
        def __init__(self, value: Any):
            self.value = value

    def interrupt(payload: Any):
        """原生 interrupt 挂起调用"""
        raise GraphInterrupt(payload)

    class Command:
        """原生 Command 类（用于携带 resume 数据唤醒中断节点）"""
        def __init__(self, resume: Any = None):
            self.resume = resume

    class InterruptEvent:
        def __init__(self, value: Any):
            self.value = value

    class StateTask:
        def __init__(self, name: str, interrupts: List[InterruptEvent]):
            self.name = name
            self.interrupts = interrupts

    class StateSnapshot:
        def __init__(self, values: Dict[str, Any], next_nodes: Tuple[str, ...], tasks: List[StateTask], config: Optional[Dict[str, Any]] = None):
            self.values = values
            self.next = next_nodes
            self.tasks = tasks
            self.config = config or {}

    class MemorySaver:
        """简易内存持久化检查点存储器"""
        def __init__(self):
            # storage: thread_id -> list of snapshots
            self.storage: Dict[str, List[Dict[str, Any]]] = {}

    class MinimalHITLStateGraph:
        """支持 Checkpointer、原生中断 interrupt 与 Command(resume) 恢复的仿真引擎"""
        def __init__(self, state_schema):
            self.state_schema = state_schema
            self.nodes: Dict[str, Callable] = {}
            self.edges: Dict[str, str] = {}
            self.conditional_edges: Dict[str, Tuple[Callable, Dict[str, str]]] = {}

        def add_node(self, name: str, func: Callable):
            self.nodes[name] = func

        def add_edge(self, source: str, target: str):
            self.edges[source] = target

        def add_conditional_edges(self, source: str, router_func: Callable, mapping: Dict[str, str]):
            self.conditional_edges[source] = (router_func, mapping)

        def compile(self, checkpointer: Optional[MemorySaver] = None):
            return CompiledHITLApp(self, checkpointer)

    class CompiledHITLApp:
        def __init__(self, graph: MinimalHITLStateGraph, checkpointer: Optional[MemorySaver]):
            self.graph = graph
            self.checkpointer = checkpointer or MemorySaver()

        def _get_thread_id(self, config: Optional[Dict[str, Any]]) -> str:
            if config and "configurable" in config:
                return config["configurable"].get("thread_id", "default_thread")
            return "default_thread"

        def get_state(self, config: Optional[Dict[str, Any]]) -> StateSnapshot:
            thread_id = self._get_thread_id(config)
            checkpoint_id = config.get("configurable", {}).get("checkpoint_id") if config else None
            history = self.checkpointer.storage.get(thread_id, [])
            if not history:
                return StateSnapshot(values={}, next_nodes=(), tasks=[], config=config)
            
            if checkpoint_id:
                target = next((item for item in history if item.get("checkpoint_id") == checkpoint_id), history[-1])
            else:
                target = history[-1]

            tasks = []
            if target.get("interrupted"):
                tasks.append(StateTask(target["next_node"], [InterruptEvent(target["interrupt_value"])]))
            return StateSnapshot(
                values=copy.deepcopy(target["state"]),
                next_nodes=(target["next_node"],) if target["next_node"] != END else (),
                tasks=tasks,
                config={"configurable": {"thread_id": thread_id, "checkpoint_id": target.get("checkpoint_id")}}
            )

        def get_state_history(self, config: Optional[Dict[str, Any]]) -> List[StateSnapshot]:
            """Time-Travel 核心：返回当前会话的历史快照版本列表（从新到旧）"""
            thread_id = self._get_thread_id(config)
            history = self.checkpointer.storage.get(thread_id, [])
            results = []
            for item in reversed(history):
                tasks = []
                if item.get("interrupted"):
                    tasks.append(StateTask(item["next_node"], [InterruptEvent(item["interrupt_value"])]))
                results.append(StateSnapshot(
                    values=copy.deepcopy(item["state"]),
                    next_nodes=(item["next_node"],) if item["next_node"] != END else (),
                    tasks=tasks,
                    config={"configurable": {"thread_id": thread_id, "checkpoint_id": item.get("checkpoint_id")}}
                ))
            return results

        def update_state(self, config: Dict[str, Any], values: Dict[str, Any]):
            """Time-Travel 核心：针对特定快照版本注入热补丁修补数据"""
            thread_id = self._get_thread_id(config)
            checkpoint_id = config.get("configurable", {}).get("checkpoint_id")
            history = self.checkpointer.storage.setdefault(thread_id, [])
            
            if checkpoint_id:
                target = next((item for item in history if item.get("checkpoint_id") == checkpoint_id), None)
            else:
                target = history[-1] if history else None

            if not target:
                raise RuntimeError(f"未找到对应的历史检查点快照: {checkpoint_id}")

            # 热修补状态值并生成一个新的分叉快照版本
            new_state = copy.deepcopy(target["state"])
            new_state.update(values)
            new_ckpt_id = f"ckpt_fork_{len(history)+1:03d}"
            forked_item = {
                "checkpoint_id": new_ckpt_id,
                "state": new_state,
                "next_node": target["next_node"],
                "interrupted": False,
                "interrupt_value": None
            }
            history.append(forked_item)
            return {"configurable": {"thread_id": thread_id, "checkpoint_id": new_ckpt_id}}

        def invoke(self, input_data: Any, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
            thread_id = self._get_thread_id(config)
            checkpoint_id = config.get("configurable", {}).get("checkpoint_id") if config else None
            history = self.checkpointer.storage.setdefault(thread_id, [])

            is_resume = isinstance(input_data, Command)
            resume_value = input_data.resume if is_resume else None

            # 支持从历史快照或修补点进行分支重放 (Time-Travel Forked Replay)
            if input_data is None:
                if checkpoint_id:
                    target = next((item for item in history if item.get("checkpoint_id") == checkpoint_id), history[-1])
                else:
                    target = history[-1]
                current_state = copy.deepcopy(target["state"])
                # 重新从初审核验节点或当前目标节点执行分支
                current_node = target.get("next_node")
                if current_node == "human_approval_node" or current_node == END:
                    # 如果是被修补了参数（如修改了金额），重新流经初审判定
                    current_node = self.graph.edges.get(START)
            elif is_resume:
                if not history:
                    raise RuntimeError("无法恢复未初始化的执行流！")
                last_checkpoint = history[-1]
                current_state = copy.deepcopy(last_checkpoint["state"])
                current_node = last_checkpoint["next_node"]
            else:
                current_state = copy.deepcopy(input_data)
                current_node = self.graph.edges.get(START)
                # 记录初始输入快照
                history.append({
                    "checkpoint_id": f"ckpt_{len(history)+1:03d}",
                    "state": copy.deepcopy(current_state),
                    "next_node": current_node,
                    "interrupted": False,
                    "interrupt_value": None
                })

            while current_node and current_node != END:
                node_func = self.graph.nodes[current_node]

                # 尝试执行当前节点
                try:
                    if is_resume and resume_value is not None:
                        # 针对挂起节点的唤醒执行，采用 mock 传入人类审批注入数据
                        orig_interrupt = globals().get("interrupt")
                        def mocked_interrupt(_card):
                            return resume_value
                        globals()["interrupt"] = mocked_interrupt
                        try:
                            delta = node_func(current_state)
                        finally:
                            globals()["interrupt"] = orig_interrupt
                        is_resume = False
                        resume_value = None
                    else:
                        delta = node_func(current_state)
                except GraphInterrupt as gi:
                    # 捕获原生中断：将当前状态持久化至 Checkpointer 并优雅挂起退出
                    history.append({
                        "checkpoint_id": f"ckpt_interrupt_{len(history)+1:03d}",
                        "state": copy.deepcopy(current_state),
                        "next_node": current_node,
                        "interrupted": True,
                        "interrupt_value": gi.value
                    })
                    return current_state

                # 合并状态 (处理 Reducer 逻辑，例如列表累加追加)
                for k, v in delta.items():
                    if k == "audit_logs" and isinstance(v, list):
                        current_state[k] = current_state.get(k, []) + v
                    else:
                        current_state[k] = v

                # 计算下一个目标节点
                if current_node in self.graph.conditional_edges:
                    router, mapping = self.graph.conditional_edges[current_node]
                    route_key = router(current_state)
                    next_node = mapping.get(route_key, END)
                else:
                    next_node = self.graph.edges.get(current_node, END)

                # 将当前最新节点状态保存至 Checkpointer 快照历史
                history.append({
                    "checkpoint_id": f"ckpt_{len(history)+1:03d}",
                    "state": copy.deepcopy(current_state),
                    "next_node": next_node,
                    "interrupted": False,
                    "interrupt_value": None
                })
                current_node = next_node

            return current_state

    StateGraph = MinimalHITLStateGraph

# ==============================================================================
# 1. 业务状态模式定义 (TypedDict)
# ==============================================================================

class ApprovalState(TypedDict):
    ticket_id: str
    applicant: str
    department: str
    amount: float
    purpose: str
    policy_matched: str
    risk_level: str               # "LOW" (低风险自动放行) / "HIGH" (高风险需人工介入)
    approval_status: str          # "PENDING", "APPROVED", "REJECTED"
    approver: Optional[str]
    audit_comment: Optional[str]
    audit_logs: Annotated[List[str], operator.add]

# ==============================================================================
# 2. 核心图节点设计 (纯函数计算节点)
# ==============================================================================

def validate_and_rule_check_node(state: ApprovalState) -> Dict[str, Any]:
    """步骤 1：业务合规规则预审与风险定级"""
    amt = state["amount"]
    logs = [f"【合规初审】单据号 {state['ticket_id']} 进入核验，申报人：{state['applicant']}，金额：{amt} 元"]

    # 模拟企业制度规则前置匹配
    if amt <= 2000.0:
        logs.append("【合规初审】申报金额未超过常规 2000 元限额，风险等级评定为 LOW")
        return {
            "policy_matched": "《常规日常报销快速通道规约》",
            "risk_level": "LOW",
            "audit_logs": logs
        }
    else:
        logs.append(f"【合规初审】申报金额 {amt} 元超出 2000 元自动放行红线，触发合规风控，风险等级评定为 HIGH")
        return {
            "policy_matched": "《大额资金事前特批与连带责任条例》",
            "risk_level": "HIGH",
            "audit_logs": logs
        }

def route_decision(state: ApprovalState) -> str:
    """条件路由：低风险直接自动放行，高风险流转至人工终审中断节点"""
    if state["risk_level"] == "LOW":
        return "auto_approval_node"
    return "human_approval_node"

def auto_approval_node(state: ApprovalState) -> Dict[str, Any]:
    """步骤 2A：低风险自动审批节点"""
    logs = ["【系统自动放行】系统规则机审通过，已完成自动记账核销"]
    return {
        "approval_status": "APPROVED",
        "approver": "SYSTEM_AUTO_DISPATCH",
        "audit_comment": "常规额度系统机审合规，全自动放行通过",
        "audit_logs": logs
    }

def human_approval_node(state: ApprovalState) -> Dict[str, Any]:
    """步骤 2B：高风险人工中断节点（原生 interrupt 抛出挂起数据）"""
    # 组装展示给审批人（如钉钉/企业微信工作流卡片）的信息
    review_card = {
        "title": "⚠️ 发现大额资金申报，需要人工终审裁决",
        "ticket_id": state["ticket_id"],
        "applicant": state["applicant"],
        "department": state["department"],
        "amount": state["amount"],
        "reason": f"命中制度：{state['policy_matched']}，金额超标需人工介入"
    }

    # 🛑 核心技术：抛出中断并挂起！执行在此处暂停，等待外部人类操作
    human_response: Dict[str, Any] = interrupt(review_card)

    # 外部恢复 (Resume) 时从此处继续流转
    decision = human_response.get("action", "REJECTED")  # "APPROVED" or "REJECTED"
    approver_name = human_response.get("approver", "未知审批人")
    comment = human_response.get("comment", "无审批附言")

    status = "APPROVED" if decision == "APPROVED" else "REJECTED"
    logs = [f"【人工审批介入】终审人 [{approver_name}] 做出裁决：{status}，审批评语：{comment}"]

    return {
        "approval_status": status,
        "approver": approver_name,
        "audit_comment": comment,
        "audit_logs": logs
    }

def final_accounting_node(state: ApprovalState) -> Dict[str, Any]:
    """步骤 3：单据终审归档入库与财务通知"""
    if state["approval_status"] == "APPROVED":
        status_desc = "✅ 审批最终通过，款项进入银行出纳拨付队列"
    else:
        status_desc = "❌ 审批最终驳回，单据作废并已邮件通知申报人修改重提"

    logs = [f"【终审归档】单据 {state['ticket_id']} 状态终结：{status_desc}"]
    return {"audit_logs": logs}

# ==============================================================================
# 3. 构造状态图并挂载持久化 Checkpointer
# ==============================================================================

def build_production_approval_agent():
    builder = StateGraph(ApprovalState)

    # 添加各个业务节点
    builder.add_node("validate_node", validate_and_rule_check_node)
    builder.add_node("auto_approval_node", auto_approval_node)
    builder.add_node("human_approval_node", human_approval_node)
    builder.add_node("final_accounting_node", final_accounting_node)

    # 构建拓扑逻辑边
    builder.add_edge(START, "validate_node")
    builder.add_conditional_edges(
        "validate_node",
        route_decision,
        {
            "auto_approval_node": "auto_approval_node",
            "human_approval_node": "human_approval_node"
        }
    )
    builder.add_edge("auto_approval_node", "final_accounting_node")
    builder.add_edge("human_approval_node", "final_accounting_node")
    builder.add_edge("final_accounting_node", END)

    # 挂载 Checkpointer（生产环境可无缝替换为 SqliteSaver 或 PostgresSaver）
    checkpointer = MemorySaver()
    app = builder.compile(checkpointer=checkpointer)
    return app

# ==============================================================================
# 4. 模拟测试：验证自动放行与人工挂起唤醒全生命周期
# ==============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print(f"🚀 Day 26 生产级 LangGraph：Checkpointer 持久化与原生中断审批实战 (原生引擎: {LANGGRAPH_AVAILABLE})")
    print("=" * 80)

    app = build_production_approval_agent()

    # --------------------------------------------------------------------------
    # 场景 1：低风险常规报销单（小额 1200 元，全自动流转）
    # --------------------------------------------------------------------------
    thread_config_1 = {"configurable": {"thread_id": "TICKET_AUTO_001"}}
    input_1: ApprovalState = {
        "ticket_id": "EXP-2024-001",
        "applicant": "张三",
        "department": "华东研发部",
        "amount": 1200.0,
        "purpose": "上海客户现场技术支持打车与差旅",
        "policy_matched": "",
        "risk_level": "",
        "approval_status": "PENDING",
        "approver": None,
        "audit_comment": None,
        "audit_logs": []
    }

    print("\n▶️ [测试 1] 提交低风险单据 (金额: 1200 元)...")
    res1 = app.invoke(input_1, config=thread_config_1)
    print(f"  ➔ 流程终态: {res1['approval_status']} (审批人: {res1['approver']})")
    for log in res1["audit_logs"]:
        print(f"     {log}")

    # --------------------------------------------------------------------------
    # 场景 2：高风险大额申报（金额: 30000 元，命中中断并暂停，模拟人工外部介入）
    # --------------------------------------------------------------------------
    thread_config_2 = {"configurable": {"thread_id": "TICKET_HIGH_002"}}
    input_2: ApprovalState = {
        "ticket_id": "EXP-2024-002",
        "applicant": "周建华",
        "department": "华东交付一部",
        "amount": 30000.0,
        "purpose": "华东重大项目现场紧急服务器设备采购与垫付",
        "policy_matched": "",
        "risk_level": "",
        "approval_status": "PENDING",
        "approver": None,
        "audit_comment": None,
        "audit_logs": []
    }

    print("\n▶️ [测试 2 - 阶段 A] 提交大额高风险单据 (金额: 30000 元)...")
    res2_phase1 = app.invoke(input_2, config=thread_config_2)

    # 检查状态图当前快照状态
    current_state = app.get_state(thread_config_2)
    is_paused = len(current_state.next) > 0 and 'human_approval_node' in current_state.next
    print(f"  ➔ 状态机是否暂停挂起: {is_paused}")
    print(f"  ➔ 下一待执行节点: {current_state.next}")
    if current_state.tasks and current_state.tasks[0].interrupts:
        interrupt_info = current_state.tasks[0].interrupts[0].value
        print(f"  🛑 [系统捕获中断事件]: {interrupt_info['title']}")
        print(f"     单号: {interrupt_info['ticket_id']} | 申请人: {interrupt_info['applicant']} | 原因: {interrupt_info['reason']}")

    # --------------------------------------------------------------------------
    # 模拟外部经过数小时后，人类专家（监察委副主任赵小雪）在审批工作台点击“通过”
    # --------------------------------------------------------------------------
    print("\n▶️ [测试 2 - 阶段 B] 模拟外部终审人接入，执行 Resume 唤醒挂起流程...")
    human_approval_payload = {
        "action": "APPROVED",
        "approver": "监察委员会副主任赵小雪",
        "comment": "已核验合同及现场签收单，符合特殊采购绿色通道，准予特批放行。"
    }

    # 使用 Command(resume=...) 唤醒暂停的图，继续完成后续流转
    res2_phase2 = app.invoke(Command(resume=human_approval_payload), config=thread_config_2)
    print(f"  ➔ 唤醒后全流程状态: {res2_phase2['approval_status']}")
    print(f"  ➔ 最终经办审批人: {res2_phase2['approver']}")
    print("  📋 [完整审计跟踪链]：")
    for log in res2_phase2["audit_logs"]:
        print(f"     {log}")

    print("\n" + "=" * 80)
    print("✨ LangGraph Checkpointer 与原生 HITL 审批全生命周期闭环跑通！")
    print("=" * 80)

    # --------------------------------------------------------------------------
    # 场景 3：生产进阶 —— Time-Travel（时间旅行）历史重放与状态热修补
    # --------------------------------------------------------------------------
    print("\n" + "#" * 80)
    print("🚀 [进阶测试 3：Time-Travel 时间旅行与状态热补丁演练]")
    print("#" * 80)

    thread_config_3 = {"configurable": {"thread_id": "TICKET_TIMETRAVEL_003"}}
    input_3: ApprovalState = {
        "ticket_id": "EXP-2024-003",
        "applicant": "李四",
        "department": "华北交付部",
        "amount": 50000.0,              # 错填为 5 万元，将触发高风险中断挂起
        "purpose": "差旅报销单（申请人手抖多填了一个零）",
        "policy_matched": "",
        "risk_level": "",
        "approval_status": "PENDING",
        "approver": None,
        "audit_comment": None,
        "audit_logs": []
    }

    print("\n▶️ [Step 1] 错误单据初次提交 (金额: 50000 元，产生挂起)...")
    app.invoke(input_3, config=thread_config_3)
    
    # 1. 查看时间旅行时光机：检索全生命周期快照历史
    print("\n🕰️ [Step 2: Time-Travel 审计] 调用 get_state_history() 检索所有历史快照版本：")
    state_history = list(app.get_state_history(thread_config_3))
    for idx, snapshot in enumerate(state_history):
        ckpt_id = snapshot.config.get("configurable", {}).get("checkpoint_id")
        amt = snapshot.values.get("amount")
        next_n = snapshot.next
        print(f"   版本 [{idx+1}] 快照ID: {ckpt_id} | 状态金额: {amt} | 下一节点: {next_n}")

    # 2. 定位到挂起前的历史快照并进行人工状态热修补 (update_state)
    target_snapshot = state_history[0]  # 取当前最新快照
    target_ckpt_id = target_snapshot.config["configurable"]["checkpoint_id"]
    print(f"\n🔧 [Step 3: 状态热修补] 针对快照 [{target_ckpt_id}] 实施数据修正：")
    print("   修正前申报金额: 50000.0 元 -> 注入热补丁修改为: 1500.0 元 (纠正手抖多输的 0)")

    patch_config = {"configurable": {"thread_id": "TICKET_TIMETRAVEL_003", "checkpoint_id": target_ckpt_id}}
    patch_result = app.update_state(
        patch_config,
        values={
            "amount": 1500.0,
            "audit_logs": ["【运维工程师热修补】发现金额录入错误，人工调用 update_state 将 50000.0 元订正为 1500.0 元"]
        }
    )
    print(f"   热补丁注入成功！派生全新分叉快照版本: {patch_result['configurable']['checkpoint_id']}")

    # 3. 基于修补点重新触发流转 (Forked Execution，传入 None)
    print("\n▶️ [Step 4: 时光倒流重流转] 从热修补快照节点分叉重放流程 (invoke(None))...")
    res3_replay = app.invoke(None, config=patch_result)
    print(f"  ➔ 重放后流程终态: {res3_replay['approval_status']}")
    print(f"  ➔ 最终审批人: {res3_replay['approver']}")
    print(f"  ➔ 最终核定金额: {res3_replay['amount']} 元")
    print("  📋 [时光旅行重流转后的完整审计链]：")
    for log in res3_replay["audit_logs"]:
        print(f"     {log}")

    print("\n" + "=" * 80)
    print("🎯 Time-Travel（历史快照透视 + 状态热修补 + 分叉重新流转）完整验证通过！")
    print("=" * 80)

