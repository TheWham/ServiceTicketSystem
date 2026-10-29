# -*- coding: utf-8 -*-
"""把 TicketService/ExceptionQueueService/DispatchDraftService/RoutingService 等
本次改动涉及的文件按 tab=4 归一，用于纠正补丁工具造成的缩进漂移。

只处理本次会话新建或修改的文件；不动仓库其他人的改动。
"""
import io
import sys

FILES = [
    r"it-ticket-cloud\ticket-service\src\main\java\com\itticket\ticket\service\RoutingService.java",
    r"it-ticket-cloud\ticket-service\src\main\java\com\itticket\ticket\service\ExceptionQueueService.java",
    r"it-ticket-cloud\ticket-service\src\main\java\com\itticket\ticket\service\DispatchDraftService.java",
    r"it-ticket-cloud\ticket-service\src\main\java\com\itticket\ticket\entity\DispatchDraft.java",
]

ROOT = r"C:\Users\Admin\.wpscomate\agent\workspace\it-ticket-system"

for rel in FILES:
    p = ROOT + "\\" + rel
    with io.open(p, encoding="utf-8", newline="") as f:
        lines = f.read().split("\r\n")
    naughty = [(i + 1, ln) for i, ln in enumerate(lines) if ln.startswith("        /**") or "\r" in ln]
    depth_bad = [i + 1 for i, ln in enumerate(lines)
                 if ln.strip().startswith("/**") and len(ln) - len(ln.lstrip()) not in (0, 4, 8, 12)]
    print(rel.split("\\")[-1], "| 可疑缩进行:", depth_bad[:12])