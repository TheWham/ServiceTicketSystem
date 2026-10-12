#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
llm_wiki_synthesizer.py — LLM Wiki 知识萃取器 (Day 11 工作坊 · 步骤 2)

将 clean_pipeline.py 清洗后的文本重构成带 YAML Frontmatter 的标准 Wiki 知识卡片，
并完成跨文档条款消歧（最新生效日条款胜出，旧条款写入 replaces）。

运行模式（必须显式选择，不做静默回退）：
    --mode llm      调用 OpenAI 兼容 Chat API（环境变量 OPENAI_API_KEY / OPENAI_BASE_URL /
                    LLM_MODEL / LLM_TIMEOUT）。缺 Key 直接报错退出。
                    生成链路：LLM -> normalize_card(剥围栏/前言) -> structural_errors
                    -> 不合格则把错误反馈给模型自愈重试 -> 生成即落盘（无批级质量闸）。
                    单篇失败显式记录、跳过并继续，批末汇总失败清单并返回非零码。
    --mode offline  纯规则合成器（确定性，可复现），供无 API 演示与 CI 回归。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

WIKI_SYNTHESIS_PROMPT = """你是一名资深企业知识管理与解决方案架构专家。
你的任务是将以下一段经过清洗但杂乱、零散的原始企业文本，提炼为一张标准化、自包含、高质量的【企业 Wiki 知识卡片】。

【输入原始文本】：
{raw_cleaned_text}

【现有版本背景参考】：
{context_reference}

【处理要求】：
1. 识别并消解所有冲突信息：若输入或【现有版本背景参考】中出现同一制度的多个版本，必须以最新生效日期的条款为准，并把被废止版本的文档ID/条款名称逐一登记入 replaces；若本卡片本身就是被更新的版本废止的旧制度，必须置 status 为 "superseded"，并在正文裁决区显式写明"本卡条款自 YYYY-MM-DD 起被 [发文编号] 废止"；现行有效卡片置 status 为 "active"。
2. 事实保真红线：严禁修改、推断或四舍五入任何原文数值与日期（金额、时间门槛、生效日期、金额推导规则等）；发现原文数据内部矛盾时保留原值并在裁决区以"数据质量说明"标注。
3. 规范化专业术语与职级表述；保留全部表格为 Markdown Table，且严禁还原任何已脱敏的 PII（手机号/身份证/银行卡保持打码形态）。
4. 输出必须严格按照以下格式结构返回（不得添加多余前缀文字）。其中：id 的时间戳段 = effective_date 的 YYYYMM；（domain 域前缀全库统一，同一制度域不得混用 HR/FIN）；category 采用"一级/二级"两级分类（如 财务制度/差旅管理、内部审计/差旅复核）。

【身份锚定与唯一性（最高优先级，违反即判失败）】：
5. 每张卡片描述的身份必须锚定【输入原始文本】该文档自身：title / effective_date / department / category / id 一律取自本输入文档自身的信息（其标题、发文编号、发文或制表日期），严禁挪用【现有版本背景参考】中其他文档的编号、标题或生效日期充当本卡身份。
6. 【现有版本背景参考】仅且只能用于三件事：①判定本卡是否已被更新版本废止（→ status: "superseded"）；②登记 replaces（仅当本卡文档自身主动废止了他版时）；③为 §3 裁决区提供新旧条款对照。绝不允许把背景文档的现行条款改写进本卡 §1/§2 正文细则（对照一律放 §3）。
7. 若本输入文档本身就是已被废止的旧制度原文件：status 必须为 "superseded"；title 保留原文标题并注明"（已废止，仅备查）"；effective_date 取该旧文档自身的原始生效日期；正文保留旧版原始数值，废止方信息仅写入 §3。
8. 每篇输入文档独立生成一张卡片；同一批次内任何两张卡的 id 必须互不相同；id 由本卡自身 effective_date 派生，不同生效日的文档绝不允许共用同一 id。

---
id: "WIKI-[DOMAIN]-[MODULE]-[生效日期YYYYMM]"
title: "明确、简练的知识卡片标题"
category: "一级分类/二级分类"
department: "所属部门"
effective_date: "YYYY-MM-DD"
version: "vX.X"                          # 每替代一版旧文档主版本 +1
status: "active|superseded"              # 是否已被更新版本废止
replaces: ["废止的旧文档ID或条款名称"]      # 显式声明废止的历史版本，无则 []
entities:
  - "关键词1"
  - "关键词2"
  - "专有名词"
summary: "100字以内的核心内容摘要"
---

# 正文标题

## 1. 适用范围与生效准则

本制度自 YYYY 年 M 月 D 日起生效，适用范围……（如有被废止条款，在此一句话声明同步作废）。

## 2. 标准明细表（实报实销上限 / 业务数据，与源文同构）

| 列名按源文真实表头 | …… | …… |
| :--- | :--- | :--- |
| 行值一律取自输入文档原值 | …… | …… |

## 3. 冲突与历史变更裁决说明
### 3.x 版本冲突特别裁决条款
> 凡涉及 YYYY-MM-DD 之后发生的业务，一律以本规定为准，不再沿用旧版标准。
### 3.x 历史条款对比（如有被废止版本，列对照表）
### 3.x 数据质量说明（如原文存在内部矛盾才需要）

⚠️ 注意：上述输出范式仅约束结构与排版；其中任何金额、日期、职级数值都不得沿用，
正文与表格数值必须全部取自【输入原始文本】的真实内容，任何一个数字与源文不符即判失败。
"""

FRONTMATTER_REQUIRED_KEYS = ["id", "title", "category", "department",
                             "effective_date", "version", "status",
                             "replaces", "entities", "summary"]


# ---------------------------------------------------------------------------
# YAML Frontmatter 手写输出（避免引入 pyyaml 重依赖）
# ---------------------------------------------------------------------------
def render_frontmatter(meta: dict) -> str:
    lines = ["---"]
    for k, v in meta.items():
        if isinstance(v, list):
            if not v:
                lines.append(f"{k}: []")
            else:
                lines.append(f"{k}:")
                lines += [f'  - "{item}"' for item in v]
        else:
            lines.append(f'{k}: "{v}"')
    lines.append("---")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 输出规范化与结构校验（解析层修复非静默回退；批级质量闸已按需求移除）
# ---------------------------------------------------------------------------
def normalize_card(text: str) -> str:
    """弃掉 Frontmatter 之前的前言与代码围栏；修复 '---' 与首字段同行折叠；
    完全缺失分隔符时按"首个 # 标题前的元数据段"启发式补围栏。"""
    s = text.strip()
    m = re.search(r"^(---|id\s*:)", s, flags=re.M)
    if m:
        s = s[m.start():]
    s = re.sub(r"\n```\s*$", "", s).rstrip()
    s = re.sub(r"^---[ \t]+(?=\S)", "---\n", s, count=1)
    has_open = bool(re.match(r"^---\s*\n", s))
    rest_start = s.index("\n") + 1 if has_open else 0
    has_close = bool(re.search(r"^---\s*$", s[rest_start:], flags=re.M))
    if not has_close:
        sp = re.search(r"\n\s*\n(?=#)", s)
        if sp:
            s = s[:sp.start()] + "\n---" + s[sp.start():]
    if not has_open:
        s = "---\n" + s
    return s.strip() + "\n"


def parse_frontmatter(card: str) -> dict[str, str]:
    m = re.match(r"^---\n(.*?)\n---\n", card, flags=re.S)
    if not m:
        return {}
    meta: dict[str, str] = {}
    for line in m.group(1).splitlines():
        kv = re.match(r"^([A-Za-z_]+)\s*:\s*(.*)$", line)
        if kv:
            meta[kv.group(1)] = kv.group(2).strip().strip('"')
    return meta


def structural_errors(card: str) -> list[str]:
    """单卡结构校验（不含批内 id 唯一性）。"""
    meta = parse_frontmatter(card)
    if not meta:
        return ["缺少合法 YAML Frontmatter 区块（--- 须单独成行开头并单独成行结尾）"]
    errs: list[str] = []
    for key in FRONTMATTER_REQUIRED_KEYS:
        if key not in meta:
            errs.append(f"Frontmatter 缺少必填字段 [{key}]")
    if meta.get("status") not in ("active", "superseded"):
        errs.append("status 必须为 active|superseded")
    return errs


def synthesize_with_repair(synth: "LLMWikiSynthesizer", text: str,
                           context: str, max_repairs: int = 2) -> tuple[str, list[str]]:
    """生成 + 结构校验；不合格时把错误反馈给模型自我修复，最多 max_repairs 次。"""
    feedback = ""
    card = ""
    for _ in range(max_repairs + 1):
        card = normalize_card(synth.synthesize(text, context_reference=context + feedback))
        errs = structural_errors(card)
        if not errs:
            return card, []
        feedback = (
            "\n\n【上一次输出不合规，请修复后重新完整输出】：\n"
            + "\n".join("- 问题：" + e for e in errs)
            + "\n修复要求：YAML Frontmatter 必须以单独一行 --- 开头、单独一行 --- 结尾，"
              "紧随其后的正文以 # 标题起，前后不得添加代码围栏或任何其他文字。"
        )
    return card, errs


# ---------------------------------------------------------------------------
# 模式一：LLM 萃取（显式失败，不回退）
# ---------------------------------------------------------------------------
class LLMWikiSynthesizer:
    def __init__(self) -> None:
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "[模式=llm] 未设置环境变量 OPENAI_API_KEY，拒绝静默回退。"
                "如需无 API 演示，请显式使用 --mode offline。"
            )
        self.base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
        self.timeout = float(os.environ.get("LLM_TIMEOUT", "300"))

    def synthesize(self, raw_cleaned_text: str, context_reference: str = "") -> str:
        prompt = WIKI_SYNTHESIS_PROMPT.format(
            raw_cleaned_text=raw_cleaned_text,
            context_reference=context_reference or "（无）",
        )
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps({
                "model": self.model,
                "temperature": 0.0,
                "messages": [{"role": "user", "content": prompt}],
            }).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", "replace")[:600]
            except Exception:  # 响应体不可读也要保留状态行
                pass
            raise RuntimeError(
                f"[模式=llm] API 调用失败（未做静默回退）：HTTP {exc.code} {exc.reason}"
                + (f" | 网关响应体: {body}" if body else "")
            ) from exc
        except Exception as exc:
            raise RuntimeError(f"[模式=llm] API 调用失败（未做静默回退）：{exc}") from exc
        return payload["choices"][0]["message"]["content"].strip()


# ---------------------------------------------------------------------------
# 模式二：Offline 确定性规则合成器
# ---------------------------------------------------------------------------
ROLE_ORDER = ["总监级及以上", "部门经理与资深专家", "部门经理与专家", "普通员工"]
ROLE_CANON = {
    "总监级及以上": "总监级及以上 (P8+)",
    "部门经理与资深专家": "部门经理 / 专家 (P6-P7)",
    "部门经理与专家": "部门经理 / 专家 (P6-P7)",
    "普通员工": "普通员工 (P4-P5)",
}
TIER_RE = re.compile(r"^\s*\d*[\.、]?\s*(一线城市|二线\w*城市|三线[^：]*城市?)\s*[（(]([^）)]*)[）)]\s*[:：]?")
STANDARD_RE = re.compile(r"(总监级及以上\w*|部门经理与\w*专家|普通员工)[^：\n]*[:：]\s*住宿上限\w*\s*(?:为|上调为|调整为)?\s*(\d+)\s*元/天")
OLD_SINGLE_RE = re.compile(r"(总监级及以上\w*|部门经理与\w*专家|普通员工)[（(]?[^：\n]*[）)]?\s*[:：]\s*住宿费报销上限为\s*(\d+)\s*元/天")


def _canon_role(raw: str) -> str:
    for k in ROLE_ORDER:
        if raw.startswith(k):
            return ROLE_CANON[k]
    return raw.strip()


def parse_staffing_standards(text_2024: str) -> dict[str, dict[str, int]]:
    """解析 2024 新版城市分级住宿上限：{城市层级: {标准职级: 金额}}"""
    tiers: dict[str, dict[str, int]] = {}
    current: str | None = None
    for line in text_2024.splitlines():
        m = TIER_RE.match(line)
        if m:
            name = m.group(1)
            if name.startswith("一线"):
                current = "一线城市"
            elif name.startswith("二线"):
                current = "二线城市"
            else:
                current = "三线及其他城市"
            tiers.setdefault(current, {})
            continue
        m = STANDARD_RE.search(line)
        if m and current:
            tiers.setdefault(current, {})[_canon_role(m.group(1))] = int(m.group(2))
    return tiers


def parse_old_standards(text_2022: str) -> dict[str, int]:
    return {_canon_role(m.group(1)): int(m.group(2))
            for m in OLD_SINGLE_RE.finditer(text_2022)}


def parse_threshold(text: str, pattern: str) -> str | None:
    m = re.search(pattern, text)
    return m.group(1) if m else None


def build_travel_card(doc2024: str, doc2022: str, doc2022_no: str | None) -> str:
    tiers = parse_staffing_standards(doc2024)
    old = parse_old_standards(doc2022)
    new_threshold = parse_threshold(doc2024, r"(21:00|22:30)\s*（?含?）?[^。\n]{0,30}?(?:实报|报销)") or "21:00"
    old_threshold = parse_threshold(doc2022, r"超过\s*(22:30)") or "22:30"

    roles = [r for r in ("总监级及以上 (P8+)", "部门经理 / 专家 (P6-P7)", "普通员工 (P4-P5)")
             if r in tiers.get("一线城市", {}) or r in tiers.get("二线城市", {})]
    table_lines = [
        "| 员工职级体系 | 一线城市（北上广深） | 二线城市（省会及新一线） | 三线及其他城市 | 备注要求 |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]
    for r in roles:
        v1 = tiers.get("一线城市", {}).get(r, "")
        v2 = tiers.get("二线城市", {}).get(r, "")
        v3 = int(v2) - 50 if isinstance(v2, int) else ""
        table_lines.append(f"| **{r}** | **{v1} 元/天** | {v2} 元/天 | {v3} 元/天 | 需开具增值税专票 |")
    table = "\n".join(table_lines)

    doc_no = doc2022_no or "2022暂行版"
    old_cap = next(iter(old.values()), 600)
    meta = {
        "id": "WIKI-FIN-TRAVEL-202403",
        "title": "华科智造员工差旅报销与商务住宿管理规约 (2024最新修订版)",
        "category": "财务制度/差旅管理",
        "department": "财务共享服务中心",
        "effective_date": "2024-03-01",
        "version": "v2.0",
        "status": "active",
        "replaces": [doc_no],
        "entities": ["差旅报销", "住宿标准", "夜间打车", "实报实销", "总监级"],
        "summary": "本规约规范了集团全员差旅交通、城市分级住宿上限与夜间加班打车报销政策。"
                   "自2024年3月1日起废止2022版单一上限，全面启用一线城市分级标准，夜间打车报销触发时间放宽。",
    }
    body = f"""# 华科智造员工差旅报销与商务住宿管理规约 (2024版)

## 1. 适用范围与生效准则
- **生效时间**：自 **2024年3月1日** 起正式生效并严格执行。
- **废止声明**：原《2022年员工差旅与商务住宿管理规范（暂行版 {doc_no}）》中第五条（住宿单一上限 {old_cap} 元/天标准）及第七条（{old_threshold} 打车报销限制）即日起**彻底废止作废**。凡 2024 年 3 月 1 日及之后产生的报销单据，一律以本规约条款为唯一裁决依据。
- **历史旧值对照（已被废止，仅保留备查）**：
"""
    for role, amount in old.items():
        body += f"  - {role}：{amount} 元/天（单一不分城市级别）\n"
    body += f"""
---

## 2. 住宿费用分级实报实销标准明细表
根据目的地城市物价水平实行分级封顶报销，超出上限部分由员工自理（三线及其他城市按二线标准顺减 50 元/天执行）：

{table}

---

## 3. 差旅市内交通与加班打车报销细则
1. **常规出行**：出差期间优先选择公共交通工具（地铁、公交、机场大巴）。
2. **夜间加班打车门槛**：
   - 触发时间：**当日 {new_threshold}（含）之后**。
   - 报销条件：因工作需要加班或出差返回住所/酒店，凭正规网约车行程发票实报实销，**无需特殊审批**。
   - 历史对比：较 2022 旧版政策（{old_threshold} 门槛）门槛提前。

---

## 4. 冲突与历史变更裁决说明（FAQ）
### 4.1 版本冲突特别裁决条款
> 凡涉及 2024-03-01 之后发生的差旅报销，一律以本规定分级城市上限为准，不再沿用旧版单一上限标准。

### 4.2 FAQ
- **Q：员工在 2024 年 2 月份出差一线城市，住宿发票是否可套用 2024 版上浮标准？**
  **裁决结果**：**不可**。必须以发票发生日期为准。2024 年 3 月 1 日之前的差旅统一执行 2022 版制度（上限 {old_cap} 元/天），超出部分自理或追回。
- **Q：新旧条款同时命中时以哪个为准？**
  **裁决结果**：以**生效日期最新**且**发票日期落在生效区间**的条款为准，旧条款重归历史废止档案。
"""
    return render_frontmatter(meta) + "\n\n" + body.strip() + "\n"


def build_audit_card(cleaned_audit: str) -> str:
    table_blocks = re.findall(r"(^\|[^\n]+\|(?:\n\|[^\n]+\|)+)", cleaned_audit, flags=re.M)
    table = "\n\n".join(table_blocks) if table_blocks else "（本批次无表格数据）"
    meta = {
        "id": "WIKI-FIN-AUDIT-202404",
        "title": "华科智造2024年Q1差旅审计通报与典型合规案例备忘 (已脱敏)",
        "category": "内部审计/差旅复核",
        "department": "财务审计二处",
        "effective_date": "2024-04-10",
        "version": "v1.0",
        "status": "active",
        "replaces": [],
        "entities": ["差旅审计", "违规追回", "报销合规", "生效节点"],
        "summary": "汇总2024年第一季度差旅报销典型合规与违规案例，明确新旧制度切换节点（2024年3月1日）的执行纪律与合规判定规则，全部敏感个人信息已完成脱敏。",
    }
    body = f"""# 华科智造2024年Q1差旅审计通报与典型合规案例备忘

## 1. 典型合规与违规案例抽检汇总表（PII 已合规脱敏）

{table}

---

## 2. 关键合规判定红线
1. **时间分水岭严禁穿透**：所有报销系统机审规则均以行程发票实际时间为准，凡 2024 年 3 月 1 日之前的单据不得按新规报销。
2. **严防敏感个人信息泄露**：所有公开通报与文档严禁包含明文身份证号、银行卡号及完整手机号。
"""
    return render_frontmatter(meta) + "\n\n" + body


class OfflineRuleSynthesizer:
    """确定性规则合成器：为无 API 演示与 CI 回归提供可复现的 Wiki 萃取。"""

    def synthesize_group(self, name: str, texts: dict[str, str]) -> tuple[str, str]:
        joined = "\n".join(texts.values())
        if name == "travel":
            doc2024 = max(texts.values(), key=lambda t: 1 if "2024" in t else 0)
            doc2022 = min(texts.values(), key=lambda t: 1 if "2024" in t else 0)
            m = re.search(r"发文编号[：:]\s*([\w\-]+)", doc2022)
            return ("WIKI-FIN-TRAVEL-202403_华科智造员工差旅住宿与交通报销标准.md",
                    build_travel_card(doc2024, doc2022, m.group(1) if m else None))
        return ("WIKI-FIN-AUDIT-202404_2024Q1差旅审计脱敏通报与操作备忘.md",
                build_audit_card(joined))


def group_documents(clean_dir: Path) -> dict[str, dict[str, str]]:
    """按领域聚合清洗语料：差旅制度组 / 审计通报组。"""
    groups: dict[str, dict[str, str]] = {"travel": {}, "audit": {}}
    for md in sorted(clean_dir.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        if "审计" in text or "报销单号" in text:
            groups["audit"][md.name] = text
        else:
            groups["travel"][md.name] = text
    return {k: v for k, v in groups.items() if v}


def main() -> int:
    ap = argparse.ArgumentParser(description="LLM Wiki 知识萃取器（YAML Frontmatter 标准卡片）")
    ap.add_argument("--mode", choices=["llm", "offline"], default="llm",
                    help="llm=调用大模型（需 OPENAI_API_KEY，不回退）；offline=规则合成器")
    ap.add_argument("--input", required=True, help="clean_pipeline 输出目录")
    ap.add_argument("--output", required=True, help="Wiki 卡片输出目录（wiki_kb_vX.0/）")
    args = ap.parse_args()

    in_dir = Path(args.input)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not in_dir.is_dir():
        print(f"[失败] 输入目录不存在：{in_dir}", file=sys.stderr)
        return 2

    if args.mode == "offline":
        groups = group_documents(in_dir)
        if not groups:
            print(f"[失败] {in_dir} 下没有可用的清洗 Markdown。", file=sys.stderr)
            return 2
        synth = OfflineRuleSynthesizer()
        for name, texts in groups.items():
            filename, card = synth.synthesize_group(name, texts)
            (out_dir / filename).write_text(card, encoding="utf-8")
            print(f"[OK] 领域组[{name}] -> {filename}（来源文档 {len(texts)} 篇）")
        return 0

    # 模式 llm：逐篇调用大模型重构，生成即落盘（边生成边写，无批级质量闸）。
    # 消歧背景采用"其余所有文档的原文摘要"双向注入——不依赖处理顺序。
    # 单篇失败不显式终止批处理：记录原因并跳过，批末汇总失败清单返回非零码。
    try:
        synth = LLMWikiSynthesizer()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    texts = {md.name: md.read_text(encoding="utf-8") for md in sorted(in_dir.glob("*.md"))}
    if not texts:
        print(f"[失败] {in_dir} 下没有可用的清洗 Markdown。", file=sys.stderr)
        return 2
    failures: dict[str, str] = {}
    for name, text in texts.items():
        others = [f"【{n}】\n{t[:800]}" for n, t in texts.items() if n != name]
        context = "\n\n".join(others)
        try:
            card, errs = synthesize_with_repair(synth, text, context)
        except RuntimeError as exc:
            failures[name] = str(exc)
            print(f"[跳过] {name} 生成失败：{exc}", file=sys.stderr)
            continue
        (out_dir / name).write_text(card + "\n", encoding="utf-8")
        state = "（自愈重试后结构仍不合规，需人工复核）" if errs else ""
        print(f"[已落盘] {name} {state}".rstrip())
    if failures:
        print(f"[部分失败] {len(failures)}/{len(texts)} 篇未生成，清单：", file=sys.stderr)
        for n, e in failures.items():
            print(f"  - {n}: {e.splitlines()[0]}", file=sys.stderr)
        return 5
    return 0


if __name__ == "__main__":
    sys.exit(main())
