# IT 服务工单系统 · 智能体研发宪法与规范注入书 (AGENTS.md)

> **版本**：V1.0 (工业级标准)  
> **适用对象**：所有协同研发的 AI Agents (Cursor, Claude Code, Antigravity, Copilot Workspace 等) 及架构师/工程师  
> **制定部门**：系统架构委员会 (Chief Architect Office)  
> **生效时间**：2026-09-24  
> **法律效力**：本宪法为项目最高工程法典，拥有**一票否决权**。任何代码生成、重构、模型设计必须 100% 严格遵守，违反任一条款均视为代码缺陷，拒绝合并。

---

## 零、最高宪法原则 (Supreme Principles)

1. **契约至上 (Spec-First & Zero Ambiguity)**：
   工程根目录 `specs/` 下归档的 Day 4 签署规范（《技术SPEC规格书》、《验收评测协议书》、《需求归因文档》、《技术风险登记册》）为项目唯一真理。严禁在没有 SPEC 支持的情况下私自臆想字段、接口、状态或非标准逻辑。
2. **零作弊原则 (Zero Tolerance for Cheating)**：
   严禁修改自动化测试断言、评测脚本或预期结果来迎合错误实现！测试红了必须修正业务代码使其符合 SPEC 契约，严禁“反向适配”。
3. **确定性优于便利性**：
   严禁“先跑起来再说”。在安全性、幂等性、并发控制、数据精度和状态机约束面前，任何绕过规范的权宜代码一律零容忍。

---

## 一、技术栈铁律 (Technology Stack Rules)

### 1.1 Python / FastAPI 核心规范
1. **框架基准**：Python 3.11+ / 3.12，基于 **FastAPI + Pydantic v2** 构建工业级 API。
2. **分层架构边界**：
   - `api/routes`：仅负责 HTTP 路由解构、依赖注入与状态码分发，严禁直接堆砌业务 SQL。
   - `schemas`：定义 Pydantic v2 请求与响应 DTO，负责出入参强类型契约校验。
   - `services`：核心领域服务，收口状态机流转、发号、幂等锁与事务逻辑。
   - `models` / `storage`：底层实体与持久化层，严格参数化交互。
3. **全局统一响应结构**：
   所有业务 API 统一输出三段式标准 JSON 载荷：
   ```json
   {
     "code": 0,
     "msg": "success",
     "data": {}
   }
   ```
   - 业务成功时 `code = 0`，HTTP 状态码统一为 `200`。
   - 业务异常必须收口至全局异常拦截器，不得向调用方泄露任何未捕获的 Python 内部堆栈。

### 1.2 Pydantic v2 专属规范 (严禁 v1 语法)
1. **严格禁止 Pydantic v1 废弃用法**：
   - ❌ 严禁使用 `class Config:`，必须使用 `model_config = ConfigDict(from_attributes=True, ...)`。
   - ❌ 严禁使用 `.dict()`，必须使用 `.model_dump()`。
   - ❌ 严禁使用 `.json()`，必须使用 `.model_dump_json()`。
   - ❌ 严禁使用 `from_orm()` 或 `parse_obj()`，必须使用 `model_validate()`。
   - ❌ 严禁使用 `@validator` 与 `@root_validator`，必须使用 `@field_validator` 与 `@model_validator`。
2. **强类型与字段契约**：
   所有 DTO 字段必须显式声明类型并配合 `Field(...)` 添加严格约束（如 `min_length`, `max_length`, `pattern`）。
3. **错误收集契约（关键验收项）**：
   多字段输入非法时，**必须逐字段收集所有错误信息一次性完整返回**，绝对禁止“遇到第一个错误就立即中断抛出”。

### 1.3 金融与数值精度铁律 (禁止 float 金额)
1. **绝对禁止 `float` / `double` 存储或计算金额**：
   - ❌ **严禁**使用 `float` 类型存储工单涉及的工时费、配件费用、赔偿金、单价或任何金额数值。
   - **理论归因**：IEEE 754 浮点数存在二进制表示误差（例如 `0.1 + 0.2 != 0.3`），在多级汇总、乘折扣率或资产核对时会导致不可逆的对账不平与财务资损漏洞。
2. **金额唯一标准实现方案**：
   - 方案 A（推荐）：**统一使用最小货币单位整数（分，`int`）**。如 ¥100.50 必须存储并计算为 `10050`（分）。
   - 方案 B：涉及高精度除法或汇率时，必须使用 Python 标准库 `decimal.Decimal`（数据库映射为 `DECIMAL(10, 2)` 或 `BIGINT` 分）。
   - **前端交互隔离**：金额计算与数据持久化全流程使用 `int` 分或 `Decimal`，仅允许在前端视图渲染展示时除以 100 格式化为元。

### 1.4 数据持久化与防 SQL 注入
1. **禁止一切 SQL 拼接**：
   所有数据库读写（无论 SQLite、MySQL 还是 ORM 框架）**必须 100% 使用参数化绑定（Parameterized Queries / Prepared Statements）**。
   - ❌ 严禁使用 f-string、`%` 格式化或 `+` 拼接字符串 SQL。
   - 遵循《验收评测协议书》TC-10 要求，所有输入（包括含 `' OR 1=1 --` 等注入 payload）必须纯作为字符串文本参数化安全落库。
2. **字符集规范**：全库全表必须统一使用 `utf8mb4` / `utf8mb4_unicode_ci`。
3. **枚举持久化**：数据库中一律存储枚举字符串名称 (`name()`)，**绝对禁止存储数字索引 (`ordinal`)**。
4. **时间与时区**：统一使用字符串格式 `YYYY-MM-DD HH:mm:ss`，时区强制锁死东八区 `Asia/Shanghai` (GMT+8)。
5. **乐观锁并发控制**：
   主实体 `ticket` 必须包含 `version INT` 乐观锁字段。状态流转与重要更新必须执行：
   ```sql
   UPDATE ticket SET ..., version = version + 1 WHERE ticket_id = :ticket_id AND version = :version
   ```
   若受影响行数为 0，必须立即回滚并抛出 `40900「工单已被他人操作,请刷新后重试」`。

---

## 二、SPEC 业务规范注入 (Specification Invariants)

### 2.1 统一错误码体系 (SPEC §2.7 闭环定义)
工程中只允许使用以下 **8 个标准错误码**，**绝对禁止新造任何未定义错误码**：

| code | HTTP 状态 | 含义 | 典型触发场景 |
| :--- | :--- | :--- | :--- |
| `0` | 200 | 成功 | 操作执行成功，返回预期业务数据 |
| `40000` | 200 | 业务错误 (通用) | 字段级校验未通过、附件超限/格式不合规、缺少必填 remark |
| `40100` | 200 / 401 | 未登录或凭据失效 | Token 缺失、签名非法或已过 12h 有效期 |
| `40300` | 200 | 无权限访问 | 员工操作工程师流转、非提单本人尝试验收或关闭他人单据 |
| `40400` | 200 | 资源不存在 | 工单号 `ticket_id` 在库中查无记录 |
| `40401` | 200 | 资产不存在 | 提交的 `asset_id` 在 CMDB 资产库中查无记录 |
| `40900` | 200 | 数据冲突 | 3s 提交防重锁抢占失败、非法状态流转、乐观锁版本冲突 |
| `500` | 200 | 系统繁忙 | 未捕获异常全局兜底，严禁向前端泄漏详细异常堆栈 |

### 2.2 工单状态机闭环宪法 (SPEC §3)
系统包含 **8 种状态**，流转**仅允许且必须严格实现以下 13 条合法流转边**。任何不在列表中的状态变迁一律拦截并返回 `40900「非法状态流转: X -> Y」`。

```
[草稿/无] ──SUBMIT(员工)──▶ CREATED(待接单) ──ACCEPT(工程师)──▶ ASSIGNED(处理中)
   │                               │                                 │
   │                               │ CLOSE(撤单)                     ├─REQUEST_SUPPLEMENT(工程师)─▶ PENDING_SUPPLEMENT(待补充)
   │                               │                                 │                               │
   │                               ▼                                 │                               └─SUPPLEMENT(提单人)─▶ ASSIGNED
   │                             CLOSED                              ├─TRANSFER_EXTERNAL(工程师)──▶ PENDING_EXTERNAL(待外部)
   │                             (终态)                              │                               │
   │                               ▲                                 │                               └─RESUME(工程师)──────▶ ASSIGNED
   │                               │                                 ├─RESOLVE(工程师)────────────▶ PENDING_ACCEPTANCE(待验收)
   │                               │                                 │                               │
   │                               ├─────CLOSE(员工放弃)──────────────┤                               ├─ACCEPT_APPROVE(提单人)─▶ ACCEPTED(终态)
   │                               │                                 │                               │                           │
   │                               └─────CLOSE(员工结单)──────────────┴──────────REWORK(工程师)◀────┴─ACCEPT_REJECT(提单人)──▶ REJECTED(已驳回)
```

#### 13 条合法流转边矩阵表：
1. `(草稿/无)` → `CREATED`：动作 `SUBMIT`（仅限角色 `EMPLOYEE`）。落 `ticket_log`（from=NULL）；异步触发 `SUBMIT_SUCCESS` 通知；清空该用户草稿。
2. `CREATED` → `ASSIGNED`：动作 `ACCEPT`（仅限角色 `ENGINEER`）。绑定 `assignee_id`；乐观锁防抢单（败者 40900）；异步触发 `DISPATCH` 通知。
3. `ASSIGNED` → `PENDING_SUPPLEMENT`：动作 `REQUEST_SUPPLEMENT`（仅限角色 `ENGINEER`）。`remark` **强制必填**（缺省拦截 40000）；异步触发 `PENDING_SUPPLEMENT` 通知。
4. `PENDING_SUPPLEMENT` → `ASSIGNED`：动作 `SUPPLEMENT`（**仅限提单本人**，非本人拦截 40300）。补充说明与附件追加写入流转日志；不发通知。
5. `ASSIGNED` → `PENDING_EXTERNAL`：动作 `TRANSFER_EXTERNAL`（仅限角色 `ENGINEER`）。`remark` **强制必填**；异步触发 `PENDING_EXTERNAL` 通知。
6. `PENDING_EXTERNAL` → `ASSIGNED`：动作 `RESUME`（仅限角色 `ENGINEER`）。恢复日常处理；不发通知。
7. `ASSIGNED` → `PENDING_ACCEPTANCE`：动作 `RESOLVE`（仅限角色 `ENGINEER`）。提交修复方案；异步触发 `PENDING_ACCEPTANCE` 通知。
8. `REJECTED` → `ASSIGNED`：动作 `REWORK`（仅限角色 `ENGINEER`）。重新返工；复用触发 `DISPATCH` 通知。
9. `PENDING_ACCEPTANCE` → `ACCEPTED`：动作 `ACCEPT_APPROVE`（**仅限提单本人**，非本人拦截 40300）。工单进入**终态**；异步触发 `ACCEPT_APPROVED` 通知。
10. `PENDING_ACCEPTANCE` → `REJECTED`：动作 `ACCEPT_REJECT`（**仅限提单本人**，非本人拦截 40300）。`remark` **强制必填**；`reject_count` 原子自增 +1；异步触发 `ACCEPT_REJECTED` 通知。
11. `ACCEPTED` → `CLOSED`：动作 `CLOSE`（**仅限提单本人**）。工单彻底关闭（终态，无后续边）。
12. `REJECTED` → `CLOSED`：动作 `CLOSE`（**仅限提单本人**，放弃验收关闭）。工单彻底关闭。
13. `CREATED` → `CLOSED`：动作 `CLOSE`（**仅限提单本人**，撤回待接单工单）。工单彻底关闭。

#### 角色守卫特权与边界红线：
- **主管特权（SUPERVISOR）**：放行普通角色权限检查（如主管可代理接单、转派），但**绝对不得放行提单人专有守卫（`creator_only`）**！验收通过、验收驳回、补充材料、关闭撤销必须且只能由提单人本人操作。
- **定时扫描红线**：
  - 处理超时（ASSIGNED 超过 2h 未更新）与滞留催办（PENDING_EXTERNAL 超过 24h 未更新）**仅降级为生成通知事件告警（`TIMEOUT_ALERT` 等）**。
  - **绝对禁止在定时任务中隐式变更 ticket_status，绝对禁止自动销毁工单**！

### 2.3 提单 7 字段级校验契约 (SPEC §1.7)
提单入参（`POST /api/ticket`）校验矩阵前后端强一致：
1. `title`：必填，长度 1~50 字符。**严禁包含 `<` 或 `>` 字符（防御 XSS，违规直接 40000 拒绝）**。
2. `category`：必填，必须严格属于枚举 `{HARDWARE, SOFTWARE, NETWORK, ACCOUNT, OTHER}`。
3. `priority`：必填，默认 `MEDIUM`，必须严格属于枚举 `{HIGH, MEDIUM, LOW}`。
4. `description`：必填，长度 10~500 字符。纯文本参数化存储，杜绝自动截断。
5. `assetId`：选填。若填写必须匹配正则 `^IT-[A-Z]{2,4}-\d{8}$`；正则通过后必须联动校验 CMDB，查无此资产返回 `40401`。
6. `attachmentUrls`：选填，JSON 数组最多 3 个元素。每个元素形态必须为先前上传返回的合法地址 `/files/{32位hex}.{jpg|jpeg|png}`。
7. `expectedFinishTime`：选填。若填写其时间必须 ≥ 当前时间（未来或当前时间），违规返回 `40000`。

### 2.4 附件上传与真实魔数防护 (TC-10 验收基准)
1. **参数规格**：单张文件 ≤ 5MB，单次请求总容量 ≤ 15MB；扩展名白名单仅限 `.jpg`, `.jpeg`, `.png`。
2. **头部魔数真实嗅探（MIME Sniffing）**：
   - 严禁仅依赖客户端传参的文件后缀名或 `Content-Type` 报头！
   - 后端读取文件流的前 8 字节进行二进制魔数比对：
     - JPEG 魔数特征：`FF D8 FF`
     - PNG 魔数特征：`89 50 4E 47 0D 0A 1A 0A`
   - 若检测到魔数与扩展名不符，或包含 Windows/Linux 可执行头（如 `MZ` / `PE` / `ELF`），一律以 `40000` 拒绝。
3. **落地安全规范**：文件落地必须重命名为 `UUID32 + 原扩展名`，隔离存储，通过静态只读路径 `/files/{filename}` 对外映射。

### 2.5 幂等防重与原子发号机制 (SPEC §1.6 / §2.1)
1. **提单防重锁（3 秒窗口）**：
   - 锁键格式：`submit:{userId}:{title.hashCode}`
   - 语义：TTL 3 秒，抢锁失败立即拦截并返回 `40900「请勿重复提交」`。
   - **注意**：字段校验未通过的请求绝对不占锁。
2. **通知去重锁（60 秒窗口）**：
   - 锁键格式：`notify:{ticketId}:{eventType}:{receiverId}`
   - 语义：TTL 60 秒，抢锁失败直接跳过该接收人本次通知记录，防止消息轰炸。
3. **原子工单发号器**：
   - 规则：`TK + yyyyMMdd + 4位递增序号`（如 `TK202609240001`）。
   - 实现：必须基于 `ticket_id_seq` 发号表原子操作递增分配，确保绝对防重、防跳号、高并发无碰撞。

---

## 三、签署 SPEC 归档体系 (specs/ Directory)

所有 Day 4 评审签署的法定技术文档已权威归档至工程根目录 `specs/` 下：

| 归档文件路径 | 角色与核心内容 |
| :--- | :--- |
| `specs/技术SPEC规格书.md` | **技术基准核心**：定义数据实体、校验规则、降级矩阵、状态机、错误码体系。 |
| `specs/IT服务工单系统-验收评测协议书.md` | **质量验收法典**：9 大指标（M-01~M-09）、27 项验收用例集、TC-10 渗透防护断言。 |
| `specs/IT服务工单系统-需求归因文档.md` | **需求溯源基准**：企业 IT 报障四大业务痛点归因与方案推导。 |
| `specs/IT服务工单系统-技术风险登记册.md` | **风险风控手册**：重放攻击、锁表、载荷注入与降级方案。 |
| `specs/IT服务工单系统PRD-0921.docx` | **产品需求总纲**：业务泳道流程图与原型设计。 |
| `specs/it工单系统-Qwen3-4B-算力与基础设施定盘表.md` | **AI 算力基准**：端侧与私有化模型资源配置与吞吐定盘。 |

---

## 四、AI Agent 行为红线与研发执行纪律

所有参与本工程的 AI Agent 必须自检并恪守以下**六不准原则**：
1. 🛑 **不准篡改测试断言**：测试脚本是验收门禁，任何修改断言逃避问题的行为属于严重违规。
2. 🛑 **不准私造业务协议**：严禁私自新增状态、事件、未定义的错误码或数据表字段。
3. 🛑 **不准后台静默变态**：定时巡检只发事件告警，绝不隐式修改状态或销毁数据。
4. 🛑 **不准出现裸拼 SQL**：任何 SQL 必须 100% 参数化绑定，阻绝一切注入漏洞。
5. 🛑 **不准使用 float 金额**：涉及金额/费用计算必须统一使用整数分（`int`）或 `Decimal`。
6. 🛑 **不准使用 Pydantic v1**：全部采用 Pydantic v2 标准语法与模型校验器。

每次完成代码编写或重构后，Agent 必须主动运行全套验证测试，确保测试套件 100% 全绿，无任何警告与回归缺陷。
