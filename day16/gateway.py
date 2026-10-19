# -*- coding: utf-8 -*-
"""ExternalAPIGateway — 外部 RESTful API 契约调用网关（超时 + 指数退避 + 抖动）。

对齐讲义第三篇「外部 API 封装的网络韧性设计」：基于「网络必定会抖动、下游随时可能
超时或崩溃」的零信任假设，对外部协同系统接口做三件防护——
  1. 超时硬约束（timeout_sec，模拟层用随机延时模拟网络开销）；
  2. 指数退避加抖动（Backoff + Jitter）：Sleep = 2^attempt * base + random；
  3. 熔断降级（重试耗尽后返回标准故障信息，而非抛异常中断 Agent）。

演示版用 `time.sleep` + 随机概率模拟下游 504 超时；生产环境应替换为 `httpx` /
`requests` 带 `timeout=` 与重试装饰器的真实调用（如调用 it-ticket-cloud 的
ticket-service 升级接口），协议与结构保持一致。
"""

import random
import time
from typing import Any, Dict


class ExternalAPIGateway:
    """外部业务 API 防御网关：针对工单升级/加急协同提供带超时硬约束与指数退避重试的调用保护。"""

    @staticmethod
    def call_ticket_escalation_api(
        payload: Dict[str, Any], max_retries: int = 3, timeout_sec: float = 2.0
    ) -> Dict[str, Any]:
        """模拟调用外部协同系统的工单升级 RESTful 接口（带重试韧性）。"""
        start_t = time.time()
        attempt = 0

        while attempt < max_retries:
            attempt += 1
            try:
                # 模拟网络调用耗时
                simulated_latency = 0.04 + random.uniform(0.01, 0.05)
                time.sleep(simulated_latency)

                # 模拟偶发网络抖动（15% 概率触发首轮 504，用于演示重试）
                if attempt == 1 and random.random() < 0.15:
                    raise TimeoutError("下游协同系统网关响应超时 (HTTP 504 Gateway Timeout)")

                # 成功提交升级申请
                return {
                    "status_code": 200,
                    "success": True,
                    "escalation_id": f"ESC-{int(time.time())}-{random.randint(100, 999)}",
                    "ticket_id": payload.get("ticket_id"),
                    "target_priority": payload.get("target_priority"),
                    "message": "已成功提交工单升级申请至协同系统，等待值班组长复核。",
                    "retry_attempts": attempt - 1,
                    "elapsed_ms": round((time.time() - start_t) * 1000, 1)
                }

            except TimeoutError as te:
                if attempt >= max_retries:
                    # 熔断降级：重试耗尽返回标准故障信息（Agent 据此反思而非崩溃）
                    return {
                        "status_code": 504,
                        "success": False,
                        "error": f"多次重试后仍然超时：{str(te)}",
                        "retry_attempts": attempt - 1,
                        "elapsed_ms": round((time.time() - start_t) * 1000, 1)
                    }
                # 指数退避加抖动 (Backoff + Jitter)
                sleep_time = (2 ** attempt) * 0.08 + random.uniform(0.01, 0.04)
                time.sleep(sleep_time)

        # 理论上不可达（while 内已 return），防御性兜底
        return {"status_code": 504, "success": False,
                "error": "未知网关故障", "retry_attempts": max_retries,
                "elapsed_ms": round((time.time() - start_t) * 1000, 1)}
