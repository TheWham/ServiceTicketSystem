# -*- coding: utf-8 -*-
"""long_task_worker.py

================================================================================
核心模块六：长任务异步化与 HMAC-SHA256 安全回调 (Celery + Redis + Webhook)
================================================================================

【架构定位与工业场景】
在现代企业级 AI 中台与 IT 智能服务台治理中，存在两类截然不同的业务负载：
1. 短响应流式交互：如 FAQ 问答、表单查询，通常要求 TTFT < 1.0s，由网关 SSE 实时流式吐出；
2. 批量与复杂计算长任务：如部门月度合规全量审计、跨系统日志关联对齐、千万级 Token 离线全量评估，
   这类任务耗时通常在 30 秒至 15 分钟不等。若依然采用 HTTP 同步挂起，会导致：
   - 接入层 Nginx / ALB 代理网关触发 60s 504 Gateway Timeout；
   - 客户端连接池占满、连接异常重置或客户端主动断开；
   - 服务端任务失去宿主而僵死或重复执行，造成算力与 Token 预算严重浪费。

【核心设计规范与工程方案】
本模块基于异步解耦黄金标准实现以下关键机制：
1. 202 Accepted 模式与状态机：
   - 客户端提交长任务请求后，网关在 50ms 内完成鉴权与任务合法性校验；
   - 异步投递至分布式任务队列（Broker），立即向客户端返回 HTTP 202 Accepted 与全局唯一 task_id；
   - 客户端可通过轮询 GET /tasks/{task_id} 或挂载 WebSocket 获取执行状态。
2. Celery 生产级可靠性调优：
   - task_acks_late=True：后置确认机制（At-least-once Delivery）。任务只有在彻底执行完毕后才向
     Broker 发送 ACK；若 Worker 意外崩溃（如 OOM、宿主机宕机），未 ACK 的任务将自动重新投递，避免丢单；
   - worker_prefetch_multiplier=1：非贪婪公平调度。长任务严禁批量预取（Prefetch），防止某单个 Worker
     囤积多个重负载长任务导致饥饿与负载倾斜；
   - task_soft_time_limit (840s) 与 task_time_limit (900s)：软/硬超时双保险。软超时触发时 Worker 会抛出
     SoftTimeLimitExceeded 异常，允许业务代码捕获并优雅清理锁资源与部分中间件持久化；硬超时则强制发送 SIGKILL。
3. HMAC-SHA256 签名与全链路防重放安全协议：
   - 签名公式：Signature = HMAC-SHA256(SecretKey, Timestamp + "." + CanonicalBody)；
   - 防重放攻击窗口：服务端与回调接收方严格校验 |T_current - T_req| <= 300s（5分钟漂移窗口）；
   - 防时序侧信道攻击：签名比对必须采用常量时间比较函数（hmac.compare_digest）。
4. Webhook 投递幂等与自适应重试：
   - 失败自动指数退避：retry_backoff=True + retry_jitter=True，规避网络抖动与接收端突发雪崩；
   - 幂等投递标识：请求头注入 X-FDE-Delivery-Id，接收方可基于 Redis SETNX 或数据库唯一键做天然幂等去重。

【生产运行方式】
  celery -A long_task_worker worker --loglevel=info --concurrency=4
【本地单机与离线自检模式】
  CELERY_EAGER=1 python long_task_worker.py
"""

import hashlib
import hmac
import json
import os
import sys
import time
from typing import Optional

# 统一 Windows/Linux 控制台 UTF-8 输出，防止乱码
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
    # 轻量模拟 Celery 对象，确保无 celery 依赖的环境下也能离线通过代码自检
    class MockTask:
        """Celery Task 模拟桩：支持 delay() 同步降级调用与 request 上下文模拟"""
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
        """Celery 模拟容器：提供基本的 conf 与 task 装饰器接口"""
        def __init__(self, name, broker=None, backend=None):
            self.conf = {}

        def task(self, *dargs, **dkwargs):
            def decorator(fn):
                return MockTask(fn, dkwargs.get("name", fn.__name__))
            return decorator

# ==============================================================================
# 1. Celery 基础配置与长任务专用策略
# ==============================================================================

# CELERY_EAGER:
#   若设置为 '1'，则任务在调用 delay() 时在当前进程同步执行，无需真实启动 Redis 与 Worker 进程。
#   在 CI/CD 单元测试、本地轻量自检或沙箱演示环境中极为实用。
EAGER = os.getenv("CELERY_EAGER", "1") == "1"
BROKER_URL = "memory://" if EAGER else os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
RESULT_BACKEND = "cache+memory://" if EAGER else os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

# Webhook 签名专用对称密钥：生产环境应通过 HashiCorp Vault、AWS KMS 或 K8s Secret 动态挂载
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "it-service-desk-fde-secret-2026").encode("utf-8")

# 初始化 Celery 分布式任务实例
celery_app = Celery("fde_long_tasks", broker=BROKER_URL, backend=RESULT_BACKEND)

# 写入生产级关键长任务策略参数
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,        # 任务被 Worker 拾取开始执行时，将状态标定为 STARTED，方便前端监控
    task_acks_late=True,            # 执行完成后才 ACK：Worker 崩溃/OOM 后任务自动重新投递，保障 At-least-once
    worker_prefetch_multiplier=1,   # 长任务不预取，Worker 每次只从 Broker 拿取 1 个任务，保障集群负载绝对均衡
    task_soft_time_limit=840,       # 软超时 (14 分钟)：向任务抛出 SoftTimeLimitExceeded，允许安全保存断点
    task_time_limit=900,            # 硬超时 (15 分钟)：向任务工作进程强发 SIGKILL，杜绝孤儿死锁
    result_expires=86400,           # 异步执行结果在 Redis / Backend 中保留 24 小时供轮询查询与追溯
    task_always_eager=EAGER,        # 同步化开关
    task_eager_propagates=EAGER,    # 同步模式下异常直接向上抛出
    task_store_eager_result=EAGER,  # 本地自检时写入内存结果后端，便于状态追踪
)

# ==============================================================================
# 2. Webhook 签名算法：HMAC-SHA256(timestamp + "." + body)
# ==============================================================================

def sign_payload(body: bytes, timestamp: str) -> str:
    """生成带有时间戳绑定的 HMAC-SHA256 防伪造防篡改签名。

    【算法原理】
    若仅对 body 计算 HMAC，恶意攻击者拦截到旧报文后可随时重放；
    将 UNIX Epoch 时间戳与 body 按照规范连接为 `Timestamp.Body`，并以共享密钥做 HMAC 计算：
      HMAC-SHA256(SecretKey, Timestamp + "." + Body)
    保证了不仅报文内容不可篡改，且请求产生的时间点也具备不可逆的数学约束。

    Args:
        body: Webhook 请求体原始字节序列 (JSON 序列化后的 bytes)
        timestamp: 产生请求时的 UNIX Epoch 时间戳字符串 (秒级，例如 "1793760000")

    Returns:
        64 位 16 进制小写散列摘要字符串
    """
    payload_to_sign = timestamp.encode("utf-8") + b"." + body
    return hmac.new(WEBHOOK_SECRET, payload_to_sign, hashlib.sha256).hexdigest()


def verify_signature(body: bytes, timestamp: str, signature: str, tolerance_s: int = 300) -> bool:
    """接收端签名安全核验：时钟防重放（5分钟漂移窗口）+ 常量时间比对防时序侧信道攻击。

    【两道关键防线】
    1. 时间窗口防重放：
       校验当前物理时间与请求时间戳的绝对差值：
         |now_ts - req_ts| <= tolerance_s (默认 300 秒)
       即使攻击者捕获了带有合法签名的网络报文，在 5 分钟之后重放该请求，也将被直接拦截；
    2. 常量时间字符串比对：
       直接使用 `==` 进行字符串比较会导致比对耗时因前缀命中长度不同而产生微小差异，
       攻击者可利用网络往返耗时测量逐步暴力推测出签名；`hmac.compare_digest` 确保无论命中多少位，
       计算耗时均严格一致，杜绝时序攻击。

    Args:
        body: 接收到的 HTTP 请求体原始字节流
        timestamp: 标头中携带的 X-FDE-Timestamp 时间戳字符串
        signature: 标头中携带的 X-FDE-Signature 签名值
        tolerance_s: 允许的最大时间漂移误差窗口（秒），默认 300 秒（5 分钟）

    Returns:
        bool: 签名合法且未过期返回 True，否则返回 False
    """
    try:
        now_ts = int(time.time())
        req_ts = int(timestamp)
        # 第一道防线：时钟漂移检查（防重放攻击）
        if abs(now_ts - req_ts) > tolerance_s:
            return False
    except (ValueError, TypeError):
        return False

    # 本地基于相同密钥与输入重新计算期望签名
    expected = sign_payload(body, timestamp)

    # 第二道防线：常量时间比对（防时序侧信道攻击）
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
    """IT 智能中台月度合规稽核长任务：演示阶段化流转、进度动态上报与回调联动。

    【设计亮点】
    1. bind=True：将当前任务执行实例 (self) 注入到函数中，可访问 self.request.id 与执行状态；
    2. 自定义 PROGRESS 状态上报：
       长任务不能长时间无声无息。每个阶段执行完后调用 self.update_state() 刷新元数据，
       前端用户轮询 GET /tasks/{task_id} 即可看到具体推进到了第几步与进度百分比；
    3. 任务编排与解耦：
       任务执行完成后，如果提供了 callback_url，不直接在当前任务中阻塞发起 HTTP 请求，
       而是通过 `deliver_webhook.delay()` 派发独立的投递任务，实现计算执行与网络投递的物理隔离。

    Args:
        self: Celery 任务绑定上下文实例
        dept_id: 待审计部门编号（如 "DEPT-OPS", "DEPT-FINANCE"）
        month: 审计归档月份（如 "2026-10"）
        callback_url: 外部系统接收审计完成通知的 Webhook 地址
        step_seconds: 模拟每个复杂步骤的耗时（秒）

    Returns:
        dict: 结构化的审计分析报告结果
    """
    total_steps = len(AUDIT_STEPS)
    # 模拟多阶段执行，实时更新任务状态机
    for idx, step in enumerate(AUDIT_STEPS, 1):
        pct = int(idx / total_steps * 100)
        # 将中间状态更新至 Celery Result Backend (Redis / Mem)
        self.update_state(state="PROGRESS", meta={"step": step, "progress": pct})
        time.sleep(step_seconds)

    # 模拟生成的真实审计结果明细
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

    # 若指定了回调地址，派发异步 Webhook 投递任务
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
    autoretry_for=(requests.RequestException,),  # 遇到网络瞬断、5xx 错误时自动捕获重试
    retry_backoff=True,                          # 开启指数退避（2s, 4s, 8s, 16s...）
    retry_backoff_max=600,                       # 最大退避重试间隔不超过 10 分钟
    retry_jitter=True,                           # 引入随机抖动 Jitter，防止大量并发重试同时击穿下游服务
    max_retries=6,                               # 最大重试次数 6 次
)
def deliver_webhook(self, url: str, payload: dict) -> int:
    """高可靠 Webhook 投递任务：具备防重放、不可篡改、幂等标头与网络退避自愈能力。

    【企业级 Webhook 请求头协议】
    - Content-Type: application/json
    - X-FDE-Event: 业务事件名，如 report.completed
    - X-FDE-Delivery-Id: 投递全局唯一流水号，接收方用作去重主键（幂等保证）
    - X-FDE-Timestamp: 发起请求的秒级 UNIX 时间戳，用于 5 分钟窗口校验
    - X-FDE-Signature: HMAC-SHA256(SecretKey, Timestamp + "." + Body) 签名密文

    Args:
        self: Celery 任务上下文（用于管理重试状态）
        url: 接收回调通知的目标 HTTP(S) URL
        payload: 回调通知数据字典

    Returns:
        int: HTTP 响应状态码（成功通常为 200 或 204）

    Raises:
        requests.RequestException: 当 HTTP 发生 4xx/5xx 或网络超时错误时抛出，触发 Celery 重试机制
    """
    # 保证字典以规范化有序方式序列化，防止键顺序变动导致验签失败
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ts = str(int(time.time()))

    # 装配企业级安全回调标头
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
# 5. 本地单机与离线自检验证
# ==============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("⏳ Day 29 长任务异步化：Celery + Webhook 签名回调本地自检")
    print("=" * 80)

    # 1. 提交异步任务
    async_res = generate_monthly_audit_report.delay("DEPT-OPS", "2026-10", None, 0.1)
    print(f"▶️ 已提交异步长任务 task_id = {async_res.id}")

    report = async_res.get(timeout=30)
    print(f"✅ 任务执行成功，状态: {async_res.state} | 违规稽核项数: {len(report['violations'])}")
    for v in report["violations"]:
        print(f"   • 工单 [{v['ticket_id']}] 人员: {v['employee']} | 违规: {v['rule']} → 处理: {v['action']}")

    # 2. 签名安全协议测试
    body = json.dumps({"task_id": async_res.id}, sort_keys=True).encode("utf-8")
    ts = str(int(time.time()))
    sig = sign_payload(body, ts)

    print("-" * 60)
    print(f"🔐 1. 合法签名校验:      {verify_signature(body, ts, sig)} (预期 True)")
    print(f"🔐 2. 篡改报文校验:      {verify_signature(body + b'tampered', ts, sig)} (预期 False)")
    expired_ts = str(int(ts) - 600)  # 10 分钟前
    print(f"🔐 3. 超过 5 分钟防重放: {verify_signature(body, expired_ts, sign_payload(body, expired_ts))} (预期 False)")
    print("=" * 80)
