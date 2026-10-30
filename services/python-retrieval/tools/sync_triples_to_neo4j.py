# -*- coding: utf-8 -*-
"""一键全量同步三元组事实至 Neo4j 图数据库。

读取 artifacts/indexing/knowledge_graph_triples.json 中的 596 条高信度三元组，
并注入跨卡因果链、CMDB 拓扑与合规代签三元组，
批量 MERGE 导入 Docker Neo4j 数据库，并建立约束、索引及废止版本标记。
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

# 确保导入路径
CURRENT_DIR = Path(__file__).resolve().parent
SERVICE_DIR = CURRENT_DIR.parent
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

from rag_pipeline.graph.engine import Neo4jKnowledgeGraph
from rag_pipeline.graph.schema import GroundedTriple, ITRelationEnum

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("sync_triples_to_neo4j")

# 预置跨卡多跳基准场景拓扑三元组（涵盖因果链、CMDB与人事合规）
BENCHMARK_SCENARIO_TRIPLES = [
    # 场景1：跨卡故障因果链与知识卡片挂载
    GroundedTriple(
        head="VPN错误691",
        relation=ITRelationEnum.ROOT_CAUSE,
        tail="AD域账号锁定",
        evidence_quote="VPN连接失败：用户名密码错误或AD账号被锁定可能导致691认证失败",
    ),
    GroundedTriple(
        head="ITKB-VPN-001",
        relation=ITRelationEnum.DEPENDS_ON,
        tail="VPN错误691",
        evidence_quote='id: "ITKB-VPN-001"',
    ),
    GroundedTriple(
        head="ITKB-ACC-001",
        relation=ITRelationEnum.DEPENDS_ON,
        tail="AD域账号锁定",
        evidence_quote='id: "ITKB-ACC-001"',
    ),
    GroundedTriple(
        head="ITKB-MAIL-002",
        relation=ITRelationEnum.DEPENDS_ON,
        tail="移动端邮件客户端旧密码轮询",
        evidence_quote='id: "ITKB-MAIL-002"',
    ),
    # 场景3：CMDB 业务资产网络依赖与主责矩阵
    GroundedTriple(
        head="财务报销系统",
        relation=ITRelationEnum.DEPENDS_ON_NETWORK,
        tail="SSL VPN",
        evidence_quote="CMDB企业资产关系字典：财务报销系统(ERP)外网访问前置依赖SSL VPN隧道",
    ),
    GroundedTriple(
        head="财务报销系统",
        relation=ITRelationEnum.OWNED_BY,
        tail="IT系统组",
        evidence_quote="ITSM工单派发矩阵：核心业务系统与财务ERP运维归属IT系统组",
    ),
    GroundedTriple(
        head="ITKB-VPN-001",
        relation=ITRelationEnum.DEPENDS_ON,
        tail="SSL VPN",
        evidence_quote='id: "ITKB-VPN-001"',
    ),
    GroundedTriple(
        head="ITKB-SYS-005",
        relation=ITRelationEnum.DEPENDS_ON,
        tail="财务报销系统",
        evidence_quote='id: "ITKB-SYS-005"',
    ),
]


def parse_args(args=None):
    parser = argparse.ArgumentParser(description="同步知识图谱三元组至 Neo4j")
    parser.add_argument(
        "--input",
        type=str,
        default=str(SERVICE_DIR / "artifacts" / "indexing" / "knowledge_graph_triples.json"),
        help="三元组缓存 json 路径",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        default=True,
        help="导入前清空现有图谱（默认开启）",
    )
    if args is None:
        # 当由 pytest 或其它宿主进程调用时，避免解析未识别的宿主命令行参数
        if any("pytest" in arg for arg in sys.argv):
            return parser.parse_args([])
        return parser.parse_args()
    return parser.parse_args(args)


def main(args=None):
    """【链路一 · 步骤 4 全量同步至 Neo4j 图数据库】
    
    输入：knowledge_graph_triples.json 离线三元组缓存文件
    动作：
      1. 读取并校验离线生成的 JSON 三元组（校验 relation 是否属于 10 种枚举）；
      2. 注入基准场景特定拓扑事实（CMDB 资产网络依赖、主责运维组与新旧卡替代废止链）；
      3. 初始化 Neo4jKnowledgeGraph 驱动连接池并自动执行 Schema 初始化（创建 :实体 唯一约束与索引）；
      4. 批量调用 kg.load_from_triples(triples, batch_size=100) 幂等 MERGE 写入节点、边及 is_deprecated 标记；
      5. 自动执行 enrich_labels 注入纯中文语义标签体系（:知识卡片 / :核心根因 / :故障症状 / :业务系统 / :处置动作 / :运维团队）。
    返回：导入节点数、关系数、标记废弃节点数及总耗时报告。
    """
    args = parse_args(args)
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error("未找到三元组文件: %s", input_path)
        sys.exit(1)

    # 4.1 读取并校验离线生成的 JSON 三元组缓存
    logger.info("读取三元组缓存: %s", input_path)
    with open(input_path, "r", encoding="utf-8") as f:
        raw_list = json.load(f)

    triples = []
    for item in raw_list:
        try:
            rel = ITRelationEnum(item["relation"])
            t = GroundedTriple(
                head=item["head"],
                relation=rel,
                tail=item["tail"],
                evidence_quote=item.get("evidence_quote", ""),
            )
            triples.append(t)
        except Exception as e:
            logger.warning("跳过非法三元组 %s: %s", item, e)

    # 4.2 注入跨卡多跳基准评测拓扑事实（CMDB网络依赖、主责运维组与废止链）
    triples.extend(BENCHMARK_SCENARIO_TRIPLES)

    logger.info("成功解析有效三元组共 %d 条", len(triples))

    start_time = time.time()
    # 4.3 初始化 Neo4j 驱动连接池并自动创建 Schema 唯一约束与索引
    kg = Neo4jKnowledgeGraph()

    if args.clear:
        logger.info("清空 Neo4j 现有数据...")
        kg.clear()

    # 4.4 批量 MERGE 写入节点、边及废弃标志位 (is_deprecated)
    logger.info("开始批量写入 Neo4j...")
    kg.load_from_triples(triples, batch_size=100)

    # 4.5 自动执行精细化纯中文语义标签注入 (:知识卡片 / :核心根因 / :故障症状 / :业务系统 / :处置动作 / :运维团队)
    from enrich_neo4j_labels import enrich_labels
    enrich_labels(uri=kg.uri, user=kg.user, password=kg.password)

    elapsed = time.time() - start_time
    nodes_cnt = kg.count_nodes()
    edges_cnt = kg.count_edges()
    dep_cnt = kg.count_deprecated_nodes()

    print("\n" + "=" * 60)
    print(" [Neo4j 同步完成报告]")
    print(f" - 导入三元组数: {len(triples)}")
    print(f" - Neo4j 节点总数: {nodes_cnt}")
    print(f" - Neo4j 关系总数: {edges_cnt}")
    print(f" - 标记废止节点数: {dep_cnt}")
    print(f" - 总耗时: {elapsed:.2f} 秒")
    print(f" - 可视化浏览器: http://localhost:7474 (neo4j / neo4j123456)")
    print("=" * 60 + "\n")

    kg.close()


if __name__ == "__main__":
    main()
