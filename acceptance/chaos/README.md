# 混沌故障注入套件（四类）· Day19 讲义对齐

对齐讲义《工业级报表输出、混沌工程故障注入与QA提测防线》的四大混沌故障注入要求。
全部为**只读测试资产**：不改任何产品代码，报告落 `acceptance/reports/`。

> 说明：本目录的套件本体（`fault_injection_suite.mjs`）与 `acceptance/blindtest/`
> 的盲测套件由并行工作流落盘（2026-10-23 11:04-11:11，F1-F4 口径，
> 真机实测 23/23 通过）；同日早前另一实现的 32 用例详细报告保留在
> `reports/chaos_fault_injection_report.{json,md}`（含 12 例脏参数矩阵、
> RBAC 越权矩阵与已知限制清单），两者可互为补充。

## 四类覆盖（F1-F4）

| 类别 | 讲义要求 | 实现口径 |
|---|---|---|
| F1 | Prompt 越狱 / 指令覆盖 | 端到端：绝不泄密/吐系统提示词/堆栈 → 拒绝通道收口 |
| F2 | 畸变脏参数 | 零 5xx、零堆栈；类型错/空/超长 → 40001 拦截；topK 非法值松散截断（已知限制） |
| F3 | 下游 504/超时故障 | 真杀 8310 → 断言 RD-006 降级（200+空结果+MODEL_UNAVAILABLE、历史落库）→ 自动恢复 → 复验 |
| F4 | SQL AST 绕过注入（对等物） | 本项目无 Text2SQL（PRD §3.3 排除项）：注入串一律当文本（零 5xx）+ 越权/伪造 ID → 404/401 不泄存在性 |

## 用法

```bash
# F1/F2/F4（不动服务）
node acceptance/chaos/fault_injection_suite.mjs

# 加 F3：真杀 8310 → 断言降级 → 自动恢复 → 断言恢复
node acceptance/chaos/fault_injection_suite.mjs --downstream
```

前置：四服务已起（网关 8080 / consultation 8301 / rag 8302 / py-rag 8310）。
可用环境变量：`IT_GATEWAY_URL`。

## 手动恢复脚本

`restart_py_rag.ps1` / `restart_agent_service.ps1`：手工拉起两个 Python 服务，
优先用仓库 `.venv\Scripts\python.exe`（与 `start-ai.ps1` 运行时一致，避免
双实例抢端口），环境注入同源 `it-ticket-cloud/scripts/ai-env.ps1`。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File acceptance/chaos/restart_py_rag.ps1
```

## 已实测的已知限制（2026-10-23，如实记录）

- `topK=0/-1/999999/缺省` 被服务端静默归一化（分别返回 5/5/6/5 条），契约未定义值域。
- 越狱问句在检索层多被判 `OFFICE_IT + reliable=false` → 走 LOW_CONFIDENCE 拒答；
  端到端最终 REFUSE（HIGH_RISK_TOPIC/OFF_TOPIC）收口，结果安全、归因不精确。
- RD-006 降级契约下 8310 挂掉时 8302 仍返回 HTTP 200（空结果+MODEL_UNAVAILABLE），
  「期望 200」的弱断言在内核已死时会假 PASS——跑 F1/F2 前先确认 8310 `/api/health` 为 UP。

## 报告

- `acceptance/reports/fault_injection_report.{json,md}`：套件标准报告（23 用例）。
- `acceptance/reports/chaos_fault_injection_report.{json,md}`：32 用例详细版
  （含 J1 端到端泄露检测、J2 脏参数矩阵、J3 逐段耗时、knownLimitations 清单）。
