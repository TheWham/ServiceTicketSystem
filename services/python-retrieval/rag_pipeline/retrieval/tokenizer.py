"""中文分词与纯 Python BM25 兜底实现。"""

import re
import math
from typing import List, Dict, Set

try:
    import jieba
except ImportError:
    jieba = None


# 纯标点/符号正则：剔除标点 token（如 "？" 在知识库仅出现 1 次导致极高 IDF 污染全部问句召回）
PUNCT_ONLY_RE = re.compile(r"^[\s\W_]+$", re.UNICODE)
# 允许保留的英文/数字/技术符号词项（如 sfc, /scannow, 806, 223.5.5.5, C:\Windows）
TECH_TOKEN_RE = re.compile(r"[A-Za-z0-9]")

# 中文检索停用词表：过滤口语虚词与通用提问泛词，保留否定词（不得/禁止/停止/无法/未）与业务实词
STOPWORDS: Set[str] = {
    "的", "了", "是", "在", "我", "有", "和", "就", "都", "而", "及", "与", "着", "或",
    "一个", "没有", "我们", "你们", "他们", "自己", "同事", "大家", "什么", "哪些", "哪里",
    "怎么", "怎么办", "怎么弄", "怎么查", "怎么处理", "怎么解决", "如何", "为什么", "是不是",
    "能不能", "可以", "应该", "需要", "请问", "一下", "一直", "总是", "偏偏", "明明", "然后",
    "如果", "还是", "或者", "因为", "所以", "但是", "而且", "这个", "那个", "这些", "那些",
    "问题", "故障", "情况", "进行", "使用", "通过", "可能", "通常", "常见", "比如", "例如",
    "第", "步", "步骤", "卡片", "检索", "增强", "关键词", "实体",
}


class ChineseTokenizer:
    """轻量稳健中文分词器（优先使用 jieba，未安装时自适应正则与 N-gram 切词，内置标点与停用词过滤）。

    为什么必须过滤标点与口语停用词：
      在旧实现中，中文问号 `？` 被作为独立词项保留；而全库 132 个切片里仅有 `ITKB-APPENDIX-1#c0`
      含有一句带问号的正文（IDF 高达 4.47），导致所有带问号的用户提问都把毫无实质排障内容的
      附录流程卡顶入 BM25 Top-3。过滤标点与口语虚词后，BM25 分数聚焦于真正的技术实体与症状词。
    """

    @staticmethod
    def _is_valid_token(tok: str) -> bool:
        if not tok or tok in STOPWORDS:
            return False
        if TECH_TOKEN_RE.search(tok):
            return True
        if PUNCT_ONLY_RE.match(tok):
            return False
        return True

    @staticmethod
    def tokenize(text: str) -> List[str]:
        if not text:
            return []
        if jieba is not None:
            raw_tokens = [w.strip().lower() for w in jieba.cut(text) if w.strip()]
            return [t for t in raw_tokens if ChineseTokenizer._is_valid_token(t)]

        # 降级分词：提取连续英文/数字编号及连续中文片段，并为中文片段构建双字/三字 N-Gram
        tokens: List[str] = []
        for m in re.finditer(r"[a-zA-Z0-9_\-\.\#\/]+|[\u4e00-\u9fa5]+", text.lower()):
            seg = m.group(0)
            if TECH_TOKEN_RE.search(seg):
                if ChineseTokenizer._is_valid_token(seg):
                    tokens.append(seg)
            else:
                # 连续中文串：生成双字 bigram（过滤停用词），兼顾召回率与精确度
                if len(seg) == 1:
                    if ChineseTokenizer._is_valid_token(seg):
                        tokens.append(seg)
                else:
                    for i in range(len(seg) - 1):
                        bg = seg[i:i + 2]
                        if ChineseTokenizer._is_valid_token(bg):
                            tokens.append(bg)
        return tokens


class PurePythonBM25:
    """纯 Python BM25Okapi 实现（当系统未预装 rank_bm25 时零依赖兜底）。"""

    def __init__(self, corpus: List[List[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_size = len(corpus)
        self.avgdl = sum(len(doc) for doc in corpus) / max(self.corpus_size, 1)
        self.doc_freqs: List[Dict[str, int]] = []
        self.idf: Dict[str, float] = {}
        self.doc_len: List[int] = []

        df: Dict[str, int] = {}
        for doc in corpus:
            self.doc_len.append(len(doc))
            frequencies: Dict[str, int] = {}
            for word in doc:
                frequencies[word] = frequencies.get(word, 0) + 1
            self.doc_freqs.append(frequencies)
            for word in frequencies:
                df[word] = df.get(word, 0) + 1

        for word, freq in df.items():
            self.idf[word] = math.log(1 + (self.corpus_size - freq + 0.5) / (freq + 0.5))

    def get_scores(self, query: List[str]) -> List[float]:
        """对整条语料打分，返回与语料同序的分数数组。O(查询词数 × 文档数)。"""
        scores = [0.0] * self.corpus_size
        for word in query:
            if word not in self.idf:
                continue
            idf_val = self.idf[word]
            for i, doc_freq in enumerate(self.doc_freqs):
                if word in doc_freq:
                    freq = doc_freq[word]
                    numerator = idf_val * freq * (self.k1 + 1)
                    denominator = freq + self.k1 * (1 - self.b + self.b * (self.doc_len[i] / max(self.avgdl, 1e-6)))
                    scores[i] += numerator / max(denominator, 1e-6)
        return scores
