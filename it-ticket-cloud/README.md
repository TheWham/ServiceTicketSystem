# IT 服务工单系统 · Spring Cloud 微服务版

由 Node.js(Express + SQLite)单体迁移而来的 Spring Cloud 微服务后端。**API 路径、`{code,msg,data}` 响应包裹、错误码与前端除登录外完全兼容**。

- 技术栈:Java 17 + Spring Boot 3.2.5 + Spring Cloud 2023.0.1 + Spring Cloud Alibaba 2023.0.1.2
- 注册/配置中心:Nacos 2.3.2;数据库:MySQL 8(每服务独立库);ORM:MyBatis-Plus 3.5.7
- 认证:JWT(jjwt 0.12.6,HS256,12h)+ BCrypt 密码;服务间调用:OpenFeign

## 目录

- [架构总览](#架构总览)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [种子账号](#种子账号)
- [环境变量](#环境变量)
- [数据库设计](#数据库设计)
- [接口一览](#接口一览)
- [工单状态机](#工单状态机)
- [关键机制](#关键机制)
- [统一响应与错误码](#统一响应与错误码)
- [与旧版的差异](#与旧版的差异)
- [验证状态](#验证状态)
- [常见问题排查](#常见问题排查)
- [待办(P1)](#待办p1)

## 架构总览

```
frontend (5173, vite proxy /api → 8080)
   │
   ▼
gateway :8080 ──── JWT 统一鉴权(AuthGlobalFilter),剥离/注入 X-User-* 头
   │  ├─ /api/v1/users/**    → lb://user-service
   │  └─ /api/v1/tickets/**  → lb://ticket-service
   │
   ├── user-service :8101   库 it_user(user、ticket_draft)
   │      登录签发 JWT、login-options、me、用户列表、草稿 CRUD、
   │      /api/internal/users(供 gateway 校验用户、供 ticket-service 查处理人)
   │
   └── ticket-service :8201 库 it_ticket(ticket、ticket_flow_log、notification_log)
          工单创建(幂等+编号)/列表/详情/派单/领取/状态操作/评分、
          状态机、通知(事务提交后异步 + 1 分钟幂等)、OpenFeign → user-service

注册中心/配置中心:Nacos(8848 HTTP / 9848 gRPC)
```

| 服务 | 端口 | 数据库 | 职责 |
|---|---|---|---|
| gateway | 8080 | — | 唯一入口:JWT 鉴权、用户状态二次校验、路由转发、CORS、健康检查 |
| user-service | 8101 | it_user | 登录/用户查询/提单草稿/内部用户接口 |
| ticket-service | 8201 | it_ticket | 工单全生命周期:创建/列表/派单/领取/状态流转/评分/通知 |

## 项目结构

```
it-ticket-cloud/
├── pom.xml                 # 父 pom(聚合 5 个模块,统一依赖版本)
├── docker-compose.yml      # 本地依赖:mysql:8.0 + nacos:v2.3.2
├── common/                 # it-ticket-common:纯 Java 公共包
│   └── Result / ErrorCode / BizException / JwtUtil / UserInfo
├── common-web/             # it-ticket-common-web:Web 公共包(业务服务引用,gateway 不引用)
│   └── GlobalExceptionHandler / UserContext(+Interceptor) / JacksonTimeConfig
├── gateway/                # 网关(WebFlux,勿引 spring-boot-starter-web)
│   └── AuthGlobalFilter / CorsConfig / JwtProperties / HealthController
├── user-service/           # 用户服务(8101)
│   └── AuthController / UserController / DraftController / InternalUserController
├── ticket-service/         # 工单服务(8201)
│   └── TicketController / TicketService / TicketStateMachine / NotificationService / UserClient(Feign)
├── db/init/                # 建库 + 建表 + 种子 SQL(00/10/11/20/21 顺序执行)
└── scripts/                # Windows 本地脚本(start-all / start-mysql-local / start-nacos / init-db)
```

**构建产物 jar**(供 `scripts/start-all.cmd` 使用):

- `gateway/target/it-ticket-gateway-1.0.0.jar`
- `user-service/target/it-ticket-user-service-1.0.0.jar`
- `ticket-service/target/it-ticket-ticket-service-1.0.0.jar`

## 快速开始

### 方式 A:Docker(推荐)

```bash
cd it-ticket-cloud
docker compose up -d          # 起 MySQL(自动挂载 db/init 建库+种子) 和 Nacos
```

- MySQL 容器 `it-ticket-mysql`:3306,root 密码 `root123`,首次启动自动执行 `db/init/*.sql`
- Nacos 容器 `it-ticket-nacos`:8848(控制台/OpenAPI)+ 9848(gRPC,2.x 客户端必需),standalone

### 方式 B:Windows 本地脚本(无 Docker)

1. **MySQL 8**:免安装版解压后直接运行 `scripts\start-mysql-local.cmd`(首次自动 `--initialize-insecure` 初始化)
2. **初始化数据库**(一次性,MySQL 已启动时):

   ```cmd
   scripts\init-db.cmd
   ```

   等价于按顺序执行 `db/init/` 下 5 个 SQL(00 建库 → 10/11 user 库表+种子 → 20/21 ticket 库表+种子),默认 `root/root123`,不同请改脚本内 `-p`。
3. **Nacos**:下载 nacos-server 2.3.x zip(https://github.com/alibaba/nacos/releases),解压后:

   ```cmd
   scripts\start-nacos.cmd [Nacos安装目录]
   ```

   需放行 8848(HTTP)与 9848(gRPC)端口。

### 构建与启动服务

```bash
# 需 JDK 17 + Maven(或直接用 IDEA 打开构建)
mvn package                    # 根目录聚合构建,生成三个可运行 jar

# 依次(或用 start-all.cmd 一键)启动
java -jar gateway/target/it-ticket-gateway-1.0.0.jar
java -jar user-service/target/it-ticket-user-service-1.0.0.jar
java -jar ticket-service/target/it-ticket-ticket-service-1.0.0.jar
```

`scripts\start-all.cmd` 一键启动全家桶:MySQL → Nacos(等待 25s)→ 三个微服务(各占一个独立 cmd 窗口)。启动顺序本地可任意,保证 Nacos 先就绪即可。

**验证**:`curl http://127.0.0.1:8080/api/health` → `{"status":"ok",...}`;前端单独 `cd frontend && npm run dev`。

## 种子账号

6 个账号,**统一默认密码 `123456`**(BCrypt 存储,见 `db/init/11-user-seed.sql`):

| userId | 姓名 | 角色 | 部门 |
|---|---|---|---|
| U001 | 张小明 | employee(员工) | 市场部 |
| U002 | 李丽 | employee(员工) | 财务部 |
| U003 | 王强 | employee(员工) | 研发部 |
| U004 | 赵工 | engineer(工程师) | IT部 |
| U005 | 钱工 | engineer(工程师) | IT部 |
| U006 | 孙主管 | supervisor(主管) | IT部 |

另预置 3 条示例工单(`TK202609180001` 待处理 / `TK202609180002` 处理中 / `TK202609180003` 待验收)及对应流转日志。

## 环境变量

所有配置均有默认值,本地零配置可跑;生产用环境变量或 Nacos 配置中心覆盖:

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `NACOS_ADDR` | `127.0.0.1:8848` | Nacos 注册中心地址(三个服务共用) |
| `MYSQL_HOST` / `MYSQL_PORT` | `localhost` / `3306` | MySQL 地址(user→it_user,ticket→it_ticket) |
| `MYSQL_USERNAME` / `MYSQL_PASSWORD` | `root` / `root123` | MySQL 账号 |
| `JWT_SECRET` | `it-ticket-dev-jwt-secret-key-32bytes-minimum!!` | JWT 密钥,**gateway 与 user-service 必须一致;生产必换** |

JWT 有效期 12 小时(`itticket.jwt.ttl-hours`,代码默认 12)。

## 数据库设计

数据库按服务拆分:`it_user`(user-service 拥有)、`it_ticket`(ticket-service 拥有),均 utf8mb4。

### it_user 库

**user**(用户表):`user_id` PK、`name`、`role` ENUM(employee/engineer/supervisor)、`department`、`phone`、`wechat_id`、`password_hash`(BCrypt)、`status` ENUM(active/inactive)、`created_at/updated_at`。索引:`idx_role`、`idx_department`。

**ticket_draft**(提单草稿,每用户一条):`draft_id` PK、`user_id` **唯一索引** `uk_user_draft`、`title/category/sub_category/priority/description/asset_id/expected_finish_time`、`attachment_urls` JSON、`updated_at`。

### it_ticket 库

**ticket**(工单表):`ticket_id` PK(工单号)、`title`(≤50)、`description`(10-500)、`category` ENUM(硬件/软件/网络/账号/其他)、`sub_category`(预留)、`priority` ENUM(高/中/低)、`status` ENUM(待处理/处理中/待补充/待外部/待验收/已完成/已取消)、`creator_id`、`assignee_id`、`asset_id`(预留 CMDB)、`expected_finish_time`、`attachment_urls` JSON(≤3)、`client_token`(幂等)、`first_response_at`、`solved_at`、`pause_minutes`、`rating_score`(1-5)、`rating_comment`(≤200)、`rated_at`、`created_at/updated_at`。索引:唯一 `uk_client_token` + `idx_status/idx_creator/idx_assignee/idx_category/idx_priority/idx_created`。

**ticket_flow_log**(流转日志):`log_id` PK、`ticket_id`、`from_status`(可 NULL,创建时)、`to_status`、`operator_id`、`remark`(≤500)、`created_at`。

**notification_log**(通知记录):`id` PK、`ticket_id`、`event_type`、`receiver_id`、`channel` ENUM(企微/短信/站内)、`is_fallback`、`delivery_status` ENUM(SUCCESS/FAILED/PENDING)、`created_at`。索引:复合 `idx_ticket_event(ticket_id, event_type)`(幂等查询用)、`idx_receiver`。

## 接口一览

前端经网关访问(网关校验 JWT 后向下游注入 `X-User-Id/Name/Role/Dept` 头);`/api/internal/**` 不配网关路由,仅服务间可达。

### 认证与用户(user-service,基路径 `/api/v1/users`)

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| POST | `/login` | 免 | body `{userId, password}` → `data:{token, user}`;用户/密码错误统一 40001「用户名或密码错误」 |
| GET | `/login-options` | 免 | 可登录的活跃用户列表(userId/name/role/department),前端先选身份再输密码 |
| GET | `/me` | 需 | 当前登录用户信息 |
| GET | `/` | 需 | 用户列表,可选 `?role=` 过滤(仅活跃用户) |
| GET/POST/DELETE | `/drafts` | 需 | 提单草稿:查(无则 data=null)/保存(UPSERT,每人一条)/清除 |

### 工单(ticket-service,基路径 `/api/v1/tickets`)

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| POST | `/` | 登录用户 | 创建工单;`client_token` 幂等(重复提交返回已有工单,HTTP 200;新建 HTTP 201);校验:标题≤50/描述10-500/分类五选一/优先级三选一/附件≤3/期望完成时间不早于当前 |
| GET | `/` | 登录用户 | 分页列表(page/page_size,按创建时间倒序);筛选:status/category/priority/assignee_id/creator_id/`unassigned=1`(待处理且未指派)/`mine_or_pool`(我负责的+待领取池) |
| GET | `/{id}` | 登录用户 | 详情 `{ticket, flow_logs}`,姓名经 Feign 批量组装(creator/assignee/operator) |
| POST | `/{id}/assign` | supervisor | 派单/改派;处理人须为在职工程师(Feign 校验);body `{assignee_id, reason}` |
| POST | `/{id}/claim` | engineer | 领取:条件更新 `assignee_id IS NULL AND status='待处理'`,失败 40912 |
| POST | `/{id}/actions` | 见状态机 | 状态操作,body `{action, remark}`;action 白名单:progress/need_info/external/done/accept/reject/cancel/supply_info/external_resolved |
| POST | `/{id}/rating` | 登录用户 | 评分 1-5 + 评语≤200,仅「已完成」工单可评 |

### 内部接口(user-service,基路径 `/api/internal/users`)

| 方法 | 路径 | 调用方 |
|---|---|---|
| GET | `/{userId}` | gateway(登录态用户状态二次校验)、ticket-service(派单校验处理人) |
| POST | `/batch` body `{ids:[...]}` | ticket-service(列表/详情姓名组装;失败降级姓名为 null,不阻塞) |

## 工单状态机

7 个状态:`待处理 → 处理中 → 待补充/待外部 → 待验收 → 已完成`,`待处理 → 已取消`(员工撤回),终态无转出。

| 从 | 到 | action | 允许角色 | guard 条件 |
|---|---|---|---|---|
| 待处理 | 处理中 | assign | supervisor | — |
| 待处理 | 处理中 | claim | engineer | 条件更新抢占,已被领走报 40912 |
| 待处理 | 已取消 | cancel | employee(撤回) | 清空 assignee |
| 处理中 | 待补充 | need_info | engineer | — |
| 处理中 | 待外部 | external | engineer | remark ≥10 字 |
| 处理中 | 待验收 | done | engineer | remark ≥5 字;须已有至少一条本人处理进展记录 |
| 待补充 | 处理中 | supply_info | employee | — |
| 待外部 | 处理中 | external_resolved | engineer/supervisor | — |
| 待验收 | 已完成 | accept | employee(验收通过) | 写 solved_at |
| 待验收 | 处理中 | reject | employee(驳回) | remark ≥10 字 |
| 待补充 | 已取消 | timeout | system | 预留:超时未补充 |
| 待验收 | 已完成 | auto_accept | system | 预留:超时 3 工作日自动通过 |

> `timeout`/`auto_accept` 两条规则已在状态机预留,调度器属 P1 待办。

非法转移返回 40910;每次转移写 `ticket_flow_log`(创建时 remark=「提交工单」)。

## 关键机制

- **网关鉴权(AuthGlobalFilter)**:白名单(`/api/health`、`/login`、`/login-options`)外要求 `Authorization: Bearer <token>`;解析 claims(sub=userId,name/role/dept);**再经 WebClient 调 user-service 校验用户在职状态**(超时 3s,非 active → 401/40101,调用失败 → 500/50000);用 `headers.set()` 覆盖注入 `X-User-*` 头剥离客户端伪造,中文值 UTF-8 URL 编码、下游解码;缺 token/无效 → 401/40100。
- **幂等**:创建时 `client_token` 存库并走唯一索引;命中则 HTTP 200 返回已有工单号「重复提交(幂等)」;工单号撞号重试最多 5 次,重试间隙再查 token 防并发窗口重复建单。
- **工单号**:`TK` + `yyyyMMdd` + 4 位自增(取当日最大号 +1),如 `TK202609210001`。
- **通知**:事务提交后(`afterCommit`)经专用线程池(核心 2/最大 4/队列 200)异步发送,失败仅记日志;P0 为模拟企微(写 `notification_log`,delivery_status=SUCCESS);**幂等:同 ticket_id+event_type 1 分钟内只发第一条**。事件:SUBMIT_SUCCESS(创建→创建者)、DISPATCH(派单/领取→处理人)、PENDING_SUPPLEMENT、PENDING_EXTERNAL、PENDING_ACCEPTANCE、ACCEPT_APPROVED、ACCEPT_REJECTED、INFO_SUPPLIED、EXTERNAL_RESOLVED、TIMEOUT_CANCEL、CANCEL、STATUS_CHANGED。
- **UserContext 链路**:gateway 注入 `X-User-*` 头 → common-web `UserContextInterceptor` 读头组装 ThreadLocal(缺 `X-User-Id` 抛 40100,兼容直连场景)→ 业务代码 `UserContext.get()` / `checkRole(...)`;请求结束自动清理。
- **统一时间格式**:Jackson 全局 `yyyy-MM-dd HH:mm:ss`;反序列化兼容 `HH:mm:ss` / ISO / datetime-local 三种格式。
- **全局异常**:BizException 按错误码映射 HTTP 状态;参数绑定失败 → 40001;404 → 40400「接口不存在: xxx」;兜底 50000。

## 统一响应与错误码

所有响应包裹为 `{code, msg, data}`,`code=0` 成功;错误响应省略 `data:null` 字段(前端只读 code/msg)。

| code | 枚举 | 含义 | HTTP |
|---|---|---|---|
| 40001 | PARAM_INVALID | 参数校验失败 | 400 |
| 40021 | ASSIGNEE_INVALID | 处理人无效或非在职工程师 | 400 |
| 40100 | NO_AUTH | 未登录/凭证缺失或无效 | 401 |
| 40101 | USER_INVALID | 用户不存在或已禁用 | 401 |
| 40300 | FORBIDDEN | 权限不足(如「需要 supervisor 或 engineer 权限」) | 403 |
| 40400 | TICKET_NOT_FOUND | 工单不存在/接口不存在 | 404 |
| 40901 | IDEMPOTENT_CONFLICT | 重复提交 | 409 |
| 40910 | ILLEGAL_TRANSITION | 非法状态转移 | 409 |
| 40911 | NOT_CLAIMABLE | 当前工单不可领取,请使用派单功能 | 409 |
| 40912 | ALREADY_CLAIMED | 手慢了,该工单已被其他工程师领取 | 409 |
| 50000 | SYSTEM_ERROR | 服务器内部错误 | 500 |

## 与旧版的差异(有意为之)

| 差异点 | 说明 |
|---|---|
| 登录 | Mock 选择身份 → 选身份+密码,JWT 12h;`X-User-Id` 头不再被信任(网关会剥离防伪造) |
| 40101 校验位置 | 旧版每个请求查库校验用户;新版由网关统一调 user-service 校验 |
| client_token 幂等并发 | 旧版并发同 token 会重试 5 次后 500;新版识别后幂等返回已有工单 |
| `expected_finish_time` 非法格式 | 旧版静默放过(SQLite 存文本);新版返回 40001 格式无效 |
| 错误响应 `data` 字段 | 成功带 data 不变;错误响应省略 `data:null`(前端只读 code/msg,无影响) |
| 通知 | 仍为模拟企微(记录 notification_log,1 分钟幂等);P1 接真实企微/短信 |

## 验证状态

已完成并通过的验证(2026-09-21,本地 Nacos + MySQL 8.0.28 实测):

- 全模块 `mvn package` 成功;状态机/JWT 单元测试通过
- 登录签发 JWT、错误密码 40001、`me`/`login-options` 中文正常
- 网关:白名单放行、无 token 401/40100、剥离伪造头、URL 编码透传中文身份
- 工单:创建(201)+ client_token 幂等重放 + 40001 合并报错 + 工单号 TK+日期连续
- 派单 403/40021/成功、claim 条件更新、状态机转移(guard:驳回≥10字、未知操作 40001)
- done→待验收→accept→已完成→评分 5 星;驳回回处理中;员工撤回已取消
- 通知:SUBMIT_SUCCESS/DISPATCH/STATUS_CHANGED/PENDING_ACCEPTANCE/ACCEPT_APPROVED/ACCEPT_REJECTED/CANCEL 全部正确落库(事务提交后异步)
- 草稿 UPSERT/GET/DELETE;Feign 姓名组装(creator_name/assignee_name/operator_name)

## 常见问题排查

- **编译报 `java.lang.ExceptionInInitializerError ... com.sun.tools.javac.code.TypeTag :: UNKNOWN`**
  Lombok 与实际编译 JDK 不匹配。确认 IDEA Project SDK = 17(Project Structure → Project/Modules、Compiler → Java Compiler 全部 17),并刷新 Maven 重新拉取 `lombok 1.18.38`;必要时 Invalidate Caches 后 Rebuild。

- **服务启动报 `HikariPool-1 - Exception during pool initialization / Communications link failure`**
  MySQL(3306)没起来。Docker 用户 `docker compose up -d`;本机免安装版运行 `scripts\start-mysql-local.cmd`;首次部署需再跑 `scripts\init-db.cmd` 建库。

- **服务注册不上 Nacos / Feign 找不到服务**
  确认 Nacos 已以 standalone 启动,且 **9848(gRPC)端口已放行**(Nacos 2.x 客户端走 gRPC,只开 8848 不够)。

- **直连服务端口(绕过网关)全部接口报 401/40100**
  正常现象:业务服务靠网关注入的 `X-User-*` 头识别用户,直连无头即 40100。调试请走 `http://127.0.0.1:8080` 并携带 `Authorization: Bearer <token>`。

## 待办(P1)

- [ ] 真实企微/短信通知渠道
- [ ] JWT secret / 数据源迁移到 Nacos 配置中心统一管理(现为本地文件 + 环境变量)
- [ ] 超时自动通过/取消的定时任务(状态机规则已预留 system 角色:timeout / auto_accept)
