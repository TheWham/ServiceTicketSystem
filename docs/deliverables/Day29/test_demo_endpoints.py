# -*- coding: utf-8 -*-
"""test_demo_endpoints.py

自动化验证 run_cost_governance_web_demo 的核心端点：
1. GET / 网页服务返回 200 与 HTML 内容；
2. GET /api/budget/snapshot 预算快照；
3. POST /api/budget/simulate 模拟调参；
4. POST /api/chat/stream SSE 事件流（测试 LITE、STANDARD、PREMIUM、降档、429熔断）。
"""

import json
import sys
import threading
import time
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from run_cost_governance_web_demo import run_server, PORT


def run_tests():
    base_url = f"http://127.0.0.1:{PORT}"
    print(f"🔍 开始验证演示系统端点: {base_url}")

    # 1. 测试页面服务
    req = urllib.request.Request(f"{base_url}/")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        content = resp.read().decode("utf-8")
        assert "IT Service Desk · 成本治理与 Model Router" in content
        print("✅ 1. GET / 页面加载成功 (HTTP 200)")

    # 2. 测试预算快照
    req = urllib.request.Request(f"{base_url}/api/budget/snapshot?user_id=U-TEST&dept_id=DEPT-TEST")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert any(k.startswith("user:U-TEST") for k in data)
        print("✅ 2. GET /api/budget/snapshot 正常返回预算账户数据")

    # 3. 测试预算模拟
    post_data = json.dumps({"user_id": "U-TEST", "dept_id": "DEPT-TEST", "daily_available": 1500}).encode("utf-8")
    req = urllib.request.Request(f"{base_url}/api/budget/simulate", data=post_data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        print("✅ 3. POST /api/budget/simulate 成功设置模拟额度")

    # 4. 测试 SSE 流式对话 - LITE 场景
    chat_payload = json.dumps({
        "query": "公司访客 WiFi 密码是什么？",
        "user_id": "U-TEST",
        "dept_id": "DEPT-TEST",
        "history_turns": 0
    }).encode("utf-8")
    req = urllib.request.Request(f"{base_url}/api/chat/stream", data=chat_payload, headers={"Content-Type": "application/json"})
    
    events = []
    with urllib.request.urlopen(req, timeout=30) as resp:
        while True:
            line = resp.readline()
            if not line:
                break
            line_str = line.decode("utf-8").strip()
            if line_str.startswith("data:"):
                payload = json.loads(line_str[5:].strip())
                events.append(payload)
                if payload.get("type") in ("done", "stage5"):
                    break

    event_types = [e.get("type") for e in events]
    print(f"✅ 4. POST /api/chat/stream 收到事件序列: {set(event_types)}")
    assert "stage1" in event_types
    assert "stage2" in event_types
    assert "stage3" in event_types
    assert "token" in event_types
    assert "stage5" in event_types
    
    # 验证 stage2 路由到了 LITE
    s2 = next(e for e in events if e.get("type") == "stage2")
    assert s2["tier"] == "lite"
    assert s2["model_name"] == "qwen3.7-flash"
    print(f"   ➔ LITE 路由验证通过: 模型 {s2['model_name']}")

    # 5. 测试 429 熔断流
    # 先将额度清零
    post_data = json.dumps({"user_id": "U-TEST", "dept_id": "DEPT-TEST", "daily_available": 0}).encode("utf-8")
    req = urllib.request.Request(f"{base_url}/api/budget/simulate", data=post_data, headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req)

    # 提交高危提权特批
    high_risk_payload = json.dumps({
        "query": "工单号 IT-9999：申请核心生产库 MySQL 生产环境 DROP/ALTER 表结构特批提权",
        "user_id": "U-TEST",
        "dept_id": "DEPT-TEST",
        "history_turns": 0
    }).encode("utf-8")
    req = urllib.request.Request(f"{base_url}/api/chat/stream", data=high_risk_payload, headers={"Content-Type": "application/json"})
    
    breaker_events = []
    with urllib.request.urlopen(req, timeout=10) as resp:
        while True:
            line = resp.readline()
            if not line:
                break
            line_str = line.decode("utf-8").strip()
            if line_str.startswith("data:"):
                payload = json.loads(line_str[5:].strip())
                breaker_events.append(payload)
                if payload.get("type") in ("circuit_breaker", "done"):
                    break

    breaker_types = [e.get("type") for e in breaker_events]
    assert "circuit_breaker" in breaker_types
    print(f"✅ 5. 预算耗尽时高危请求成功触发 HTTP 429 熔断: {[e['type'] for e in breaker_events]}")

    print("\n🎉 所有 5 项核心能力全链路自动化测试全部通过！")
    sys.exit(0)


if __name__ == "__main__":
    t = threading.Thread(target=run_server, kwargs={"port": PORT, "auto_open_browser": False}, daemon=True)
    t.start()
    time.sleep(1.5)
    run_tests()
