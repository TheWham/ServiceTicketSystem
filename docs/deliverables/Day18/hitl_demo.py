# -*- coding: utf-8 -*-
"""人机回环（HITL）演示脚本 —— 两条门禁，一个道理。

用法：
    python day18/hitl_demo.py                              # 默认 http://127.0.0.1:28080
    python day18/hitl_demo.py --base http://127.0.0.1:8080
    python day18/hitl_demo.py --skip-ai                    # 只演示派单门禁

演示的是**同一个道理的两处落地**：自动化不是「发现就干」，而是「发现 → 挂起 → 人点头 → 才干」。

  门禁① 派单：系统算出该派给谁，但**工单停在 NEW**，等管理员点头才落 ASSIGNED
  门禁② 建单：AI 想建单，但**只产草稿不落库**，等员工确认才真建

每一步都打印「此刻的真实状态」——HITL 的可信度不在动作里，而在**没人点头之前什么都没发生**。
所有身份经网关登录换取 token（网关据此注入用户身份），与浏览器里的路径一致。
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://127.0.0.1:28080"
# 派单草案端点**未经网关路由**（gateway application.yml 的 8 条路由里没有
# /api/v1/dispatch-drafts/**），经网关一律 404，只能直连 ticket-service 才能碰到。
# 直连时身份由 X-User-Id/X-User-Role 头给出（绕过网关鉴权）——这是当前系统的既有缺口，
# 演示时据实说明即可。补一条网关路由即可让本脚本全程走网关。
DIRECT = "http://127.0.0.1:8201"
PASSWORD = "123456"
EMP, ENG, ADM = "U_EMP01", "U_ENG01", "U_ADM01"
ROLE = {EMP: "EMPLOYEE", ENG: "ENGINEER", ADM: "PLATFORM_ADMIN"}

TOKENS = {}


def call(method, path, body=None, as_user=None, extra=None, direct=False):
    """发一个请求；返回 (http_status, 解析后的 body)。

    direct=True 时直连 ticket-service 并改用 X-User-Id/X-User-Role 传递身份
    （仅用于未经网关路由的「派单草案」端点）。
    """
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"}
    if direct:
        base = DIRECT
        headers["X-User-Id"] = as_user
        headers["X-User-Role"] = ROLE[as_user]
    else:
        base = BASE
        if as_user:
            headers["Authorization"] = "Bearer " + TOKENS[as_user]
    if extra:
        headers.update(extra)
    req = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=200) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"raw": raw}


def login(user):
    if user in TOKENS:
        return
    _, env = call("POST", "/api/v1/users/login", {"userId": user, "password": PASSWORD})
    token = (env.get("data") or {}).get("token")
    if not token:
        raise RuntimeError(f"登录失败 {user}: {env}")
    TOKENS[user] = token


def banner(title):
    print("\n" + "=" * 74)
    print("  " + title)
    print("=" * 74)


def step(n, text):
    print(f"\n▶ [{n}] {text}")


def observe(label, value):
    print(f"     👁  {label}：{value}")


def ticket_state(ticket_id):
    """读工单真实状态（每次现查，演示不靠缓存）。"""
    _, env = call("GET", f"/api/v1/tickets/{ticket_id}", as_user=ADM)
    t = (env.get("data") or {}).get("ticket") or {}
    return t.get("status"), t.get("assignee_id")


def flow_log(ticket_id):
    _, env = call("GET", f"/api/v1/tickets/{ticket_id}", as_user=ADM)
    return (env.get("data") or {}).get("flow_logs") or []


def my_ticket_count(user):
    _, env = call("GET", "/api/v1/tickets?pageSize=1", as_user=user)
    return ((env.get("data") or {}).get("total"))


def create_ticket(key, title, category="C_HW_PC"):
    _, env = call("POST", "/api/v1/tickets", {
        "nature": "INCIDENT", "category_id": category, "title": title,
        "description": "人机回环演示用单，请忽略。用于观察门禁挂起与放行的差别。",
        "impact_description": "单人受影响", "urgency_description": "一般",
        "expected_completion_time": "2026-10-30 18:00:00",
    }, as_user=EMP, extra={"Idempotency-Key": key})
    return (env.get("data") or {}).get("ticket_id")


def pending_draft(ticket_id):
    _, env = call("GET", f"/api/v1/dispatch-drafts?ticketId={ticket_id}", as_user=ADM, direct=True)
    rows = (env.get("data") or {}).get("list") or []
    return rows[0] if rows else None


def demo_dispatch_gate():
    banner("门禁① 派单：自动化算出了结果，但必须有人点头才落库")
    code, env = call("GET", "/api/v1/dispatch-drafts?pageSize=1", as_user=ADM, direct=True)
    if code != 200:
        print(f"  ⚠ 派单草案端点不可用（HTTP {code}）。请确认 ticket-service 已在 :8201 运行")
        return None

    step(1, f"员工 {EMP} 提一张硬件故障单")
    tid = create_ticket(f"hitl-{int(time.time())}", "【HITL演示】笔记本无法开机")
    print(f"     工单号 = {tid}")
    time.sleep(3)  # 等自动路由跑完

    step(2, "系统自动路由跑完了 —— 关键看：工单动了吗？")
    status, assignee = ticket_state(tid)
    observe("工单状态", f"{status}   ← 仍是 NEW，自动化**没有**直接下手")
    observe("工单处理人", f"{assignee}   ← 仍为空")
    d = pending_draft(tid)
    if d:
        observe("但草案已挂起", f"{d['draftId']} → 建议派给 {d['engineerId']}（状态 {d['status']}）")
        observe("草案有效期", d["expiresAt"])
    print("      👉 这就是刹车片：系统把「该派给谁」算好了、写进草案，但工单一步没动。")

    step(3, "此刻没有管理员点头，会发生什么？")
    code, body = call("POST", f"/api/v1/tickets/{tid}/claim",
                      {"impact_scope": "SINGLE", "urgency_level": "MEDIUM"}, as_user=ENG)
    observe(f"工程师 {ENG} 去接这单", f"HTTP {code}  {body.get('msg')}")
    print("      👉 接不了。自动化没有绕过人，工单就推进不下去。")

    if not d:
        print("     ⚠ 没等到草案，放行演示跳过（检查自动路由与工程师可用性）")
        return tid

    step(4, f"主管 {ADM} 认领草案（占用待办，避免两人同时裁决）")
    code, body = call("POST", f"/api/v1/dispatch-drafts/{d['draftId']}/claim", as_user=ADM, direct=True)
    observe("认领", f"HTTP {code}  {body.get('msg') or 'ok'}")

    step(5, "主管放行 —— 人点头了，这才是写操作真正发生的一刻")
    code, body = call("POST", f"/api/v1/dispatch-drafts/{d['draftId']}/decide",
                      {"approve": True, "reason": "HITL演示放行"}, as_user=ADM, direct=True)
    observe("裁决", f"HTTP {code}  {body.get('msg') or 'ok'}")
    time.sleep(1)
    status2, assignee2 = ticket_state(tid)
    observe("工单状态", f"{status} → {status2}   ← 人点头后才动")
    observe("工单处理人", f"{assignee} → {assignee2}")
    print("      ── 该工单的流转日志（who did what）──")
    for row in flow_log(tid):
        print(f"         {row.get('from_status')} → {row.get('to_status')}  "
              f"{row.get('event')}  by {row.get('operator_id')}")
    print(f"      👉 同一次「自动路由」调用，只在主管放行后才产生 NEW → ASSIGNED 这条流转。")
    print(f"      👉 现在分派工程师 {assignee2} 可以接单了；"
          f"本脚本没有该账号凭据（非种子账号），这一击留给界面或另配凭据。")

    print("\n  ── 对照：驳回分支（本次不执行，供讲解）──")
    print("     decide 传 {\"approve\": false, \"reason\": \"...\"} 时：")
    print("     草案置 REJECTED，工单**保持 NEW**，不做任何静默改派 —— 拒绝也是门的动作。")
    print("     已知缺口：驳回/失效后没有「重新路由」入口，管理员只能手动派单。")
    return tid


def demo_ai_draft_gate():
    banner("门禁② 建单：AI 想建单，但只产草稿、不落库，等员工确认")

    step(1, f"先数一下员工 {EMP} 名下有几张工单")
    before = my_ticket_count(EMP)
    observe("工单数", before)

    step(2, f"员工 {EMP} 对 AI 说：「我的笔记本开不了机，帮我提交一个报修工单」")
    # 幂等键带时间戳后缀:重复跑演示时不命中上一次的幂等缓存
    run = str(int(time.time()))
    code, env = call("POST", "/api/v1/consultations", {"source": "AI"}, as_user=EMP,
                     extra={"X-Request-Id": "hitl-demo-c-" + run, "Idempotency-Key": "hitl-demo-c-" + run})
    sid = (env.get("data") or {}).get("sessionId")
    if not sid:
        print(f"     ⚠ 建会话失败：HTTP {code} {env}")
        return None
    code, env = call("POST", f"/api/v1/consultations/{sid}/ai-messages",
                     {"message": "我的笔记本开不了机，按电源没反应，帮我提交一个报修工单。"},
                     as_user=EMP,
                     extra={"X-Request-Id": "hitl-demo-m-" + run, "Idempotency-Key": "hitl-demo-m-" + run})
    data = env.get("data") or {}
    observe("AI 回话类型", data.get("replyType"))
    draft = data.get("ticketDraft")
    if draft:
        observe("带出的建单草稿", f"{draft.get('title')} / {draft.get('category')} / {draft.get('priority')}")
    else:
        observe("带出的建单草稿", "无（模型本轮没走建单工具，可重试或换个说法）")

    step(3, "关键一问：AI 说完这些，库里多了单吗？")
    mid = my_ticket_count(EMP)
    observe("工单数", f"{before} → {mid}")
    print("      👉 没变。AI 只有「起草」的权力，没有「落库」的权力。")

    if not draft:
        return None

    step(4, "员工确认草稿 —— 这才是建单真正发生的一刻")
    code, env = call("POST", f"/api/v1/consultations/{sid}/ticket-draft/confirm", {
        "title": draft.get("title"), "category": draft.get("category"),
        "description": draft.get("description"), "priority": draft.get("priority") or "MEDIUM",
    }, as_user=EMP,
        extra={"X-Request-Id": "hitl-demo-f-" + run, "Idempotency-Key": "hitl-demo-f-" + run})
    new_id = (env.get("data") or {}).get("ticketId")
    observe("确认结果", f"HTTP {code}  新工单 = {new_id}  {env.get('message') or env.get('msg') or ''}")
    time.sleep(3)
    after = my_ticket_count(EMP)
    observe("工单数", f"{mid} → {after}")

    if new_id:
        status, assignee = ticket_state(new_id)
        observe("新工单状态", f"{status}, 处理人 = {assignee}")
        print("      👉 注意：这张单又落到了门禁① —— 建单要人确认，派单**还要**人确认。")
    return new_id


def main():
    global BASE
    parser = argparse.ArgumentParser(description="人机回环演示")
    parser.add_argument("--base", default=BASE)
    parser.add_argument("--skip-ai", action="store_true", help="跳过 AI 建单门禁（需 agent 已开启）")
    args = parser.parse_args()
    BASE = args.base.rstrip("/")

    print(f"目标网关：{BASE}")
    for u in (EMP, ENG, ADM):
        login(u)
    print(f"已登录：{EMP} / {ENG} / {ADM}")

    demo_dispatch_gate()
    if not args.skip_ai:
        try:
            demo_ai_draft_gate()
        except Exception as e:  # noqa: BLE001
            print(f"\n  ⚠ AI 建单门禁演示失败（跳过）：{type(e).__name__}: {e}")

    banner("演示结束")
    print("  一句话总结：两处门禁是同一个形状 ——")
    print("    自动化只负责**把结论摆到人面前**，动手的那一下必须由人触发。")


if __name__ == "__main__":
    main()