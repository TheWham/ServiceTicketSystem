"""中文分词与纯 Python BM25 兜底实现。"""

import re
import math
from typing import List, Dict

try:
    import jieba
except ImportError:
    jieba = None


class ChineseTokenizer:
    """轻量稳健中文分词器（优先使用 jieba，未安装时自适应正则与 N-gram 切词）。

    为什么 BM25 通道必须先分词：BM25 基于"词项是否命中"打分，中文没有天然空格，
    必须先切成词项；且专有编号（错误码/命令/端口）要作为完整 token 保留，
    否则字面硬匹配优势尽失。
    """

    @staticmethod
    def tokenize(text: str) -> List[str]:
        if not text:
            return []
        if jieba is not None:
            return [w.strip() for w in jieba.cut(text) if w.strip()]
        
        # 降级分词：提取中文字符串、连续英文单词及专有名词编号
        pattern = re.compile(r"[a-zA-Z0-9_\-\.\#]+|[\u4e00-\u9fa5]")
        tokens = pattern.findall(text)
        
        # 为单字构建双字 N-Gram 提升检索召回
        ngrams = []
        for i in range(len(tokens) - 1):
            if len(tokens[i]) == 1 and len(tokens[i+1]) == 1:
                ngrams.append(tokens[i] + tokens[i+1])
        return tokens + ngrams


class PurePythonBM25:
    """纯 Python BM25Okapi 实现（当系统未预装 rank_bm25 时零依赖兜底）。

    BM25 打分三要素：
      - TF（词频）：查询词在文档中出现越多越相关，用 k1 做饱和衰减；
      - IDF（逆文档频率）：越稀有的词权重越高（"806"远比"故障"珍贵）；
      - 长度归一化（b）：长文档不因字数多被额外加分。
    参数约定：k1=1.5 控制词频饱和度，b=0.75 控制长度归一化强度（工业常用默认）。
    """

    def __init__(self, corpus: List[List[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_size = len(corpus)
        self.avgdl = sum(len(doc) for doc in corpus) / max(self.corpus_size, 1)
        self.doc_freqs: List[Dict[str, int]] = []
        self.idf: Dict[str, float] = {}
        self.doc_len: List[int] = []

        # 统计每篇文档的词频（TF）与每个词出现在几篇文档（DF）
        df: Dict[str, int] = {}
        for doc in corpus:
            self.doc_len.append(len(doc))
            frequencies: Dict[str, int] = {}
            for word in doc:
                frequencies[word] = frequencies.get(word, 0) + 1
            self.doc_freqs.append(frequencies)
            for word in frequencies:
                df[word] = df.get(word, 0) + 1

        # 预计算每个词的 IDF（只算一次，检索时直接查表）
        for word, freq in df.items():
            self.idf[word] = math.log(1 + (self.corpus_size - freq + 0.5) / (freq + 0.5))

    def get_scores(self, query: List[str]) -> List[float]:
        """对整条语料打分，返回与语料同序的分数数组。O(查询词数 × 文档数)。"""
        scores = [0.0] * self.corpus_size
        for word in query:
            if word not in self.idf:
                continue  # 未在语料出现的词直接跳过，不贡献分数
            idf_val = self.idf[word]
            for i, doc_freq in enumerate(self.doc_freqs):
                if word in doc_freq:
                    freq = doc_freq[word]
                    numerator = idf_val * freq * (self.k1 + 1)
                    denominator = freq + self.k1 * (1 - self.b + self.b * (self.doc_len[i] / max(self.avgdl, 1e-6)))
                    scores[i] += numerator / max(denominator, 1e-6)
        return scores


# ==============================================================================
# 1. KSP Cross-Encoder 重排模型适配器 (qwen3-reranker-8b / 启发式兜底)
# ==============================================================================

