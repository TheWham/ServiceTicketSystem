# IT 服务工单与知识咨询 MCP Server 技术架构规格书 (Technical Specification)

**文档编号**：SPEC-20261103-IT-TICKET-MCP-01  
**生效日期**：2026-11-03  
**状态**：APPROVED (评审通过)  
**设计负责人**：Antigravity & FDE 交付工程组  
**关联规范**：[AGENTS.md](file:///d:/day12/demos/AGENTS.md) / [2026-09-30-rag-consultation-composition-design.md](file:///d:/day12/demos/docs/superpowers/specs/2026-09-30-rag-consultation-composition-design.md) / [武汉柯莱特企培_Day27 讲义](file:///d:/day12/demos/day27/%E6%AD%A6%E6%B1%89%E6%9F%AF%E8%8E%B1%E7%89%B9%E4%BC%81%E5%9F%B9_Day27_%E5%B7%A5%E4%B8%9A%E4%BA%92%E8%81%94%E6%96%B0%E6%A0%87%E5%87%86%EF%BC%9AAnthropic_MCP%E5%8D%8F%E8%AE%AE%E6%9E%B6%E6%9E%84%E4%B8%8E%E4%BC%81%E4%B8%9BServer%E8%B5%84%E4%BA%A7%E5%8C%96%E8%AE%B2%E4%B9%89.md)

---

## 1. 业务背景与设计目标

### 1.1 业务诉求
当前项目中的核心业务工具（知识检索 `search_knowledge`、员工工单状态查询 `query_my_tickets`、建单草稿整理 `prepare_ticket`）硬编码在 `services/python-retrieval/agent_service/tools.py` 内部。这种“烟囱式”的开发方式导致这些优质能力无法跨框架、跨端复用，外部开发环境（如 Cursor、Claude Desktop、Antigravity IDE）完全无法直接调用。

### 1.2 目标收益
1. **资产标准化**：基于 Anthropic 开源的 **MCP (Model Context Protocol)** 工业标准，将 IT 知识检索与工单管理能力统一抽象为标准 MCP Server。
2. **核心下沉与开箱即用**：MCP Server 核心实现直接下沉至 `services/python-retrieval/mcp_service`，作为项目的共享公共基础设施。
3. **供项目端高效调用**：提供专用的 `ITServiceMCPClient`，支持进程内零开销直调与子进程 stdio 管道调用，并支持将 MCP 工具列表动态导出为 OpenAI Function Calling 格式，方便项目内 Agent 随时挂载。
4. **Day 27 教学交付打卡**：在 `day27/` 目录下提供完整的一键自检运行入口、客户端演练脚本、Cursor 挂载配置与协议验证报告。

---

## 2. 整体架构与模块设计

### 2.1 系统三层拓扑架构

```text
┌────────────────────────────────────────────────────────────────────────┐
│ Host 宿主层                                                             │
│  ├── 外部开发工具：Cursor / Claude Desktop / Antigravity IDE (stdio 管道)│
│  └── 项目内应用：agent_service / 自动化脚本 (ITServiceMCPClient 直调)    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ JSON-RPC 2.0 (stdio / in-process)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ MCP Server 端: IT-Ticket-Service-Server                                │
│ (services/python-retrieval/mcp_service)                                │
│                                                                        │
│  ├── 1. 双模自适应通信引擎 (ZeroDepFastMCP / 官方 FastMCP 自动适配)       │
│  ├── 2. 身份上下文与链路追踪守卫 (X-User-Id / X-User-Role / X-Request-Id)│
│  ├── 3. 核心原语注册池 (Tools / Resources / Prompts)                     │
│  └── 4. 微服务适配网关 (集成连接池、超时控制与精准错误捕获)               │
└──────────────────┬─────────────────────────────────┬───────────────────┘
                   │ HTTP GET (X-Request-Id)         │ HTTP GET/POST
                   ▼                                 ▼
┌─────────────────────────────────────┐ ┌────────────────────────────────┐
│ consultation-service (Port: 8301)   │ │ ticket-service (Port: 8201)    │
│  - /api/v1/knowledge/search 知识检索 │ │  - /api/v1/tickets/my 本人查单 │
└─────────────────────────────────────┘ └────────────────────────────────┘
```

### 2.2 目录结构与代码组织

```text
services/python-retrieval/
└── mcp_service/                         # 核心下沉服务包（公共基础设施）
    ├── __init__.py                      # 统一导出 ITTicketMCPServer 与 ITServiceMCPClient
    ├── server.py                        # MCP Server 核心实现（三大原语注册与底层微服务适配）
    ├── client.py                        # 项目端 MCP 客户端适配器（支持 in_process/stdio 及 to_openai_tools）
    ├── engine.py                        # 双模自适应 FastMCP 引擎（零依赖 JSON-RPC 2.0 降级兼容）
    ├── contract.py                      # 核心数据契约（TicketDraft, CategoryTree, Envelopes）
    └── tests/                           # 测试套件
        ├── __init__.py
        ├── test_mcp_server.py           # 原语逻辑与微服务连通性测试
        └── test_mcp_client_e2e.py       # 端到端 stdio 管道通信测试

day27/
├── run_day27_it_ticket_mcp.py           # Day 27 交付快捷入口（支持 stdio 运行与一键全量自检）
├── run_day27_it_mcp_client.py           # Day 27 项目调用端演练脚本（演示三种调用姿势）
├── mcp_config.json                      # 供 Cursor / Claude Desktop 导入的挂载配置文件
└── mcp_verification_report.md           # Day 27 生产级协议调试与验证交付报告
```

---

## 3. 三大核心原语详细定义

### 3.1 Tools（可执行工具）

#### 1. `search_knowledge`
* **功能描述**：在企业知识库中检索已发布（PUBLISHED）的 IT 办公知识条目，返回标题、摘要与排障指南。
* **输入参数**：
  * `query: str`（必填，检索关键词，如 "VPN 无法连接"）
  * `category_id: Optional[str]`（可选，限定分类 ID）
  * `limit: int`（可选，返回条数，默认 5，最大 20）
* **底层调用**：`consultation-service` (`GET /api/v1/knowledge/search?query=...&page=1&pageSize=...`)
* **输出规范**：返回格式化后的匹配文章切片列表；若下游微服务不可用，返回带有明确错误状态的说明，不伪造静默数据。

#### 2. `query_my_tickets`
* **功能描述**：查询当前员工名下的工单流水及其处理进度。
* **输入参数**：
  * `user_id: Optional[str]`（可选，覆盖当前操作员工号；缺省时从环境变量 `MCP_USER_ID` 读取）
  * `status: Optional[str]`（可选，按状态过滤：`NEW`/`ASSIGNED`/`IN_PROGRESS`/`PENDING_ACCEPTANCE`/`COMPLETED`/`CLOSED`）
  * `limit: int`（可选，默认 10，最大 50）
  * `created_after: Optional[str]`（可选，ISO 日期格式 `YYYY-MM-DD`）
  * `category: Optional[str]`（可选，按分类过滤）
* **底层调用**：`ticket-service` (`GET /api/v1/tickets/my`)
* **输出规范**：返回格式化的工单卡片列表（包含流水号、标题、状态、优先级、提交时间及当前处理人）。

#### 3. `prepare_ticket_draft`
* **功能描述**：将员工报告的 IT 故障事实整理为标准工单草稿。**仅产出草稿，严格不执行落库写入**。
* **输入参数**：
  * `title: str`（必填，工单简明标题）
  * `description: str`（必填，问题详细现象与环境描述）
  * `category: Optional[str]`（可选，仅限有效分类：`C_HW_PC`/`C_HW_PR`/`C_SW`/`C_NET`/`C_ACC`/`C_OTH`）
  * `priority: Optional[str]`（可选，优先级：`HIGH`/`MEDIUM`/`LOW`，默认 `MEDIUM`）
* **业务逻辑**：本地数据契约校验；非法优先级或分类自动纠正或提示。
* **输出规范**：返回草稿 JSON 与确认提示文本（“工单草稿已准备完毕，请员工复核确认后再正式提交”）。

### 3.2 Resources（只读资源通道）

#### 1. `it://categories/tree`
* **MIME 类型**：`application/json`
* **数据内容**：企业官方 IT 工单末级分类树字典。
```json
{
  "categories": [
    {"id": "C_HW_PC", "name": "PC与电脑硬件", "description": "台式机/笔记本/显示器/鼠标键盘硬件故障"},
    {"id": "C_HW_PR", "name": "打印机与外设", "description": "办公室共享打印机卡纸/缺墨/扫描故障"},
    {"id": "C_SW", "name": "办公软件与授权", "description": "Office/邮件客户端/操作系统与企业软件安装授权"},
    {"id": "C_NET", "name": "办公网络与VPN", "description": "内网WiFi/工位网口/企业远程VPN拨号连接异常"},
    {"id": "C_ACC", "name": "账号权限与密码", "description": "域账号锁定/密码重置/业务系统权限申请"},
    {"id": "C_OTH", "name": "其他IT支持", "description": "未归类办公IT支持与咨询"}
  ]
}
```

#### 2. `it://system/status`
* **MIME 类型**：`application/json`
* **数据内容**：当前 MCP Server 运行状态、绑定的员工身份及下游微服务健康连通性。

### 3.3 Prompts（标准化指令模版）

#### 1. `it_troubleshoot_prompt(issue_keyword: str)`
* **提示词模版**：引导大模型扮演资深企业 IT 桌面工程师，遵循四步排查法（收集事实、检索内部知识、谨慎排查避开高危、无法解决生成草稿）。

#### 2. `ticket_draft_confirm_prompt(title: str, description: str, category: str, priority: str)`
* **提示词模版**：面向员工起草规范的人机确认沟通卡片，征询建单放行指令。

---

## 4. 身份穿透、安全规范与异常处理

1. **身份双轨机制**：
   * 默认从运行环境读取 `MCP_USER_ID`（默认 `U1001`）与 `MCP_USER_ROLE`（默认 `EMPLOYEE`）。
   * 工具支持显式传入 `user_id`（主要供自动化集成测试与多身份模拟）。
2. **全链路追踪（Tracing）**：
   * 每次 MCP 工具调用自动生成全局唯一请求 ID（`X-Request-Id: mcp-<uuid>`），并透传给 Spring Cloud 网关。
3. **零静默降级原则（遵守 AGENTS.md 军规）**：
   * 下游微服务（8201 / 8301）若网络不可达或返回 HTTP 4xx/5xx，MCP 工具**明确返回真实错误原因**，绝不伪造虚假通过数据。

---

## 5. 项目端 MCP Client 架构 (`ITServiceMCPClient`)

```python
class ITServiceMCPClient:
    def __init__(self, mode: str = "in_process", server_cmd: Optional[List[str]] = None):
        """
        mode:
          - 'in_process': 进程内直调，无管道开销，适于 Agent 业务直接集成
          - 'stdio': 启动子进程通过标准输入输出执行 JSON-RPC 2.0 报文通信，适于协议验证
        """
        ...

    def list_tools(self) -> List[Dict[str, Any]]: ...
    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]: ...
    def read_resource(self, uri: str) -> str: ...
    def get_prompt(self, name: str, arguments: Dict[str, Any]) -> str: ...
    def to_openai_tools(self) -> List[Dict[str, Any]]: ...
```

---

## 6. 验收与交付检查清单 (Checklist)

- [ ] **代码实现**：
  - [ ] `services/python-retrieval/mcp_service/engine.py`（零依赖自适应 FastMCP 引擎）
  - [ ] `services/python-retrieval/mcp_service/contract.py`（数据模型契约）
  - [ ] `services/python-retrieval/mcp_service/server.py`（核心原语注册与微服务通信）
  - [ ] `services/python-retrieval/mcp_service/client.py`（通用 MCP Client 与 OpenAI 工具适配器）
  - [ ] `services/python-retrieval/mcp_service/__init__.py`
- [ ] **测试与交付件**：
  - [ ] `services/python-retrieval/mcp_service/tests/test_mcp_server.py`（原语功能单元测试）
  - [ ] `services/python-retrieval/mcp_service/tests/test_mcp_client_e2e.py`（stdio 管道端到端测试）
  - [ ] `day27/run_day27_it_ticket_mcp.py`（Day 27 独立运行与自检入口）
  - [ ] `day27/run_day27_it_mcp_client.py`（项目调用端实操演示）
  - [ ] `day27/mcp_config.json`（Cursor / Claude Desktop 配置文件）
  - [ ] `day27/mcp_verification_report.md`（协议验证报告）
