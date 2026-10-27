# -*- coding: utf-8 -*-
"""受控词表的加载、校验与确定性抽取。

三条纪律，全部由代码而非注释保证：

1. **只做子串包含**，不执行任何文本 —— 工单描述是外部输入，对提示词注入天然免疫；
2. **最长命中优先**，长度相同按词表书写顺序 —— 顺序敏感的人工优先级维护成本高、
   且一改词表就可能悄悄改变历史工单的归属，最长命中让"越专有的词越优先"成为
   自动性质（`打印机脱机` 必然压过 `脱机`）；
3. **禁用裸泛化词** —— `无反应`/`无法调节` 这类词单独出现时不构成症状判据。实测
   反例：「打印机再次脱机」的描述里同时有"打印机"和"无反应"，「电脑音量无法调节」
   的描述里也有"无反应" —— 任何一条裸泛化词都会把它们从正确标签下抢走。加载时
   校验 `generic_denylist`，违规直接抛错而不是静默降级。

词表外置于 `configs/taxonomy.yaml`，版本号参与配置指纹（见 config.py）。
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import yaml

AXIS_SYMPTOM = "SYMPTOM"
AXIS_DEVICE = "DEVICE"
AXIS_ROOT_CAUSE = "ROOT_CAUSE"

# prepare_ticket 生成的模板话术起点标记。
# 「待补充」一条即可覆盖「等信息待补充」/「待补充信息」等变体；按位置取最早的一处切割。
_TEMPLATE_MARKERS = ("待补充信息", "待员工补充", "待工程师", "待补充")


class TaxonomyError(ValueError):
    """词表本身不合规（不是运行时数据问题），加载即失败，不静默降级。"""


@dataclass(frozen=True)
class Keyword:
    """词表里的一个关键词。

    · `order`           —— 该词在其轴内的**书写顺序**（下标）。`_best_hit` 在长度
                           相同时据此裁决，所以它是人工维护的优先级，不是元数据；
    · `requires_device` —— 泛化词专用标记：仅当同一段文本另有 DEVICE 命中时才计数。
                           这是让 `打印无反应` 这类泛化词能安全使用的唯一方式
                           （裸泛化词在加载期就被 `generic_denylist` 拒掉）。
    """

    word: str
    label: str
    axis: str
    order: int
    requires_device: bool = False


@dataclass(frozen=True)
class Hit:
    axis: str
    label: str
    word: str

    @property
    def evidence(self) -> str:
        """写进 findings 的命中依据 —— 结论必须可解释，不能只给一个标签。"""
        return f"命中词「{self.word}」"


@dataclass
class Extraction:
    """一条工单文本的抽取结果。未命中的轴为 None，由调用方决定如何降级。"""

    symptom: Optional[str] = None
    device: Optional[str] = None
    root_cause: Optional[str] = None
    hits: List[Hit] = field(default_factory=list)

    def evidence_of(self, axis: str) -> Optional[str]:
        for h in self.hits:
            if h.axis == axis:
                return h.evidence
        return None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "symptom": self.symptom,
            "device": self.device,
            "root_cause": self.root_cause,
            "evidence": {h.axis: h.evidence for h in self.hits},
        }


@dataclass(frozen=True)
class Domain:
    """子域：把"网络与打印设备"这类范围限定词映射到 (设备, 症状) 集合。

    基于词典而非 `category_id` —— 实测唯一那张打印机工单的 `category_id` 是
    `C_HW_PC`（提交人手选的），按分类过滤会静默漏掉它。
    """

    name: str
    keywords: Tuple[str, ...]
    devices: Tuple[str, ...]
    symptoms: Tuple[str, ...]

    def matches(self, device: Optional[str], symptom: Optional[str]) -> bool:
        """设备命中 **或** 症状命中即属于该子域（并集）。

        只看设备会漏掉「VPN连接不上」这类没写明设备的单；只看症状会漏掉
        「交换机」这类没写明症状的单。
        """
        return (device is not None and device in self.devices) or \
               (symptom is not None and symptom in self.symptoms)


@dataclass
class Taxonomy:
    """加载并校验后的受控词表。

    刻意用**列表**而非 dict/set 保存 `keywords`：同长度词的裁决完全依赖书写顺序，
    换成无序结构会悄悄改变历史工单的标签归属。`fingerprint` 是词表文件的内容哈希，
    与 `version` 一起进配置快照，保证历史统计口径可追溯。
    """

    version: str
    fingerprint: str
    generic_denylist: frozenset
    keywords: Dict[str, List[Keyword]]          # axis -> 按书写顺序（顺序参与裁决）
    labels: Dict[str, List[str]]                # axis -> 标签顺序（给 DOMAIN 引用校验用）
    domains: List[Domain] = field(default_factory=list)


# ------------------------------------------------------------------ 加载与校验

def _load_yaml(path: Path) -> Dict[str, Any]:
    """读词表 YAML。文件缺失 / 语法错 / 根节点不是映射，三种都直接抛 TaxonomyError。

    不做任何兜底：词表坏了必须让人看见。静默降级成一个空词表的表现是"所有工单都
    抽不出标签"，那看起来像数据问题，会把排查方向带偏。
    """
    if not path.exists():
        raise TaxonomyError(f"词表文件不存在：{path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise TaxonomyError(f"词表 YAML 解析失败：{e}") from e
    if not isinstance(data, dict):
        raise TaxonomyError(f"词表根节点必须是映射：{path}")
    return data


def _normalize_keywords(raw: Any, axis: str, label: str) -> List[Tuple[str, bool]]:
    """把词表里的 keyword 写法归一为 (词, 是否要求设备共现)。

    允许两种写法：纯字符串，或 `{word: xxx, requires_device: true}`（泛化词专用）。
    """
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise TaxonomyError(f"{axis}.{label} 的 keywords 必须是列表")
    out: List[Tuple[str, bool]] = []
    for item in raw:
        if isinstance(item, str):
            word, requires = item, False
        elif isinstance(item, dict):
            word = str(item.get("word") or "").strip()
            requires = bool(item.get("requires_device"))
        else:
            raise TaxonomyError(f"{axis}.{label} 的关键词写法非法：{item!r}")
        if not word:
            raise TaxonomyError(f"{axis}.{label} 存在空关键词")
        out.append((word.lower(), requires))
    return out


def build_taxonomy(data: Dict[str, Any], fingerprint: str) -> Taxonomy:
    """把词表 YAML 解析成 `Taxonomy`，并把**全部纪律在这里一次性校验**。

    校验项（任一不满足即抛 TaxonomyError，不做静默降级）：
      · `generic_denylist` 非空 —— 它是防截胡的唯一硬约束；
      · 关键词不得是裸泛化词，除非标注 `requires_device`；
      · 同一轴内标签不重名、不得有空关键词、每个轴不得为空；
      · DOMAIN 引用的设备/症状标签必须真实存在。

    最后一条尤其重要：写错标签名会让子域过滤**静默失效**，表现是"过滤没生效"
    却查不出原因 —— 在加载期拦下，比在统计结果里发现少了几张单容易得多。
    """
    denylist = frozenset(
        str(w).strip().lower() for w in (data.get("generic_denylist") or []) if str(w).strip()
    )
    if not denylist:
        raise TaxonomyError("generic_denylist 不能为空 —— 它是防截胡的唯一硬约束")

    keywords: Dict[str, List[Keyword]] = {}
    labels: Dict[str, List[str]] = {}

    for axis in (AXIS_SYMPTOM, AXIS_DEVICE, AXIS_ROOT_CAUSE):
        entries = data.get(axis) or []
        if not isinstance(entries, list):
            raise TaxonomyError(f"{axis} 必须是列表")
        axis_kw: List[Keyword] = []
        axis_labels: List[str] = []
        for entry in entries:
            if not isinstance(entry, dict):
                raise TaxonomyError(f"{axis} 条目必须是映射：{entry!r}")
            label = str(entry.get("label") or "").strip()
            if not label:
                raise TaxonomyError(f"{axis} 存在无 label 的条目")
            if label in axis_labels:
                raise TaxonomyError(f"{axis} 标签重复：{label}")
            axis_labels.append(label)
            for word, requires in _normalize_keywords(entry.get("keywords"), axis, label):
                # 硬约束：裸泛化词一律拒绝。要么写成复合词，要么显式声明 requires_device。
                if word in denylist and not requires:
                    raise TaxonomyError(
                        f"{axis}.{label} 使用了裸泛化词「{word}」——"
                        f"它会截胡更专有的标签。请改写成复合词，或标注 requires_device。"
                    )
                axis_kw.append(Keyword(word=word, label=label, axis=axis,
                                       order=len(axis_kw), requires_device=requires))
        if not axis_kw:
            raise TaxonomyError(f"{axis} 词表为空")
        keywords[axis] = axis_kw
        labels[axis] = axis_labels

    domains: List[Domain] = []
    for entry in (data.get("DOMAIN") or []):
        if not isinstance(entry, dict):
            raise TaxonomyError(f"DOMAIN 条目必须是映射：{entry!r}")
        name = str(entry.get("name") or "").strip()
        if not name:
            raise TaxonomyError("DOMAIN 存在无 name 的条目")
        kws = tuple(str(k).strip().lower() for k in (entry.get("keywords") or []) if str(k).strip())
        if not kws:
            raise TaxonomyError(f"DOMAIN.{name} 缺少 keywords")
        # 子域引用的标签必须真实存在 —— 写错标签名会让过滤条件静默失效，
        # 表现为"子域过滤没生效"却查不出原因，这里直接拦下。
        devs = tuple(str(d).strip() for d in (entry.get("devices") or []))
        syms = tuple(str(s).strip() for s in (entry.get("symptoms") or []))
        for d in devs:
            if d not in labels[AXIS_DEVICE]:
                raise TaxonomyError(f"DOMAIN.{name} 引用了不存在的设备标签：{d}")
        for s in syms:
            if s not in labels[AXIS_SYMPTOM]:
                raise TaxonomyError(f"DOMAIN.{name} 引用了不存在的症状标签：{s}")
        domains.append(Domain(name=name, keywords=kws, devices=devs, symptoms=syms))

    return Taxonomy(
        version=str(data.get("version") or "unknown"),
        fingerprint=fingerprint,
        generic_denylist=denylist,
        keywords=keywords,
        labels=labels,
        domains=domains,
    )


def taxonomy_fingerprint(path: Path) -> str:
    """词表指纹：内容哈希。与版本号一起进配置快照，保证历史统计口径可追溯。"""
    if not path.exists():
        return "missing"
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


_cache: Dict[str, Taxonomy] = {}


def load_taxonomy(path: Optional[Path] = None, *, use_cache: bool = True) -> Taxonomy:
    from . import config as cfg
    target = Path(path) if path is not None else cfg.TAXONOMY_PATH
    key = str(target)
    if use_cache and key in _cache:
        return _cache[key]
    tax = build_taxonomy(_load_yaml(target), taxonomy_fingerprint(target))
    if use_cache:
        _cache[key] = tax
    return tax


# ------------------------------------------------------------------ 模板剥离

def strip_template(text: str) -> str:
    """剔除 prepare_ticket 生成的「待补充信息」模板话术。

    为什么必须做：模板里写着"待补充：蓝屏错误代码（如 CRITICAL_PROCESS_DIED）"，
    这些**举例性质的词**会被词表当成真实现象匹配到，污染抽取结果。模板出现在描述
    尾部，从最早一处标记起整段丢弃。
    """
    if not text:
        return ""
    cut = len(text)
    for marker in _TEMPLATE_MARKERS:
        pos = text.find(marker)
        if pos != -1 and pos < cut:
            cut = pos
    return text[:cut].strip()


# ------------------------------------------------------------------ 噪声判定

# 标题即垃圾：test / 123 / hello 之类
_JUNK_TITLE = re.compile(r"^(test|test123|123+|hello|zq|无|空)$", re.IGNORECASE)
# 联调/集成测试单：标题里的模板串
_JUNK_MARKER = re.compile(r"\[P0-verify\]|\[分派探测\]|【P0修复验证】|【HITL联调测试】")
# 自带「请忽略」标记的单据：内容看着真实，但描述里写着可随时撤销。
# 不识别这类会污染子域统计 —— 实测「网络与打印设备」7 张里有 2 张是这类。
_IGNORE_MARKER = re.compile(r"请忽略|请勿处理|演示用单|联调测试|演示单|请勿操作")

LOW_INFO_JUNK = "JUNK_TITLE"
LOW_INFO_TEST = "TEST_TICKET"
LOW_INFO_IGNORE = "MARKED_IGNORE"
LOW_INFO_EMPTY = "EMPTY_DESCRIPTION"


def low_information_reason(title: str, description: str) -> Optional[str]:
    """返回低信息量与噪声的判定原因；正常工单返回 None。

    刻意区分三种原因而不是笼统一个 `noise` 标志 —— 覆盖率披露时它们要分开报，
    否则"噪声多少张"这个数字没法解释，也无法定位是哪一环的口径出了问题。
    """
    t = (title or "").strip()
    body = (description or "").strip()
    combined = f"{t} {body}"

    if _IGNORE_MARKER.search(combined):
        return LOW_INFO_IGNORE
    if _JUNK_MARKER.search(t):
        return LOW_INFO_TEST
    if _JUNK_TITLE.match(t):
        return LOW_INFO_JUNK
    if len(body) < 5:
        return LOW_INFO_EMPTY
    return None


# ------------------------------------------------------------------ 抽取

def _best_hit(axis_kw: Sequence[Keyword], text_lower: str,
              device_present: bool) -> Optional[Keyword]:
    """在一组关键词里取命中：最长优先，长度相同取词表靠前者。

    裁决用严格 `>` 而非 `>=` —— 这正是"长度相同取靠前者"的实现方式：只有**更长**
    的词才顶掉当前命中，等长的后来者不覆盖。改这个符号会静默改变标签归属，
    `test_taxonomy.py` 有对应用例。
    """
    best: Optional[Keyword] = None
    for kw in axis_kw:
        if kw.word not in text_lower:
            continue
        # 泛化词要求同一段文本里另有 DEVICE 命中才计数
        if kw.requires_device and not device_present:
            continue
        if best is None:
            best = kw
            continue
        if len(kw.word) > len(best.word):
            best = kw
    return best


def extract(text: str, taxonomy: Optional[Taxonomy] = None) -> Extraction:
    """从一段文本抽取 (症状, 设备, 根因)。

    设备先算 —— 泛化词的关键词需要知道本段是否出现了设备实体。
    """
    tax = taxonomy or load_taxonomy()
    lowered = (text or "").lower()

    device_hit = _best_hit(tax.keywords[AXIS_DEVICE], lowered, True)
    symptom_hit = _best_hit(tax.keywords[AXIS_SYMPTOM], lowered, device_hit is not None)
    root_hit = _best_hit(tax.keywords[AXIS_ROOT_CAUSE], lowered, True)

    hits: List[Hit] = [
        Hit(axis=h.axis, label=h.label, word=h.word)
        for h in (device_hit, symptom_hit, root_hit) if h is not None
    ]
    return Extraction(
        symptom=symptom_hit.label if symptom_hit else None,
        device=device_hit.label if device_hit else None,
        root_cause=root_hit.label if root_hit else None,
        hits=hits,
    )


def extract_ticket(title: str, description: str,
                   taxonomy: Optional[Taxonomy] = None) -> Extraction:
    """工单抽取：标题权重高于描述（标题是人工填的概括），且描述先剥掉模板话术。"""
    tax = taxonomy or load_taxonomy()
    title_hit = extract(title or "", tax)
    body = strip_template(description or "")
    body_hit = extract(body, tax)
    return Extraction(
        symptom=title_hit.symptom or body_hit.symptom,
        device=title_hit.device or body_hit.device,
        root_cause=title_hit.root_cause or body_hit.root_cause,
        hits=title_hit.hits + body_hit.hits,
    )


def resolve_domains(text: str, taxonomy: Optional[Taxonomy] = None) -> List[Domain]:
    """把问题文本里的范围限定词解析成子域。

    用的是**文本 span 去重**而不是单纯的"最长命中只留一个"，两者在真实提问上差别很大：

      · 「网络与打印设备」——「网络与打印」（子域名）与「打印设备」（打印子域的
        关键词）在文本里**重叠**，后者只是前者的片段。若并列保留，打印会被算两次、
        且「网络」也会独立成域。→ 只保留跨度更长的那一个。
      · 「打印机和外设」——两个关键词在文本里**不重叠**，是用户真的并列了两个域。
        「最长命中只留一个」会把「外设」丢掉，答出一份只有打印机的结果。
        → 两个都保留。

    返回顺序按跨度长度降序（更具体的在前），便于调用方取"主域"。
    """
    tax = taxonomy or load_taxonomy()
    lowered = (text or "").lower()

    matched: List[Tuple[int, int, Domain]] = []      # (start, length, domain)
    for dom in tax.domains:
        best: Optional[Tuple[int, int]] = None        # (start, length)
        for kw in dom.keywords:
            pos = lowered.find(kw)
            if pos == -1:
                continue
            if best is None or len(kw) > best[1]:
                best = (pos, len(kw))
        if best is not None:
            matched.append((best[0], best[1], dom))

    if not matched:
        return []

    # 长跨度优先占用，短跨度与之重叠则视为它的片段而丢弃
    matched.sort(key=lambda m: (-m[1], m[0]))
    taken: List[Tuple[int, int]] = []
    kept: List[Domain] = []
    for start, length, dom in matched:
        end = start + length
        if any(start < t_end and t_start < end for t_start, t_end in taken):
            continue
        taken.append((start, end))
        kept.append(dom)
    return kept


def resolve_domain_names(names: Sequence[str],
                         taxonomy: Optional[Taxonomy] = None) -> List[Domain]:
    """把名字列表解析成 `Domain` 对象（Node A 的模型槽位走这条入口）。

    `resolve_domains` 从**提问文本**里匹配子域，本函数从**已抽好的名字**里取 ——
    两条入口共用同一份词表，所以"哪些子域存在"只有一处真源。

    两条纪律：

    1. **只认词表里真实存在的名字**，其余静默丢弃。模型多写一个不存在的领域，
       后果只是范围限定少生效一项、退回更宽的口径；为它让整条链路失败是本末倒置。
    2. **子集去重**。词表里存在组合子域（`网络与打印设备`）与它的子域（`网络设备`
       `打印设备`）并存的情况，模型可能两个都给出。三者的成员是同一批，全留着只会让
       页面上的"范围限定"出现重复项。覆盖关系明确时保留更大的那个；成员完全相同时
       保留书写顺序靠前的，避免互相顶掉导致一个都不剩。
    """
    tax = taxonomy or load_taxonomy()
    by_name = {d.name: d for d in tax.domains}
    picked: List[Domain] = []
    for raw in names or ():
        name = str(raw or "").strip().strip("「」【】\"'")
        dom = by_name.get(name)
        if dom is None or any(d.name == dom.name for d in picked):
            continue
        picked.append(dom)

    out: List[Domain] = []
    for i, dom in enumerate(picked):
        key = (frozenset(dom.devices), frozenset(dom.symptoms))
        superseded = False
        for j, other in enumerate(picked):
            if i == j:
                continue
            if not (key[0] <= frozenset(other.devices) and key[1] <= frozenset(other.symptoms)):
                continue
            if key == (frozenset(other.devices), frozenset(other.symptoms)) and j > i:
                continue      # 成员完全相同的两个域：保留靠前的，不互相顶掉
            superseded = True
            break
        if not superseded:
            out.append(dom)
    return out


def describe(taxonomy: Taxonomy) -> str:
    """词表摘要（用于日志与运维自检，不参与判定）。"""
    return json.dumps(
        {
            "version": taxonomy.version,
            "fingerprint": taxonomy.fingerprint,
            "counts": {axis: len(kws) for axis, kws in taxonomy.keywords.items()},
        },
        ensure_ascii=False,
    )