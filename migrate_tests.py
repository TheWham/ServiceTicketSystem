# -*- coding: utf-8 -*-
"""迁移测试里的构造调用：RoutingService / TicketService 各新增了一个依赖。

按括号配对找到参数表末尾插入 mock。先在原文里定位所有插入点，
再从后往前写入，避免偏移失效；不修改除插入点外的任何字符。
"""
import io
import os

ROOT = (r"C:\Users\Admin\.wpscomate\agent\workspace\it-ticket-system"
        r"\it-ticket-cloud\ticket-service\src\test\java\com\itticket\ticket")

MARKERS = ["new RoutingService(", "new TicketService("]
EXTRA = "mock(DispatchDraftService.class)"


def insertion_points(src):
    """返回所有 (插入位置, ) —— 即构造调用参数表右括号的下标。"""
    pts = []
    for marker in MARKERS:
        pos = 0
        while True:
            i = src.find(marker, pos)
            if i < 0:
                break
            depth = 0
            k = i + len(marker) - 1
            while k < len(src):
                c = src[k]
                if c == "(":
                    depth += 1
                elif c == ")":
                    depth -= 1
                    if depth == 0:
                        break
                k += 1
            if k >= len(src):
                break
            pts.append(k)
            pos = i + 1
    return sorted(set(pts))


total = 0
for dirpath, _, names in os.walk(ROOT):
    for n in sorted(names):
        if not n.endswith(".java"):
            continue
        p = os.path.join(dirpath, n)
        with io.open(p, encoding="utf-8", newline="") as f:
            src = f.read()
        if not any(m in src for m in MARKERS):
            continue
        if EXTRA in src:
            print("%-42s 已迁移，跳过" % n)
            continue
        pts = insertion_points(src)
        if not pts:
            continue
        out = src
        for k in reversed(pts):
            out = out[:k] + ", " + EXTRA + out[k:]
        with io.open(p, "w", encoding="utf-8", newline="") as f:
            f.write(out)
        total += len(pts)
        print("%-42s +%d" % (n, len(pts)))
print("total inserted:", total)