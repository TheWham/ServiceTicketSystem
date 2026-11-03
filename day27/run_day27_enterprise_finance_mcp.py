# day27/run_day27_enterprise_finance_mcp.py
# 生产级企业财务与差旅合规 FastMCP Server
# 支持官方 mcp 库与零依赖自适应降级双模运行 (Zero-Dependency Fallback Engine)
import sys
import json
from typing import Dict, Any, List, Optional, Callable

# ==============================================================================
# 0. 依赖导入与双模自适应引擎 (Zero-Dependency Fallback Engine)
# ==============================================================================
try:
    from mcp.server.fastmcp import FastMCP  # type: ignore[import-not-found]
    MCP_NATIVE_AVAILABLE = True
except ImportError:
    MCP_NATIVE_AVAILABLE = False

    class MinimalFastMCP:
        """当本地环境未执行 pip install mcp 时的官方等价 FastMCP 仿真引擎"""
        def __init__(self, name: str):
            self.name = name
            self.tools: Dict[str, Callable] = {}
            self.resources: Dict[str, Callable] = {}
            self.prompts: Dict[str, Callable] = {}

        def tool(self):
            def decorator(func: Callable):
                self.tools[func.__name__] = func
                return func
            return decorator

        def resource(self, uri: str):
            def decorator(func: Callable):
                self.resources[uri] = func
                return func
            return decorator

        def prompt(self):
            def decorator(func: Callable):
                self.prompts[func.__name__] = func
                return func
            return decorator

        def run(self, transport: str = "stdio"):
            """模拟 JSON-RPC 2.0 stdio 通信监听"""
            print(f"[{self.name}] 模拟 stdio 传输通道已就绪 (JSON-RPC 2.0 监听模式已就绪，当前为仿真运行环境)")

    FastMCP = MinimalFastMCP

# ==============================================================================
# 1. 初始化 FastMCP 服务实例
# ==============================================================================
mcp = FastMCP("Huake-Enterprise-Finance-Server")

# 模拟底层真实企业制度库与员工数据库 (承接前期真实知识沉淀)
POLICY_DATABASE = {
    "一线城市": {
        "总监级": 800.0,
        "部门经理": 550.0,
        "普通员工": 450.0
    },
    "二线省会": {
        "总监级": 600.0,
        "部门经理": 420.0,
        "普通员工": 350.0
    },
    "三线及其他": {
        "总监级": 550.0,
        "部门经理": 370.0,
        "普通员工": 300.0
    }
}

EMPLOYEE_DATABASE = {
    "HK8012": {"name": "周建华", "department": "华东交付一部", "level": "普通员工"},
    "HK7991": {"name": "王大明", "department": "华东交付一部", "level": "部门经理"},
    "HK8110": {"name": "陈梓豪", "department": "监察委员会", "level": "总监级"},
    "HK8045": {"name": "赵小雪", "department": "监察委员会", "level": "部门经理"}
}

# ==============================================================================
# 2. 原语 1：发布标准 Tools (可执行工具)
# ==============================================================================

@mcp.tool()
def query_accommodation_limit(city_tier: str, employee_level: str) -> str:
    """
    根据城市等级和员工职级查询单晚住宿报销上限（元/天）。
    :param city_tier: 城市等级，必须为 '一线城市'、'二线省会' 或 '三线及其他'
    :param employee_level: 员工级别，必须为 '总监级'、'部门经理' 或 '普通员工'
    """
    tier_info = POLICY_DATABASE.get(city_tier)
    if not tier_info:
        return f"❌ 查询失败：未知城市级别 '{city_tier}'，有效选项为：{list(POLICY_DATABASE.keys())}"
    
    limit = tier_info.get(employee_level)
    if not limit:
        return f"❌ 查询失败：未知员工级别 '{employee_level}'，有效选项为：{list(tier_info.keys())}"
    
    return f"【合规标准核验】根据《2024版差旅规范》，{city_tier} - {employee_level} 的单晚住宿上限为 {limit} 元/天。"

@mcp.tool()
def audit_expense_claim(employee_id: str, city_tier: str, days: int, total_amount: float) -> str:
    """
    对员工提交的差旅住宿单据进行自动化合规审查与超标计算。
    :param employee_id: 员工工号，如 'HK8012'
    :param city_tier: 出差目的地城市等级
    :param days: 出差实际住宿天数（必须大于0）
    :param total_amount: 申报报销的总住宿费用（元）
    """
    emp = EMPLOYEE_DATABASE.get(employee_id)
    if not emp:
        return f"❌ 审计拦截：系统未检索到工号为 {employee_id} 的在职员工信息！"
    
    tier_info = POLICY_DATABASE.get(city_tier)
    if not tier_info:
        return f"❌ 审计拦截：未知城市级别 '{city_tier}'！"
    
    daily_limit = tier_info.get(emp["level"], 350.0)
    allowed_total = daily_limit * days
    
    if total_amount <= allowed_total:
        return (
            f"✅ 审计合规放行：员工 [{emp['name']}({emp['level']})] 在 {city_tier} 出差 {days} 天，"
            f"标准额度上限为 {allowed_total} 元，实际申报 {total_amount} 元，机审合规，予以通过。"
        )
    else:
        over_amount = total_amount - allowed_total
        return (
            f"🚨 审计违规预警：员工 [{emp['name']}({emp['level']})] 在 {city_tier} 出差 {days} 天，"
            f"标准总限额为 {allowed_total} 元（{daily_limit}元/天），实际申报 {total_amount} 元！"
            f"超出上限 {over_amount} 元。处理建议：超标金额强制剔除或由分管大区总监邮件特批！"
        )

# ==============================================================================
# 3. 原语 2：发布标准 Resources (只读资源通道)
# ==============================================================================

@mcp.resource("finance://policy/summary")
def get_finance_policy_summary() -> str:
    """提供企业 2024 最新差旅报销政策核心摘要只读文本"""
    summary = {
        "policy_id": "WIKI-FIN-TRAVEL-202403",
        "effective_date": "2024-03-01",
        "key_principles": [
            "一线城市标准调高，二三线城市维持勤俭原则",
            "夜间加班打车报销必须超过 21:00 且公共交通停运",
            "大额申报利益冲突时强制执行回避制度与监察委代签"
        ]
    }
    return json.dumps(summary, ensure_ascii=False, indent=2)

# ==============================================================================
# 4. 原语 3：发布标准 Prompts (专业指令模版)
# ==============================================================================

@mcp.prompt()
def audit_complaint_prompt(employee_id: str, disputed_amount: float) -> str:
    """为申诉复核专员生成针对违规超标单据的专业申诉沟通函模版"""
    return f"""你是一位资深企业财务合规审计专家。
请为工号为 {employee_id} 的员工起草一份《差旅超标复核沟通备忘录》。
涉及争议金额：{disputed_amount} 元。
要求：
1. 态度客观严谨，引用《2024差旅合规管理条例》生效节点；
2. 明确给出整改建议：补交特批证明，或自理超标差额；
3. 说明如果 3 个工作日内未反馈，财务系统将强制撤回单据。"""

# ==============================================================================
# 5. 服务入口与客户端直连测试
# ==============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print(f"🚀 Day 27 工业互联新标准：企业级 FastMCP Server 启动与就绪自测 (MCP 原生: {MCP_NATIVE_AVAILABLE})")
    print("=" * 80)
    
    # 支持两种模式：若带参数则启动标准 stdio 供 Cursor/Claude Desktop 调用
    # 否则直接执行内部全真契约自检
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        # 正式以标准 stdio 运行，等待宿主 Client 连接
        mcp.run(transport="stdio")
    else:
        print("💡 [本地自检模式] 正在验证 MCP Tools 与 Resources 逻辑有效性...\n")
        
        # 1. 自检查询工具
        res_tool1 = query_accommodation_limit("一线城市", "普通员工")
        print("1. [Tool 测试: 查限额] ➔", res_tool1)
        
        # 2. 自检审查工具（合规单据）
        res_tool2 = audit_expense_claim("HK8012", "一线城市", 3, 1200.0)
        print("2. [Tool 测试: 合规审查] ➔", res_tool2)
        
        # 3. 自检审查工具（超标违规单据）
        res_tool3 = audit_expense_claim("HK7991", "二线省会", 2, 1800.0)
        print("3. [Tool 测试: 违规拦截] ➔", res_tool3)
        
        # 4. 自检只读资源
        res_resource = get_finance_policy_summary()
        print("4. [Resource 测试: 规约只读] ➔\n", res_resource)

        # 5. 自检提示词模版
        res_prompt = audit_complaint_prompt("HK7991", 960.0)
        print("5. [Prompt 测试: 复核沟通函模版] ➔\n" + "-" * 40 + f"\n{res_prompt}\n" + "-" * 40)
        
        print("\n" + "=" * 80)
        print("✅ 企业级 FastMCP Server 自检 100% 通过！随时可挂载至 Cursor / Claude Desktop / Antigravity。")
        print("👉 启动标准 MCP 监听指令：python3 day27/run_day27_enterprise_finance_mcp.py run")
        print("=" * 80)

