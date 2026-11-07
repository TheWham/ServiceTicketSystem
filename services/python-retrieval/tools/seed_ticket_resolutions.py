#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""seed_ticket_resolutions.py — 给现存工单补写「处置记录」，让根因维度可用于分析。

**为什么需要**：`ticket_resolution` 表在服务端从来没有写入方（Java 侧零引用），
远程库实测 0 行。而分析链路的根因维度**只从解决方案文本抽取、绝不从工单描述推断**
（从描述猜根因正是幻觉的主要来源）。所以没有这张表的数据，根因维度只能如实声明
「不可归纳」—— 这是诚实的行为，但演示不出根因归纳能力。

**这份数据是什么、不是什么**：
  · 是 —— 按每张工单的**实际症状**写的合理可信的处置记录（「蓝屏」→ 内存条接触不良，
    「无法开机」→ 电源适配器损坏），根因与症状严格对应；
  · 不是 —— 真实业务沉淀的记录。仓库里没有这种来源，不要把它当成真实历史数据。
  写入时用 `DEMO-` 前缀的确定性主键，与真实记录可区分、可一键撤销。

**刻意让同一根因横跨不同症状**（「驱动缺陷」同时出现在蓝屏 / 外设失灵 / 无线异常上）：
跨症状的共性才是「共性根因」要回答的问题，每个症状各配一个根因等于什么都没归纳。

幂等：主键 `DEMO-RES-{ticket_id}`，`INSERT ... ON DUPLICATE KEY UPDATE` 全字段覆盖。
撤销：`--rollback` 只删 `resolution_id LIKE 'DEMO-RES-%'` 的行，不碰任何其他数据。

用法（在 services/python-retrieval 目录下）：
    export DB_PASSWORD=...
    python tools/seed_ticket_resolutions.py --dry-run      # 先看要写什么
    python tools/seed_ticket_resolutions.py                # 写入
    python tools/seed_ticket_resolutions.py --rollback     # 撤销全部
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO_HOME = Path(__file__).resolve().parents[1]
if str(REPO_HOME) not in sys.path:
    sys.path.insert(0, str(REPO_HOME))

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from analytics_service import taxonomy as tx   # noqa: E402

RESOLUTION_ID_PREFIX = "DEMO-RES-"
SUBMITTED_BY = "U_ENG01"      # 演示工程师，与种子账号一致

# ---------------------------------------------------------------------------
# 症状 → 处置记录模板。每个症状给多套说法，按工单顺序轮转，
# 免得 9 张蓝屏写得一字不差（那会让演示数据一眼看出是造的）。
#
# 每条 = (solution, verification, 期望根因标签)
# 期望根因标签用于自检：写完后断言「模板声明的根因」与「词表实际抽出的根因」一致 ——
# 词表改了而模板没跟着改时，这里会立刻报错，而不是悄悄统计出一批错数字。
# ---------------------------------------------------------------------------
RESOLUTIONS: Dict[str, List[Tuple[str, str, str]]] = {
    "无法开机/电源无反应": [
        ("现场检测判定电源适配器损坏（输出端无电压），更换同型号适配器后正常开机。",
         "员工现场确认可正常开机并完成当日办公；连续 3 天未复发。", "电源故障"),
        ("拆机排查发现主板供电模块损坏，电源指示灯始终不亮；更换主板后恢复。",
         "整机功能自检通过，员工试用一周无异常。", "电源故障"),
        ("交叉验证确认电源适配器损坏（输出端无 19V），换新适配器后开机正常。",
         "员工确认可正常使用；旧适配器已回收报废。", "电源故障"),
        ("排查为电源键接触不良导致无法触发上电，清理触点并加固后恢复。",
         "连续按压测试 50 次均正常上电，员工使用无异常。", "电源故障"),
        ("检测为主板供电故障（南桥供电异常），返修后恢复开机。",
         "返修机回装后连续运行 72 小时稳定。", "电源故障"),
    ],
    "蓝屏": [
        ("拆机重新插拔内存条并用橡皮清洁金手指，判定内存条接触不良导致偶发蓝屏。",
         "复测 48 小时含高负载场景未再蓝屏。", "内存故障"),
        ("蓝屏日志判定为显卡驱动版本缺陷，回退到上一稳定版本后不再蓝屏。",
         "员工连续使用一周无复现。", "驱动缺陷"),
        ("排查发现内存条氧化导致读写错误，更换内存条后蓝屏消失。",
         "内存压力测试 2 小时通过。", "内存故障"),
        ("检测到散热风道积尘严重、CPU 过热触发保护性蓝屏，清灰并更换散热硅脂后恢复。",
         "满载运行 1 小时温度正常，未再蓝屏。", "散热失效"),
        ("复现后确认为内存条接触不良（搬动后必现），重新插拔并固定插槽后恢复。",
         "搬运震动测试后仍稳定运行。", "内存故障"),
        ("蓝屏代码指向网卡驱动版本缺陷，升级到厂商修复版后问题消失。",
         "连续联网使用三天无异常。", "驱动缺陷"),
        ("双条内存交叉测试锁定其中一条内存条损坏，更换后不再蓝屏。",
         "替换后跑满一周无复现。", "内存故障"),
    ],
    "外设失灵": [
        ("排查为外设驱动版本缺陷，安装厂商最新驱动后设备识别正常。",
         "重启后设备仍在，员工确认可正常使用。", "驱动缺陷"),
        ("检查发现 USB 接口氧化导致接触不良，清洁接口后设备恢复。",
         "换插多个端口均正常识别。", "硬件接触不良"),
        ("确认鼠标接口氧化接触不良，清洁触点后光标恢复正常。",
         "连续使用一周无掉线。", "硬件接触不良"),
        ("摄像头驱动不兼容当前系统版本，更新驱动后画面正常。",
         "会议软件实测可用，员工确认恢复。", "驱动缺陷"),
        ("键盘排线松动导致部分按键无响应，重新压接排线后全部按键恢复。",
         "全键位测试通过。", "硬件接触不良"),
    ],
    "VPN连接失败": [
        ("排查为网关并发许可证耗尽导致拨号被拒，运维扩容许可并重启服务后恢复。",
         "同一时段多人同时拨号测试均成功。", "配置漂移"),
        ("客户端配置与网关策略冲突，运维侧修正策略后连接正常。",
         "员工连续远程办公一周无断连。", "配置漂移"),
        ("定位为客户端配置漂移（路由表被改），恢复标准配置模板后连接稳定。",
         "复测连接成功率正常。", "配置漂移"),
    ],
    "应用闪退": [
        ("排查为系统文件损坏导致运行库异常，执行系统修复后软件启动正常。",
         "连续打开关闭软件 20 次无闪退。", "系统文件损坏"),
        ("确认为系统镜像损坏引起的组件缺失，修复系统后问题消失。",
         "员工使用一周无复现。", "系统文件损坏"),
    ],
    "打印机脱机": [
        ("进纸组件异响并频繁卡纸，拆检发现搓纸轮橡胶老化打滑，更换搓纸轮后恢复正常。",
         "连续打印 200 页无卡纸。", "橡胶老化"),
    ],
    "无线网络异常": [
        ("排查为无线网卡驱动版本缺陷导致无法启用，升级驱动后 WiFi 恢复正常。",
         "连续联网使用三天稳定。", "驱动缺陷"),
    ],
}


def connect():
    import pymysql
    pw = os.environ.get("DB_PASSWORD") or os.environ.get("MYSQL_PASSWORD")
    if not pw:
        print("[中止] 缺少 DB_PASSWORD（或 MYSQL_PASSWORD）", file=sys.stderr)
        sys.exit(2)
    return pymysql.connect(
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ.get("DB_USER", "root"),
        password=pw,
        database=os.environ.get("DB_NAME", "it_ticket_system"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def plan_rows(tax: tx.Taxonomy) -> List[Dict[str, str]]:
    """读出全部工单，按症状挑模板，产出待写行。

    噪声单（test/123、标注「请忽略」的联调单、演示单）**不写** —— 分析链路本来就会
    把它们排除，给它们补处置记录纯属制造脏数据。判定口径直接复用词表模块，不另写一套。
    """
    import pymysql
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT ticket_id, title, description, created_at FROM ticket "
                        "ORDER BY created_at, ticket_id")
            tickets = cur.fetchall()
    finally:
        conn.close()

    out: List[Dict[str, str]] = []
    counters: Dict[str, int] = {}
    skipped_noise = skipped_no_symptom = 0

    for t in tickets:
        if tx.low_information_reason(t["title"], t["description"]):
            skipped_noise += 1
            continue
        ext = tx.extract_ticket(t["title"], t["description"], tax)
        variants = RESOLUTIONS.get(ext.symptom or "")
        if not variants:
            skipped_no_symptom += 1
            continue
        idx = counters.get(ext.symptom, 0) % len(variants)
        counters[ext.symptom] = idx + 1
        solution, verification, expect = variants[idx]
        out.append({
            "resolution_id": RESOLUTION_ID_PREFIX + t["ticket_id"],
            "ticket_id": t["ticket_id"],
            "solution": solution,
            "verification": verification,
            "expect_root_cause": expect,
            "symptom": ext.symptom or "",
        })

    print(f"扫描 {len(tickets)} 张：噪声跳过 {skipped_noise}、无匹配症状跳过 {skipped_no_symptom}"
          f" → 待写 {len(out)} 条")
    return out


def self_check(rows: List[Dict[str, str]], tax: tx.Taxonomy) -> None:
    """写库前自检：模板声明的根因必须能被词表抽出来。

    词表与模板分开维护，任一方改了另一方没跟上时，这里当场报错 ——
    否则会安静地写进一批「统计口径对不上模板」的数据，事后很难查。
    """
    bad = []
    for r in rows:
        got = tx.extract(r["solution"], tax).root_cause
        if got != r["expect_root_cause"]:
            bad.append(f'  {r["ticket_id"]} 模板声明「{r["expect_root_cause"]}」'
                       f' 但词表抽出「{got}」：{r["solution"][:40]}…')
    if bad:
        print("\n❌ 自检失败：模板声明的根因与词表抽取结果不一致", file=sys.stderr)
        print("\n".join(bad), file=sys.stderr)
        sys.exit(1)
    print(f"✅ 自检通过：{len(rows)} 条处置记录的根因均可被词表正确抽出")


UPSERT_SQL = """
INSERT INTO ticket_resolution
  (resolution_id, ticket_id, solution, verification, submitted_by,
   submitted_at, created_at, updated_at)
VALUES (%s, %s, %s, %s, %s, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), UTC_TIMESTAMP(6))
ON DUPLICATE KEY UPDATE
  solution=VALUES(solution), verification=VALUES(verification),
  submitted_by=VALUES(submitted_by), updated_at=UTC_TIMESTAMP(6)
"""


def write_rows(rows: List[Dict[str, str]]) -> int:
    conn = connect()
    try:
        with conn.cursor() as cur:
            for r in rows:
                cur.execute(UPSERT_SQL, (r["resolution_id"], r["ticket_id"], r["solution"],
                                         r["verification"], SUBMITTED_BY))
        conn.commit()
    finally:
        conn.close()
    return len(rows)


def rollback() -> int:
    """只删本脚本写的数据。用 LIKE 前缀而不是全表清空 —— 万一库里以后有了真实记录，
    撤销演示数据不能顺手把人家删掉。"""
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM ticket_resolution "
                        "WHERE resolution_id LIKE %s", (RESOLUTION_ID_PREFIX + "%",))
            n = cur.fetchone()["n"]
            cur.execute("DELETE FROM ticket_resolution WHERE resolution_id LIKE %s",
                        (RESOLUTION_ID_PREFIX + "%",))
        conn.commit()
    finally:
        conn.close()
    return n


def main() -> int:
    parser = argparse.ArgumentParser(description="给现存工单补写演示用处置记录")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划，不写库")
    parser.add_argument("--rollback", action="store_true", help="撤销本脚本写入的全部数据")
    args = parser.parse_args()

    if args.rollback:
        n = rollback()
        print(f"🧹 已撤销 {n} 条演示处置记录（resolution_id LIKE '{RESOLUTION_ID_PREFIX}%'）")
        return 0

    tax = tx.load_taxonomy(use_cache=False)
    print(f"词表 v{tax.version}（指纹 {tax.fingerprint}）")
    rows = plan_rows(tax)
    self_check(rows, tax)

    if args.dry_run:
        print("\n--- 计划写入（前 8 条）---")
        for r in rows[:8]:
            print(f"  {r['ticket_id']}  [{r['symptom']}]  根因={r['expect_root_cause']}")
            print(f"      {r['solution']}")
        print(f"\n（共 {len(rows)} 条，--dry-run 未写库）")
        return 0

    n = write_rows(rows)
    print(f"✅ 已写入 {n} 条处置记录（resolution_id = '{RESOLUTION_ID_PREFIX}<ticket_id>'）")
    print("   撤销：python tools/seed_ticket_resolutions.py --rollback")
    return 0


if __name__ == "__main__":
    sys.exit(main())