# IT 服务工单系统 (Service Ticket System) · 架构宪法与开发指令库 (CLAUDE.md)

> **文档性质**：项目最高工程宪法与 Claude Code 专属开发规范注入  
> **签发人**：系统架构负责人 (Chief Architect)  
> **核心基准**：严格以 `specs/` 目录下签署归档的 Day 4 技术 SPEC 为唯一准则  
> **适用范围**：工程全生命周期代码生成、重构、审计与自动化测试

---

## 常用命令清单 (Build, Run & Test Commands)

### 1. 自动化验收与测试套件 (Python / pytest)
```bash
# 运行全部 P0 阶段验收测试套件 (含 TC-10 注入防护测试)
pytest acceptance/tests/ -v

# 单独执行指定模块测试
pytest acceptance/tests/test_validation.py -v       # 字段级校验测试 (M-01/M-02)
pytest acceptance/tests/test_state_machine.py -v    # 13 条状态机边与权限测试
pytest acceptance/tests/test_security.py -v         # TC-10 SQL/XSS/魔数安全测试

# 执行端到端验收与回放脚本
python acceptance/scripts/run_eval.py
```

### 2. 微服务后端 (Java 17 + Spring Cloud / Maven)
```bash
# 依赖环境启动 (Nacos + MySQL)
cd it-ticket-cloud && docker compose up -d

# 父模块打包
cd it-ticket-cloud && mvn clean package -DskipTests

# 各子服务独立启动
java -jar gateway/target/it-ticket-gateway-1.0.0.jar
java -jar user-service/target/it-ticket-user-service-1.0.0.jar
java -jar ticket-service/target/it-ticket-ticket-service-1.0.0.jar
```

### 3. 前端工程 (Vue 3 + Vite + Element Plus)
```bash
cd frontend
npm install         # 安装依赖
npm run dev         # 启动前端开发服务器 (:5173，反向代理网关 :8080)
npm run build       # 生产环境打包构建
```

---

## 一、技术栈铁律 (Technology Stack Rules)

### 1.1 Python / FastAPI + Pydantic v2 规范
- **框架版本**：Python 3.11+ / 3.12，必须基于 **FastAPI + Pydantic v2** 构建工业级 API。
- **Pydantic v2 铁律（严禁 v1 废弃语法）**：
  - ❌ 禁止 `class Config:`，一律改用 `model_config = ConfigDict(from_attributes=True, ...)`。
  - ❌ 禁止 `.dict()`，一律改用 `.model_dump()`。
  - ❌ 禁止 `.json()`，一律改用 `.model_dump_json()`。
  - ❌ 禁止 `from_orm()` / `parse_obj()`，一律改用 `model_validate()`。
  - ❌ 禁止 `@validator` / `@root_validator`，一律改用 `@field_validator` / `@model_validator`。
  - 所有请求 DTO 字段使用 `Field(...)` 严格定义约束（如 `min_length`, `max_length`, `pattern`, `ge` 等）。
- **字段校验多重错误收集契约**：
  若请求中有多个字段不合法，**必须一次性收集所有违规字段及其原因**后完整输出，绝对禁止“碰到第一个字段错误就提前终止”。
- **统一响应封包**：
  所有 HTTP 接口必须统一返回三元组结构 `{ "code": 0, "msg": "success", "data": ... }`。未捕获异常统一由全局异常拦截器兜底返回 `500「系统繁忙,请稍后重试」`，**严禁泄露内部堆栈信息**。

### 1.2 金额与高精度数值铁律 (禁止 float 金额)
- ❌ **绝对禁止使用 `float` / `double` 存储、计算或在接口中传输任何金额/费用/价格**！
- **理论原因**：二进制浮点数在 IEEE 754 规范下具有天然的精度舍入缺陷，极易在结算、计费、优惠折算和财务对账中产生账目不平，引发严重的资损漏洞。
- **强制实现标准**：
  1. 金额统一采用**最小货币单位整数（分，`int`）**（例如 ¥88.50 必须存为 `8850`）。
  2. 若业务涉及高精度汇率或比例折算，必须使用标准库 `decimal.Decimal`，数据库统一映射为 `DECIMAL(10, 2)` 或 `BIGINT` 分。
  3. 仅在最终前端视图层展示时，方可除以 100 格式化输出为元。

### 1.3 数据库持久化与防 SQL 注入
- ❌ **绝对禁止任何形式的 SQL 字符串拼接**（禁止 f-string、`%`、`+` 拼接 SQL）。
- 所有数据库读写（无论 SQLite、MySQL 还是 ORM）**必须 100% 使用参数化占位符绑定（Parameterized Query）**。
- 遵循《验收评测协议书》TC-10 要求，对包含注入特征字符（如 `' OR 1=1 --`）的输入内容，必须纯作为字符串文本参数化安全落库。
- **字符集**：全库全表强制采用 `utf8mb4` / `utf8mb4_unicode_ci`。
- **时间规范**：统一格式为 `YYYY-MM-DD HH:mm:ss`，时区锁死东八区 `Asia/Shanghai` (GMT+8)。
- **枚举持久化**：数据库中一律存储枚举字符串名称 (`name()`)，严禁存储数字索引 (`ordinal`)。
- **乐观锁控制**：主表 `ticket` 必须包含 `version INT` 字段，更新必须携带 `WHERE ticket_id = :id AND version = :version`，行受影响为 0 则返回 `40900「工单已被他人操作,请刷新后重试」`。

---

## 二、SPEC 业务规范注入 (Specification Invariants)

### 2.1 统一错误码字典 (SPEC §2.7，仅限这 8 个)
全工程严格收敛于以下 8 个标准业务错误码，**严禁私自新造错误码**：

| 错误码 code | 语义说明 | 典型触发场景 |
| :--- | :--- | :--- |
| `0` | 操作成功 | 正常业务返回 |
| `40000` | 业务错误 (通用) | 字段级校验未通过、附件超限或格式不合法、缺少必填 remark |
| `40100` | 未登录或凭证失效 | Token 缺失、签名无效或过期 |
| `40300` | 无权限访问 | 跨角色操作、非提单本人尝试验收/补充/关闭他人工单 |
| `40400` | 资源不存在 | 工单号查无记录 |
| `40401` | 资产不存在 | 提交的 `asset_id` 在 CMDB 资产库中匹配失败 |
| `40900` | 数据冲突 | 3s 提交防重锁冲突、非法状态机流转、乐观锁并发冲突 |
| `500` | 系统繁忙 | 全局未捕获异常兜底，严禁泄漏堆栈 |

### 2.2 工单状态机闭环宪法 (SPEC §3)
包含 **8 种状态**，必须且仅能支持以下 **13 条合法流转边**。任何未定义流转一律返回 `40900「非法状态流转: X -> Y」`：

1. `(草稿/无)` → `CREATED`：动作 `SUBMIT`（仅限角色 `EMPLOYEE`）。落 `ticket_log(from=NULL)`；异步发送 `SUBMIT_SUCCESS` 通知；清空草稿。
2. `CREATED` → `ASSIGNED`：动作 `ACCEPT`（仅限角色 `ENGINEER`）。绑定处理人；乐观锁防抢单（冲突报 40900）；异步发送 `DISPATCH` 通知。
3. `ASSIGNED` → `PENDING_SUPPLEMENT`：动作 `REQUEST_SUPPLEMENT`（仅限角色 `ENGINEER`）。`remark` **强制必填**；异步发送 `PENDING_SUPPLEMENT` 通知。
4. `PENDING_SUPPLEMENT` → `ASSIGNED`：动作 `SUPPLEMENT`（**仅限提单本人**，非本人拦截 40300）。补充内容写入日志；不发通知。
5. `ASSIGNED` → `PENDING_EXTERNAL`：动作 `TRANSFER_EXTERNAL`（仅限角色 `ENGINEER`）。`remark` **强制必填**；异步发送 `PENDING_EXTERNAL` 通知。
6. `PENDING_EXTERNAL` → `ASSIGNED`：动作 `RESUME`（仅限角色 `ENGINEER`）。恢复日常处理；不发通知。
7. `ASSIGNED` → `PENDING_ACCEPTANCE`：动作 `RESOLVE`（仅限角色 `ENGINEER`）。提交解决方案；异步发送 `PENDING_ACCEPTANCE` 通知。
8. `REJECTED` → `ASSIGNED`：动作 `REWORK`（仅限角色 `ENGINEER`）。返工重新处理；复用 `DISPATCH` 通知。
9. `PENDING_ACCEPTANCE` → `ACCEPTED`：动作 `ACCEPT_APPROVE`（**仅限提单本人**，非本人拦截 40300）。工单进入**终态**；异步发送 `ACCEPT_APPROVED` 通知。
10. `PENDING_ACCEPTANCE` → `REJECTED`：动作 `ACCEPT_REJECT`（**仅限提单本人**，非本人拦截 40300）。`remark` **强制必填**；`reject_count` +1；异步发送 `ACCEPT_REJECTED` 通知。
11. `ACCEPTED` → `CLOSED`：动作 `CLOSE`（**仅限提单本人**）。工单彻底关闭（终态不可逆）。
12. `REJECTED` → `CLOSED`：动作 `CLOSE`（**仅限提单本人**，放弃验收关闭）。工单彻底关闭。
13. `CREATED` → `CLOSED`：动作 `CLOSE`（**仅限提单本人**，撤回待接单）。工单彻底关闭。

#### 角色守卫特权与红线边界：
- **主管（SUPERVISOR）特权**：放行普通角色权限检查（如代接单、代转派），但**绝不放行提单人专有守卫（`creator_only`）**！验收通过、验收驳回、补充材料、关闭工单必须由提单本人操作。
- **定时扫描红线**：超时与滞留扫描（处理超时 2h、滞留催办 24h）**仅生成通知事件告警（如 `TIMEOUT_ALERT`）**，**严禁在定时任务中隐式修改 ticket_status，严禁自动销毁工单**！

### 2.3 提单 7 字段级校验契约 (SPEC §1.7)
- `title`：必填，1~50 字符。**含 `<` 或 `>` 直接拒绝（40000，防御 XSS）**。
- `category`：必填，枚举 `{HARDWARE, SOFTWARE, NETWORK, ACCOUNT, OTHER}`。
- `priority`：必填，默认 `MEDIUM`，枚举 `{HIGH, MEDIUM, LOW}`。
- `description`：必填，10~500 字符。纯文本参数化存储，杜绝自动截断。
- `assetId`：选填，正则 `^IT-[A-Z]{2,4}-\d{8}$`，通过后必须调 CMDB 验证，查无返回 `40401`。
- `attachmentUrls`：选填，JSON 数组最多 3 个元素，形态必须匹配 `/files/{32位hex}.{jpg|jpeg|png}`。
- `expectedFinishTime`：选填，必须 ≥ 当前时间（未来或当前），违规返回 `40000`。

### 2.4 附件上传与真实魔数防护 (TC-10 验收基准)
- 单张 ≤ 5MB，单次请求 ≤ 15MB；白名单仅限 `.jpg`, `.jpeg`, `.png`。
- **必须嗅探二进制文件头魔数（MIME Sniffing）**，严禁轻信扩展名或 Content-Type。
  - JPEG 魔数：`FF D8 FF`
  - PNG 魔数：`89 50 4E 47 0D 0A 1A 0A`
  - 检出可执行头（如 `MZ` / `PE`）或魔数不符一律以 `40000` 拒绝。
- 落盘必须重命名为 `UUID32 + 原扩展名`，通过静态只读路径 `/files/{filename}` 映射。

### 2.5 幂等防重锁与原子发号机制 (SPEC §1.6 / §2.1)
- **提单防重锁（3 秒窗口）**：键 `submit:{userId}:{title.hashCode}`，TTL 3 秒，抢占失败返回 `40900「请勿重复提交」`。校验失败的请求不占锁。
- **通知去重锁（60 秒窗口）**：键 `notify:{ticketId}:{eventType}:{receiverId}`，TTL 60 秒，抢占失败直接跳过该接收人本次通知记录。
- **原子工单发号器**：主键 `ticket_id` 格式 `^TK\d{8}\d{4}$`（如 `TK202609240001`），基于发号表原子自增生成，严禁产生重复或断号混乱。

---

## 三、签署 SPEC 归档库与索引 (specs/)

项目签署 SPEC 已全量归档至根目录 `specs/` 并在工程中具备最高法律地位：
- `specs/技术SPEC规格书.md`：核心实体、校验规则、降级矩阵、13 边状态机、错误码总表。
- `specs/IT服务工单系统-验收评测协议书.md`：9 大量化评测指标、27 项验收用例、TC-10 安全防护。
- `specs/IT服务工单系统-需求归因文档.md`：企业 IT 报障痛点归因与方案推导。
- `specs/IT服务工单系统-技术风险登记册.md`：技术风险等级与应急预案。
- `specs/IT服务工单系统PRD-0921.docx`：原型设计与五角色泳道业务总纲。
- `specs/it工单系统-Qwen3-4B-算力与基础设施定盘表.md`：AI 本地化模型基础设施基线。

---

## 四、Claude Code 行为准则与红线守则

1. **绝对禁止篡改测试用例或评测断言**。
2. **绝对禁止引入未经 SPEC 签署的字段、枚举、流转边或错误码**。
3. **绝对禁止在定时任务中隐式变更工单状态或自动销毁工单**。
4. **绝对禁止裸拼 SQL 字符串**。
5. **绝对禁止使用 float 存储或计算金额**。
6. **绝对禁止使用 Pydantic v1 废弃语法**。
7. 每次完成代码修改，必须主动运行 pytest 全套用例进行回归验证，确保 100% 通过。
