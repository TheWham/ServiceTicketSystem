# -*- coding: utf-8 -*-
"""取数：ticket-service 只读投影扫描接口的客户端。

**架构 8.1：工单是 ticket-service 的事实源，其他服务不得跨库读 ticket 表。**
所以这里走 HTTP，不直连 MySQL —— 与 `agent_service/tools.py` 的取数方式一致。

接口职责边界（与聚合职责严格分开）：
  Java 侧  只按时间窗过滤、返回脱敏明细，**不做 GROUP BY**
  Python 侧 去噪、剥离模板、词表抽取、聚合

为什么不让 Java 用 SQL 聚合：库里存的是**未清洗**原始工单，`GROUP BY category_id`
会把 test/123 联调单算进分母；且 SQL 无法按 `configs/taxonomy.yaml` 的词表去按症状
分组。几百行脱敏文本在内存里跑一次词表匹配只需几毫秒，换来的是 excluded 剔除口径
与双分母**绝对一致**。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

import httpx

from . import config as cfg
from .contract import TicketRow
from .timewindow import Window


class DataSource(Protocol):
    """取数抽象。链路只依赖这个协议，不关心背后是 HTTP 还是 fixture。"""

    def scan_tickets(self, window: Window, category: str = "") -> List[TicketRow]:
        ...


class ScanError(RuntimeError):
    """取数失败。**不静默回退**：区分「失败」与「正常空结果」，让上游能如实降级。"""


class HttpDataSource:
    """ticket-service 内部接口客户端。

    `category` 槽位：接口保留了它，但**分析链路默认不传** —— 子域过滤走词表而不是
    分类（实测唯一那张打印机工单的 `category_id` 是 `C_HW_PC`，按分类过滤会静默
    丢数据）。保留参数仅用于接口通用能力与单测验收。
    """

    def __init__(self, base_url: Optional[str] = None, user_id: str = "", role: str = "",
                 request_id: str = "", timeout: Optional[float] = None):
        self.base_url = (base_url if base_url is not None else cfg.TICKET_SERVICE_BASE_URL).rstrip("/")
        self.user_id = user_id
        self.role = role
        self.request_id = request_id
        self.timeout = timeout or cfg.SCAN_TIMEOUT

    def scan_tickets(self, window: Window, category: str = "") -> List[TicketRow]:
        if not self.base_url:
            raise ScanError("工单系统未配置（ANALYTICS_TICKET_BASE_URL）")

        params: Dict[str, Any] = {
            "created_after": window.start_iso,
            "created_before": window.end_iso,
            "limit": cfg.SCAN_MAX_ROWS,
        }
        # 槽位白名单式传参：只有显式给出才带上，空串一律不发 —— 避免
        # "category=" 这种空槽位传到下游被当成过滤条件。
        if category.strip():
            params["category"] = category.strip()

        headers = {"X-User-Id": self.user_id, "X-User-Role": self.role}
        if self.request_id:
            # 下游强制要求的透传头，缺失即 400；链路靠它跨进程串起来。
            headers["X-Request-Id"] = self.request_id

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(f"{self.base_url}/api/internal/tickets/analytics/scan",
                                  params=params, headers=headers)
                if resp.status_code != 200:
                    # 带上响应体片段：缺头/校验失败这类问题只在 body 里说得清。
                    raise ScanError(f"投影扫描 HTTP {resp.status_code}: {resp.text[:300]}")
                body = resp.json()
        except ScanError:
            raise
        except Exception as e:  # noqa: BLE001
            raise ScanError(f"工单系统暂时不可用: {type(e).__name__}: {e}") from e

        # ticket-service 的成功包络是 {"code": 0, "msg": ...}（Result）。
        code = body.get("code") if isinstance(body, dict) else None
        if code != 0:
            raise ScanError(f"下游业务错误 code={code!r}")
        data = body.get("data")
        items = data if isinstance(data, list) else (data or {}).get("items") or []
        return [TicketRow.from_dict(i) for i in items]


class FixtureDataSource:
    """离线 fixture 取数（单测与纯确定性演示用，不联网）。

    刻意与 `HttpDataSource` 同协议而不是打个桩返回 `[]`：链路的降级分支要能在
    离线状态下一路跑到 Node E，否则那些分支只会是"从没被执行过的死代码"。
    """

    def __init__(self, rows: List[TicketRow], *, fail: Optional[str] = None):
        self._rows = list(rows)
        self._fail = fail

    @classmethod
    def from_json(cls, path: Path, **kwargs: Any) -> "FixtureDataSource":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        items = raw if isinstance(raw, list) else raw.get("tickets") or []
        return cls([TicketRow.from_dict(i) for i in items], **kwargs)

    def scan_tickets(self, window: Window, category: str = "") -> List[TicketRow]:
        if self._fail:
            raise ScanError(self._fail)
        if not category.strip():
            return list(self._rows)
        return [r for r in self._rows if r.category_id == category.strip()]


def dump_rows(rows: List[TicketRow], path: Path) -> None:
    """把扫描结果落盘（调试与 unmatched 回捞用）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [{"ticketId": r.ticket_id, "categoryId": r.category_id, "title": r.title,
                "description": r.description, "createdAt": r.created_at} for r in rows]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")