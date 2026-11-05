# Day 27 生产级 MCP Server 协议调试与验证交付报告

**报告编号**：VERIFY-DAY27-IT-TICKET-MCP-01  
**测试时间**：2026-11-03  
**执行角色**：交付工程师 (Junior FDE) & 质量负责人  
**测试对象**：企业级 IT 工单与知识咨询 FastMCP Server (`mcp_service` / `run_day27_it_ticket_mcp.py`)  
**被测环境**：Windows 11 / Python 3.14 / ZeroDepFastMCP / Spring Cloud (8201 ticket-service & 8301 consultation-service 在线)

---

## 1. 协议合规与三层架构拓扑验证

### 1.1 三层拓扑架构图
```text
[Host 宿主环境: Cursor / Claude Desktop / Antigravity / Agent]
                     │ JSON-RPC 2.0 (stdio)
                     ▼
[MCP Server: IT-Ticket-Service-Server (mcp_service)]
  ├── ZeroDepFastMCP 协议编解码 (支持 initialize / tools / resources / prompts)
  ├── 身份透传守卫 (X-User-Id: U1001, X-User-Role: EMPLOYEE, X-Request-Id)
  └── 微服务适配层 (HTTPX 连接池)
                     │
       ┌─────────────┴─────────────┐
       ▼                           ▼
[consultation-service: 8301]   [ticket-service: 8201]
```

### 1.2 协议报文抓包记录 (JSON-RPC 2.0)

#### ① 协议握手 (`initialize`)
```json
// Client -> Server
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {"name": "ITServiceMCPClient", "version": "1.0.0"}
  }
}

// Server -> Client
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": {"listChanged": false},
      "resources": {"subscribe": false, "listChanged": false},
      "prompts": {"listChanged": false}
    },
    "serverInfo": {
      "name": "IT-Ticket-Service-Server",
      "version": "1.0.0"
    }
  }
}
```

#### ② 工具调用 (`tools/call` - `prepare_ticket_draft`)
```json
// Client -> Server
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "prepare_ticket_draft",
    "arguments": {
      "title": "会议室投屏盒子无法连接",
      "description": "HDMI 信号线无画面输入，无线投屏搜索不到设备",
      "category": "C_HW_PR",
      "priority": "MEDIUM"
    }
  }
}

// Server -> Client
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "📝 【工单草稿已就绪（待员工复核）】\n--------------------------------------------------\n📌 标题: 会议室投屏盒子无法连接\n🏷️ 分类: C_HW_PR (打印机与外设)\n⚡ 优先级: MEDIUM\n📄 描述: HDMI 信号线无画面输入，无线投屏搜索不到设备\n--------------------------------------------------\n⚠️ 安全防线提示：本单据尚未提交至企业数据库。需员工在前端确认无误后方可正式建单。"
      }
    ],
    "isError": false
  }
}
```

---

## 2. 自动化测试套件执行证据

全量测试套件执行覆盖契约模型、协议引擎、真实原语、端到端 stdio 管道：
```text
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\day12\demos
collected 19 items

services/python-retrieval/mcp_service/tests/test_contract.py ....        [ 21%]
services/python-retrieval/mcp_service/tests/test_engine.py .....         [ 47%]
services/python-retrieval/mcp_service/tests/test_mcp_client_e2e.py ..    [ 57%]
services/python-retrieval/mcp_service/tests/test_mcp_server.py ........  [100%]

============================= 19 passed in 0.65s ==============================
```

---

## 3. 真实微服务联动与输出验证

### 3.1 真实知识库检索 (`search_knowledge`)
* **请求入参**：`query="VPN 无法连接", limit=2`
* **下游响应**：通过 `consultation-service` (8301) 真实检索命中：
  1. `VPN连接失败（拨号/认证失败）` (ID: `art-1792650382237-99`, 版本 v1.0, 分类: "VPN与远程办公")
  2. `VPN连接失败（拨号/认证失败）` (ID: `art-1792085759135-484`)

### 3.2 真实工单流水查询 (`query_my_tickets`)
* **请求入参**：`user_id="U1001", limit=3`
* **下游响应**：穿透 `ticket-service` (8201) 内部接口，携带 `X-User-Id: U1001` 与链路追踪 ID，正确返回流水信息。

### 3.3 连通性状态探针 (`it://system/status`)
* **响应报文**：
```json
{
  "server_name": "IT-Ticket-Service-Server",
  "current_user_context": {
    "user_id": "U1001",
    "role": "EMPLOYEE"
  },
  "services": {
    "ticket_service_8201": {
      "url": "http://127.0.0.1:8201",
      "status": "UP"
    },
    "consultation_service_8301": {
      "url": "http://127.0.0.1:8301",
      "status": "UP"
    }
  }
}
```

---

## 4. 交付打卡项 Checklist

- [x] **语义自包含**：每一个 `@mcp.tool` 函数具备完整 Docstring 与精确的入参类型注解，自动推导出合规的 JSON Schema。
- [x] **协议合规性**：`tools/list`、`tools/call`、`resources/read`、`prompts/get` 100% 遵照 JSON-RPC 2.0 工业标准。
- [x] **健壮错误处理**：下游网络不可达或超时时返回带有具体 HTTP 错误描述的业务友好字符串，绝不让底层抛出未捕获异常崩溃。
- [x] **跨平台复用**：已生成 `day27/mcp_config.json`，可直接粘贴挂载至 Cursor、Claude Desktop 或 Antigravity。
- [x] **双模自适应**：在当前无 `mcp` 第三方库的 Python 3.14 环境下，`ZeroDepFastMCP` 引擎零依赖完美承接全套功能。
- [x] **项目端开箱即用**：提供 `ITServiceMCPClient`，支持进程内调用、stdio 管道调用及一键转换为 OpenAI Tools 数组。
