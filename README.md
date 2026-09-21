# IT 服务工单系统 — 全栈项目

> 企业级 IT 服务工单管理系统,覆盖**提单→派单→处理→验收→评价**完整闭环。
> 后端已完成 **Node.js 单体 → Spring Cloud 微服务** 迁移,新旧两套并存,前端默认对接微服务版。

---

## 技术栈

| 层 | 微服务版(当前) | 旧单体版(legacy) |
|:---|:---|:---|
| 前端 | Vue 3 + Vite + Pinia + Vue Router + Axios | 同左 |
| 后端 | Java 17 + Spring Boot 3.2.5 + Spring Cloud 2023.0.1 + Spring Cloud Alibaba | Node.js + Express |
| 数据库 | MySQL 8(双库 it_user / it_ticket) | SQLite(better-sqlite3) |
| 服务治理 | Nacos(注册中心)+ OpenFeign + Gateway | — |
| 认证 | JWT(HS256,12h)+ BCrypt,网关统一鉴权 | Mock(请求头 X-User-Id) |

## 项目结构

```
it-ticket-system/
├── it-ticket-cloud/          # ✅ 微服务后端(当前使用)
│   ├── gateway/              # 网关 :8080 —— 唯一入口 + JWT 统一鉴权 + 路由
│   ├── user-service/         # 用户服务 :8101 —— 登录/JWT、用户、草稿(库 it_user)
│   ├── ticket-service/       # 工单服务 :8201 —— 工单全业务、状态机、通知(库 it_ticket)
│   ├── common/               # Result/错误码/JWT 工具(纯 Java,gateway 可引用)
│   ├── common-web/           # 全局异常、UserContext 透传头解析、时间格式
│   ├── db/init/              # MySQL 建库 + 建表 + 种子(自动执行顺序 00→21)
│   ├── scripts/              # 本地一键启动/初始化脚本(Windows)
│   ├── docker-compose.yml    # Nacos + MySQL 一键起(Docker 环境)
│   └── README.md             # 微服务版详细文档 ⭐
├── backend/                  # 旧 Node.js 单体(:3001,保留作行为基准,可随时删除)
│   ├── db/                   # SQLite 建表/种子/init 脚本
│   └── src/                  # Express 入口、controllers、stateMachine 等
└── frontend/                 # Vue 3 前端(:5173,vite proxy /api → 8080)
    └── src/
        ├── api/index.js      # Axios 封装(自动注入 Authorization: Bearer)
        ├── stores/user.js    # Pinia(token + 用户信息,localStorage 持久化)
        └── views/            # 登录(选身份+密码)/ 员工端 / 工程师端 / 主管端
```

## 快速开始(微服务版)

### 1. 起依赖

**有 Docker:**
```bash
cd it-ticket-cloud && docker compose up -d   # Nacos(8848/9848) + MySQL(3306,自动建库+种子)
```

**无 Docker(Windows,本项目已验证的方式):**
```bash
# MySQL 免安装版:Nacos 需先就绪顺序无要求
it-ticket-cloud\scripts\start-mysql-local.cmd   # 首次自动初始化数据目录并启动 3306
it-ticket-cloud\scripts\start-nacos.cmd         # standalone 模式启动 8848/9848
it-ticket-cloud\scripts\init-db.cmd             # 建库+建表+种子(root/root123)
```

### 2. 起服务(需 JDK 17 + Maven)

```bash
cd it-ticket-cloud
mvn package                                    # 或 IDE 中分别启动三个 Application
java -jar gateway/target/it-ticket-gateway-1.0.0.jar
java -jar user-service/target/it-ticket-user-service-1.0.0.jar
java -jar ticket-service/target/it-ticket-ticket-service-1.0.0.jar
```

环境变量(均有默认值):`NACOS_ADDR=127.0.0.1:8848`、`MYSQL_PASSWORD=root123`、`JWT_SECRET`(生产必换)。

### 3. 起前端

```bash
cd frontend && npm run dev    # 5173,proxy /api → 8080 网关
```

### 4. 登录

种子账号 6 个,**默认密码均为 `123456`**:

| 账号 | 姓名 | 角色 |
|:---|:---|:---|
| U001 | 张小明 | 员工 employee |
| U002 | 李丽 | 员工 employee |
| U003 | 王强 | 员工 employee |
| U004 | 赵工 | 工程师 engineer |
| U005 | 钱工 | 工程师 engineer |
| U006 | 孙主管 | 主管 supervisor |

## API 一览(与旧版完全兼容)

统一响应 `{code, msg, data}`,`code=0` 成功。经网关访问:`http://localhost:8080/api/v1/**`。

| 方法 | 路径 | 说明 | 权限 |
|:---|:---|:---|:---|
| GET | /api/health | 健康检查 | 免认证 |
| POST | /api/v1/users/login | 登录,`{userId,password}` → `{token,user}` | 免认证 |
| GET | /api/v1/users/login-options | 可登录用户列表 | 免认证 |
| GET | /api/v1/users/me | 当前用户 | 登录 |
| GET | /api/v1/users?role= | 用户列表(派单用) | 登录 |
| GET/POST/DELETE | /api/v1/users/drafts | 提单草稿(每用户一条) | 登录 |
| POST | /api/v1/tickets | 创建工单(client_token 幂等) | 登录 |
| GET | /api/v1/tickets | 列表(8 种筛选 + 分页) | 登录 |
| GET | /api/v1/tickets/:id | 详情 + 流转日志 | 登录 |
| POST | /api/v1/tickets/:id/assign | 派单/改派 | supervisor |
| POST | /api/v1/tickets/:id/claim | 领取(条件更新防抢领) | engineer |
| POST | /api/v1/tickets/:id/actions | 状态操作(progress/need_info/external/done/accept/reject/cancel/supply_info/external_resolved) | 状态机校验 |
| POST | /api/v1/tickets/:id/rating | 评价 1-5 星(仅已完成) | 登录 |

核心错误码:`40001` 参数校验、`40021` 处理人无效、`40100/40101` 未登录/用户禁用、`40300` 权限不足、`40400` 工单不存在、`40901` 幂等冲突、`40910` 非法状态转移、`40912` 已被他人领取。

工单状态机:待处理→处理中→待补充/待外部→待验收→已完成/已取消,7 状态 12 条转移规则(含驳回≥10字、完成需有进展记录等 guard),每次流转写 `ticket_flow_log`,并按事件类型异步发通知(`notification_log` 落库,1 分钟幂等)。

## 迁移验证状态(2026-09-21)

全链路已在本地实测通过:登录/JWT、网关鉴权与透传、建单+幂等、工单号连续、派单 403/40021、领取防抢领、状态机 guard、验收评分、撤回、草稿 CRUD、7 种通知事件落库。详见 [it-ticket-cloud/README.md](it-ticket-cloud/README.md)。

## 与旧版的差异

| 差异点 | 说明 |
|:---|:---|
| 登录 | Mock 选身份 → 选身份+密码,JWT 12h;`X-User-Id` 头不再被信任(网关剥离防伪造) |
| 40101 校验位置 | 旧版每请求查库;新版由网关统一调 user-service 校验 |
| client_token 并发幂等 | 旧版并发会 500;新版识别后幂等返回已有工单 |
| 错误响应 | data 为 null 时省略字段(前端只读 code/msg,无影响) |

---

<details>
<summary><b>旧 Node.js 单体(legacy,已停用)</b></summary>

```bash
cd backend && npm install && npm run db:init && npm start   # :3001
```
前端切回旧后端:把 `frontend/vite.config.js` 的 proxy target 改回 `http://localhost:3001`。
技术细节见 `backend/` 源码与 `db/schema.sqlite.sql`(5 张表)、`db/init.js`(一键建库)。

</details>
