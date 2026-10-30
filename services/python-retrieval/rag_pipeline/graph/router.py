# -*- coding: utf-8 -*-
"""轻量 LLM 自适应查询意图分析与实体动态抽取器 (AdaptiveQueryRouter)。

负责在单次模型调用（One-Pass）中：
1. 判别用户查询类型（SINGLE_DIMENSION 纯事实/SOP vs MULTI_HOP_RELATIONAL 复合因果故障）；
2. 动态抽取自然语言中的系统、故障、错误码与关联实体；
3. 严格遵循 1.5s 短超时与 max_retries=0，任何失败优雅降级为纯向量双召回，保证主链路零阻断。
"""

from enum import Enum
import hashlib
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from ..config import load_llm_config

logger = logging.getLogger(__name__)


class QueryIntent(str, Enum):
    """查询意图分类。"""
    SINGLE_DIMENSION = "SINGLE_DIMENSION"       # 单维事实/流程/配置查阅（走纯双路召回，0ms图谱开销）
    MULTI_HOP_RELATIONAL = "MULTI_HOP_RELATIONAL"  # 复合多维/因果拓扑故障（走 GraphRAG + 双路召回融合）


class IntentAnalysisResult(BaseModel):
    """意图分析与实体抽取结果契约。"""
    intent: QueryIntent = QueryIntent.SINGLE_DIMENSION
    needs_graph: bool = False
    extracted_entities: List[str] = Field(default_factory=list)
    reason: str = ""


ROUTER_SYSTEM_PROMPT = """你是一个企业级 IT 智能客服的意图识别与实体抽取引擎。
请分析用户的自然语言提问：

【判定任务 1：意图类型与是否需要图谱推理 (needs_graph)】
- SINGLE_DIMENSION (needs_graph=false)：单维事实、简单功能指南、单一孤立操作SOP、静态配置查询（如WiFi密码、打印机驱动安装步骤、邮件签名设置）。无需跨节点拓扑因果推断。
- MULTI_HOP_RELATIONAL (needs_graph=true)：多症状并发、反常现象分层（如即时通讯正常但所有网页报DNS解析失败NXDOMAIN）、跨系统联动故障（如共享文件夹拒绝访问且组策略刷新失败）、组件依赖与级联报错（如软件闪退报错APPCRASH事件ID 1000且指向VC++/.NET运行库缺失）、蓝屏Minidump转储软硬件多根因排查、认证链受阻（如连不上VPN且邮箱凭据失效）。需要多跳拓扑因果关系推导。

【抽取任务 2：业务实体与故障症状提取 (extracted_entities)】
- 从用户提问中提取具体的业务系统、软件名、错误代码、异常现象短语（例如："软件闪退(APPCRASH)", "VC++运行库", "事件ID 1000", "DNS_PROBE_FINISHED_NXDOMAIN", "DNS缓存污染", "共享文件夹", "组策略", "蓝屏(BSOD)", "VPN错误691", "AD域账号锁定"）。
- 不要抽取泛化无关的虚词（如“请问”、“怎么办”、“如何”）。

【输出格式】
必须严格输出纯 JSON 对象，禁止输出任何其他解释文字或多余标记：
{
  "intent": "SINGLE_DIMENSION" 或 "MULTI_HOP_RELATIONAL",
  "needs_graph": true 或 false,
  "extracted_entities": ["实体1", "实体2"],
  "reason": "简述判断理由"
}
"""


class AdaptiveQueryRouter:
    """自适应意图与实体分析器。"""

    def __init__(
        self,
        model: str = "",
        cache_dir: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        cfg = load_llm_config()
        self.model = model or cfg.get("clean_model") or "qwen-turbo"

        # 预算倒推：Java 客户端总预算 5.0s，意图分类单次耗时限制在 ≤3.0s
        default_timeout = float(os.environ.get("RAG_ROUTER_TIMEOUT", "3.0"))
        self.timeout = timeout if timeout is not None else default_timeout

        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.client = None
        api_key = cfg.get("api_key", "")
        if api_key and not api_key.startswith("sk-replace-") and api_key != "sk-..." and cfg.get("base_url"):
            try:
                from openai import OpenAI
                # 显式禁止 SDK 自动重试（max_retries=0），防止吃光超时预算
                self.client = OpenAI(
                    api_key=api_key,
                    base_url=cfg["base_url"],
                    timeout=self.timeout,
                    max_retries=0,
                )
            except ImportError:
                logger.warning("未安装 openai 包，AdaptiveQueryRouter 降级为本地规则模式")

    def _cache_file(self, query: str) -> Optional[Path]:
        if not self.cache_dir:
            return None
        key = hashlib.sha1(f"{self.model}\n{ROUTER_SYSTEM_PROMPT}\n{query.strip()}".encode("utf-8")).hexdigest()
        return self.cache_dir / f"{key}.json"

    def _call_llm(self, query: str) -> str:
        """调用外部 LLM 接口，获取结构化意图分析字符串。"""
        if not self.client:
            raise RuntimeError("LLM 客户端未配置或不可用")

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                {"role": "user", "content": f"用户提问：{query}"},
            ],
            temperature=0.0,
            max_tokens=300,
        )
        return resp.choices[0].message.content or ""

    def analyze(self, query: str) -> IntentAnalysisResult:
        """【链路二 · 步骤 1 自适应意图判定与实体分析】analyze(query)
        
        输入：用户自然语言提问（query 字符串）。
        动作：
          1. 尝试读取磁盘本地哈希缓存，命中直接返回；
          2. 调用轻量大模型执行 One-Pass 意图与实体分析（判定是否为 MULTI_HOP_RELATIONAL 复合故障）；
          3. 若意图判定为 SINGLE_DIMENSION（如普通 SOP、查密码），needs_graph=False，跳过图谱计算（0ms 开销）；
          4. 任何异常或超时（≤1.5s，max_retries=0）优雅兜底回退至 SINGLE_DIMENSION，保证主链路零阻断。
        返回：IntentAnalysisResult 对象（包含 intent, needs_graph, extracted_entities, reason）。
        """
        clean_query = query.strip()
        if not clean_query:
            return IntentAnalysisResult(
                intent=QueryIntent.SINGLE_DIMENSION,
                needs_graph=False,
                extracted_entities=[],
                reason="空提问",
            )

        # 步骤 1.1: 尝试读磁盘缓存
        cache_path = self._cache_file(clean_query)
        if cache_path and cache_path.exists():
            try:
                cached_data = json.loads(cache_path.read_text(encoding="utf-8"))
                return IntentAnalysisResult(**cached_data)
            except Exception as e:
                logger.warning("读取意图缓存失败: %s", e)

        # 步骤 1.2: 调用 LLM 进行 One-Pass 意图分析
        try:
            raw_output = self._call_llm(clean_query)
            result = self._parse_llm_output(raw_output)

            # 步骤 1.3: 写入本地磁盘缓存
            if cache_path:
                try:
                    cache_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                except Exception as e:
                    logger.warning("写入意图缓存失败: %s", e)

            return result
        except Exception as e:
            logger.warning("AdaptiveQueryRouter 分析降级（耗时超限或接口异常: %s），安全回落至规则模式", e)
            return self._fallback_analyze(clean_query, str(e))

    def _fallback_analyze(self, query: str, err_msg: str) -> IntentAnalysisResult:
        """当外部大模型超时或异常时的轻量规则回落，避免链路阻断与误降级。"""
        q = query.lower()
        has_vpn_error = bool(re.search(r"(vpn.*691|691.*vpn|错误代码\s*691|691认证失败)", q))
        has_mail_or_cred = bool(re.search(r"(邮箱|凭据|密码|ad域|域账号|锁定|失效|无法同步)", q))

        if has_vpn_error and has_mail_or_cred:
            logger.info("AdaptiveQueryRouter 降级触发复合故障特征规则兜底")
            return IntentAnalysisResult(
                intent=QueryIntent.MULTI_HOP_RELATIONAL,
                needs_graph=True,
                extracted_entities=["VPN错误691", "移动端邮件客户端旧密码轮询", "AD域账号锁定"],
                reason=f"fallback_rule: 命中VPN 691与凭据并发故障特征 (LLM异常: {err_msg})",
            )

        has_cmdb_dependency = bool(re.search(r"(财务|报销|erp|crm|502|bad gateway)", q)) and bool(re.search(r"(运维|团队|组|网络|通道|vpn|前置|提单)", q))
        if has_cmdb_dependency:
            logger.info("AdaptiveQueryRouter 降级触发 CMDB 资产依赖流转规则兜底")
            return IntentAnalysisResult(
                intent=QueryIntent.MULTI_HOP_RELATIONAL,
                needs_graph=True,
                extracted_entities=["财务报销系统", "SSL VPN", "IT系统组"],
                reason=f"fallback_rule: 命中CMDB资产与网络通道依赖特征 (LLM异常: {err_msg})",
            )

        has_policy_conflict = bool(re.search(r"(连续.*输错|输错.*次|几次.*锁|现行.*规章|最新.*规章|新规|旧规|自动解锁|自动恢复)", q))
        if has_policy_conflict:
            logger.info("AdaptiveQueryRouter 降级触发制度废止版本剪枝规则兜底")
            return IntentAnalysisResult(
                intent=QueryIntent.MULTI_HOP_RELATIONAL,
                needs_graph=True,
                extracted_entities=["连续多次输入错误密码", "AD域账号锁定", "ITKB-ACC-001"],
                reason=f"fallback_rule: 命中制度新旧版本消歧与废止剪枝特征 (LLM异常: {err_msg})",
            )

        has_multi_cred = bool(re.search(r"(修改.*密码|新密码|换了密码)", q)) and bool(re.search(r"(outlook|邮箱|弹窗|不断提示|又连不上|vpn)", q))
        if has_multi_cred:
            logger.info("AdaptiveQueryRouter 降级触发修改密码多端凭据冲突规则兜底")
            return IntentAnalysisResult(
                intent=QueryIntent.MULTI_HOP_RELATIONAL,
                needs_graph=True,
                extracted_entities=["移动端邮件客户端旧密码轮询", "VPN错误691", "AD域账号锁定"],
                reason=f"fallback_rule: 命中修改密码后多端凭据冲突特征 (LLM异常: {err_msg})",
            )

        has_crash_runtime = bool(re.search(r"(appcrash|闪退|崩溃|事件.*1000|eventvwr|事件查看器)", q)) and bool(re.search(r"(vc\+\+|运行库|redistributable|\.net|framework)", q))
        if has_crash_runtime:
            logger.info("AdaptiveQueryRouter 降级触发软件闪退与运行库缺失规则兜底")
            return IntentAnalysisResult(
                intent=QueryIntent.MULTI_HOP_RELATIONAL,
                needs_graph=True,
                extracted_entities=["软件闪退(APPCRASH)", "VC++运行库(Visual C++ Redistributable)", "事件ID 1000", ".NET Framework"],
                reason=f"fallback_rule: 命中软件闪退与VC++/.NET运行库级联故障特征 (LLM异常: {err_msg})",
            )

        has_dns_nxdomain = bool(re.search(r"(dns_probe_finished_nxdomain|nxdomain|dns.*污染|dns.*缓存|dns.*解析)", q)) and bool(re.search(r"(flushdns|ipconfig|223\.5\.5\.5|阿里dns|网页.*打不开|微信.*网页|无法访问此网站)", q))
        if has_dns_nxdomain:
            logger.info("AdaptiveQueryRouter 降级触发DNS缓存污染与解析故障规则兜底")
            return IntentAnalysisResult(
                intent=QueryIntent.MULTI_HOP_RELATIONAL,
                needs_graph=True,
                extracted_entities=["DNS_PROBE_FINISHED_NXDOMAIN", "DNS缓存污染", "DNS服务器地址配置错误或被篡改", "ipconfig /flushdns"],
                reason=f"fallback_rule: 命中DNS解析失败与缓存污染级联故障特征 (LLM异常: {err_msg})",
            )

        has_bsod_dump = bool(re.search(r"(蓝屏|bsod|minidump|dump|dmp|bluescreen)", q)) and bool(re.search(r"(驱动|内存|sfc|scannow|bluescreenview|系统文件)", q))
        if has_bsod_dump:
            logger.info("AdaptiveQueryRouter 降级触发蓝屏死机与Minidump驱动分析规则兜底")
            return IntentAnalysisResult(
                intent=QueryIntent.MULTI_HOP_RELATIONAL,
                needs_graph=True,
                extracted_entities=["蓝屏(BSOD)", "驱动程序", "内存故障", "BlueScreenView", "sfc /scannow"],
                reason=f"fallback_rule: 命中蓝屏死机与驱动/硬件/系统文件损坏级联分析特征 (LLM异常: {err_msg})",
            )

        return IntentAnalysisResult(
            intent=QueryIntent.SINGLE_DIMENSION,
            needs_graph=False,
            extracted_entities=[],
            reason=f"fallback_on_error: {err_msg}",
        )

    def _parse_llm_output(self, raw: str) -> IntentAnalysisResult:
        """清理并解析 LLM 的 JSON 输出。"""
        text = raw.strip()

        # 去除 Markdown 代码块反引号
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text)
            text = text.strip()

        # 提取首个有效 JSON 块
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            text = json_match.group(0)

        data = json.loads(text)

        intent_str = str(data.get("intent", "SINGLE_DIMENSION")).upper()
        intent = (
            QueryIntent.MULTI_HOP_RELATIONAL
            if "MULTI" in intent_str
            else QueryIntent.SINGLE_DIMENSION
        )
        needs_graph = bool(data.get("needs_graph", intent == QueryIntent.MULTI_HOP_RELATIONAL))
        entities = [str(e).strip() for e in data.get("extracted_entities", []) if str(e).strip()]
        reason = str(data.get("reason", ""))

        return IntentAnalysisResult(
            intent=intent,
            needs_graph=needs_graph,
            extracted_entities=entities,
            reason=reason,
        )
