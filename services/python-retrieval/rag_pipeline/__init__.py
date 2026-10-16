"""rag_pipeline — RAG 数据治理与检索全链路包。

模块地图：
  config      统一配置中心（configs/pipeline.yaml 加载 + 指纹 + 切块器工厂）
  ingestion   04 清洗生成（docx -> Wiki 卡片）
  chunking    切块（父子切片 / 结构感知 / 朴素基线 / 指纹）
  embedding   KSP 嵌入提供者
  store       Chroma 向量库管理（含 manifest）
  retrieval   检索（分词 / BM25 / Reranker / 混合检索器）
  evaluation  评测（题集 / 报告 / 黄金集评测引擎 golden）
  pipelines   索引构建 / 四轨检索评测 / 黄金集评测 主流水线入口
"""
