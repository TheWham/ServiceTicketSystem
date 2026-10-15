"""Wiki 卡片集合内容指纹（供 manifest 语料一致性校验）。"""

import hashlib
from pathlib import Path
from typing import List


def compute_wiki_fingerprint(wiki_files: List[Path]) -> str:
    """对 Wiki 卡片集合计算内容指纹（文件名+内容 sha1）。

    用途：检索评测加载持久化向量库前比对 manifest——若清洗流水线重跑或卡片被改，
    旧库里的 embedding 已与当前语料不一致，必须重建，否则 Dense（旧文本）与
    BM25（运行时新切块）两路召回的不是同一批 chunk，RRF 按 page_content 去重失效。
    """
    h = hashlib.sha1()
    for f in sorted(wiki_files, key=lambda p: p.name):
        h.update(f.name.encode("utf-8"))
        h.update(f.read_bytes())
    return h.hexdigest()


