# IT 服务工单与知识咨询 MCP Server 实施计划 (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个生产级 IT 服务工单与知识咨询 FastMCP Server（封装知识检索、员工工单状态查询与规范草稿整理），并提供轻量级 Python MCP Client（支持进程内直调、stdio 管道与 OpenAI tools 格式导出），实现项目内部及外部 IDE 的开箱即用调用。

**Architecture:** 采用双模自适应 FastMCP 引擎（官方 `mcp` 库与零依赖高可靠 `ZeroDepFastMCP` 动态降级兼容），集成全链路身份追踪守卫（`X-User-Id` / `X-Request-Id`），全面发布 3 个 Tools、2 个 Resources 与 2 个 Prompts 标准原语，并通过下沉的 `mcp_service` 包与 `day27/` 快捷脚本形成完整的交付闭环。

**Tech Stack:** Python 3.14, JSON-RPC 2.0, HTTPX, FastMCP, Pytest.

**Spec:** [docs/superpowers/specs/2026-11-03-it-ticket-mcp-server-design.md](file:///d:/day12/demos/docs/superpowers/specs/2026-11-03-it-ticket-mcp-server-design.md)

## Global Constraints

- 不为外部依赖故障添加静默回退。当下游微服务（8201/8301）异常时，必须明确区分失败、正常空结果与业务拒绝，保留真实原因（严格遵守 AGENTS.md）。
- 严格遵循身份边界：工单查询必须携带正确的 `X-User-Id` 请求头，默认取自环境变量 `MCP_USER_ID`（默认 `U1001`）。
- 每次工具调用必须生成并透传全局唯一的 `X-Request-Id` UUID，确保链路审计完整。
- 零依赖自适应降级：当前环境无需预装 `mcp` 外部库，ZeroDepFastMCP 必须完整跑通标准 JSON-RPC 2.0 stdio 协议。
- 建单防误触红线：`prepare_ticket_draft` 严格只产出草稿数据结构与人机复核提示，严禁直接向数据库写入真实工单。

## Review Focus

1. 下游微服务断网或 503 异常：工具调用必须返回带有明确 HTTP/网络错误描述的业务错误，绝不抛出未捕获异常导致 Server 进程挂死。
2. 缺失 `user_id` 查询工单：能自动读取 `MCP_USER_ID` 或兜底 `U1001`，保证在 Cursor/Claude 桌面端零配置可用。
3. `search_knowledge` 缺失 `X-Request-Id`：自动生成 UUID 补齐请求头，杜绝下游 400 VALIDATION_ERROR。
4. 非法分类或优先级输入：草稿生成工具必须执行防御性校验并纠正或提示。
5. stdio 通道换行与缓冲区管理：JSON-RPC 2.0 序列化必须采用单行 JSON 附加换行符，避免管道死锁。

---

## File Structure

```text
services/python-retrieval/mcp_service/
├── __init__.py                      # 统一导出 ITTicketMCPServer 与 ITServiceMCPClient
├── contract.py                      # 核心数据契约（TicketDraft, CategoryTree, Envelopes）
├── engine.py                        # 双模自适应 FastMCP 引擎（ZeroDepFastMCP 零依赖实现）
├── server.py                        # MCP Server 核心实现（三大原语注册与微服务适配）
├── client.py                        # 项目端 MCP 客户端适配器（in_process/stdio 及 to_openai_tools）
└── tests/                           # 单元与集成测试套件
    ├── __init__.py
    ├── test_contract.py             # 契约与序列化测试
    ├── test_engine.py               # 协议引擎 JSON-RPC 2.0 报文处理测试
    ├── test_mcp_server.py           # 原语逻辑与微服务连通性测试
    └── test_mcp_client_e2e.py       # 端到端 stdio 管道交互测试

day27/
├── run_day27_it_ticket_mcp.py       # Day 27 交付快捷启动与自检入口脚本
├── run_day27_it_mcp_client.py       # Day 27 项目调用端实操演示脚本
├── mcp_config.json                  # Cursor / Claude Desktop 配置文件片段
└── mcp_verification_report.md       # Day 27 生产级协议调试与验证交付报告
```

---

### Task 1: 核心数据契约与常量定义 (`contract.py`)

**Files:**
- Create: `services/python-retrieval/mcp_service/contract.py`
- Create: `services/python-retrieval/mcp_service/tests/__init__.py`
- Test: `services/python-retrieval/mcp_service/tests/test_contract.py`

**Interfaces:**
- Consumes: None (标准库 `dataclasses`, `typing`, `json`)
- Produces:
  - `VALID_CATEGORIES: Dict[str, Dict[str, str]]`
  - `VALID_PRIORITIES: set`
  - `TicketDraft(title: str, description: str, category: Optional[str], priority: str)`
  - `CategoryItem(id: str, name: str, description: str)`
  - `ToolResultEnvelope(success: bool, data: Any, error: Optional[str])`

- [ ] **Step 1: 编写失败的单元测试 (`test_contract.py`)**

```python
# services/python-retrieval/mcp_service/tests/test_contract.py
import pytest
from mcp_service.contract import (
    VALID_CATEGORIES,
    VALID_PRIORITIES,
    TicketDraft,
    ToolResultEnvelope,
)

def test_valid_categories_content():
    assert "C_HW_PC" in VALID_CATEGORIES
    assert "C_SW" in VALID_CATEGORIES
    assert "C_NET" in VALID_CATEGORIES
    assert "C_OTH" in VALID_CATEGORIES
    assert VALID_CATEGORIES["C_HW_PC"]["name"] == "PC与电脑硬件"

def test_ticket_draft_validation():
    draft = TicketDraft(title="测试标题", description="测试问题描述", category="C_HW_PC", priority="HIGH")
    assert draft.category == "C_HW_PC"
    assert draft.priority == "HIGH"

def test_ticket_draft_invalid_fallback():
    draft = TicketDraft(title="测试", description="描述", category="UNKNOWN_CAT", priority="URGENT")
    assert draft.category == "C_OTH"
    assert draft.priority == "MEDIUM"

def test_tool_result_envelope_to_text():
    env = ToolResultEnvelope(success=True, data={"ticket_id": "T123"})
    assert "ticket_id" in env.to_text()
    assert env.success is True
```

- [ ] **Step 2: 运行测试验证失败**

Run: `$env:PYTHONPATH="services/python-retrieval"; python -m pytest services/python-retrieval/mcp_service/tests/test_contract.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'mcp_service'`

- [ ] **Step 3: 实现 `contract.py`**

创建 `services/python-retrieval/mcp_service/contract.py`，实现 `VALID_CATEGORIES`、`VALID_PRIORITIES`、`TicketDraft`（内置分类与优先级校验重整逻辑）、`CategoryItem` 与 `ToolResultEnvelope`。

- [ ] **Step 4: 运行测试验证通过**

Run: `$env:PYTHONPATH="services/python-retrieval"; python -m pytest services/python-retrieval/mcp_service/tests/test_contract.py`
Expected: PASS (4 passed)

- [ ] **Step 5: 提交代码**

```bash
git add services/python-retrieval/mcp_service/contract.py services/python-retrieval/mcp_service/tests/
git commit -m "feat(mcp): add core data contracts and categories taxonomy"
```

---

### Task 2: 双模自适应 FastMCP 引擎 (`engine.py`)

**Files:**
- Create: `services/python-retrieval/mcp_service/engine.py`
- Test: `services/python-retrieval/mcp_service/tests/test_engine.py`

**Interfaces:**
- Consumes: None (标准库 `sys`, `json`, `inspect`, `typing`)
- Produces:
  - `FastMCP`: 自适应导出的类（优先导入官方 `mcp.server.fastmcp.FastMCP`，不存在时导出 `ZeroDepFastMCP`）
  - `ZeroDepFastMCP(name: str)`
    - `@tool(name=None, description=None)`
    - `@resource(uri: str)`
    - `@prompt(name=None)`
    - `handle_jsonrpc(request: Dict[str, Any]) -> Optional[Dict[str, Any]]`
    - `run(transport="stdio")`

- [ ] **Step 1: 编写失败的测试用例 (`test_engine.py`)**

```python
# services/python-retrieval/mcp_service/tests/test_engine.py
from mcp_service.engine import ZeroDepFastMCP

def test_engine_tool_registration_and_list():
    mcp = ZeroDepFastMCP("TestServer")
    
    @mcp.tool()
    def greet(name: str) -> str:
        """Say hello to someone."""
        return f"Hello, {name}!"
        
    req = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    resp = mcp.handle_jsonrpc(req)
    assert resp["id"] == 1
    assert "result" in resp
    tools = resp["result"]["tools"]
    assert len(tools) == 1
    assert tools[0]["name"] == "greet"
    assert tools[0]["description"] == "Say hello to someone."
    assert "name" in tools[0]["inputSchema"]["properties"]

def test_engine_tool_call():
    mcp = ZeroDepFastMCP("TestServer")
    
    @mcp.tool()
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b
        
    req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": "add", "arguments": {"a": 3, "b": 7}}
    }
    resp = mcp.handle_jsonrpc(req)
    assert resp["id"] == 2
    assert resp["result"]["isError"] is False
    assert resp["result"]["content"][0]["text"] == "10"

def test_engine_resource_read():
    mcp = ZeroDepFastMCP("TestServer")
    
    @mcp.resource("test://info")
    def get_info() -> str:
        return "system_ok"
        
    req = {"jsonrpc": "2.0", "id": 3, "method": "resources/read", "params": {"uri": "test://info"}}
    resp = mcp.handle_jsonrpc(req)
    assert resp["result"]["contents"][0]["text"] == "system_ok"
```

- [ ] **Step 2: 运行测试验证失败**

Run: `$env:PYTHONPATH="services/python-retrieval"; python -m pytest services/python-retrieval/mcp_service/tests/test_engine.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'mcp_service.engine'`

- [ ] **Step 3: 实现 `engine.py`**

实现 `ZeroDepFastMCP`，支持：
1. 装饰器 `@tool()`, `@resource(uri)`, `@prompt()`；
2. 利用 `inspect.signature` 和类型注解自动解析生成符合 JSON Schema 的 `inputSchema`；
3. 处理 `initialize`, `notifications/initialized`, `tools/list`, `tools/call`, `resources/list`, `resources/read`, `prompts/list`, `prompts/get`, `ping` 方法；
4. 异常隔离：调用抛出异常时返回 `isError=True` 与友好错误文本，不让 Server 崩溃；
5. `run(transport="stdio")`：从 `sys.stdin` 逐行读取 JSON 报文，写入 `sys.stdout` 并 flush。

- [ ] **Step 4: 运行测试验证通过**

Run: `$env:PYTHONPATH="services/python-retrieval"; python -m pytest services/python-retrieval/mcp_service/tests/test_engine.py`
Expected: PASS (3 passed)

- [ ] **Step 5: 提交代码**

```bash
git add services/python-retrieval/mcp_service/engine.py services/python-retrieval/mcp_service/tests/test_engine.py
git commit -m "feat(mcp): implement zero-dependency dual-mode FastMCP engine"
```

---

### Task 3: IT Ticket MCP Server 核心实现 (`server.py`)

**Files:**
- Create: `services/python-retrieval/mcp_service/server.py`
- Create: `services/python-retrieval/mcp_service/__init__.py`
- Test: `services/python-retrieval/mcp_service/tests/test_mcp_server.py`

**Interfaces:**
- Consumes:
  - `engine.FastMCP`
  - `contract.*` (TicketDraft, VALID_CATEGORIES, etc.)
  - 下游真实微服务 HTTP (`8201` ticket-service, `8301` consultation-service)
- Produces:
  - `mcp: FastMCP` (已配置好所有原语的服务实例)
  - `search_knowledge(query, category_id, limit)`
  - `query_my_tickets(user_id, status, limit, created_after, category)`
  - `prepare_ticket_draft(title, description, category, priority)`
  - `get_categories_tree()` (`it://categories/tree`)
  - `get_system_status()` (`it://system/status`)
  - `it_troubleshoot_prompt(issue_keyword)`
  - `ticket_draft_confirm_prompt(title, description, category, priority)`

- [ ] **Step 1: 编写单元测试 (`test_mcp_server.py`)**

```python
# services/python-retrieval/mcp_service/tests/test_mcp_server.py
import pytest
from mcp_service.server import (
    mcp,
    prepare_ticket_draft,
    get_categories_tree,
    it_troubleshoot_prompt,
    query_my_tickets,
    search_knowledge,
)

def test_prepare_ticket_draft_valid():
    res = prepare_ticket_draft("网络无法连接", "工位网口亮红灯，无法上网", "C_NET", "HIGH")
    assert "工单草稿已就绪" in res
    assert "网络无法连接" in res
    assert "C_NET" in res
    assert "需员工在前端确认" in res

def test_resource_categories_tree():
    raw_json = get_categories_tree()
    assert "C_HW_PC" in raw_json
    assert "打印机与外设" in raw_json

def test_prompt_troubleshoot():
    prompt = it_troubleshoot_prompt("VPN")
    assert "VPN" in prompt
    assert "排查" in prompt

def test_live_or_graceful_tickets():
    # 测试连接 8201 真实服务或错误捕获
    res = query_my_tickets(user_id="U1001", limit=3)
    assert isinstance(res, str)
    # 不发生未捕获异常崩溃

def test_live_or_graceful_knowledge():
    # 测试连接 8301 真实服务或错误捕获
    res = search_knowledge(query="VPN", limit=2)
    assert isinstance(res, str)
```

- [ ] **Step 2: 运行测试验证失败**

Run: `$env:PYTHONPATH="services/python-retrieval"; python -m pytest services/python-retrieval/mcp_service/tests/test_mcp_server.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'mcp_service.server'`

- [ ] **Step 3: 实现 `server.py` 与 `__init__.py`**

1. 读取环境变量 `TICKET_SERVICE_BASE_URL` (默认 `http://127.0.0.1:8201`) 与 `KNOWLEDGE_SEARCH_BASE_URL` (默认 `http://127.0.0.1:8301`)；
2. 注入身份解析与 `X-Request-Id` UUID 生成器；
3. 注册 3 个 `@mcp.tool()`，严格处理 HTTP 连接、状态码与业务包裹返回；
4. 注册 2 个 `@mcp.resource()`；
5. 注册 2 个 `@mcp.prompt()`；
6. 完善 `__init__.py` 导出 `mcp` 实例。

- [ ] **Step 4: 运行测试验证通过**

Run: `$env:PYTHONPATH="services/python-retrieval"; python -m pytest services/python-retrieval/mcp_service/tests/test_mcp_server.py`
Expected: PASS (5 passed)

- [ ] **Step 5: 提交代码**

```bash
git add services/python-retrieval/mcp_service/server.py services/python-retrieval/mcp_service/__init__.py services/python-retrieval/mcp_service/tests/test_mcp_server.py
git commit -m "feat(mcp): implement core IT ticket and knowledge MCP server primitives"
```

---

### Task 4: 项目端通用 MCP Client (`client.py`) 与协议测试

**Files:**
- Create: `services/python-retrieval/mcp_service/client.py`
- Test: `services/python-retrieval/mcp_service/tests/test_mcp_client_e2e.py`

**Interfaces:**
- Consumes:
  - `mcp_service.server.mcp`
  - `subprocess`, `threading`, `json`
- Produces:
  - `class ITServiceMCPClient`
    - `list_tools() -> List[Dict[str, Any]]`
    - `call_tool(name: str, arguments: Dict[str, Any]) -> str`
    - `read_resource(uri: str) -> str`
    - `get_prompt(name: str, arguments: Dict[str, Any]) -> str`
    - `to_openai_tools() -> List[Dict[str, Any]]`

- [ ] **Step 1: 编写客户端端到端测试用例 (`test_mcp_client_e2e.py`)**

```python
# services/python-retrieval/mcp_service/tests/test_mcp_client_e2e.py
import pytest
from mcp_service.client import ITServiceMCPClient

def test_client_in_process_mode():
    client = ITServiceMCPClient(mode="in_process")
    
    # 1. 发现工具
    tools = client.list_tools()
    tool_names = [t["name"] for t in tools]
    assert "search_knowledge" in tool_names
    assert "query_my_tickets" in tool_names
    assert "prepare_ticket_draft" in tool_names
    
    # 2. 导出为 OpenAI Tools
    openai_tools = client.to_openai_tools()
    assert len(openai_tools) >= 3
    assert openai_tools[0]["type"] == "function"
    assert "name" in openai_tools[0]["function"]
    
    # 3. 直调草稿工具
    draft_res = client.call_tool("prepare_ticket_draft", {
        "title": "显示器黑屏",
        "description": "电源灯亮但屏幕无显示",
        "category": "C_HW_PC",
        "priority": "MEDIUM"
    })
    assert "工单草稿已就绪" in draft_res
    
    # 4. 读取资源
    cat_res = client.read_resource("it://categories/tree")
    assert "C_HW_PC" in cat_res
```

- [ ] **Step 2: 运行测试验证失败**

Run: `$env:PYTHONPATH="services/python-retrieval"; python -m pytest services/python-retrieval/mcp_service/tests/test_mcp_client_e2e.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'mcp_service.client'`

- [ ] **Step 3: 实现 `client.py` 并增加子进程 stdio 交互支持**

实现 `ITServiceMCPClient`：
1. 默认 `mode="in_process"` 直接调用绑定好的 `mcp` 实例字典；
2. 支持 `mode="stdio"` 通过 `subprocess.Popen` 启动子进程，通过标准管道读写 JSON-RPC 2.0 报文；
3. 实现 `to_openai_tools()` 格式转换方法。

- [ ] **Step 4: 运行测试验证通过**

Run: `$env:PYTHONPATH="services/python-retrieval"; python -m pytest services/python-retrieval/mcp_service/tests/test_mcp_client_e2e.py`
Expected: PASS

- [ ] **Step 5: 提交代码**

```bash
git add services/python-retrieval/mcp_service/client.py services/python-retrieval/mcp_service/tests/test_mcp_client_e2e.py
git commit -m "feat(mcp): implement ITServiceMCPClient and OpenAI tools adapter"
```

---

### Task 5: Day 27 交付套件与跨端配置文件集成

**Files:**
- Create: `day27/run_day27_it_ticket_mcp.py`
- Create: `day27/run_day27_it_mcp_client.py`
- Create: `day27/mcp_config.json`
- Create: `day27/mcp_verification_report.md`

**Interfaces:**
- Consumes:
  - `mcp_service.server.mcp`
  - `mcp_service.client.ITServiceMCPClient`
- Produces:
  - CLI 执行入口（支持自检测试与 `run` 监听）
  - 项目调用演示输出
  - Cursor/Claude 挂载配置文件
  - 详细验收打卡报告

- [ ] **Step 1: 编写 `day27/run_day27_it_ticket_mcp.py`**

封装服务启动器：
* 当参数带 `run` 时，执行 `mcp.run(transport="stdio")`；
* 当不带参数时，执行全量原语自检（测试工具调用、只读资源、提示词渲染）并打印自测报告。

- [ ] **Step 2: 编写 `day27/run_day27_it_mcp_client.py`**

演示项目内部如何使用 `ITServiceMCPClient`：
1. 演示以进程内直调方式获取分类树与生成工单草稿；
2. 演示将 MCP 工具转换为 OpenAI 格式，模拟大模型 Function Calling；
3. 演示以 stdio 子进程方式发起真实的 JSON-RPC 2.0 工具调用。

- [ ] **Step 3: 编写 `day27/mcp_config.json`**

提供可直接粘贴至 Cursor（`.cursor/mcp.json`）与 Claude Desktop（`claude_desktop_config.json`）的标准配置结构。

- [ ] **Step 4: 运行全量测试验证与演练**

Run:
1. `python day27/run_day27_it_ticket_mcp.py`
2. `python day27/run_day27_it_mcp_client.py`
3. `$env:PYTHONPATH="services/python-retrieval"; python -m pytest services/python-retrieval/mcp_service/tests/`

Expected: 全部自检通过，输出清晰的 JSON-RPC 交互日志。

- [ ] **Step 5: 编写 `day27/mcp_verification_report.md` 并提交**

完整记录本次 MCP Server 的协议握手抓包日志、工具执行结果、真实微服务响应时延以及打卡 Checklist。

```bash
git add day27/run_day27_it_ticket_mcp.py day27/run_day27_it_mcp_client.py day27/mcp_config.json day27/mcp_verification_report.md
git commit -m "feat(day27): deliver IT ticket FastMCP server, client runner, and verification report"
```
