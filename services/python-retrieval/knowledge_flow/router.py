# services/python-retrieval/knowledge_flow/router.py
"""FastAPI 路由定义：知识库沉淀流程编排的 RESTful 接口。

直接挂载至现有的 Python 检索内核 (rag_service :8310)，避免多占端口，实现统一复用：
- POST /api/v1/knowledge-flow/trigger       : 接收候选案例并触发编排
- GET  /api/v1/knowledge-flow/pending/{id}  : 查询指定会话的挂起断点工单
- POST /api/v1/knowledge-flow/resume/{id}   : 人工审批决议注入并唤醒继续执行
- GET  /api/v1/knowledge-flow/history/{id}  : 检索全生命周期快照（Time-Travel 时光机）
- POST /api/v1/knowledge-flow/patch/{id}    : 注入状态热补丁并分叉重放
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List

from .contract import (
    TriggerFlowRequest,
    KnowledgeReviewDecision,
    TimeTravelPatchRequest,
    FlowResponse
)
from .engine import KnowledgeFlowEngine, build_knowledge_flow_app

# 默认全局单例引擎
_default_engine: KnowledgeFlowEngine = build_knowledge_flow_app()

router = APIRouter(prefix="/api/v1/knowledge-flow", tags=["knowledge-flow"])


def get_engine() -> KnowledgeFlowEngine:
    return _default_engine


@router.post("/trigger", response_model=FlowResponse)
def trigger_flow(req: TriggerFlowRequest, engine: KnowledgeFlowEngine = Depends(get_engine)):
    """发起知识库沉淀流转。"""
    res = engine.trigger(req)
    return FlowResponse(
        code=0,
        message="flow triggered",
        thread_id=res["thread_id"],
        status="PAUSED" if res.get("is_paused") else "COMPLETED",
        is_paused=res.get("is_paused", False),
        current_node=res.get("current_node"),
        state=res.get("state"),
        interrupt_payload=res.get("interrupt_payload")
    )


@router.get("/pending/{thread_id}")
def get_pending_task(thread_id: str, engine: KnowledgeFlowEngine = Depends(get_engine)):
    """获取当前挂起的中断终审任务详情。"""
    task = engine.get_pending(thread_id)
    if task:
        return {"code": 0, "message": "success", "data": task}

    # 若未找到挂起任务，排查历史版本树并给出明确业务诊断原因，避免冷冰冰的无意义 404
    history = engine.get_history(thread_id)
    if history:
        latest_status = history[0].get("state", {}).get("review_status")
        if latest_status == "APPROVED":
            raise HTTPException(
                status_code=404,
                detail=f"会话 [{thread_id}] 已于此前审核【通过】并发布入库，当前未处于挂起状态。如需查看，请点击「⏱️ 打开 Time-Travel 时光机」。"
            )
        elif latest_status == "REJECTED":
            raise HTTPException(
                status_code=404,
                detail=f"会话 [{thread_id}] 已被安全合规【驳回】归档，当前未处于挂起状态。"
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"会话 [{thread_id}] 当前状态为 [{latest_status}]，不在等待人工审批的挂起点。"
            )

    raise HTTPException(status_code=404, detail=f"Checkpointer 数据库中未找到会话 [{thread_id}]，请确认单号是否输入正确。")


@router.post("/resume/{thread_id}", response_model=FlowResponse)
def resume_flow(thread_id: str, decision: KnowledgeReviewDecision, engine: KnowledgeFlowEngine = Depends(get_engine)):
    """管理员审批裁决恢复流转。"""
    try:
        res = engine.resume(thread_id, decision)
        return FlowResponse(
            code=0,
            message="flow resumed and finished",
            thread_id=res["thread_id"],
            status="PAUSED" if res.get("is_paused") else "COMPLETED",
            is_paused=res.get("is_paused", False),
            current_node=res.get("current_node"),
            state=res.get("state"),
            interrupt_payload=res.get("interrupt_payload")
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/history/{thread_id}")
def get_flow_history(thread_id: str, engine: KnowledgeFlowEngine = Depends(get_engine)):
    """Time-Travel 接口：查询该工单的全生命周期版本快照树。"""
    history = engine.get_history(thread_id)
    return {
        "code": 0,
        "message": "success",
        "thread_id": thread_id,
        "total_versions": len(history),
        "history": history
    }


@router.post("/patch/{thread_id}", response_model=FlowResponse)
def time_travel_patch(thread_id: str, patch: TimeTravelPatchRequest, engine: KnowledgeFlowEngine = Depends(get_engine)):
    """Time-Travel 接口：针对特定历史快照打热补丁并分叉重放。"""
    try:
        res = engine.time_travel_patch(thread_id, patch.checkpoint_id, patch.patch_values)
        return FlowResponse(
            code=0,
            message="patched and replay initiated",
            thread_id=res["thread_id"],
            status="PAUSED" if res.get("is_paused") else "COMPLETED",
            is_paused=res.get("is_paused", False),
            current_node=res.get("current_node"),
            state=res.get("state"),
            interrupt_payload=res.get("interrupt_payload")
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
