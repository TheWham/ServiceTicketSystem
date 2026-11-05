# CLAUDE.md

完整宪法见 AGENTS.md，冲突以 AGENTS.md 为准。本文件仅摘取高频要点，只引用、不新增规则。

## 高频命令（AGENTS.md 第三层 指令字典）

- 后端构建：`mvn -f it-ticket-cloud/pom.xml clean package`（无 mvnw wrapper）
- 后端单测：`mvn -f it-ticket-cloud/pom.xml test`（提交前必过；现有单测不依赖 MySQL/Redis/Nacos）
- 前端：`cd frontend && npm run dev` / `npm run build` / `npm run preview`（无 lint script）
- 验收评测门禁：`cd acceptance && python scripts/run_acceptance.py`（Windows 控制台需 `PYTHONIOENCODING=utf-8`）；pytest 27 用例：`python -m pytest`
- evals 门禁：`python evals/test_acceptance_gate.py <metrics.json>`
- 本地环境一键起：`cd it-ticket-cloud && docker compose up -d`；免 Docker：`it-ticket-cloud\scripts\start-all.cmd`
- pre-commit 门禁挂载（一次性初始化，每人在仓库根执行一次，幂等）：`git config core.hooksPath .githooks && chmod +x .githooks/pre-commit`（验证：`git config core.hooksPath` 输出 `.githooks`；详见 AGENTS.md 第三层）
- 契约测试 / 代码风格门禁：待建（见 AGENTS.md 第三层）

任何门禁命令失败，不允许跳过、注释用例或放宽断言（AGENTS.md 第三层）。

## 工作流要点（AGENTS.md 1.2 / 4.4）

- specs/ 是唯一真理源，改契约必须「先改 specs/ → 评审 → 再改代码」；禁止在业务代码中篡改契约。涉及：`specs/SPEC_API_CONTRACTS.yaml`、`specs/SPEC_ERROR_CODES.md`、`specs/SPEC_DATA_MODELS.md`、`specs/MIGRATION_STATUS_MAPPING.md`。
- 代码与 specs/ 冲突时，视为代码有 bug，而非 specs/ 有误。
- 冻结区 9 项存量在跑契约（AGENTS.md 4.4）改动同样必须先走 specs/ + 评审 + 迁移方案。

## 自愈纪律摘要（AGENTS.md 第五层）

1. 测试红字先对照 specs/ 修代码，禁止反向修改断言迁就实现。
2. 对外/内部字段冲突（如 `idempotency_key` vs `client_token`、七态 vs 八态）先查设计文档 2.4 映射表与 `specs/MIGRATION_STATUS_MAPPING.md`，多数应在网关/映射层解决。
3. 连续两次修复失败 → 停止尝试，输出偏离报告（冲突条款+代码位置、PRD/设计依据、已试修复、建议方案）等待人工决策；禁止跳过/注释测试、放宽 Schema、`--skip` 门禁、把八态改回七态凑绿。
