# -*- coding: utf-8 -*-
"""给测试补 import com.itticket.ticket.service.DispatchDraftService;（需要时）。

只在该文件引用了 DispatchDraftService.class 且尚无 import 时插入，
位置紧跟既有的同包 service import 之后，保持 import 分组顺序。
"""
import io
import os

ROOT = (r"C:\Users\Admin\.wpscomate\agent\workspace\it-ticket-system"
        r"\it-ticket-cloud\ticket-service\src\test\java\com\itticket\ticket")
IMP = "import com.itticket.ticket.service.DispatchDraftService;"

total = 0
for dirpath, _, names in os.walk(ROOT):
    for n in sorted(names):
        if not n.endswith(".java"):
            continue
        p = os.path.join(dirpath, n)
        with io.open(p, encoding="utf-8", newline="") as f:
            src = f.read()
        if "DispatchDraftService.class" not in src or IMP in src:
            continue
        lines = src.split("\r\n")
        # 找最后一个 com.itticket.* import 行
        last = None
        for i, ln in enumerate(lines):
            if ln.startswith("import com.itticket."):
                last = i
        if last is None:
            print("%-42s 未找到锚点，跳过" % n)
            continue
        lines.insert(last + 1, IMP)
        with io.open(p, "w", encoding="utf-8", newline="") as f:
            f.write("\r\n".join(lines))
        total += 1
        print("%-42s import 已补" % n)
print("files touched:", total)