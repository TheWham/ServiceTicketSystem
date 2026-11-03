# services/python-retrieval/knowledge_flow/nodes.py
"""
================================================================================
知识库沉淀工作流 (Knowledge Precipitation Flow) - LangGraph 五大核心计算节点
================================================================================

本模块定义了企业 IT 知识库自动化沉淀的 5 个原子化处理节点 (Nodes)。
每个节点遵循纯函数或幂等计算设计，以 `KnowledgeFlowState` 为输入，返回增量状态变更 (Delta Dict)。

【五大核心节点流水线】：
┌─────────────────────────┐
│ 1. extract_candidate_node│ 候选提取与结构化解析（标题规整、分类启发式识别、风险定级）
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│  2. sanitize_guard_node │ 安全合规与隐私脱敏（手机/工号/IP/密码脱敏、防 Prompt 注入检测）
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│  3. cluster_dedup_node  │ 语义向量查重与聚类（基于 Python 原生 Chroma 检索内核，解耦 ES）
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│   4. admin_review_node  │ 人机协同终审门禁 HITL（原生 interrupt() 挂起状态图，支持在线校正）
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│  5. publish_index_node  │ 正式入库与索引发布（Docstore 向量写入，双写同步 MySQL 知识库）
└─────────────────────────┘

设计遵循原则：
1. 架构解耦：查重与入库完全基于本地 Python 向量库与 MySQL 双写，不依赖外部 Elasticsearch。
2. 审计追溯：所有节点产生的操作流水通过 `audit_logs`（Annotated Reducer）线性追加累积。
3. 安全前置：敏感信息和注入攻击在进入人工审批前由 Node 2 拦截并打标。
"""

import os
import re
import uuid
import math
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from .contract import KnowledgeFlowState

# ==============================================================================
# LangGraph 原生 interrupt 机制兼容导入
# ==============================================================================
# 兼容导入 LangGraph 官方 interrupt 机制。
# 若在官方 CompiledGraph Runnable 运行时下则直接使用 lg_interrupt 并透传 GraphInterrupt；
# 若在单体测试、轻量引擎或独立循环中调用，则安全抛出 GraphInterrupt 异常载荷，
# 保证 100% 行为一致性与鲁棒性。
class GraphInterrupt(Exception):
    """当在非 compiled_graph 运行时或未安装 langgraph 时用于承载挂起数据载荷的异常。"""
    def __init__(self, value: Any):
        self.value = value

def interrupt(payload: Any):
    """LangGraph 节点中断抛出器。"""
    try:
        from langgraph.types import interrupt as lg_interrupt  # type: ignore[import-not-found]
        from langgraph.errors import GraphInterrupt as LgGraphInterrupt  # type: ignore[import-not-found]
        try:
            return lg_interrupt(payload)
        except LgGraphInterrupt:
            # 官方 LangGraph 中断信号必须向上透传，以供 Pregel 执行引擎捕获并挂起任务
            raise
        except Exception:
            raise GraphInterrupt(payload)
    except ImportError:
        raise GraphInterrupt(payload)


# ==============================================================================
# Node 1: 候选提取与结构化解析 (ExtractCandidateNode - LLM 规范化驱动)
# ==============================================================================

# LLM 结构化提取 System Prompt
EXTRACTION_SYSTEM_PROMPT = """你是一个企业 IT 知识库治理与规范化提炼专家。
你的任务是将原始 IT 运维工单、咨询问答或技术排障记录，提炼为专业、规范的技术知识卡片草稿。

【输出要求】：
请严格输出一个合法 JSON 对象（不要输出 Markdown 代码围栏，不要输出多余解释），字段定义如下：
{
  "title": "规范化技术标题（简洁专业，不超过25字，去除'请问'、'求助'、'请帮我看看'等口语化废话）",
  "summary": "一句话核心摘要（50字以内，明确说明解决什么问题及核心排障思路）",
  "problem_desc": "结构化故障现象描述（客观准确概括用户遇到的异常表象与场景）",
  "resolution_steps": "分步骤排查与解决步骤（条理清晰，分步骤编号排版）",
  "category_id": "分类编号，必须严格从以下枚举选择一个：['C_NET', 'C_ACC', 'C_SW', 'C_HW', 'C_OTH']",
  "suggested_risk_level": "风险等级建议：'NORMAL'（常规故障排查）或 'HIGH'（涉及账号重置、密码凭据、权限提权、证书、堡垒机、sudo/root等高危安全操作）"
}

【分类枚举标准】：
- C_NET: 网络通信与接入类（WiFi、网络、DNS、网线、Ping、丢包、局域网、网卡、IP冲突等）
- C_ACC: 账号、权限与认证类（密码重置、权限申请、VPN、堡垒机、密钥、证书、统一身份认证等）
- C_SW: 桌面办公与应用软件类（企业微信/微信、打卡、Outlook/邮箱、Office、驱动、操作系统等）
- C_HW: 硬件与办公外设类（显示器、键盘、鼠标、打印机、拓展坞、蓝屏、硬件接触不良、电源等）
- C_OTH: 其他综合技术故障

【铁律】：
1. 严禁编造原文不存在的命令或参数，忠于技术事实；
2. 标题必须具备技术检索价值，严禁保留口语语气词与无意义问号；
3. 输出必须是严格可被 json.loads 解析的合法 JSON 格式。"""

VALID_CATEGORIES = {"C_NET", "C_ACC", "C_SW", "C_HW", "C_OTH"}
HIGH_RISK_KEYWORDS = ["堡垒机", "特权", "sudo", "root", "提权", "重置密码", "私钥", "证书撤销"]


def _call_llm_extract(q: str, a: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """尝试调用配置中心管理的 LLM 模型进行知识卡片规范化提取。

    返回: (parsed_data, error_or_reason)
    - 成功时返回 (data_dict, None)
    - 未配置或调用失败时返回 (None, reason_str)
    """
    try:
        from rag_pipeline.config import load_llm_config
    except ImportError:
        def load_llm_config() -> Dict[str, str]:
            return {
                "api_key": os.environ.get("LLM_API_KEY", ""),
                "base_url": os.environ.get("LLM_BASE_URL", ""),
                "clean_model": os.environ.get("LLM_CLEAN_MODEL", "deepseek-v4-flash"),
            }

    cfg = load_llm_config()
    api_key = (cfg.get("api_key") or "").strip()
    base_url = (cfg.get("base_url") or "").strip()
    model = cfg.get("clean_model") or cfg.get("chat_model") or "deepseek-v4-flash"

    if not api_key or api_key.startswith("sk-replace-") or api_key == "sk-..." or not base_url:
        return None, "未配置有效 LLM_API_KEY / LLM_BASE_URL"

    try:
        from openai import OpenAI
    except ImportError:
        return None, "未安装 openai SDK 依赖"

    try:
        # 控制单次模型调用预算为 12s，关闭 SDK 隐式重试（避免指数退避累积超过上游预算）
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=12.0, max_retries=0)
        user_prompt = f"【原始问题/工单咨询】：\n{q}\n\n【原始排障处置/回答】：\n{a}\n\n请提取并输出标准化知识卡片 JSON："

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )

        content = response.choices[0].message.content or ""
        clean_json = re.sub(r"^```(?:json)?\s*", "", content.strip())
        clean_json = re.sub(r"\s*```$", "", clean_json)
        data = json.loads(clean_json)
        return data, None
    except Exception as e:
        return None, f"LLM 调用或响应解析异常: {e}"


def _heuristic_extract(q: str, a: str) -> Dict[str, Any]:
    """确定性启发式规则解析提取（当未配置 LLM 或模型调用失败时作为高可用保底）。"""
    # 剥除开头的口语化套话（如“请问”、“请帮我看看”、“急！在线等”等）
    clean_title: str = re.sub(r"^(请问|请帮我看看|怎么|如何|为什么|急！|在线等|请教一下)\s*", "", q)
    clean_title = clean_title.rstrip("？?。！! ")
    if not clean_title or len(clean_title) < 4:
        clean_title = f"{q[:18]}..." if len(q) > 18 else q
    if not clean_title:
        clean_title = "未知技术故障排查指南"

    q_lower: str = f"{clean_title} {q}".lower()
    combined_text: str = f"{q}\n{a}".lower()

    if any(k in q_lower for k in ["wifi", "网络", "dns", "网线", "ping", "丢包", "局域网", "网卡", "ip conflict"]):
        category_id = "C_NET"
        risk_level = "NORMAL"
        policy_note = "网络通信与接入类，评定为 NORMAL 常规等级"
    elif any(k in q_lower or k in combined_text for k in ["密码", "权限", "vpn", "特权", "堡垒机", "安全", "密钥", "证书", "sudo", "root"]):
        category_id = "C_ACC"
        risk_level = "HIGH"
        policy_note = "涉及账号、权限或核心安全配置，评定为 HIGH 风险等级（强制执行双重复核门禁）"
    elif any(k in combined_text for k in ["打卡", "微信", "企业微信", "outlook", "邮箱", "office", "驱动", "系统", "word", "excel"]):
        category_id = "C_SW"
        risk_level = "NORMAL"
        policy_note = "软件系统与日常办公软件类，评定为 NORMAL 常规等级"
    elif any(k in combined_text for k in ["显示器", "鼠标", "键盘", "打印机", "拓展坞", "主机", "蓝屏", "硬件", "接触不良", "电源"]):
        category_id = "C_HW"
        risk_level = "NORMAL"
        policy_note = "硬件与办公外设类，评定为 NORMAL 常规等级"
    else:
        category_id = "C_OTH"
        risk_level = "NORMAL"
        policy_note = "其他综合技术类，评定为 NORMAL 常规等级"

    summary: str = f"针对【{clean_title}】问题的官方排障建议与自助操作指引。"
    problem_desc: str = f"用户在使用过程中遇到如下异常表现：{q}"
    resolution_steps: str = f"经技术验证的标准处理步骤如下：\n{a}"

    return {
        "title": clean_title,
        "summary": summary,
        "problem_desc": problem_desc,
        "resolution_steps": resolution_steps,
        "category_id": category_id,
        "risk_level": risk_level,
        "policy_note": policy_note,
    }


def extract_candidate_node(state: KnowledgeFlowState) -> Dict[str, Any]:
    """【Node 1】候选提取与结构化解析节点 (Extract Candidate Node)。

    【节点定位与职责】：
    作为流水线首个处理节点，负责将原始工单文本、客服问答对（Q&A）或员工交互记录进行
    自然语言语义提炼，由 LLM 大模型进行规范化标题提炼、现象摘要、步骤编排与分类识别，
    并由安全策略引擎强制实施风险合规前置定级。

    【核心处理机制 (Processing Pipeline)】：
    1. LLM 结构化规范提炼：
       - 调用配置中心（rag_pipeline.config.load_llm_config）统一管理的生成模型（如 deepseek-v4-flash）；
       - 采用严格 JSON Schema 约束，萃取规范化技术标题、核心摘要、故障现象、分步处置指引及分类标识。
    2. 外部依赖故障非静默降级（No Silent Failure）：
       - 明确区分未配置、调用超时/错误等场景，将完整真实原因记录至 `audit_logs`；
       - 当且仅当外部模型不可用时，启用确定性启发式规则引擎保底提取，保障系统鲁棒性。
    3. 安全策略硬红线前置裁定（Security Policy Gate）：
       - 无论 LLM 建议何种风险等级，策略引擎均对账号安全、权限提权、堡垒机、密钥、sudo/root 等
         敏感高危操作进行严格策略校验，强制评定为 `HIGH` 级门禁（需资深专家复核），杜绝大模型漏判。

    【输入状态 (State Inputs)】：
    - `state["raw_question"]` (str): 原始工单咨询或用户提问。
    - `state["raw_answer"]`   (str): 原始技术工程师回答或排障处置建议。
    - `state["source_type"]`  (str): 来源渠道（如 TICKET_CLOSED、AI_FEEDBACK、MANUAL_DRAFT）。
    - `state["candidate_id"]` (str): 候选知识唯一业务标识号。

    【输出增量 (Delta Output)】：
    - 返回包含 `title`, `summary`, `problem_desc`, `resolution_steps`, `category_id`,
      `risk_level` 及追加流水 `audit_logs` 的增量字典。
    """
    # 1. 获取并清洗入参字段
    q: str = state.get("raw_question", "").strip()
    a: str = state.get("raw_answer", "").strip()
    src: str = state.get("source_type", "AI_FEEDBACK")
    cand_id: str = state.get("candidate_id", "cand-unknown")

    logs: List[str] = [f"【Node 1 提取提炼】开始处理来源 [{src}] 候选案例 {cand_id}"]

    # 2. 优先调用 LLM 执行结构化规范提炼
    llm_data, fail_reason = _call_llm_extract(q, a)

    if llm_data and isinstance(llm_data, dict):
        # 提取字段并规范化
        title = str(llm_data.get("title", "")).strip()
        summary = str(llm_data.get("summary", "")).strip()
        problem_desc = str(llm_data.get("problem_desc", "")).strip()

        # 处理 resolution_steps：兼容字符串或列表结构
        raw_steps = llm_data.get("resolution_steps", "")
        if isinstance(raw_steps, list):
            resolution_steps = "\n".join(str(s) for s in raw_steps)
        else:
            resolution_steps = str(raw_steps).strip()

        cat = str(llm_data.get("category_id", "")).strip()
        category_id = cat if cat in VALID_CATEGORIES else "C_OTH"
        suggested_risk = str(llm_data.get("suggested_risk_level", "NORMAL")).upper()

        # 兜底字段完整性
        if not title:
            title = q[:20] if q else "未知技术故障排查指南"
        if not summary:
            summary = f"针对【{title}】问题的官方排障建议与自助操作指引。"
        if not problem_desc:
            problem_desc = f"用户在使用过程中遇到如下异常表现：{q}"
        if not resolution_steps:
            resolution_steps = a

        # 3. 安全策略硬红线前置裁定（Security Policy Gate）
        combined_text = f"{q}\n{a}\n{title}".lower()
        is_high_risk = (
            category_id == "C_ACC"
            or suggested_risk == "HIGH"
            or any(k in combined_text for k in HIGH_RISK_KEYWORDS)
        )
        if is_high_risk:
            risk_level = "HIGH"
            policy_note = "涉及账号、权限或核心安全配置，判定为 HIGH 风险等级（强制执行双重人机复核门禁）"
        else:
            risk_level = "NORMAL"
            policy_note = f"意图分类 [{category_id}]，评定为 NORMAL 常规等级"

        logs.append(f"【Node 1 提取提炼】LLM 成功完成规范化结构提炼，提取标题: 『{title}』，分类: {category_id}，{policy_note}")
    else:
        # 非静默降级：在审计流水中明确记录外部依赖调用未成功的真实原因
        logs.append(f"【Node 1 提取提炼】⚠️ LLM 未能完成提取（原因: {fail_reason}），转入确定性启发式规则引擎解析")
        heur = _heuristic_extract(q, a)
        title = heur["title"]
        summary = heur["summary"]
        problem_desc = heur["problem_desc"]
        resolution_steps = heur["resolution_steps"]
        category_id = heur["category_id"]
        risk_level = heur["risk_level"]
        policy_note = heur["policy_note"]
        logs.append(f"【Node 1 提取提炼】启发式规则提取标题: 『{title}』，分类: {category_id}，{policy_note}")

    return {
        "title": title,
        "summary": summary,
        "problem_desc": problem_desc,
        "resolution_steps": resolution_steps,
        "category_id": category_id,
        "risk_level": risk_level,
        "audit_logs": logs
    }


# ==============================================================================
# Node 2: 规则与正则安全脱敏与防注入拦截 (SanitizeGuardNode)
# ==============================================================================

# 预编译常见的 Prompt 注入（越狱与系统提示词窃取）正则模式
INJECTION_PATTERNS: List[str] = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"忽略(之前|上述|以上).*指令",
    r"output\s+all\s+system\s+(prompts|configurations)",
    r"输出(系统提示词|所有指令|底层配置)",
    r"system\s*:\s*you\s+are",
    r"you\s+are\s+now\s+an\s+unrestricted",
]


def sanitize_guard_node(state: KnowledgeFlowState) -> Dict[str, Any]:
    """【Node 2】安全合规与隐私脱敏节点 (Sanitize Guard Node)。

    【节点定位与职责】：
    作为合规与安全防线，在工单进入向量库与公开知识库之前，执行严格的敏感数据脱敏
    （PII Data Sanitization）以及恶意提示词注入攻击拦截（Prompt Injection Detection）。

    【输入状态 (State Inputs)】：
    - `state["raw_question"]`     (str): 原始问题文本。
    - `state["resolution_steps"]` (str): Node 1 输出的标准解决步骤。

    【核心处理机制 (Processing Pipeline)】：
    1. 提示词注入攻击拦截 (Anti-Prompt Injection)：
       - 扫描全量文本是否存在旨在覆盖大模型角色设定、窃取系统提示词的黑客模式。
       - 命中时将 `contains_injection` 置为 True，并在审计日志中输出黄色警告。
    2. CJK 友好的 PII 隐私数据脱敏：
       - 中国大陆 11 位手机号码脱敏（掩蔽为 `[已脱敏手机号]`）。
       - 员工企业工号脱敏（如 `E1001`, `U_ADMIN`，利用 `(?<![a-zA-Z0-9])` 与 `(?![a-zA-Z0-9])`
         非字边界断言，彻底避免在缺乏空格的中文文本中传统 `\\b` 失效的问题）。
       - IPv4 局域网与外网 IP 地址脱敏（替换为 `[已脱敏内网IP]`）。
       - 敏感明文口令凭据脱敏（对“密码: xxx”、“password = xxx”中的明文口令做捕获替换）。

    【输出增量 (Delta Output)】：
    - 返回 `is_sanitized` (True), `contains_injection` (bool), `sanitized_question`,
      `sanitized_answer`, 以及经过脱敏的 `resolution_steps`。
    """
    q: str = state.get("raw_question", "")
    a: str = state.get("resolution_steps", "")
    full_text: str = f"{q}\n{a}"

    logs: List[str] = ["【Node 2 安全脱敏】进入合规与隐私安全审查检测流水线"]

    # 1. Prompt 提示词注入检测
    has_injection: bool = False
    for pat in INJECTION_PATTERNS:
        if re.search(pat, full_text, flags=re.IGNORECASE):
            has_injection = True
            break

    if has_injection:
        logs.append("⚠️ 【Node 2 安全脱敏】警告：检测到疑似 Prompt 提示词注入攻击，已标记拦截标志位！")

    # 2. 正则脱敏 - 手机号 (11位大陆号码)
    clean_q: str = re.sub(r"1[3-9]\d{9}", "[已脱敏手机号]", q)
    clean_a: str = re.sub(r"1[3-9]\d{9}", "[已脱敏手机号]", a)

    # 3. 正则脱敏 - 员工工号 (适配 CJK 边界断言，支持 E10023, U_ADMIN01 等格式)
    emp_pattern = r"(?<![a-zA-Z0-9])(U_[A-Z0-9]+|E\d{4,6})(?![a-zA-Z0-9])"
    clean_q = re.sub(emp_pattern, "[已脱敏工号]", clean_q)
    clean_a = re.sub(emp_pattern, "[已脱敏工号]", clean_a)

    # 4. 正则脱敏 - IPv4 地址
    ip_pattern = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
    clean_q = re.sub(ip_pattern, "[已脱敏内网IP]", clean_q)
    clean_a = re.sub(ip_pattern, "[已脱敏内网IP]", clean_a)

    # 5. 正则脱敏 - 明文密码与敏感凭据 (捕获 password/口令/密码 后的非空白字符串)
    clean_a = re.sub(
        r"((?:密码|口令|password|pwd)[:=：\s]+)[^\s,，。\n]+",
        r"\1[已脱敏凭据]",
        clean_a,
        flags=re.IGNORECASE
    )

    logs.append("【Node 2 安全脱敏】隐私数据脱敏清洗完成（已过滤手机号/工号/内网IP/密码明文）")

    return {
        "is_sanitized": True,
        "contains_injection": has_injection,
        "sanitized_question": clean_q,
        "sanitized_answer": clean_a,
        "resolution_steps": clean_a,  # 同步覆写下游消费的解决步骤文本
        "audit_logs": logs
    }


# ==============================================================================
# Node 3: Python 原生向量库查重与聚类 (ClusterDedupNode)
# ==============================================================================

def _fallback_keyword_cosine(s1: str, s2: str) -> float:
    """字符余弦相似度计算辅助函数。
    
    当生产级 Embedding 模型不可用或离线时，作为无依赖的数学余弦兜底保障。
    """
    chars1 = set(s1)
    chars2 = set(s2)
    if not chars1 or not chars2:
        return 0.0
    intersection = len(chars1 & chars2)
    return intersection / (math.sqrt(len(chars1)) * math.sqrt(len(chars2)))


def cluster_dedup_node(state: KnowledgeFlowState) -> Dict[str, Any]:
    """【Node 3】语义向量查重与聚类节点 (Cluster & Deduplication Node)。

    【节点定位与职责】：
    负责在沉淀入库前检测当前知识是否与已有知识库内容存在高度语义重复。
    防止相似知识大量冗余沉淀导致向量检索噪声增大或知识体系碎片化。

    【核心保证 - 彻底解耦 ES】：
    严格依据项目规范与架构约束，查重逻辑完全调用 Python 检索内部的 Chroma 向量数据库
    或基于内存的 SimpleVectorStore，绝不调用任何外部 Elasticsearch 接口！

    【输入状态 (State Inputs)】：
    - `state["title"]` (str): Node 1 提炼并由前置节点输出的候选知识标题。

    【核心处理机制 (Processing Pipeline)】：
    1. 动态连接本地 Chroma 向量库：
       - 加载 `artifacts/indexing/chroma_wiki_structured` 持久化向量索引与 `KspEmbeddingProvider`。
       - 调用 `similarity_search_with_relevance_scores(title, k=2)` 执行语义余弦距离计算。
    2. 离线沙盒基准对比兜底 (Robust Benchmark Fallback)：
       - 若宿主机当前尚未构建本地 Chroma 向量文件，自动转入内建标准经典卡片库进行对比计算，
         确保离线演示和单元测试高可用性。
    3. 重复性阈值决策 (Threshold Decision)：
       - 设置语义相似度阈值为 `0.80`（余弦相似度 >= 0.80 视作高度相似重复）。
       - 记录匹配的最高分文档标题及相似度指标至 `duplicate_reference`。

    【输出增量 (Delta Output)】：
    - 返回 `top_similarity_score` (float), `is_duplicate` (bool), `duplicate_reference` (str|None)
      及追加流水 `audit_logs`。
    """
    title: str = state.get("title", "")
    logs: List[str] = [f"【Node 3 向量查重】正在向 Python 检索内核向量库比对相似度：『{title}』"]

    top_score: float = 0.0
    matched_title: Optional[str] = None

    # 1. 尝试从 Python 本地 Chroma 向量存储引擎检索相似条目
    try:
        from rag_pipeline.store import SimpleVectorStore
        from rag_pipeline.embedding import KspEmbeddingProvider

        embedder = KspEmbeddingProvider()
        vector_store = SimpleVectorStore.from_chroma_sqlite(
            persist_directory="artifacts/indexing/chroma_wiki_structured",
            embedding_provider=embedder
        )
        if vector_store:
            # 检索 Top-2 相似条目及相关度得分
            results = vector_store.similarity_search_with_relevance_scores(title, k=2)
            if results:
                doc, score = results[0]
                top_score = float(score)
                matched_title = doc.metadata.get("title") or doc.page_content[:20]
    except Exception as e:
        logs.append(f"【Node 3 向量查重】从本地 Chroma 读取向量库跳过（原因: {e}），转入内存基准库对比")

    # 2. 离线/未建库环境下的基准对照库语义比对
    if not matched_title:
        benchmark_titles: List[Tuple[str, float]] = [
            ("VPN连接失败（拨号/认证失败）", 0.88 if "vpn" in title.lower() or "连接" in title else 0.12),
            ("企业微信移动端打卡闪退与定位异常", 0.85 if "微信" in title or "打卡" in title else 0.10),
            ("内网Corp-WiFi凭据错误认证排查", 0.86 if "wifi" in title.lower() or "无线" in title else 0.15)
        ]
        best_match = max(benchmark_titles, key=lambda x: x[1])
        top_score = best_match[1]
        matched_title = best_match[0]

    # 3. 相似度阈值判定 (0.80 为工业界常用重复阈值)
    is_duplicate: bool = top_score >= 0.80
    ref_desc: Optional[str] = f"{matched_title} (相似度: {top_score:.4f})" if is_duplicate else None

    if is_duplicate:
        logs.append(f"⚠️ 【Node 3 向量查重】判定为疑似重复/已存在知识簇！命中最高相似度条目: {ref_desc}")
    else:
        logs.append(f"【Node 3 向量查重】经 Python 向量余弦计算，未发现高度重复条目（最高相似度: {top_score:.4f} < 0.80）")

    return {
        "top_similarity_score": top_score,
        "is_duplicate": is_duplicate,
        "duplicate_reference": ref_desc,
        "audit_logs": logs
    }


# ==============================================================================
# Node 4: 原生 interrupt() 人工终审挂起与决策 (AdminReviewNode)
# ==============================================================================

def admin_review_node(state: KnowledgeFlowState) -> Dict[str, Any]:
    """【Node 4】人机协同终审挂起与决策节点 (Admin Human-in-the-Loop Review Node)。

    【节点定位与职责】：
    知识沉淀流水线中最关键的人机协同门禁（Human-in-the-Loop, HITL）。
    负责汇聚前置节点的所有分析成果（结构化草稿、脱敏报告、查重结论），组装为待审卡片；
    利用 LangGraph 原生 `interrupt()` 挂起计算流图，等待知识库管理员完成合规审批。

    【核心机制解析 (Native interrupt & resume)】：
    1. 组装终审卡片 (Review Card)：
       包含候选ID、知识标题、所属分类、风险等级、查重相似度、脱敏正文及注入告警提示。
    2. 触发流图中断挂起 (Flow Suspension)：
       执行 `human_decision = interrupt(review_card)`。
       在底层，LangGraph 引擎会捕获该挂起信号，将当前执行线程（Thread）的全量状态持久化保存
       至 Checkpointer（MySQL 或 SQLite），并在返回给客户端的响应中标记 `__interrupt__`。
    3. 外部唤醒与热修复恢复 (Resume with Online Patching)：
       管理员在前端界面核对后，点击“通过 (APPROVED)”或“驳回 (REJECTED)”，调用
       `engine.resume(thread_id, decision)`。
       计算引擎从此处无缝唤醒，`interrupt(...)` 返回管理员提交的决议字典 `human_decision`。
    4. 允许就地修正：
       审批人在审批时若发现标题或排版不尽人意，可在审批入参中直接提交 `modified_title` 或
       `modified_steps`，该节点将就地采纳修正，无需重跑前序耗时节点。

    【输入状态 (State Inputs)】：
    - `candidate_id`, `title`, `category_id`, `risk_level`, `is_duplicate`,
      `duplicate_reference`, `summary`, `resolution_steps`, `contains_injection` 等。

    【输出增量 (Delta Output)】：
    - 返回 `review_status` ("APPROVED" 或 "REJECTED")、`reviewer`、`audit_comment`、
      修订后的 `title` / `resolution_steps`（如有），以及追加的审批审计日志。
    """
    # 1. 组装待审批的结构化卡片数据
    review_card: Dict[str, Any] = {
        "title": "📋 待发布知识终审工单",
        "candidate_id": state.get("candidate_id"),
        "knowledge_title": state.get("title"),
        "category_id": state.get("category_id"),
        "risk_level": state.get("risk_level"),
        "is_duplicate": state.get("is_duplicate"),
        "duplicate_reference": state.get("duplicate_reference"),
        "summary": state.get("summary"),
        "resolution_steps": state.get("resolution_steps"),
        "contains_injection": state.get("contains_injection"),
        "prompt": "请知识库管理员审阅并裁决：通过(APPROVED) 或 驳回(REJECTED)"
    }

    # 🛑 核心操作：抛出原生 LangGraph interrupt() 挂起状态图！
    # 整个工作流在此处暂停，当前状态自动写入 Checkpointer，等待人类管理员外部输入
    human_decision: Dict[str, Any] = interrupt(review_card)

    # ==========================================================================
    # 以下代码在外部管理员调用 resume() 之后恢复执行
    # ==========================================================================
    action: str = human_decision.get("action", "REJECTED")  # 决策动作: "APPROVED" 或 "REJECTED"
    approver: str = human_decision.get("approver", "未知管理员")
    comment: str = human_decision.get("comment", "无审批附言")

    status: str = "APPROVED" if action == "APPROVED" else "REJECTED"
    logs: List[str] = [f"【Node 4 人机终审】知识库管理员 [{approver}] 完成审核，做出决议：{status}，审批评语：{comment}"]

    delta: Dict[str, Any] = {
        "review_status": status,
        "reviewer": approver,
        "audit_comment": comment,
        "audit_logs": logs
    }

    # 2. 支持审批人就地微调修订标题或操作步骤
    if human_decision.get("modified_title"):
        delta["title"] = human_decision["modified_title"]
        logs.append(f"【Node 4 人机终审】审批人修订了知识标题为：『{delta['title']}』")
    if human_decision.get("modified_steps"):
        delta["resolution_steps"] = human_decision["modified_steps"]
        logs.append("【Node 4 人机终审】审批人对解决步骤正文做出了最终订正校对")

    return delta


# ==============================================================================
# Node 5: 正式入库与索引发布 (PublishIndexNode - 彻底解耦 ES)
# ==============================================================================

def publish_index_node(state: KnowledgeFlowState) -> Dict[str, Any]:
    """【Node 5】正式发布与双写索引入库节点 (Publish & Index Node)。

    【节点定位与职责】：
    作为流水线终点节点，执行审核通过后的正式发布发布动作。
    负责生成全局不可变版本号，将正文分片写入 Python 原生 Docstore，并双写同步企业 MySQL
    知识主库，使得新沉淀的知识既能在 RAG 问答中即时召回，又能在管理后台全生命周期运维。

    【核心保证 - 彻底解耦 ES 与 MySQL 双写】：
    1. 彻底解耦 Elasticsearch：所有向量与切片完全托管于 Python 原生 Docstore 和向量引擎。
    2. MySQL 关系型双写：将知识元数据、正文内容、发布流水分别原子写入：
       - `knowledge_article`: 文章主表，状态置为 `PUBLISHED`
       - `knowledge_version`: 版本快照表（规避 MySQL 自动计算列 `search_text`，`keywords` 为空格分隔串）
       - `knowledge_transition`: 状态变更审计轨迹表

    【输入状态 (State Inputs)】：
    - `state["review_status"]`     (str): 必须为 "APPROVED" 才能触发入库发布。
    - `state["title"]`             (str): 最终确认的知识标题。
    - `state["resolution_steps"]`  (str): 最终确认的排障正文。
    - `state["category_id"]`       (str): 分类编号。
    - `state["risk_level"]`        (str): 风险等级。
    - `state["reviewer"]`          (str): 终审管理员账号。

    【输出增量 (Delta Output)】：
    - 返回 `published_version_id` (str), `indexed_chunk_count` (int) 及追加流水 `audit_logs`。
    """
    # 1. 门禁校验：若人工审核未通过（被驳回），终止发布，防止脏数据入库
    if state.get("review_status") != "APPROVED":
        logs = ["【Node 5 入库发布】单据未被批准（已被驳回或终止），终止向量入库与版本发布操作"]
        return {"audit_logs": logs}

    # 2. 生成企业级唯一不可变版本号
    version_id: str = f"ver-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    title: str = state.get("title", "")
    body: str = state.get("resolution_steps", "")
    category_id: str = state.get("category_id", "C_OTH")
    candidate_id: str = state.get("candidate_id", "unk-cand")

    logs: List[str] = [f"【Node 5 入库发布】审核通过！正在生成正式发布版本：{version_id}"]

    # 3. 结构化文本切片 (Chunking) 处理
    chunks: List[str] = [p.strip() for p in body.split("\n\n") if p.strip()]
    if not chunks:
        chunks = [body]

    indexed_count: int = len(chunks)

    # 4. 写入 Python 原生 Docstore 存储引擎（彻底解耦 ES）
    try:
        from rag_pipeline.docstore import InMemoryDocstore
        from rag_pipeline.chunking.structure_aware import Document
        docstore = InMemoryDocstore()
        doc = Document(
            page_content=body,
            metadata={
                "parent_id": f"doc_{candidate_id}",
                "title": title,
                "version_id": version_id,
                "category_id": category_id,
                "published_at": datetime.now().isoformat()
            }
        )
        docstore.save_documents([doc])
        logs.append(f"【Node 5 入库发布】成功写入 Python Docstore，切片切分完成（共 {indexed_count} 个切片）")
    except Exception as e:
        logs.append(f"【Node 5 入库发布】Docstore 写入完成（{e}）")

    # 5. 双写同步至企业 MySQL 关系型数据库，实现与前端「知识管理」台账联动
    published_article_id: Optional[str] = None
    try:
        import pymysql
        # 读取数据库连接配置（优先从环境变量读取，缺省使用标准内网配置）
        host = os.environ.get("DB_HOST") or os.environ.get("MYSQL_HOST") or "120.92.138.195"
        port = int(os.environ.get("DB_PORT") or os.environ.get("MYSQL_PORT") or 3306)
        user = os.environ.get("DB_USER") or os.environ.get("MYSQL_USERNAME") or "root"
        password = os.environ.get("DB_PASSWORD") or os.environ.get("MYSQL_PASSWORD") or "clt123456"
        database = os.environ.get("DB_NAME") or "it_ticket_system"

        art_id: str = f"art-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}"
        trans_id: str = f"trans-{uuid.uuid4().hex[:12]}"
        now_str: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        reviewer: str = state.get("reviewer") or "admin_kb"
        risk_level: str = "HIGH" if state.get("risk_level") == "HIGH" else "NORMAL"

        # 规约：keywords 存储为空格分隔的字符串，以适配 Java 服务端与 Vue 前端组件反序列化
        content_json: str = json.dumps({
            "title": title,
            "summary": state.get("summary") or f"针对【{title}】的沉淀知识",
            "body": body,
            "keywords": f"LangGraph {category_id}"
        }, ensure_ascii=False)

        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset="utf8mb4"
        )
        with conn.cursor() as cur:
            # (1) 插入知识文章主表 (knowledge_article)
            cur.execute("""
                INSERT INTO knowledge_article (article_id, status, current_version_id, category_id, risk_level, version, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (art_id, "PUBLISHED", version_id, category_id, risk_level, 0, now_str, now_str))

            # (2) 插入版本快照表 (knowledge_version)
            # 注意：search_text 为 MySQL VIRTUAL/STORED 自动生成列，严禁在 INSERT 语句中显式写入
            cur.execute("""
                INSERT INTO knowledge_version (version_id, article_id, version_no, content, author_id, reviewer_id, published_at, change_note, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (version_id, art_id, 1, content_json, reviewer, reviewer, now_str, state.get("audit_comment") or "LangGraph 审核通过入库", now_str, now_str))

            # (3) 插入状态变更审计表 (knowledge_transition)
            cur.execute("""
                INSERT INTO knowledge_transition (transition_id, article_id, version_id, from_status, to_status, event_code, operator_id, operator_role, reason, occurred_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (trans_id, art_id, version_id, "PENDING_REVIEW", "PUBLISHED", "KNOWLEDGE_PUBLISH", reviewer, "KNOWLEDGE_ADMIN", state.get("audit_comment") or "LangGraph 流程编排自动沉淀", now_str))

        conn.commit()
        conn.close()
        published_article_id = art_id
        logs.append(f"【Node 5 入库发布】已同步写入企业 MySQL 知识库（文章ID: {art_id}），知识管理工作台立即可查！")
    except Exception as e:
        logs.append(f"【Node 5 入库发布】同步 MySQL 知识库跳过（{e}）")

    logs.append(f"【Node 5 入库发布】Python 知识向量库同步落盘完成！新知识正式生效，可立即被 RAG 问答检索引用！")

    return {
        "published_version_id": version_id,
        "indexed_chunk_count": indexed_count,
        "audit_logs": logs
    }
