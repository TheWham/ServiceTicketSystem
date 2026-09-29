# IT 服务工单系统

> 企业级 IT 服务工单管理系统,覆盖**提单→路由→处理→验收→评价**完整闭环。
> 后端基于 Spring Cloud 微服务,前端基于 Vue 3 + Element Plus,业务规则对齐《PRD-Ultimate》。

---

## 技术栈

| 层 | 技术 |
|:---|:---|
| 前端 | Vue 3 + Vite + Pinia + Vue Router + Element Plus + Axios |
| 后端 | Java 17 + Spring Boot 3.2.5 + Spring Cloud 2023.0.1 + Spring Cloud Alibaba |
| 数据库 | MySQL 8(单库 `it_ticket_system`,28 张表,执行顺序 00→10) |
| 服务治理 | Nacos(注册中心)+ OpenFeign + Spring Cloud Gateway |
| 认证 | JWT(HS256,12h)+ BCrypt,网关统一鉴权 |
| ORM | MyBatis-Plus 3.5.7 |

## 项目结构

```
it-ticket-system/
├── it-ticket-cloud/          # 微服务后端
│   ├── gateway/              # 网关 :8080 —— 唯一入口 + JWT 统一鉴权 + 路由
│   ├── user-service/         # 用户服务 :8101 —— 登录/JWT、用户、草稿
│   ├── ticket-service/       # 工单服务 :8201 —— 工单全业务、状态机、路由、SLA、通知、异常队列
│   ├── common/               # Result/错误码/JWT 工具(纯 Java,gateway 可引用)
│   ├── common-web/           # 全局异常、UserContext 透传头解析、时间格式
│   ├── db/init/              # MySQL 建表 + 种子(00-schema.sql → 10-seed.sql)
│   ├── scripts/              # 本地一键启动/初始化脚本(Windows)
│   ├── docker-compose.yml    # Nacos + MySQL 一键起(Docker 环境)
│   ├── pom.xml               # 父 POM
│   └── README.md             # 微服务版详细技术文档 ⭐
├── frontend/                 # Vue 3 + Element Plus 前端(:5173,vite proxy /api → 8080)
│   └── src/
│       ├── api/              # Axios 封装(自动注入 Authorization: Bearer)
│       ├── router/           # 路由 + 角色守卫(meta.role 支持数组)
│       ├── stores/           # Pinia(token + 用户信息,localStorage 持久化)
│       ├── views/            # 登录 / 员工端 / 工程师端 / 主管端
│       ├── components/       # NotificationBell(通知铃铛)、SlaBadge/SlaTimer(SLA 倒计时)
│       ├── styles/           # 全局样式 + 暗黑主题变量
│       ├── App.vue           # 经典后台布局(aside + header + main,暗黑切换 + 通知入口)
│       └── main.js           # ElementPlus 注册入口
├── acceptance/               # 验收评测(27 项用例全绿,详见 acceptance/README.md)
│   ├── src/ticket_p0/        # P0 阶段 8 大模块参考实现
│   ├── tests/                # pytest 测试套件(含 TC-10 注入防护)
│   ├── scripts/              # 评测执行脚本
│   └── reports/              # 评测报告输出
├── IT服务工单系统PRD-Ultimate.md  # 产品需求文档(业务规则唯一依据)
└── README.md                 # 本文档
```

## 快速开始

### 1. 起依赖

**有 Docker:**
```bash
cd it-ticket-cloud && docker compose up -d   # Nacos(8848/9848) + MySQL(3306,自动建表+种子)
```

**无 Docker(Windows,本项目已验证的方式):**
```bash
it-ticket-cloud\scripts\start-mysql-local.cmd   # MySQL 免安装版,首次自动初始化数据目录并启动 3306
it-ticket-cloud\scripts\start-nacos.cmd         # Nacos standalone 模式启动 8848/9848
it-ticket-cloud\scripts\init-db.cmd             # 建库+建表+种子(root/root123)
```

### 2. 起服务(需 JDK 17 + Maven)

```bash
cd it-ticket-cloud
mvn package                                    # 或在 IDE 中分别启动三个 Application
java -jar gateway/target/it-ticket-gateway-1.0.0.jar
java -jar user-service/target/it-ticket-user-service-1.0.0.jar
java -jar ticket-service/target/it-ticket-ticket-service-1.0.0.jar
```

环境变量(均有默认值):`NACOS_ADDR=127.0.0.1:8848`、`MYSQL_PASSWORD=root123`、`JWT_SECRET`(生产必换)。

### 3. 起前端

```bash
cd frontend && npm install && npm run dev    # 5173,proxy /api → 8080 网关
```

### 4. 登录

种子账号 4 个,**默认密码均为 `123456`**,角色为 PRD §5.1 大写枚举:

| 用户ID | 姓名 | 角色 |
|:---|:---|:---|
| U_EMP01 | 演示员工 | EMPLOYEE |
| U_ENG01 | 演示工程师 | ENGINEER |
| U_ADM01 | 平台管理员 | PLATFORM_ADMIN |
| U_KBA01 | 知识库管理员 | KB_ADMIN |

## API 一览

统一响应 `{code, msg, data}`,`code=0` 成功。经网关访问:`http://localhost:8080/api/v1/**`。

| 方法 | 路径 | 说明 | 权限 |
|:---|:---|:---|:---|
| GET | /api/health | 健康检查 | 免认证 |
| POST | /api/v1/users/login | 登录,`{userId,password}` → `{token,user}` | 免认证 |
| GET | /api/v1/users/login-options | 可登录用户列表 | 免认证 |
| GET | /api/v1/users/me | 当前用户 | 登录 |
| GET | /api/v1/users?role= | 用户列表(派单用) | 登录 |
| GET/POST/DELETE | /api/v1/users/drafts | 提单草稿(每用户一条) | 登录 |
| GET | /api/v1/categories/leaf | 叶子分类(提单表单下拉) | 登录 |
| POST | /api/v1/tickets | 创建工单(client_token 幂等,创建后自动路由) | 登录 |
| GET | /api/v1/tickets | 列表(8 种筛选 + 分页) | 登录 |
| GET | /api/v1/tickets/:id | 详情 + 流转日志 | 登录 |
| POST | /api/v1/tickets/:id/assign | 派单/改派 | supervisor |
| POST | /api/v1/tickets/:id/claim | 领取(条件更新防抢领) | engineer |
| POST | /api/v1/tickets/:id/actions | 状态操作(route/accept/request_supplement/supply_info/external_wait/external_resolved/submit_resolution/reject/cancel/abnormal_close/reopen 等) | 状态机校验 |
| POST | /api/v1/tickets/:id/rating | 评价 1-5 星(仅已完成) | 登录 |
| GET | /api/v1/sla/:ticketId | SLA 计时(目标时刻/已用工时/剩余工作秒,前端倒计时基准) | 登录 |
| GET | /api/v1/notifications | 通知列表(分页) | 登录 |
| GET | /api/v1/notifications/pending-count | 未读待办数(前端 30s 轮询) | 登录 |
| GET | /api/v1/exceptions/pending-count | 异常队列待处理数(路由失败工单) | supervisor |

核心错误码:`40001` 参数校验、`40021` 处理人无效、`40100/40101` 未登录/用户禁用、`40300` 权限不足、`40400` 工单不存在、`40901` 幂等冲突、`40910` 非法状态转移、`40911` 不可领取、`40912` 已被他人领取。

工单状态机(PRD §9,9 态 18 条边):NEW → ASSIGNED → IN_PROGRESS → PENDING_SUPPLEMENT ⇄ / PENDING_EXTERNAL ⇄ / PENDING_ACCEPTANCE → COMPLETED / CANCELLED / CLOSED。含系统自动边:响应超时转派、72h 未补充自动关闭、48h 未验收自动通过、7 日内复发重开;通用边:员工撤销、管理员异常关闭/标记重复单。每次流转写 `ticket_transition`,并按事件类型发通知(`notification` 落库,1 分钟幂等)。

## 核心机制

- **自动路由(F-06)**:创建工单后按分类路由规则(`category_route`)定位支持组,组内按加权负载选工程师;无可用候选人时工单留在 NEW 并进入异常队列,由管理员处理。
- **SLA 计时(F-08)**:按优先级生成 SLA 实例(高 4 工作小时/中 1 工作日/低 3 工作日),基于工作日历(`work_calendar`)只计工作时间;暂停时段(`sla_pause`)不计入;超时自动转入异常处理。前端 SlaBadge/SlaTimer 以服务端计算的剩余工作秒为基准做本地倒计时。
- **站内通知(F-10)**:9 态流转事件驱动通知(分配/接单/请求补充/验收/超时等),接收人按目标状态推导;前端 NotificationBell 30s 轮询未读数,点击通知跳转对应待办入口。

## 当前进展(2026-09-29)

**已完成**:
- **后端微服务化**:登录/JWT、网关鉴权与透传、建单+幂等、自动路由、SLA 计时与自动流转、9 态状态机 guard、异常队列、通知事件落库(详见 [it-ticket-cloud/README.md](it-ticket-cloud/README.md))
- **前端 Element Plus 化**:经典后台布局 + 暗黑模式 + 通知中心(SlaBadge/SlaTimer/NotificationBell),角色值域对齐 PRD 大写枚举
- **数据库结构按 PRD 全量对齐**:单库 28 张表重建(2026-09-28)
- **验收评测**:27 项用例全绿(含 TC-10 注入防护),代码位于 `acceptance/`

**未完成**:知识库推荐(F-01)、智能客服(F-03)等 PRD 后续功能点尚未开发。

## 相关文档

- [IT服务工单系统PRD-Ultimate.md](IT服务工单系统PRD-Ultimate.md) —— 产品需求文档(状态机/SLA/通知/路由规则依据)
- [it-ticket-cloud/README.md](it-ticket-cloud/README.md) —— 微服务版详细技术文档(架构/接口/错误码/状态机/数据库/排查指南)
- [acceptance/README.md](acceptance/README.md) —— 验收评测报告(27 项用例全绿)

## 仓库

- **主仓库(GitHub)**:https://github.com/TheWham/ServiceTicketSystem
- **镜像(Gitee)**:https://gitee.com/early-rise/it-ticket-system
