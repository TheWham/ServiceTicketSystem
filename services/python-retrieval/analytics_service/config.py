# -*- coding: utf-8 -*-
"""analytics_service 运行配置（环境变量驱动，风格与 agent_service/config.py 一致）。

与 agent_service 的分工：agent_service 是模型驱动的 ReAct 工具循环；本服务是
**确定性节点链** —— 模型只在两处充当语义单元：Node A 的「意图判定 + 槽位抽取」
与 Node D 的「归因叙事」。**所有数字与日期都由 Python 算出**：模型给的是语义槽位
（"本季度"），日期区间由 timewindow 解，聚合出的每个数字由 aggregate 算。
配置里因此多了一组统计闸门常量，它们直接决定"什么时候不给结论"。
"""

import os
from pathlib import Path
from typing import Dict

# RAG_HOME 缺省回退包上级目录（services/python-retrieval）；须在业务模块导入前设置。
REPO_ROOT = Path(os.environ.get("RAG_HOME", "") or Path(__file__).resolve().parents[1])


def _load_dotenv() -> Dict[str, str]:
    """解析 REPO_ROOT/.env（与 rag_pipeline / agent_service 同一约定）：进程环境变量优先。"""
    env_file = REPO_ROOT / ".env"
    if not env_file.exists():
        return {}
    kv: Dict[str, str] = {}
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        kv[k.strip()] = v.strip().strip('"').strip("'")
    return kv


_DOTENV = _load_dotenv()


def _cfg(name: str, dotenv_key: str = "", default: str = "") -> str:
    """取值顺序：环境变量 > .env > 默认。"""
    return os.environ.get(name) or (_DOTENV.get(dotenv_key, "") if dotenv_key else "") or default


HOST = os.environ.get("ANALYTICS_SERVICE_HOST", "127.0.0.1")
PORT = int(os.environ.get("ANALYTICS_SERVICE_PORT", "8340"))

# ---- 归因叙事模型（OpenAI 兼容）----
LLM_BASE_URL = _cfg("ANALYTICS_LLM_BASE_URL", "LLM_BASE_URL")
LLM_API_KEY = _cfg("ANALYTICS_LLM_API_KEY", "LLM_API_KEY")
LLM_MODEL = _cfg("ANALYTICS_LLM_MODEL", "LLM_CLEAN_MODEL", "deepseek-v4-flash")
LLM_TIMEOUT = float(os.environ.get("ANALYTICS_LLM_TIMEOUT", "180"))
# 归因叙事的输出预算。**16384 是实测值，不是拍脑袋**。
#
# ⚠️ 本仓库 .env 配的 `deepseek-v4-flash` 在这一端点**实际是推理模型**，且推理开销极大。
# 直接探测（prompt 1587 字）：completion=9344、其中 **reasoning=9004**、正文只有 564 字，
# 即推理:正文 ≈ 16:1，单次 55 秒。精简事实包后仍要 6338（子域）/ 9971（全库）个 token。
# 推理量由**事实要协调的条目数**驱动，不是提示词长度 —— 把 facts 从 3 维×8 项砍到
# 3 维×4 项，只把推理从 9004 降到 6037。
#
# 实测 8192 会在全库题上稳定截断：tokens_out 正好等于上限、finish_reason=length、
# content 一个字都没有，链路只能退回确定性模板。模型名里的 "flash" 在这里不构成任何保证。
#
# 想让这个值降下来，正解是**换一个非推理的对话模型**（`ANALYTICS_LLM_MODEL`），
# 而不是继续加大预算。
SYNTH_MAX_OUTPUT_TOKENS = int(os.environ.get("ANALYTICS_SYNTH_MAX_OUTPUT_TOKENS", "16384"))
# 路由调用的输出预算：一次同时出「意图二分类 + 时间/范围/维度槽位」。
#
# 取代了原来的 `max_tokens=16` —— 那个值是按"只输出一个标签"估的，而本端点的模型
# 是推理模型，思维链会先把额度吃掉，16 个 token 很可能连正文都留不下（表现是
# content 为空 → 收敛失败 → 静默退回规则）。截断在这里是**安全**的降级（退回正则），
# 但会让"模型主抽"名存实亡，所以预算必须给足。2048 是起点值，按端点实测校准。
ROUTER_MAX_OUTPUT_TOKENS = int(os.environ.get("ANALYTICS_ROUTER_MAX_OUTPUT_TOKENS", "2048"))
# 路由调用的独立超时。**必须显著小于 LLM_TIMEOUT** —— 它跑在 Node A，取数与聚合
# 都还没开始；一次慢推理卡在这里，整个请求会在做任何实事之前先烧掉这份预算。
# 超时的后果是退回正则解析，不影响正确性。
ROUTER_TIMEOUT = float(os.environ.get("ANALYTICS_ROUTER_TIMEOUT", "60"))
# 模型路由与槽位抽取的总开关。置 0 则 Node A 整趟不调模型，意图与槽位全部由
# 规则/正则决定 —— 保留纯确定性演示与"规则 vs 模型"对照的口子（回归基线也走它）。
MODEL_ROUTING_ENABLED = (os.environ.get("ANALYTICS_MODEL_ROUTING", "1").strip() or "1") != "0"
# kimi-k3 不接受 temperature；deepseek 接受。默认不传，走模型默认值。
TEMPERATURE = os.environ.get("ANALYTICS_TEMPERATURE", "")

# ---- 取数（ticket-service 内部接口）----
# 架构 8.1：工单是 ticket-service 事实源，其他服务不得跨库读 ticket 表。
TICKET_SERVICE_BASE_URL = _cfg("ANALYTICS_TICKET_BASE_URL", "TICKET_SERVICE_BASE_URL",
                               "http://127.0.0.1:8201")
SCAN_TIMEOUT = float(os.environ.get("ANALYTICS_SCAN_TIMEOUT", "15"))
# 单次投影扫描的取数上限。分析要在内存里跑词表匹配，几百到几千行都只需几毫秒；
# 但这个上限必须有 —— 没有上限的"全量拉取"迟早会撞上内存与超时。
SCAN_MAX_ROWS = int(os.environ.get("ANALYTICS_SCAN_MAX_ROWS", "5000"))

# ---- 词表与策略 ----
TAXONOMY_PATH = Path(os.environ.get("ANALYTICS_TAXONOMY_PATH", "")
                     or REPO_ROOT / "configs" / "taxonomy.yaml")
# 策略配置（备件系数等）。与词表同一条纪律：版本参与指纹 —— 系数一改，
# 历史的备件建议就不可复现了。
POLICY_PATH = Path(os.environ.get("ANALYTICS_POLICY_PATH", "")
                   or REPO_ROOT / "configs" / "analytics.yaml")

# ---- 统计闸门（决定"什么时候不给结论"）----
# 全库拒答线：时间窗内工单总数低于此值，整体不做宏观归纳。
MIN_UNIVERSE = int(os.environ.get("ANALYTICS_MIN_UNIVERSE", "20"))
# 条目级降级线：分母或命中数低于此值，该条只给计数、不给占比。
# 注意这里**不设子域专用常量** —— 子域样本少是用户自己限定范围造成的，直接拒答
# 等于把问题推回去；复用同一个分母阈值即可，也免去 `5 < 5` 这类边界碰撞。
MIN_DENOM = int(os.environ.get("ANALYTICS_MIN_DENOM", "10"))
MIN_LABEL_HITS = int(os.environ.get("ANALYTICS_MIN_LABEL_HITS", "5"))
# 标签覆盖率低于此值：照常作答但强制声明，并压低置信度。
MIN_COVERAGE_WARN = float(os.environ.get("ANALYTICS_MIN_COVERAGE_WARN", "0.30"))

# ---- 权限 ----
# 跨人聚合是本服务唯一新增权限面。Python 侧这道仅用于早退省钱，不作为安全依据
# —— 权威判定在 Java 侧 AuthzService 与控制器内校验。
# 只放 ENGINEER：这个能力是给一线工程师做归纳用的管理动作面之外的读场景，
# 平台管理员不在此列（放开须两处 Java 守卫 + 前端路由一并改）。
ALLOWED_ROLES = frozenset(
    r.strip().upper() for r in
    os.environ.get("ANALYTICS_ALLOWED_ROLES", "ENGINEER").split(",")
    if r.strip()
)


def model_configured() -> bool:
    """归因叙事模型是否已配置。未配置时链路照走，退回确定性模板并标注 estimated。"""
    return bool(LLM_BASE_URL and LLM_API_KEY)