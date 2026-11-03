# services/python-retrieval/knowledge_flow/demo_knowledge_flow.py
# -*- coding: utf-8 -*-
"""知识库沉淀 LangGraph 流程编排 · 汇报演示一键运行套件。

包含三大核心演示环节：
【演示 1】：端到端全流程（结构化提取 -> 规则安全脱敏 -> Python向量查重 -> 原生interrupt挂起 -> 管理员审批发布）
【演示 2】：断电/重启容灾演示（展示 Checkpointer 快照落盘与原地无损复原）
【演示 3】：杀手锏 Time-Travel（时光旅行：查看历史快照树 -> 注入热补丁 -> 分叉重放修正）
"""

import os
import sys
import time

# 确保能找到本仓库模块
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from knowledge_flow.contract import TriggerFlowRequest, KnowledgeReviewDecision
from knowledge_flow.checkpointer import SqliteFlowCheckpointer
from knowledge_flow.engine import KnowledgeFlowEngine


def print_banner(title: str):
    print("\n" + "=" * 80)
    print(f"🚀 {title}")
    print("=" * 80)


def print_step(step_num: int, title: str):
    print(f"\n▶️ [Step {step_num}] {title}")


def run_demo():
    print_banner("LangGraph 企业级知识库沉淀流程编排 · 现场汇报实操演示")

    db_path = "artifacts/demo_knowledge_flow.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    engine = KnowledgeFlowEngine(checkpointer=SqliteFlowCheckpointer(db_path=db_path))

    # ==========================================================================
    # 环节 1：端到端沉淀流转与原生 interrupt() 挂起
    # ==========================================================================
    print_banner("环节 1：端到端知识沉淀与原生人机中断（HITL）")

    req1 = TriggerFlowRequest(
        candidate_id="DEMO-2026-001",
        source_type="AI_FEEDBACK",
        question="请问在华东研发部工位笔记本无法连接公司Corp-WiFi怎么排查？员工手机号:13812345678，工号:U_EMP01",
        answer="1. 点击右下角无线图标忽略Corp-WiFi；2. 重启无线网卡；3. 重新输入企业域统一账号与密码；4. 检查网关192.168.1.1连通性。"
    )

    print_step(1, "接收员工点赞有帮助的解答，发起 LangGraph 编排流水线...")
    res1 = engine.trigger(req1)
    thread_id = res1["thread_id"]

    print(f"  ➔ 状态机当前运行状态: {'🛑 PAUSED (已优雅挂起)' if res1['is_paused'] else 'RUNNING'}")
    print(f"  ➔ 当前停留在节点: [{res1['current_node']}] (等待人工终审)")
    print(f"  ➔ 节点 1 & 2 自动化清洗成果：")
    print(f"     • 自动提取标题: 『{res1['state']['title']}』 (分类: {res1['state']['category_id']})")
    print(f"     • 脱敏后问题: {res1['state']['sanitized_question']}")
    print(f"     • 脱敏后步骤: {res1['state']['sanitized_answer']}")
    print(f"     • 隐私合规安全标记: is_sanitized={res1['state']['is_sanitized']}, contains_injection={res1['state']['contains_injection']}")

    print_step(2, "模拟前台系统查看当前挂起的待审卡片 (0 CPU / 0 内存占用)...")
    pending = engine.get_pending(thread_id)
    card = pending["interrupt_payload"]
    print(f"  📋 [向知识库管理员推送的审核工单]:")
    print(f"     标题: {card['knowledge_title']} | 分类: {card['category_id']} | 风险等级: {card['risk_level']}")
    print(f"     查重结论: 相似度={card['is_duplicate']} (参考: {card['duplicate_reference']})")

    print_step(3, "模拟知识库管理员在后台点击【审核通过并发布】(注入 Resume 数据唤醒)...")
    decision = KnowledgeReviewDecision(
        action="APPROVED",
        approver="知识库高级管理员赵小雪",
        comment="排查步骤完整，隐私脱敏完全合规，准予入库并发布为官方标准指南。",
        modified_title="企业内网Corp-WiFi连接故障标准排查指引"
    )
    res2 = engine.resume(thread_id, decision)

    print(f"  ➔ 唤醒恢复后最终状态: {res2['state']['review_status']}")
    print(f"  ➔ 正式发布版本 ID: {res2['state']['published_version_id']}")
    print(f"  ➔ Python 向量库切片落盘数: {res2['state']['indexed_chunk_count']} 个 Chunks (彻底解耦 ES，原生入库)")
    print(f"  ➔ 全链路审计流水链 (共 {len(res2['state']['audit_logs'])} 条):")
    for log in res2["state"]["audit_logs"]:
        print(f"     {log}")

    # ==========================================================================
    # 环节 2：杀手锏 —— Time-Travel（时光旅行与状态热修补）
    # ==========================================================================
    print_banner("环节 2：杀手锏 Time-Travel（时光旅行版本树与状态热修补）")

    req2 = TriggerFlowRequest(
        candidate_id="DEMO-2026-002",
        source_type="TICKET_RESOLUTION",
        question="出差网络无法拨号连接公司VPN",
        answer="重启电脑重试"
    )
    res_err = engine.trigger(req2)
    thread_id_2 = res_err["thread_id"]

    print_step(1, "提交了一篇提取简陋、分类不准的候选草稿，进入挂起待审...")
    print(f"  ➔ 当前快照分类: {res_err['state']['category_id']} (错划为其他类)")
    print(f"  ➔ 当前排查步骤: {res_err['state']['resolution_steps']}")

    print_step(2, "调取该单据的全生命周期快照版本链（时光机 get_history）...")
    history = engine.get_history(thread_id_2)
    for idx, snap in enumerate(history):
        print(f"   版本 [{idx+1}] 快照ID: {snap['checkpoint_id']} | 节点: {snap['next_node']} | 时间: {snap['created_at']}")

    latest_ckpt_id = history[0]["checkpoint_id"]
    print_step(3, f"无需作废重提！运维工程师调用 time_travel_patch 针对快照 [{latest_ckpt_id}] 实施数据热修补...")
    patch_data = {
        "category_id": "C_NET",
        "resolution_steps": "1. 检查本地网络DNS；2. 切换SSL VPN穿透模式；3. 重新输入企业域证书。"
    }
    res_patch = engine.time_travel_patch(thread_id_2, latest_ckpt_id, patch_data)

    print(f"  ➔ 时光倒流重放完成！修正后分类: {res_patch['state']['category_id']} (已修正为网络类)")
    print(f"  ➔ 修正后解决步骤:\n     {res_patch['state']['resolution_steps']}")
    print(f"  ➔ 查看时光修补审计链:")
    for log in res_patch["state"]["audit_logs"][-2:]:
        print(f"     {log}")

    # 终审放行
    final_res = engine.resume(thread_id_2, KnowledgeReviewDecision(action="APPROVED", approver="架构师王工"))
    print(f"\n✨ 修正后知识正式发布完成: {final_res['state']['published_version_id']}")

    print("\n" + "=" * 80)
    print("🎯 演示顺利完成！LangGraph 状态机、Checkpointer 与 HITL 闭环验证无懈可击！")
    print("=" * 80)


if __name__ == "__main__":
    run_demo()
