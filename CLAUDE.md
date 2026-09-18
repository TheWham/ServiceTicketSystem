# CLAUDE.md

This file provides guidance to kscc (claude.ai/code) when working with code in this repository.

## 项目概述

IT 服务工单系统全栈项目（P0 MVP），覆盖「提单 → 派单 → 处理 → 验收 → 评价」闭环。Monorepo 结构：

- `backend/` — Node.js + Express + SQLite（better-sqlite3），端口 3001
- `frontend/` — Vue 3 + Vite + Pinia + Vue Router + Axios，端口 5173

认证为 Mock 模式：前端在请求头注入 `X-User-Id`，后端据此识别身份。角色三色：`employee`（员工）、`engineer`（工程师）、`supervisor`（主管）。

## 命令

后端（在 `backend/` 下）：
```bash
npm install
npm run db:init    # 重建表结构 + 写入种子数据（会 DROP 重建所有表）
npm run dev        # nodemon 热重载，监听 :3001
npm start          # 无热重载启动
```

前端（在 `frontend/` 下）：
```bash
npm install
npm run dev        # Vite，监听 :5173，/api 代理到 :3001
npm run build      # 生产构建（可作为编译检查手段）
```

- 无测试框架、无 lint 配置。验证改动靠 `npm run dev` 后手工访问，或 `npm run build` 检查前端能否编译。
- 数据库路径可用 `DB_PATH` 覆盖（默认 `backend/db/it_ticket.db`），端口用 `PORT` 覆盖。
- **`db:init` 会先 DROP 所有表再重建**。这是必要的：`CREATE TABLE IF NOT EXISTS` 不会给已存在的表新增列，改动 schema（如加列）后必须重跑 `db:init` 才能生效。

## 后端架构（backend/src）

分层 `routes → controllers → services → db`：

- **`db.js`** — 关键抽象。控制器代码是**按 MySQL/mysql2 风格写的**，本文件提供异步兼容层：`query(sql, params)` 返回 `[rows, fields]`，`getConnection()` 返回带事务的伪连接对象，并做 **MySQL → SQLite 方言翻译**（`NOW()`、`DATE_SUB(...)` 等）与参数净化（`Date` → 本地时间字符串、`boolean` → 0/1）。因此**控制器里的 SQL 是 MySQL 方言**，勿写纯 SQLite 语法（个别草稿 SQL 已用 `ON CONFLICT` UPSERT，属例外）。
- **`services/stateMachine.js`** — 领域核心。定义状态（`待处理/处理中/待补充/待外部/待验收/已完成/已取消`）、合法转移图 `TRANSITIONS`、通知事件类型与接收人映射。提供两个校验入口：`validateTransition(from,to,role)`（按目标状态）与 `resolveAction(fromStatus, action)`（按 action 名，找不到返回 `null`）。
- **`middleware/auth.js`** — 从 `X-User-Id` 识别用户写入 `req.currentUser`；`requireRole(...)` 角色守卫。
- **`services/idGenerator.js`** — 工单号 `TK + yyyyMMdd + 4位自增`（含主键冲突重试）。
- **`services/notification.js`** — 通道抽象 `wechatChannel`/`smsChannel`（模拟实现；`WECHAT_FAIL_RATE` 开关可模拟企微失败）。企微失败且工单为**高优先级**时走短信兜底。幂等键为 `ticket_id:event_type:receiver_id`——**含接收人**，故同一事件可分别通知多方。
- **`services/scheduler.js`** — SLA 定时任务。`startScheduler()` 在 `index.js` 中启动，每 60 秒扫描：待补充超时自动取消、待验收超 3 工作日自动验收、其它中间态超时预警主管。阈值常量在文件顶部，测试时可调短。

## 前端架构（frontend/src）

- **`api/index.js`** — axios 单例封装，请求拦截器从 Pinia store 读取 `userId` 并注入 `X-User-Id`；响应拦截器 `res => res.data`（调用处拿到的是后端整个 body `{code,msg,data}`，业务数据在 `.data`）。导出 `userApi`/`ticketApi`/`draftApi`/`assetApi`/`kbApi`/`uploadApi`。
- **`stores/user.js`** — Pinia store，`userId` 持久化到 `localStorage('mock_user_id')`；提供 `isEmployee/isEngineer/isSupervisor` 计算属性。
- **`router/index.js`** — 每条路由带 `meta.role`，`beforeEach` 守卫按角色重定向；未登录跳 `/login`。
- **`views/`** — 按角色分四页：`LoginView`（Mock 选身份）、`EmployeeView`（提单/草稿/验收，含标题、资产校验、截图上传、知识库推荐卡）、`EngineerView`（看板，`onMounted` 起 15s 轮询）、`SupervisorView`（派单/改派/全局统计）。

## 需要跨文件理解的关键点

1. **状态转移只有一处定义**：所有流转规则集中在 `stateMachine.js` 的 `TRANSITIONS`。`assignTicket` 用 `validateTransition`，`actionTicket` 用 `resolveAction`，二者读同一张表——改流转规则只需改 `TRANSITIONS` 一处。注意 `progress`（记录进展、**不改变状态**）是 `actionTicket` 内的特例，不在 `TRANSITIONS` 中。

2. **前后端对同一规则各校验一遍**：例如「工程师提交方案前须有至少一条进展记录」——后端在 `actionTicket` 的 `done` 分支查 `ticket_flow_log`，前端在 `EngineerView.vue` 的 `canDone` 计算属性判断。改这类业务规则需同时改前后端。

3. **统一响应格式 `{code, msg, data}`**：`errorHandler` 兜底 `50000`；业务错误码内联在控制器（`40001` 参数、`40021` 处理人无效、`40100/40101` 认证、`40300` 权限、`40400` 不存在、`40910` 非法状态转移）。前端拦截器把非 0 响应转成 `Error(msg)` 供 `catch` 使用。

4. **事务模式**：跨多条 SQL 的写操作（`createTicket`/`assignTicket`/`actionTicket`/`scheduler` 的状态转移）用 `pool.getConnection()` 手动 `beginTransaction/commit/rollback`，`finally` 中 `release()`；简单读/单条写直接用 `pool.query`。通知 `sendNotification` 在事务外异步触发，不阻塞响应。

5. **附件上传**：`POST /api/v1/uploads`（multer，field 名 `files`，jpg/png ≤5MB ≤3 张）落盘到 `backend/uploads/`，由 `index.js` 的 `express.static('/uploads')` 暴露——**该 static 挂在 `mockAuth` 之前**，因为 `<img>` 请求不带认证头。返回值是相对 URL，存入 `ticket.attachment_urls`。

6. **`attachment_urls` 是 JSON 字符串**：出入库在 controller 层手动 `JSON.stringify`/`JSON.parse`（见 `parseTicketRow` 与 `saveDraft`）；草稿表 `ticket_draft` 以 `user_id` 唯一键 UPSERT。

7. **`db/schema.sql` 与 `db/seed.sql` 是遗留的 MySQL 备用文件**（README 说切回 MySQL 时用），**真正生效的是 `db/schema.sqlite.sql` + `db/seed.sqlite.sql`**。

## 主要接口

`/api/v1/tickets`（CRUD + `/stats` 全局统计 + `/:id/assign` + `/:id/actions` + `/:id/rating`）、`/api/v1/users`（含 `/drafts`）、`/api/v1/assets`、`/api/v1/uploads`、`/api/v1/notify/dispatch`、`/api/kb/recommend`（注意 kb 不在 `/api/v1` 下）。除 `/api/health` 与 `/api/v1/users/login-options` 外均需 `X-User-Id` 头。
