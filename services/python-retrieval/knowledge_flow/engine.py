# services/python-retrieval/knowledge_flow/engine.py
"""LangGraph 知识库沉淀流程编排引擎 (原生 StateGraph 编译执行版)。

基于 LangGraph 官方核心机制：
1. StateGraph / add_node / add_edge 构建 DAG 拓扑
2. graph.compile(checkpointer=...) 编译为 Pregel 反应式状态机
3. graph.invoke(...) 驱动有向图节点流转与 interrupt 中断挂起
4. graph.invoke(Command(resume=...)) 恢复中断节点流转
5. graph.get_state / get_state_history 实现状态读取与 Time-Travel
6. graph.update_state(...) 实现历史快照热修补与分叉
"""

import copy
import uuid
import sqlite3
import os
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime

from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

from .contract import KnowledgeFlowState, TriggerFlowRequest, KnowledgeReviewDecision
from .checkpointer import BaseFlowCheckpointer, MySqlFlowCheckpointer, SqliteFlowCheckpointer, MemoryFlowCheckpointer
from .nodes import (
    extract_candidate_node,
    sanitize_guard_node,
    cluster_dedup_node,
    admin_review_node,
    publish_index_node
)


# 统一存储在 services/python-retrieval/artifacts/knowledge_flow_checkpoints.db
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SQLITE_PATH = os.path.abspath(os.path.join(_MODULE_DIR, "../artifacts/knowledge_flow_checkpoints.db"))


# ==============================================================================
# LangGraph 标准图拓扑构建器 (StateGraph Builder with add_node & add_edge)
# ==============================================================================

def create_knowledge_flow_graph() -> StateGraph:
    """使用 LangGraph 官方标准的 StateGraph、add_node 与 add_edge 编排有向状态图。"""
    builder = StateGraph(KnowledgeFlowState)

    # 1. 注册核心原子计算节点 (add_node)
    builder.add_node("extract_candidate_node", extract_candidate_node)
    builder.add_node("sanitize_guard_node", sanitize_guard_node)
    builder.add_node("cluster_dedup_node", cluster_dedup_node)
    builder.add_node("admin_review_node", admin_review_node)
    builder.add_node("publish_index_node", publish_index_node)

    # 2. 编排有向拓扑边 (add_edge)
    builder.add_edge(START, "extract_candidate_node")
    builder.add_edge("extract_candidate_node", "sanitize_guard_node")
    builder.add_edge("sanitize_guard_node", "cluster_dedup_node")
    builder.add_edge("cluster_dedup_node", "admin_review_node")
    builder.add_edge("admin_review_node", "publish_index_node")
    builder.add_edge("publish_index_node", END)

    return builder


class KnowledgeFlowEngine:
    """知识库沉淀流程编排主中枢 (100% 由 LangGraph 编译图内核驱动)。"""

    def __init__(self, checkpointer: Optional[Any] = None):
        # 1. 声明 LangGraph 图结构
        self.graph_builder = create_knowledge_flow_graph()

        # 2. 装配 LangGraph 官方 Checkpointer 适配器
        self._raw_checkpointer = checkpointer
        self.sqlite_conn = None
        self.mysql_mirror = None

        if isinstance(checkpointer, BaseCheckpointSaver):
            self.lg_checkpointer = checkpointer
        elif isinstance(checkpointer, SqliteFlowCheckpointer):
            os.makedirs(os.path.dirname(os.path.abspath(checkpointer.db_path)), exist_ok=True)
            self.sqlite_conn = sqlite3.connect(checkpointer.db_path, check_same_thread=False)
            self.lg_checkpointer = SqliteSaver(self.sqlite_conn)
            self.lg_checkpointer.setup()
        elif isinstance(checkpointer, MemoryFlowCheckpointer):
            self.lg_checkpointer = MemorySaver()
        else:
            # 默认：使用本地持久化 SQLite Checkpointer，并选配镜像至 MySQL
            os.makedirs(os.path.dirname(DEFAULT_SQLITE_PATH), exist_ok=True)
            self.sqlite_conn = sqlite3.connect(DEFAULT_SQLITE_PATH, check_same_thread=False)
            self.lg_checkpointer = SqliteSaver(self.sqlite_conn)
            self.lg_checkpointer.setup()
            if isinstance(checkpointer, MySqlFlowCheckpointer):
                self.mysql_mirror = checkpointer
            else:
                self.mysql_mirror = MySqlFlowCheckpointer()

        # 3. 核心：通过 LangGraph 原生 compile 编译生成真正的 Pregel 执行应用
        self.app = self.graph_builder.compile(checkpointer=self.lg_checkpointer)

    def _sync_mysql_mirror(
        self,
        thread_id: str,
        checkpoint_id: str,
        state: Dict[str, Any],
        next_node: str,
        interrupted: bool = False,
        interrupt_value: Any = None
    ) -> None:
        """镜像快照到远程 MySQL 表 (若配置)，便于工单大盘与管理端直查。"""
        if self.mysql_mirror:
            try:
                self.mysql_mirror.save_checkpoint(
                    thread_id=thread_id,
                    checkpoint_id=checkpoint_id,
                    state=state,
                    next_node=next_node,
                    interrupted=interrupted,
                    interrupt_value=interrupt_value
                )
            except Exception:
                pass

    def trigger(self, req: TriggerFlowRequest) -> Dict[str, Any]:
        """发起一条全新知识沉淀流转 (完全由 compiled LangGraph app.invoke 驱动执行)。"""
        candidate_id = req.candidate_id or f"cand-{uuid.uuid4().hex[:8]}"
        thread_id = f"flow-{candidate_id}"
        config = {"configurable": {"thread_id": thread_id}}

        initial_state: KnowledgeFlowState = {
            "candidate_id": candidate_id,
            "source_type": req.source_type,
            "raw_question": req.question,
            "raw_answer": req.answer,
            "title": "",
            "summary": "",
            "problem_desc": "",
            "resolution_steps": "",
            "category_id": req.category_hint or "C_OTH",
            "risk_level": "NORMAL",
            "is_sanitized": False,
            "contains_injection": False,
            "sanitized_question": "",
            "sanitized_answer": "",
            "top_similarity_score": 0.0,
            "is_duplicate": False,
            "duplicate_reference": None,
            "review_status": "PENDING_REVIEW",
            "reviewer": None,
            "audit_comment": None,
            "published_version_id": None,
            "indexed_chunk_count": 0,
            "audit_logs": [f"【流程发起】创建知识沉淀编排流，单号: {thread_id}"]
        }

        # 真正调用 LangGraph compiled app.invoke 驱动有向图流转
        self.app.invoke(initial_state, config=config)

        # 获取执行完成或挂起后的快照状态
        snapshot = self.app.get_state(config)
        is_paused = bool(snapshot.next)
        current_node = snapshot.next[0] if snapshot.next else END
        ckpt_id = snapshot.config["configurable"].get("checkpoint_id", f"ckpt_{uuid.uuid4().hex[:8]}")

        # 提取原生 interrupt 挂起载荷
        interrupt_payload = None
        if snapshot.tasks:
            for task in snapshot.tasks:
                if task.interrupts:
                    interrupt_payload = task.interrupts[0].value
                    break

        self._sync_mysql_mirror(
            thread_id=thread_id,
            checkpoint_id=ckpt_id,
            state=snapshot.values,
            next_node=current_node,
            interrupted=is_paused,
            interrupt_value=interrupt_payload
        )

        return {
            "thread_id": thread_id,
            "checkpoint_id": ckpt_id,
            "is_paused": is_paused,
            "current_node": current_node,
            "interrupt_payload": interrupt_payload,
            "state": snapshot.values
        }

    def get_pending(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """获取当前挂起的中断审核任务信息 (从 LangGraph get_state 读取，支持多模态容灾)。"""
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = self.app.get_state(config)

        # 1. 优先从 LangGraph 原生快照状态中解析挂起任务
        if snapshot and snapshot.next:
            interrupt_payload = None
            if snapshot.tasks:
                for task in snapshot.tasks:
                    if task.interrupts:
                        interrupt_payload = task.interrupts[0].value
                        break

            # 若中断任务已保存或经过 Time-Travel 重建，但 task.interrupts 暂未回填，从快照状态中自动组装待审卡片
            if not interrupt_payload and snapshot.values:
                s = snapshot.values
                interrupt_payload = {
                    "title": "📋 待发布知识终审工单",
                    "candidate_id": s.get("candidate_id"),
                    "knowledge_title": s.get("title"),
                    "category_id": s.get("category_id"),
                    "risk_level": s.get("risk_level"),
                    "is_duplicate": s.get("is_duplicate"),
                    "duplicate_reference": s.get("duplicate_reference"),
                    "summary": s.get("summary"),
                    "resolution_steps": s.get("resolution_steps"),
                    "contains_injection": s.get("contains_injection"),
                    "prompt": "请知识库管理员审阅并裁决：通过(APPROVED) 或 驳回(REJECTED)"
                }

            ckpt_id = snapshot.config["configurable"].get("checkpoint_id", "")
            return {
                "thread_id": thread_id,
                "checkpoint_id": ckpt_id,
                "current_node": snapshot.next[0],
                "interrupt_payload": interrupt_payload,
                "state": snapshot.values,
                "created_at": datetime.now().isoformat()
            }

        # 2. 如果本地 SQLite 无该线程但配置了 MySQL Checkpointer，回退查验远程共享库
        if self.mysql_mirror:
            try:
                ckpt = self.mysql_mirror.get_latest_checkpoint(thread_id)
                if ckpt and ckpt.get("interrupted"):
                    return {
                        "thread_id": thread_id,
                        "checkpoint_id": ckpt["checkpoint_id"],
                        "current_node": ckpt["next_node"],
                        "interrupt_payload": ckpt.get("interrupt_value"),
                        "state": ckpt["state"],
                        "created_at": ckpt.get("created_at")
                    }
            except Exception:
                pass

        return None

    def resume(self, thread_id: str, decision: KnowledgeReviewDecision) -> Dict[str, Any]:
        """唤醒中断节点，注入审批裁决数据继续流转 (通过 LangGraph 原生 Command(resume=...) 执行)。"""
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = self.app.get_state(config)
        if not snapshot or not snapshot.values:
            raise RuntimeError(f"未找到该会话的历史快照: {thread_id}")
        if not snapshot.next:
            raise RuntimeError(f"该会话当前未处于挂起中断状态，无需恢复: {thread_id}")

        resume_payload = {
            "action": decision.action,
            "approver": decision.approver,
            "comment": decision.comment,
            "modified_title": decision.modified_title,
            "modified_steps": decision.modified_steps
        }

        # 真正通过 LangGraph 原生 Command 唤醒
        self.app.invoke(Command(resume=resume_payload), config=config)

        final_snapshot = self.app.get_state(config)
        is_paused = bool(final_snapshot.next)
        current_node = final_snapshot.next[0] if final_snapshot.next else END
        ckpt_id = final_snapshot.config["configurable"].get("checkpoint_id", f"ckpt_{uuid.uuid4().hex[:8]}")

        self._sync_mysql_mirror(
            thread_id=thread_id,
            checkpoint_id=ckpt_id,
            state=final_snapshot.values,
            next_node=current_node,
            interrupted=is_paused,
            interrupt_value=None
        )

        return {
            "thread_id": thread_id,
            "checkpoint_id": ckpt_id,
            "is_paused": is_paused,
            "current_node": current_node,
            "interrupt_payload": None,
            "state": final_snapshot.values
        }

    def get_history(self, thread_id: str) -> List[Dict[str, Any]]:
        """Time-Travel 核心：获取全生命周期快照历史版本链 (通过 LangGraph get_state_history 获取)。"""
        config = {"configurable": {"thread_id": thread_id}}
        history = []
        for s in self.app.get_state_history(config):
            interrupt_val = None
            if s.tasks:
                for task in s.tasks:
                    if task.interrupts:
                        interrupt_val = task.interrupts[0].value
                        break
            ckpt_id = s.config["configurable"].get("checkpoint_id", "")
            # 准确判定：只有真正抵达 admin_review_node 人机复核或持有中断载荷的快照，才属于中断挂起 (HITL Interrupt)
            is_paused_node = (s.next and s.next[0] == "admin_review_node") or bool(interrupt_val)
            history.append({
                "thread_id": thread_id,
                "checkpoint_id": ckpt_id,
                "next_node": s.next[0] if s.next else END,
                "interrupted": is_paused_node,
                "interrupt_value": interrupt_val,
                "state": s.values,
                "created_at": datetime.now().isoformat()
            })
        return history

    def time_travel_patch(self, thread_id: str, checkpoint_id: str, patch_values: Dict[str, Any]) -> Dict[str, Any]:
        """Time-Travel 核心：对指定历史快照注入热修补数据 (通过 LangGraph 原生 update_state 实施)。"""
        config = {"configurable": {"thread_id": thread_id}}
        target_config = None
        for s in self.app.get_state_history(config):
            if s.config["configurable"].get("checkpoint_id") == checkpoint_id:
                target_config = s.config
                break

        if not target_config:
            target_config = {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_id": checkpoint_id,
                    "checkpoint_ns": ""
                }
            }

        patch_dict = copy.deepcopy(patch_values)
        if "audit_logs" not in patch_dict:
            patch_dict["audit_logs"] = [f"【Time-Travel 热修补】针对历史快照 [{checkpoint_id}] 实施数据纠偏"]

        # 真正使用 LangGraph update_state 更新状态
        new_config = self.app.update_state(target_config, values=patch_dict)

        # 核心：使用 LangGraph 原生 invoke(None, config=new_config) 进行分叉重放！
        self.app.invoke(None, config=new_config)

        # 读取重放后最新的快照
        latest_config = {"configurable": {"thread_id": thread_id}}
        snapshot = self.app.get_state(latest_config)
        is_paused = bool(snapshot.next)
        current_node = snapshot.next[0] if snapshot.next else END
        ckpt_id = snapshot.config["configurable"].get("checkpoint_id", checkpoint_id)

        interrupt_payload = None
        if snapshot.tasks:
            for task in snapshot.tasks:
                if task.interrupts:
                    interrupt_payload = task.interrupts[0].value
                    break

        # 核心增强：若任务处于 admin_review_node 挂起且载荷未填，从当前快照 state 中自动组装审阅卡片
        if not interrupt_payload and snapshot.values and is_paused and current_node == "admin_review_node":
            s = snapshot.values
            interrupt_payload = {
                "title": "📋 待发布知识终审工单",
                "candidate_id": s.get("candidate_id"),
                "knowledge_title": s.get("title"),
                "category_id": s.get("category_id"),
                "risk_level": s.get("risk_level"),
                "is_duplicate": s.get("is_duplicate"),
                "duplicate_reference": s.get("duplicate_reference"),
                "summary": s.get("summary"),
                "resolution_steps": s.get("resolution_steps"),
                "contains_injection": s.get("contains_injection"),
                "prompt": "请知识库管理员审阅并裁决：通过(APPROVED) 或 驳回(REJECTED)"
            }

        self._sync_mysql_mirror(
            thread_id=thread_id,
            checkpoint_id=ckpt_id,
            state=snapshot.values,
            next_node=current_node,
            interrupted=is_paused,
            interrupt_value=interrupt_payload
        )

        return {
            "thread_id": thread_id,
            "checkpoint_id": ckpt_id,
            "is_paused": is_paused,
            "current_node": current_node,
            "interrupt_payload": interrupt_payload,
            "state": snapshot.values
        }


def build_knowledge_flow_app(checkpointer: Optional[BaseFlowCheckpointer] = None) -> KnowledgeFlowEngine:
    """工厂方法：构建知识沉淀编排引擎实例。"""
    return KnowledgeFlowEngine(checkpointer=checkpointer)
