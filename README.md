# IT 服务工单系统

> 企业级 IT 服务工单管理系统,覆盖**提单→派单→处理→验收→评价**完整闭环。
> 后端基于 Spring Cloud 微服务,前端基于 Vue 3 + Element Plus。

---

## 技术栈

| 层 | 技术 |
|:---|:---|
| 前端 | Vue 3 + Vite + Pinia + Vue Router + Element Plus + Axios |
| 后端 | Java 17 + Spring Boot 3.2.5 + Spring Cloud 2023.0.1 + Spring Cloud Alibaba |
| 数据库 | MySQL 8(双库 `it_user` / `it_ticket`) |
| 服务治理 | Nacos(注册中心)+ OpenFeign + Spring Cloud Gateway |
| 认证 | JWT(HS256,12h)+ BCrypt,网关统一鉴权 |
| ORM | MyBatis-Plus 3.5.7 |

## 项目结构

```
it-ticket-system/
├── it-ticket-cloud/          # 微服务后端
│   ├── gateway/              # 网关 :8080 —— 唯一入口 + JWT 统一鉴权 + 路由
│   ├── user-service/         # 用户服务 :8101 —— 登录/JWT、用户、草稿(库 it_user)
│   ├── ticket-service/       # 工单服务 :8201 —— 工单全业务、状态机、通知(库 it_ticket)
│   ├── common/               # Result/错误码/JWT 工具(纯 Java,gateway 可引用)
│   ├── common-web/           # 全局异常、UserContext 透传头解析、时间格式
│   ├── db/init/              # MySQL 建库 + 建表 + 种子(执行顺序 00→21)
│   ├── scripts/              # 本地一键启动/初始化脚本(Windows)
│   ├── docker-compose.yml    # Nacos + MySQL 一键起(Docker 环境)
│   ├── pom.xml               # 父 POM
│   └── README.md             # 微服务版详细技术文档 ⭐
├── frontend/                 # Vue 3 + Element Plus 前端(:5173,vite proxy /api → 8080)
│   └── src/
│       ├── api/              # Axios 封装(自动注入 Authorization: Bearer)
│       ├── router/           # 路由 + 角色守卫
│       ├── stores/           # Pinia(token + 用户信息,localStorage 持久化)
│       ├── views/            # 登录 / 员工端 / 工程师端 / 主管端
│       ├── components/       # 公共组件
│       ├── styles/           # 全局样式 + 暗黑主题变量
│       ├── App.vue           # 经典后台布局(aside + header + main,暗黑切换)
│       └── main.js           # ElementPlus 注册入口
├── acceptance/               # 验收评测(27 项用例全绿,详见 acceptance/README.md)
│   ├── src/ticket_p0/        # P0 阶段 8 大模块参考实现
│   ├── tests/                # pytest 测试套件(含 TC-10 注入防护)
│   ├── scripts/              # 评测执行脚本
│   └── reports/              # 评测报告输出
├── README.md                 # 本文档
└── ROADMAP.md                # 未完成功能点清单(按 PRD+SPEC 对比)
```

## 快速开始

### 1. 起依赖

**有 Docker:**
```bash
cd it-ticket-cloud && docker compose up -d   # Nacos(8848/9848) + MySQL(3306,自动建库+种子)
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

种子账号 6 个,**默认密码均为 `123456`**:

| 账号 | 姓名 | 角色 |
|:---|:---|:---|
| U001 | 张小明 | 员工 employee |
| U002 | 李丽 | 员工 employee |
| U003 | 王强 | 员工 employee |
| U004 | 赵工 | 工程师 engineer |
| U005 | 钱工 | 工程师 engineer |
| U006 | 孙主管 | 主管 supervisor |

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
| POST | /api/v1/tickets | 创建工单(client_token 幂等) | 登录 |
| GET | /api/v1/tickets | 列表(8 种筛选 + 分页) | 登录 |
| GET | /api/v1/tickets/:id | 详情 + 流转日志 | 登录 |
| POST | /api/v1/tickets/:id/assign | 派单/改派 | supervisor |
| POST | /api/v1/tickets/:id/claim | 领取(条件更新防抢领) | engineer |
| POST | /api/v1/tickets/:id/actions | 状态操作(progress/need_info/external/done/accept/reject/cancel/supply_info/external_resolved) | 状态机校验 |
| POST | /api/v1/tickets/:id/rating | 评价 1-5 星(仅已完成) | 登录 |

核心错误码:`40001` 参数校验、`40021` 处理人无效、`40100/40101` 未登录/用户禁用、`40300` 权限不足、`40400` 工单不存在、`40901` 幂等冲突、`40910` 非法状态转移、`40912` 已被他人领取。

工单状态机:CREATED → ASSIGNED → PENDING_SUPPLEMENT ⇄ PENDING_EXTERNAL → PENDING_ACCEPTANCE → ACCEPTED / REJECTED → CLOSED,共 8 状态 12 条转移规则(含驳回 ≥10 字、完成需有进展记录等 guard),每次流转写 `ticket_flow_log`,并按事件类型异步发通知(`notification_log` 落库,1 分钟幂等)。

## 当前进展(2026-09-22)

**已完成**:
- **后端微服务化**:登录/JWT、网关鉴权与透传、建单+幂等、工单号连续、派单 403/40021、领取防抢领、状态机 guard、验收评分、撤回、草稿 CRUD、7 种通知事件落库(详见 [it-ticket-cloud/README.md](it-ticket-cloud/README.md))
- **前端 Element Plus 化**:经典后台布局 + 暗黑模式 + ElMessage/MessageBox,业务调用零改动
- **验收评测**:27 项用例全绿(含 TC-10 注入防护),代码位于 `acceptance/`
- **目录结构扁平化**:微服务源码直接纳入主仓库跟踪,不再有嵌套 git 仓库

**未完成 / 待办**:见 [ROADMAP.md](ROADMAP.md) —— 按 PRD(7) + SPEC(2) 对比列出的功能缺口,含 F-01 知识库推荐、F-02 通知调度、F-03 智能客服等。

- [AGENTS.md](AGENTS.md) —— **智能体研发宪法与规范注入书 (工业级标准，最高法律地位)** ⚖️
- [CLAUDE.md](CLAUDE.md) —— **架构宪法与开发指令库 (Claude Code / AI 专属执行手册)** 📜
- [specs/](specs/) (及 [docs/specs/](docs/specs/)) —— **Day 4 签署技术 SPEC 规格书、PRD 与评测协议归档库** 📋
- [docs/diagrams/业务流转泳道图.png](docs/diagrams/业务流转泳道图.png) —— **全景业务流转泳道图 (五角色规范版)** ⭐
- [ROADMAP.md](ROADMAP.md) —— 未完成功能点清单(P0/P1/P2 共 15 项)
- [it-ticket-cloud/README.md](it-ticket-cloud/README.md) —— 微服务版详细技术文档(架构/接口/错误码/状态机/数据库/排查指南)
- [acceptance/README.md](acceptance/README.md) —— 验收评测报告(27 项用例全绿)

## 仓库

- **主仓库(GitHub)**:https://github.com/TheWham/ServiceTicketSystem
- **镜像(Gitee)**:https://gitee.com/early-rise/it-ticket-system
