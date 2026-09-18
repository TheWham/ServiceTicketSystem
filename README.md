# IT 服务工单系统 — 全栈项目 (P0 MVP)

> 企业级 IT 服务工单管理系统，覆盖**提单→派单→处理→验收→评价**完整闭环。

---

## 技术栈

| 层 | 技术 |
|:---|:---|
| 前端 | Vue 3 + Vite + Pinia + Vue Router + Axios |
| 后端 | Node.js + Express |
| 数据库 | **SQLite**（better-sqlite3，零安装、文件型） |
| 认证 | Mock（请求头 `X-User-Id`） |

> 数据库层已封装为 MySQL 风格异步 API 兼容层（`backend/src/db.js`），
> 如需切回 MySQL，只需替换 `db.js` 并执行 `db/schema.sql` + `db/seed.sql`。

---

## 项目结构

```
it-ticket-system/
├── backend/                  # 后端 (Express, Port 3001)
│   ├── db/
│   │   ├── schema.sqlite.sql # ✅ SQLite 建表脚本 (5张表)
│   │   ├── seed.sqlite.sql   # ✅ SQLite 种子数据 (3角色共6人 + 3条示例工单)
│   │   ├── init.js           # ✅ 一键初始化 (npm run db:init)
│   │   ├── schema.sql        # (备用) MySQL 建表脚本
│   │   ├── seed.sql          # (备用) MySQL 种子数据
│   │   └── it_ticket.db      # SQLite 数据库文件 (自动生成)
│   ├── src/
│   │   ├── index.js          # 入口 (Express App)
│   │   ├── db.js             # SQLite 连接 + MySQL 风格兼容层
│   │   ├── controllers/
│   │   │   ├── ticketController.js  # 工单 CRUD + 状态流转 + 评价
│   │   │   └── userController.js    # 用户查询 + Mock登录 + 草稿
│   │   ├── middleware/
│   │   │   ├── auth.js       # Mock 认证 + 角色守卫
│   │   │   └── errorHandler.js
│   │   ├── routes/
│   │   │   ├── tickets.js    # /api/v1/tickets/*
│   │   │   └── users.js      # /api/v1/users/*
│   │   └── services/
│   │       ├── stateMachine.js    # 状态机引擎 (合法转移+通知事件+接收人)
│   │       ├── notification.js    # 通知服务 (模拟企微+幂等)
│   │       └── idGenerator.js     # 工单号生成 TK+yyyyMMdd+4位自增
│   └── package.json
├── frontend/                 # 前端 (Vue 3 + Vite, Port 5173)
│   ├── src/
│   │   ├── main.js + App.vue      # 入口 + 全局布局
│   │   ├── api/index.js           # Axios 封装 (自动注入 X-User-Id)
│   │   ├── router/index.js        # 路由 (login/employee/engineer/supervisor)
│   │   ├── stores/user.js         # Pinia 用户状态
│   │   └── views/
│   │       ├── LoginView.vue      # Mock 登录页 (选择身份)
│   │       ├── EmployeeView.vue   # 员工端：提单+表单校验+草稿+我的工单+验收评价
│   │       ├── EngineerView.vue   # 工程师端：看板工作台+状态操作+15s轮询
│   │       └── SupervisorView.vue # 主管端：全局工单+派单/改派+统计卡+强制恢复
│   └── vite.config.js
└── README.md
```

---

## 快速启动

### 1. 初始化数据库

```bash
cd backend
npm install
npm run db:init    # 建表 + 写入种子数据（幂等，可重复执行）
```

### 2. 启动后端

```bash
cd backend
npm run dev        # nodemon 热重载，监听 :3001
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev        # Vite 热重载，监听 :5173
```

### 4. 访问

打开 `http://localhost:5173`，选择一个身份（在 `db/seed.sql` 里预置）：

| 用户 | 角色 | 说明 |
|:---|:---|:---|
| 张小明 | 员工 | 市场部，可提单/验收 |
| 李丽 | 员工 | 财务部 |
| 王强 | 员工 | 研发部 |
| 赵工 | 工程师 | IT部，可处理工单 |
| 钱工 | 工程师 | IT部 |
| 孙主管 | 主管 | IT部，可派单/改派/全局管理 |

---

## 核心 API 一览

| 方法 | 路径 | 用途 | 需角色 |
|:---|:---|:---|:---|
| POST | /api/v1/tickets | 创建工单 (幂等 client_token) | 全员 |
| GET | /api/v1/tickets | 工单列表 (支持筛选) | 全员 |
| GET | /api/v1/tickets/:id | 工单详情+流转日志 | 全员 |
| POST | /api/v1/tickets/:id/assign | 派单/改派 | 主管 |
| POST | /api/v1/tickets/:id/actions | 状态操作 (progress/need_info/external/done/reject/accept) | 按角色 |
| POST | /api/v1/tickets/:id/rating | 满意度评价 (1-5星) | 员工 |
| GET | /api/v1/users/login-options | Mock 登录选项 | 无需认证 |
| POST | /api/v1/users/drafts | 草稿保存 (UPSERT) | 员工 |
| GET | /api/v1/users/drafts | 获取草稿 | 员工 |

### 错误码约定

| 码 | 含义 |
|:---|:---|
| 40001 | 参数校验失败 |
| 40021 | 处理人无效 |
| 40300 | 权限不足 |
| 40901 | client_token 重复(幂等) |
| 40910 | 非法状态转移 |

---

## 状态机

```
待处理 ──派单──▶ 处理中 ──完成──▶ 待验收 ──通过──▶ 已完成
  │              │  ▲              │  │
  │              │  │    ┌─驳回───┘  │
  │              ▼  │    ▼          │
  │           待补充──┘   │          │
  │              │        │          │
  │              ▼        │          │
  ▼           已取消      │          │
已取消                    ▼          │
                       待外部───────┘
```

完整状态转移表见 PRD 规格文档 §2.2。

---

## P1/P2 预留 (本期未实现)

- [ ] 文件上传 (OSS/S3 截图存储)
- [ ] 企业微信真实推送 + 短信兜底
- [ ] AI 知识库推荐 (提单时防抖 800ms)
- [ ] SLA 超时自动升级通知主管
- [ ] 统计报表大屏
- [ ] CMDB 资产联动 (`asset_id` 字段已预留)
- [ ] JWT 真实认证