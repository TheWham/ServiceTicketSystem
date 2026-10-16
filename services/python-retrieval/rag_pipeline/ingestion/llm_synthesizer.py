"""
Layer 2 LLM Wiki 知识治理层：llm_synthesizer.py
职责：
1. LLM Knowledge Synthesizer：调用 kimi-k3 为每个知识条目萃取 Wiki frontmatter 元数据
   （规范化标题、实体抽取与术语规范化、一句话摘要、版本/状态/废止推断）
2. 工程保障：严格 JSON 输出约束、代码围栏剥离、结构完整性守卫（防表格丢失/文本坍缩）、双重试、磁盘缓存、规则兜底
3. API 配置安全：key 只从环境变量 / .env 读取，绝不硬编码入库
"""

import json
import os
import re
from typing import Any, Dict, Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from ..config import load_llm_config
from .clean_pipeline import Entry

DEFAULT_CLEAN_MODEL = "deepseek-v4-flash"  # LLM 清洗（正文清洗规范化，LlmSynthesizer 兜底用）


# ==================== API 配置加载 ====================


def load_api_config(search_dir: Optional[str] = None) -> Dict[str, str]:
    """加载 LLM 配置（包装 config.load_llm_config，保留旧函数名供 04_wiki_pipeline 调用）。

    返回 {api_key, base_url, chat_model, clean_model}，来源独立 LLM_* 环境变量。
    key 绝不硬编码进代码，.env 已被 .gitignore 忽略，防止提交入库。
    """
    return load_llm_config()


# ==================== LLM 萃取器 ====================

SYSTEM_PROMPT = """你是企业知识库治理专家。给定一条 IT 运维知识条目的结构化内容，为其萃取 Wiki 知识卡片元数据。

严格输出一个 JSON 对象（不要输出任何其他文字、不要用代码围栏），字段如下：
{
  "title": "规范化标题（简洁名词短语，不超过20字，去除冗余口语）",
  "entities": ["抽取3-8个关键实体/术语并规范化（如 WiFi->无线局域网(WiFi) 仅在确有必要时扩写，设备、协议、系统、命令名保持原样）"],
  "summary": "一句话摘要（50字以内，说明该条目解决什么问题+核心处置思路）",
  "version": "版本号，若原文无版本信息输出 \\"v1.0\\"",
  "status": "条目状态：若原文明确标注已废止/已下线则输出 \\"已废止\\" 或 \\"已下线\\"，否则输出 \\"现行\\"",
  "effective_date": "生效日期 YYYY-MM-DD，若原文无明确日期输出 null",
  "replaces": ["被本条废止/替代的历史版本或旧制度标识，无则空数组"],
  "conflict_note": "若发现与常见旧规/历史版本冲突之处，一句话说明废止裁决；无则空字符串"
}

铁律：
1. 不得编造原文中不存在的日期、金额、版本号，无依据字段一律输出 null 或默认值；
2. entities 必须是原文出现的概念（可做术语规范化），禁止引入外部知识；
3. 输出必须是可被 json.loads 解析的合法 JSON。"""

REQUIRED_FIELDS = ["title", "entities", "summary", "version", "status", "effective_date", "replaces", "conflict_note"]

CLEAN_SYSTEM_PROMPT = """你是企业知识库文档清洗专家。给定一条知识条目的若干字段（格式为【字段名】：内容），执行语义级清洗：

1. 修正明显的错别字与 OCR 式混淆（如"人氏币"->"人民币"、"VNP"->"VPN"、金额中的字母 O 混淆为数字 0），但不得改变技术含义与任何数值；
2. 统一术语与大小写（如 wifi/WIFI 统一为 WiFi）；
3. 规范化编号与排版（①②③、步骤1/2/3、1. 2. 3. 保持原有编号风格，每条一行）；
4. 剔除无意义的重复语句与多余空白，但严禁删减任何事实、步骤、命令、参数、金额、日期；
5. Markdown 表格必须完整保留原表格全部行列结构，严禁删减或省略任何表格内容、不得修改任何数字；
6. 发现残留的个人敏感信息（姓名、身份证号、手机号、个人邮箱、银行账号、凭证密钥等）一律替换为类型占位符（如 [姓名]、[手机号]、[银行账号]），并在 fixes 中记录；但公共 DNS（如 223.5.5.5、114.114.114.114）、回环地址（127.0.0.1）及内网排障示例网段（如 192.168.x.x、10.x.x.x）属于关键技术排障参数，必须原样保留，严禁替换为 [IP地址]；
7. 严禁编造原文不存在的内容。

严格输出一个 JSON 对象（不要输出任何其他文字、不要用代码围栏）：
- JSON 的 key 必须与输入给出的字段名一一对应，值为清洗后的内容（多行列表行间用 \\n 分隔）；
- 额外增加一个 "fixes" 字段：数组，列出本次清洗的实际修改点摘要，无修改则为空数组。
输出必须是可被 json.loads 解析的合法 JSON。"""


def _is_valid_cleaned_field(original: str, cleaned: str) -> bool:
    """校验 LLM 清洗后的字段是否发生结构丢失（如整张 Markdown 表格被吞）或异常截断。"""
    if not cleaned:
        return False
    orig_str = original.strip()
    clean_str = cleaned.strip()
    if not orig_str:
        return True
    # 1. 表格行数守卫：若原文包含 Markdown 表格行（以 | 开头），清洗后表格行数不得减少
    orig_table_rows = sum(1 for ln in orig_str.splitlines() if ln.strip().startswith("|"))
    clean_table_rows = sum(1 for ln in clean_str.splitlines() if ln.strip().startswith("|"))
    if orig_table_rows >= 2 and clean_table_rows < orig_table_rows:
        return False
    # 2. 长度坍缩守卫：若原文较长（>= 60 字符），清洗后长度缩水超过 35% 视为异常截断
    if len(orig_str) >= 60 and len(clean_str) < len(orig_str) * 0.65:
        return False
    return True


class LlmSynthesizer:
    def __init__(self, cfg: Dict[str, str], cache_dir: Optional[str] = None):
        if not cfg.get("base_url"):
            raise ValueError(
                "未配置 LLM_BASE_URL：请设置环境变量或在 .env 中填写 base_url"
            )
        if OpenAI is None:
            raise RuntimeError("缺少 openai 依赖包，请执行 pip install openai 或使用 --offline 模式")
        self.client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])
        self.model = cfg["chat_model"]
        self.clean_model = cfg.get("clean_model", DEFAULT_CLEAN_MODEL)
        self.cache_dir = cache_dir
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)

    # ---------- 缓存 ----------

    def _cache_path(self, code: str, prefix: str = "") -> Optional[str]:
        if not self.cache_dir:
            return None
        return os.path.join(self.cache_dir, f"{prefix}{code}.json")

    def _read_cache(self, code: str, prefix: str = "") -> Optional[Dict[str, Any]]:
        path = self._cache_path(code, prefix)
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return None

    def _write_cache(self, code: str, data: Dict[str, Any], prefix: str = "") -> None:
        path = self._cache_path(code, prefix)
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    # ---------- 条目 -> 用户提示词 ----------

    @staticmethod
    def _entry_to_prompt(e: Entry) -> str:
        parts = [f"条目代码：{e.code}", f"原始标题：{e.title}", f"所属分类：{e.category}"]
        if e.keywords:
            parts.append("检索关键词：" + ", ".join(e.keywords))
        for k, v in e.fields.items():
            parts.append(f"{k}：\n{v}")
        for para in e.body_paras:
            parts.append(para)
        if e.remark:
            parts.append(f"备注：{e.remark}")
        return "\n\n".join(parts)

    # ---------- 响应解析 ----------

    @staticmethod
    def _parse_json_loose(raw: str) -> Dict[str, Any]:
        """剥代码围栏 + 截取首个 JSON 对象"""
        text = raw.strip()
        text = re.sub(r"^```(?:json|yaml)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if m:
                return json.loads(m.group(0))
            raise

    # ---------- 通用调用 ----------

    def _chat_json(self, model: str, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """★ 全工程唯一的 LLM 调用出口（清洗和萃取都走这里）。
        收敛到单点的好处：模型名注入、响应解析、错误处理只写一遍。"""
        resp = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            # 注意：kimi-k3 服务端只允许 temperature=1，传其他值会 400，故不传该参数
        )
        # choices[0].message.content 是模型原文，剥围栏后解析为 JSON dict
        return self._parse_json_loose(resp.choices[0].message.content or "")

    # ---------- 主流程 ----------

    def extract_frontmatter(self, e: Entry) -> Dict[str, Any]:
        """【Step 3】萃取单条目的 frontmatter 元数据。
        固定模式：查缓存 -> LLM 调用 -> 失败重试 1 次 -> 规则兜底 -> 写缓存。"""
        cached = self._read_cache(e.code)
        if cached:
            cached.setdefault("status", "已废止" if "废止" in e.title else "现行")
            return cached  # 命中磁盘缓存，零 API 调用

        last_err: Optional[Exception] = None
        for _attempt in range(2):  # 首次 + 1 次重试
            try:
                meta = self._chat_json(self.model, SYSTEM_PROMPT, self._entry_to_prompt(e))
                # 补齐缺失字段，防止下游渲染 KeyError
                for field_name in REQUIRED_FIELDS:
                    if field_name == "status":
                        meta.setdefault("status", "已废止" if "废止" in e.title else "现行")
                    elif field_name in ("title", "summary", "conflict_note"):
                        meta.setdefault(field_name, "")
                    elif field_name in ("entities", "replaces"):
                        meta.setdefault(field_name, [])
                    else:
                        meta.setdefault(field_name, None)
                meta["meta_source"] = "llm"  # 来源标记：审计时可筛出未经 LLM 的卡片
                self._write_cache(e.code, meta)
                return meta
            except Exception as err:  # 网络错误 / 非法 JSON 统一重试
                last_err = err

        # 两次都失败：规则兜底，流水线不中断，并把错误原因写入缓存备查
        meta = self.fallback_frontmatter(e)
        meta["llm_error"] = str(last_err)
        self._write_cache(e.code, meta)
        return meta

    # ---------- LLM 清洗（deepseek-v4-flash） ----------

    def clean_entry(self, e: Entry) -> Dict[str, Any]:
        """【Step 2】用清洗模型（deepseek-v4-flash）对条目字段做语义级清洗。
        字段名动态跟随条目结构（IT 文档是四字段，PDF/DOCX/Excel 样本是各自适配器产生的字段），
        正文段落在无结构化字段时归入"正文"字段。
        返回 {"fields": {...}, "fixes": [...}, "clean_source": "llm"|"rule"}，失败或结构受损时回退原文。"""
        cached = self._read_cache(e.code, prefix="clean_")  # 清洗缓存与萃取缓存用前缀隔离
        if cached:
            # 对缓存结果同样执行结构守卫校验，防止早期脏缓存导致表格丢失
            raw_check: Dict[str, str] = dict(e.fields)
            if e.remark:
                raw_check["备注"] = e.remark
            if not raw_check and e.body_paras and not e.tables:
                raw_check["正文"] = "\n".join(e.body_paras)
            if all(_is_valid_cleaned_field(orig, str(cached.get("fields", {}).get(k) or ""))
                   for k, orig in raw_check.items()):
                return cached

        # 待清洗字段：结构化字段 + 备注 + （无结构化字段且无内联表格时的）纯正文段落
        # 若条目同时含有 body_paras 与内联 tables（如 SLA-001），不将 body_paras 单独塞入"正文"字段，
        # 从而保持 body_blocks 中段落与表格的严格物理阅读顺序。
        raw_fields: Dict[str, str] = dict(e.fields)
        if e.remark:
            raw_fields["备注"] = e.remark
        if not raw_fields and e.body_paras and not e.tables:
            raw_fields["正文"] = "\n".join(e.body_paras)

        if not raw_fields:
            return {"fields": {}, "fixes": [], "clean_source": "rule"}

        user_prompt = f"条目代码：{e.code}\n原始标题：{e.title}\n\n" + "\n\n".join(
            f"{key}：\n{value}" for key, value in raw_fields.items()
        )

        last_err: Optional[Exception] = None
        for _attempt in range(2):
            try:
                data = self._chat_json(self.clean_model, CLEAN_SYSTEM_PROMPT, user_prompt)
                cleaned_fields = {}
                for key, original in raw_fields.items():
                    value = str(data.get(key) or "").strip()
                    # 防御：模型把字段清空、删丢 Markdown 表格或异常截断时，该字段单独回退原文
                    cleaned_fields[key] = value if _is_valid_cleaned_field(original, value) else original
                result = {
                    "fields": cleaned_fields,
                    "fixes": data.get("fixes") if isinstance(data.get("fixes"), list) else [],
                    "clean_source": "llm",
                }
                self._write_cache(e.code, result, prefix="clean_")
                return result
            except Exception as err:
                last_err = err

        result = {
            "fields": raw_fields,
            "fixes": [],
            "clean_source": "rule",
            "clean_error": str(last_err),
        }
        self._write_cache(e.code, result, prefix="clean_")
        return result

    # ---------- 规则兜底 ----------

    @staticmethod
    def fallback_frontmatter(e: Entry) -> Dict[str, Any]:
        phenomenon = e.fields.get("现象描述", "")
        summary = re.sub(r"\s+", "", phenomenon)[:80]
        return {
            "title": e.title,
            "entities": e.keywords[:8],
            "summary": summary,
            "version": "v1.0",
            "status": "已废止" if "废止" in e.title else "现行",
            "effective_date": None,
            "replaces": [],
            "conflict_note": "",
            "meta_source": "rule",
        }

    # ---------- 版本冲突/废止检测框架 ----------

    def detect_conflicts(self, metas: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
        """汇总各条目 LLM 给出的 conflict_note，返回非空冲突说明（本文档预期全部为空）"""
        return {
            code: m.get("conflict_note", "")
            for code, m in metas.items()
            if m.get("conflict_note")
        }
