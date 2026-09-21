# IT 服务工单系统 · Spring Cloud 微服务版

由 Node.js(Express + SQLite)单体迁移而来的 Spring Cloud 微服务后端。**API 路径、`{code,msg,data}` 响应包裹、错误码与前端除登录外完全兼容**。

## 架构

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

## 技术栈

- Java 17 + Spring Boot 3.2.5
- Spring Cloud 2023.0.1 + Spring Cloud Alibaba 2023.0.1.2(Nacos 注册+配置)
- Spring Cloud Gateway(唯一入口)、OpenFeign(服务间调用)
- MyBatis-Plus 3.5.7 + MySQL 8(每服务独立库)
- JWT(jjwt 0.12,HS256,12h)+ BCrypt 密码

## 快速开始

### 方式 A:Docker(推荐)

```bash
cd it-ticket-cloud
docker compose up -d          # 起 MySQL(自动建库+种子) 和 Nacos
```

### 方式 B:Windows 手动安装(无 Docker)

1. **MySQL 8**:安装后以 root 运行初始化脚本(顺序执行):
   ```
   mysql -uroot -p < db/init/00-create-databases.sql
   mysql -uroot -p < db/init/10-user-db.sql
   mysql -uroot -p < db/init/11-user-seed.sql
   mysql -uroot -p < db/init/20-ticket-db.sql
   mysql -uroot -p < db/init/21-ticket-seed.sql
   ```
   root 密码默认假定 `root123`,不同则用环境变量 `MYSQL_PASSWORD` 覆盖。
2. **Nacos**:下载 nacos-server 2.3.x zip(https://github.com/alibaba/nacos/releases),
   解压后在 `bin` 下执行 `startup.cmd -m standalone`(需放行 8848 与 9848 端口)。

### 启动服务(任一 IDE 或命令行)

```bash
# 需 JDK 17 + Maven
mvn -pl gateway,spring-boot:run     # 或逐个启动
```

启动顺序(本地可任意,Nacos 先就绪即可):

| 服务 | 端口 | 说明 |
|---|---|---|
| gateway | 8080 | 唯一入口,前端 proxy 指向它 |
| user-service | 8101 | 用户/登录/草稿 |
| ticket-service | 8201 | 工单全业务 |

环境变量(均有默认值):`NACOS_ADDR`(默认 127.0.0.1:8848)、`MYSQL_HOST/PORT/USERNAME/PASSWORD`(默认 localhost:3306 root/root123)、`JWT_SECRET`(默认开发密钥,**生产必换**)。

## 登录(JWT)

- 种子账号 6 个,**统一默认密码 `123456`**(BCrypt 存储,见 `db/init/11-user-seed.sql`)。
- `POST /api/v1/users/login` body `{userId, password}` → `{code:0, data:{token, user}}`。
- `GET /api/v1/users/login-options` 保留(免认证),前端先选身份再输密码。
- 前端持 `Authorization: Bearer <token>` 访问;网关校验后向下游注入 `X-User-Id/Name/Role/Dept` 头。
- 401/40100(未登录/过期)、401/40101(用户被禁用)由网关返回,msg 格式与旧版一致。

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

## 待办(P1)

- [ ] 真实企微/短信通知渠道
- [ ] JWT secret / 数据源迁移到 Nacos 配置中心统一管理(现为本地文件 + 环境变量)
- [ ] 超时自动通过/取消的定时任务(旧版也未实现,状态机规则已预留 system 角色)
