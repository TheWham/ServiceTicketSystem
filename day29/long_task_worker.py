# -*- coding: utf-8 -*-
"""long_task_worker.py

Day 29 Celery + Redis 长任务异步执行与 HMAC 签名 Webhook 回调套件。
用于执行部门月度合规稽核、复杂报表与高耗时推理长任务（3~10 分钟）：
1. 202 Accepted 模式：任务异步投递，解耦 HTTP 连接，避免网关 60s 504 超时；
2. 进度上报：Celery 自定义状态 PROGRESS 实时上报执行百分比；
3. Webhook 签名与防重放：HMAC-SHA256(secret, timestamp + "." + body)，5 分钟过期窗口；
4. 容灾与幂等：指数退避重试 (最多 6 次) + X-FDE-Delivery-Id 幂等去重。

生产运行方式：
  celery -A long_task_worker worker --loglevel=info --concurrency=4
无 Redis 环境的本地自检（当前进程同步执行）：
  CELERY_EAGER=1 python long_task_worker.py
"""

import hashlib
import hmac
import json
import os
import sys
import time
from typing import Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import requests

try:
    from celery import Celery
    HAS_CELERY = True
except ImportError:
    HAS_CELERY = False
    # 轻量模拟 Celery 对象，确保无 celery 依赖下也能离线自检
    class MockTask:
        def __init__(self, fn, name):
            self.fn = fn
            self.name = name
            self.request = type("Req", (), {"id": f"mock-task-{int(time.time())}"})()
        def delay(self, *args, **kwargs):
            res = self.fn(self, *args, **kwargs)
            return type("AsyncRes", (), {
                "id": self.request.id,
                "state": "SUCCESS",
                "result": res,
                "get": lambda self, timeout=None: res
            })()
        def update_state(self, state, meta):
            pass

    class Celery:
        def __init__(self, name, broker=None, backend=None):
            self.conf = {}
        def task(self, *dargs, **dkwargs):
            def decorator(fn):
                return MockTask(fn, dkwargs.get("name", fn.__name__))
            return decorator

# ==============================================================================
# 1. Celery 基础配置与长任务专用策略
# ==============================================================================

EAGER = os.getenv("CELERY_EAGER", "1") == "1"
BROKER_URL = "memory://" if EAGER else os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
RESULT_BACKEND = "cache+memory://" if EAGER else os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "it-service-desk-fde-secret-2026").encode("utf-8")

celery_app = Celery("fde_long_tasks", broker=BROKER_URL, backend=RESULT_BACKEND)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,            # 执行完成后才 ACK：Worker 崩溃后任务自动重新投递
    worker_prefetch_multiplier=1,   # 长任务不预取，避免单 Worker 囤积任务
    task_soft_time_limit=840,       # 软超时：抛 SoftTimeLimitExceeded，允许释放资源
    task_time_limit=900,            # 硬超时：强制终止进程
    result_expires=86400,           # 结果保留 24 小时供轮询查询
    task_always_eager=EAGER,
    task_eager_propagates=EAGER,
    task_store_eager_result=EAGER,  # 本地自检时写入结果后端，便于状态查询
)

# ==============================================================================
# 2. Webhook 签名算法：HMAC-SHA256(timestamp + "." + body)
# ==============================================================================

def sign_payload(body: bytes, timestamp: str) -> str:
    """生成防伪造签名"""
    payload_to_sign = timestamp.encode("utf-8") + b"." + body
    return hmac.new(WEBHOOK_SECRET, payload_to_sign, hashlib.sha256).hexdigest()


def verify_signature(body: bytes, timestamp: str, signature: str, tolerance_s: int = 300) -> bool:
    """接收方校验：时钟防重放（超出 300 秒拒绝）+ 常量时间比对防时序攻击"""
    try:
        now_ts = int(time.time())
        req_ts = int(timestamp)
        if abs(now_ts - req_ts) > tolerance_s:
            return False
    except (ValueError, TypeError):
        return False
    expected = sign_payload(body, timestamp)
    return hmac.compare_digest(expected, signature)


# ==============================================================================
# 3. 业务长任务：IT 服务台月度合规稽核报告 (耗时长任务)
# ==============================================================================

AUDIT_STEPS = [
    "拉取当月所有 IT 提权与特批工单记录",
    "逐单执行合规核验与越权判定",
    "关联生产库敏感变更与双人审批审计",
    "生成月度综合合规稽核 PDF 报告",
]


@celery_app.task(bind=True, name="reports.monthly_audit")
def generate_monthly_audit_report(
    self,
    dept_id: str,
    month: str,
    callback_url: Optional[str] = None,
    step_seconds: float = 0.5,
) -> dict:
    """模拟长任务逐单推理与进度动态上报"""
    total_steps = len(AUDIT_STEPS)
    for idx, step in enumerate(AUDIT_STEPS, 1):
        pct = int(idx / total_steps * 100)
        self.update_state(state="PROGRESS", meta={"step": step, "progress": pct})
        time.sleep(step_seconds)

    result = {
        "dept_id": dept_id,
        "month": month,
        "total_claims": 128,
        "violations": [
            {
                "employee": "张三",
                "rule": "核心生产库表结构未报备执行 ALTER 操作",
                "ticket_id": "IT-9011",
                "action": "通报批评并收回临时提权",
            },
            {
                "employee": "李四",
                "rule": "高危特批工单缺失 DBA 负责人带外复核签字",
                "ticket_id": "IT-9045",
                "action": "挂起复核",
            },
        ],
        "report_url": f"/reports/{dept_id}/{month}/audit_report.pdf",
    }

    if callback_url:
        deliver_webhook.delay(
            callback_url,
            {
                "event": "report.completed",
                "task_id": self.request.id,
                "result": result,
            },
        )
    return result


# ==============================================================================
# 4. Webhook 投递任务：带幂等 ID、指数退避重试与签名保护
# ==============================================================================

@celery_app.task(
    bind=True,
    name="webhooks.deliver",
    autoretry_for=(requests.RequestException,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=6,
)
def deliver_webhook(self, url: str, payload: dict) -> int:
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ts = str(int(time.time()))
    headers = {
        "Content-Type": "application/json",
        "X-FDE-Event": payload.get("event", "unknown"),
        "X-FDE-Delivery-Id": payload.get("task_id", ""),  # 接收方据此做幂等去重
        "X-FDE-Timestamp": ts,
        "X-FDE-Signature": sign_payload(body, ts),
    }
    resp = requests.post(url, data=body, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.status_code


# ==============================================================================
# 5. 本地自检验证
# ==============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("⏳ Day 29 长任务异步化：Celery + Webhook 签名回调本地自检")
    print("=" * 80)

    # 提交异步任务
    async_res = generate_monthly_audit_report.delay("DEPT-OPS", "2026-10", None, 0.1)
    print(f"▶️ 已提交异步长任务 task_id = {async_res.id}")

    report = async_res.get(timeout=30)
    print(f"✅ 任务执行成功，状态: {async_res.state} | 违规稽核项数: {len(report['violations'])}")
    for v in report["violations"]:
        print(f"   • 工单 [{v['ticket_id']}] 人员: {v['employee']} | 违规: {v['rule']} → 处理: {v['action']}")

    # 签名安全测试
    body = json.dumps({"task_id": async_res.id}, sort_keys=True).encode("utf-8")
    ts = str(int(time.time()))
    sig = sign_payload(body, ts)

    print("-" * 60)
    print(f"🔐 1. 合法签名校验:      {verify_signature(body, ts, sig)} (预期 True)")
    print(f"🔐 2. 篡改报文校验:      {verify_signature(body + b'tampered', ts, sig)} (预期 False)")
    expired_ts = str(int(ts) - 600)  # 10 分钟前
    print(f"🔐 3. 超过 5 分钟防重放: {verify_signature(body, expired_ts, sign_payload(body, expired_ts))} (预期 False)")
    print("=" * 80)
