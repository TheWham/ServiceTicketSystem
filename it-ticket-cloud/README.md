# IT 服务工单系统 · Spring Cloud 微服务版

> 企业级 IT 服务工单系统后端微服务，业务规则对齐《PRD-Ultimate》。
> 本文档描述**当前真实实现**，与代码保持一致（2026-09-29 重构后）。

---

## 目录

- [架构总览](#架构总览)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [种子账号](#种子账号)
- [环境变量与配置](#环境变量与配置)
- [数据库设计](#数据库设计)
- [接口一览](#接口一览)
- [工单状态机](#工单状态机)
- [关键机制](#关键机制)
- [统一响应与错误码](#统一响应与错误码)
- [验证状态](#验证状态)
- [常见问题排查](#常见问题排查)

---

## 架构总览

```
                        ┌─────────────────────────────┐
        浏览器(:5173)    │  Vue3 + Element Plus 前端    │
              │         └─────────────────────────────┘
              │  /api/**  (vite proxy → 8080)
              ▼
   ┌──────────────────────┐
   │  gateway  :8080       │  JWT 统一鉴权 / 路由 / CORS
   └─────────┬────────────┘
             │  lb:// (Nacos 服务发现)
   ┌─────────┴────────────┐
   ▼                       ▼
┌─────────────┐     ┌──────────────────────┐
│ user-service│     │ ticket-service :8201  │
│   :8101     │◄────│ OpenFeign /internal   │
│ 登录/JWT/   │     │ 工单/状态机/路由/SLA/  │
│ 用户/草稿   │     │ 通知/异常队列          │
└──────┬──────┘     └──────────┬───────────┘
       └───────────┬───────────┘
                   ▼
        ┌──────────────────────┐
        │ MySQL it_ticket_system│  统一远程库 120.92.138.195
        │ 28 张表(单库)         │
        └──────────────────────┘
        ┌──────────────────────┐
        │ Nacos :8848           │  注册中心(+可选配置中心)
        └──────────────────────┘
```

| 服务 | 端口 | 职责 |
|:---|:---|:---|
| gateway | 8080 | 唯一入口；JWT 校验、解析后透传 `X-User-Id`/`X-User-Role`、路由、CORS |
| user-service | 8101 | 登录(BCrypt+JWT)、忘记/修改密码、账号管理、用户查询、提单草稿 |
| ticket-service | 8201 | 工单全业务：提单、自动路由、状态机、SLA、通知、异常队列 |

---

## 项目结构

```
it-ticket-cloud/
├── gateway/            # 网关:AuthGlobalFilter(JWT 白名单校验)
├── user-service/       # 用户服务
│   └── src/main/java/com/itticket/user/
│       ├── controller/   # AuthController(认证) / UserController / InternalUserController(Feign)
│       ├── service/      # UserService(登录/密码/账号) / DraftService
│       ├── entity/       # User / UserRoleEntity / TicketDraft
│       └── dto/          # Login/ChangePassword/ForgotPassword/CreateUser/ResetPassword
├── ticket-service/     # 工单服务
│   └── src/main/java/com/itticket/ticket/
│       ├── controller/   # TicketController / CategoryController / SlaController
│       │                 # NotificationController / ExceptionQueueController
│       ├── service/      # TicketService / RoutingService / SlaService
│       │                 # WorkCalendarService / SlaAutoTransitionService
│       │                 # NotificationService / ExceptionQueueService
│       ├── statemachine/ # TicketStateMachine / Transition(流转边) / TicketStatus(9态)
│       └── entity/       # Ticket / TicketTransition / Assignment / SlaInstance ...
├── common/             # Result/错误码/JWT 工具(纯 Java)
├── common-web/         # 全局异常、UserContext 透传头解析、时间格式
├── db/init/            # 00-schema.sql(28表结构) → 10-seed.sql(种子)
├── nacos-config/       # Nacos 配置中心 DataId + 导入 zip + 配置管理说明
├── scripts/            # start-all / start-nacos / init-db(连远程库)
└── docker-compose.yml  # Nacos + MySQL(MySQL 仅可选本地/CI,日常连远程)
```

---

## 快速开始

### 0. 数据库（统一远程）

数据库**统一连远程库** `120.92.138.195:3306`（默认密码 `clt123456`，库名 `it_ticket_system`），无需本地起 MySQL。首次初始化：

```bash
scripts\init-db.cmd    # 默认连远程库,建表+种子;可用 MYSQL_HOST/MYSQL_PASSWORD 覆盖
```

> docker-compose 里的 MySQL 仅为「离线/CI 可选本地库」，日常联调不启动。

### 1. 起 Nacos

```bash
docker compose up -d nacos        # 有 Docker
scripts\start-nacos.cmd           # 无 Docker(Windows standalone,8848/9848)
```

### 2. 构建与启动服务（需 JDK 17 + Maven）

```bash
cd it-ticket-cloud
mvn package                                  # 或 IDEA 分别启动三个 Application
java -jar gateway/target/it-ticket-gateway-1.0.0.jar
java -jar user-service/target/it-ticket-user-service-1.0.0.jar
java -jar ticket-service/target/it-ticket-ticket-service-1.0.0.jar
```

也可 `scripts\start-all.cmd` 一键启动。

**配置加载**：默认加载 `application-dev.yml`（本地 profile，连远程库）。生产 `--spring.profiles.active=prod`（敏感项强制环境变量）。Nacos 配置中心为可选开关 `NACOS_CONFIG_ENABLED=true`，详见 `nacos-config/配置管理说明.md`。

---

## 种子账号

4 个角色（PRD §5.1 大写枚举），**默认密码均为 `123456`**（BCrypt 落库）：

| 用户ID | 员工号 | 姓名 | 角色 |
|:---|:---|:---|:---|
| U_EMP01 | E1001 | 演示员工 | EMPLOYEE |
| U_ENG01 | E2001 | 演示工程师 | ENGINEER |
| U_ADM01 | E3001 | 平台管理员 | PLATFORM_ADMIN |
| U_KBA01 | E4001 | 知识库管理员 | KB_ADMIN |

> `123456` 为演示用默认密码（管理员预置，登录仅校验哈希）。用户「修改密码」时新密码仍需满足强度规则（6-32 位含字母+数字）。

---

## 环境变量与配置

| 变量 | 默认(dev) | 说明 |
|:---|:---|:---|
| `SPRING_PROFILES_ACTIVE` | `dev` | 环境: dev 本地连远程库 / prod 生产 |
| `NACOS_ADDR` | `127.0.0.1:8848` | Nacos 地址 |
| `NACOS_CONFIG_ENABLED` | `false` | 是否启用 Nacos 配置中心(默认本地 profile) |
| `MYSQL_HOST` / `MYSQL_PORT` | `120.92.138.195` / `3306` | 数据库地址 |
| `MYSQL_PASSWORD` | `clt123456` | 数据库密码(prod 必须注入,无默认) |
| `JWT_SECRET` | dev 弱密钥 | JWT 签名密钥(prod 必须注入) |

配置分层：`application.yml`(启动项) → `application-{profile}.yml`(业务) → Nacos(可选覆盖)。

---

## 数据库设计

单库 `it_ticket_system`，28 张表，全部对齐 PRD-Ultimate §20。

**核心表**：
- `user`：`user_id` PK、`employee_no`、`name`、`department_id`、`status`(ACTIVE/DISABLED)、`identity_source`、`password_hash`(BCrypt)、`created_at/updated_at`
- `user_role`：`user_id + role_code`(EMPLOYEE/ENGINEER/PLATFORM_ADMIN/KB_ADMIN)、`granted_at/revoked_at`
- `ticket`：`ticket_id` PK(TK+日期+序号)、`title`、`ticket_nature`(INCIDENT/SERVICE_REQUEST)、`category_id`、`impact/urgency_description`、`priority`(HIGH/MEDIUM/LOW)、`status`(9态)、`assignee_id`、`idempotency_key`、`version`(乐观锁) 等
- `ticket_transition`：流转日志(只追加)
- `assignment`：派单记录、`response_deadline/responded_at`
- `sla_instance` / `sla_pause` / `work_calendar`：SLA 计时三件套
- `notification`：通知(`event_id+receiver+channel` 幂等)
- `exception_queue`：异常队列(路由失败/补充超限/外部等待超时)
- `category` / `category_route` / `support_team` / `team_member`：分类与路由
- `attachment` / `ticket_draft` 等

DDL 见 `db/init/00-schema.sql`，种子见 `db/init/10-seed.sql`。

---

## 接口一览

统一响应 `{code, msg, data}`，`code=0` 成功。经网关 `http://localhost:8080/api/v1/**`。

### 认证与用户（user-service，基路径 `/api/v1/users`）

| 方法 | 路径 | 权限 | 说明 |
|:---|:---|:---|:---|
| POST | `/login` | 免认证 | 登录 `{userId,password}` → `{token,user}` |
| GET | `/login-options` | 免认证 | 可登录用户列表 |
| POST | `/forgot-password` | 免认证 | 忘记密码(工号+姓名+员工号三要素→重置) |
| POST | `/change-password` | 登录 | 修改密码(旧密码校验) |
| GET | `/me` | 登录 | 当前用户 |
| GET | `/accounts` | ADMIN/KB_ADMIN | 账号列表(可视化) |
| POST | `/accounts` | ADMIN/KB_ADMIN | 新建账号(注册仅主管) |
| POST | `/accounts/{id}/reset-password` | ADMIN/KB_ADMIN | 重置他人密码 |
| GET/POST/DELETE | `/drafts` | 登录 | 提单草稿(每用户一条) |

### 工单（ticket-service，基路径 `/api/v1/tickets`）

| 方法 | 路径 | 权限 | 说明 |
|:---|:---|:---|:---|
| POST | `/` | 登录 | 创建工单;`idempotency_key` 幂等(重复返回已有);创建后自动路由 |
| GET | `/` | 登录 | 列表(状态/分类/优先级/关键字等筛选+分页) |
| GET | `/{id}` | 登录 | 详情 + 流转日志 + 附件 |
| POST | `/{id}/claim` | ENGINEER | 接单(矩阵确认影响×紧急→算优先级) |
| POST | `/{id}/assign` | PLATFORM_ADMIN | 派单/改派 |
| POST | `/{id}/actions` | 状态机 | 状态操作(见下) |
| POST | `/{id}/rating` | 登录 | 评价 1-5 星(仅已完成) |

**actions 支持的动作**（body `{action, remark, ...}`）：
`progress`(进度)、`need_info`(请求补充)、`supply_info`(补充)、`external`(外部等待)、`external_resolved`(外部恢复)、`done`(提交方案)、`accept`(验收通过)、`cancel`(撤销) 等。

### 其他

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| GET | `/api/v1/categories/leaf` | 末级分类(提单下拉) |
| GET | `/api/v1/sla/{ticketId}` | SLA 计时(target_at/已用工时/剩余工作秒) |
| GET | `/api/v1/notifications` | 通知列表(分页) |
| GET | `/api/v1/notifications/pending-count` | 未读数(前端 30s 轮询) |
| GET | `/api/v1/exceptions` | 异常队列(管理员) |
| POST | `/api/v1/exceptions/{id}/resolve` | 标记异常已解决 |

### 内部接口（user-service，基路径 `/api/internal/users`，网关不暴露）

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| GET | `/{userId}` | 单查用户 |
| POST | `/batch` | 批量查询 |
| GET | `/engineers` | 在职工程师列表(路由用) |
| GET | `/admins` | 管理员列表(路由失败通知用) |

---

## 工单状态机

PRD §9，**9 态**（英文枚举）：`NEW / ASSIGNED / IN_PROGRESS / PENDING_SUPPLEMENT / PENDING_EXTERNAL / PENDING_ACCEPTANCE / COMPLETED / CANCELLED / CLOSED`

流转由 `statemachine/Transition.java` 的 **18 条声明式流转边** 驱动，`TicketStateMachine.validateTransition` 三重校验（边存在/角色/业务守卫）。

关键自动边：响应超时转派、72h 未补充自动关闭、48h 未验收自动通过、路由失败保持 NEW + 进异常队列 + 通知管理员。守卫：补充信息累计 3 次上限、外部等待超 5 工作日进异常队列。每次流转写 `ticket_transition`，并按事件发通知。

---

## 关键机制

- **自动路由(F-06)**：创建后按 `category_route` 定位支持组 → 组内加权负载选工程师；无候选保持 NEW + 进异常队列 + 通知管理员。
- **优先级矩阵(§11.4)**：提单不填优先级(暂按 MEDIUM);工程师接单时确认「影响×紧急」3×3 矩阵算出正式优先级,触发 SLA 重算。
- **SLA 计时(F-08)**：按优先级生成目标(HIGH 4工作小时/MEDIUM 1工作日/LOW 3工作日),基于 `work_calendar` 只计工作时间;补充/外部等待暂停;80%/违约扫描 + 48h/72h 自动流转。前端 SlaBadge/SlaTimer 以服务端剩余工作秒为基准倒计时。
- **站内通知(F-10)**：流转事件驱动,`event_id+receiver+channel` 生命周期幂等;中文文案 + `/tickets/:id` 点击直达;失败重试入异常队列。
- **幂等**：提单 `idempotency_key`(uk_idem 唯一索引) + 通知幂等键 + 乐观锁 `version`。

---

## 统一响应与错误码

`{code, msg, data}`，`code=0` 成功。

| code | 说明 |
|:---|:---|
| 40001 | 参数校验失败 |
| 40100 / 40101 | 未登录 / 用户禁用 |
| 40300 | 权限不足(如「需要 PLATFORM_ADMIN 权限」) |
| 40400 | 资源不存在 |
| 40901 | 幂等冲突 |
| 40910 | 非法状态转移 |

---

## 验证状态

- 后端编译 0 错误；状态机单测 12/12 通过；前端构建成功
- 数据库字段/枚举/优先级矩阵已按 PRD-Ultimate 全量对齐
- 验收评测 27 项用例全绿（`acceptance/`，含 TC-10 注入防护）

---

## 常见问题排查

| 现象 | 排查 |
|:---|:---|
| 登录 401 | 确认连的是远程库(120.92.138.195)；种子密码是否被改；JWT_SECRET 是否一致 |
| 提单后无人接 | 查 `exception_queue` 是否有路由失败记录；该分类是否配 `category_route`；团队是否有 ACTIVE 工程师 |
| 分类下拉空 | 确认 gateway 已重启(路由 `/api/v1/categories/**`)；category 表有末级分类 |
| 通知不跳转 | 确认 ticket-service 为含 `@JsonNaming` 蛇形的新 jar；Notification 返回字段应为 `action_url` |
| 配置不生效 | 确认 profile(dev/prod)；Nacos 是否启用(`NACOS_CONFIG_ENABLED`)；本地 yml 为基线 |
