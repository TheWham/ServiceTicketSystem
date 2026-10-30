"""轻量 GraphRAG POC：NetworkX 内存图 + 实体三元组 + 多跳子图遍历。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import networkx as nx
from pydantic import BaseModel, Field


class Triple(BaseModel):
    """一条实体关系三元组。"""

    head: str = Field(description="头实体/主语")
    relation: str = Field(description="关联关系/谓词")
    tail: str = Field(description="尾实体/宾语")
    context_snippet: str = Field(default="", description="抽取该三元组的原文佐证")


ALIASES = {
    "华科智造": "华科智造",
    "本公司": "华科智造",
    "公司": "华科智造",
    "我司": "华科智造",
    "陈主任": "陈梓豪",
    "监察委主任陈梓豪": "陈梓豪",
    "监察委员会主任陈梓豪": "陈梓豪",
    "副主任赵小雪": "赵小雪",
    "监察委员会副主任赵小雪": "赵小雪",
    "交付总监王大明": "王大明",
}


def canonicalize(entity: str) -> str:
    """按讲义要求做最小实体消歧，避免同一实体分裂成多个节点。"""

    normalized = entity.strip()
    return ALIASES.get(normalized, normalized)


class LightKnowledgeGraph:
    """基于 NetworkX MultiDiGraph 的轻量知识图谱。"""

    def __init__(self) -> None:
        self.graph = nx.MultiDiGraph()

    def add_triple(self, triple: Triple) -> None:
        head = canonicalize(triple.head)
        relation = triple.relation.strip()
        tail = canonicalize(triple.tail)
        if not head or not relation or not tail:
            raise ValueError(f"三元组字段不能为空: {triple!r}")
        self.graph.add_edge(
            head,
            tail,
            relation=relation,
            context_snippet=triple.context_snippet,
        )

    def add_triples(self, triples: list[Triple]) -> None:
        for triple in triples:
            self.add_triple(triple)

    def extract_subgraph_facts(self, seed_entities: list[str], max_hops: int = 2) -> list[str]:
        """从种子实体出发，双向 BFS 抽取 k-Hop 内的事实边。"""

        visited_nodes: set[str] = set()
        matched_facts: list[str] = []

        for entity in seed_entities:
            seed = canonicalize(entity)
            if not self.graph.has_node(seed):
                continue

            current_layer = {seed}
            visited_nodes.add(seed)

            for _ in range(max_hops):
                next_layer: set[str] = set()
                for node in current_layer:
                    for _, target, edge_data in self.graph.out_edges(node, data=True):
                        fact = self._format_fact(node, target, edge_data, reverse=False)
                        if fact not in matched_facts:
                            matched_facts.append(fact)
                        if target not in visited_nodes:
                            next_layer.add(target)
                            visited_nodes.add(target)

                    for source, _, edge_data in self.graph.in_edges(node, data=True):
                        fact = self._format_fact(source, node, edge_data, reverse=True)
                        if fact not in matched_facts:
                            matched_facts.append(fact)
                        if source not in visited_nodes:
                            next_layer.add(source)
                            visited_nodes.add(source)

                current_layer = next_layer
                if not current_layer:
                    break

        return matched_facts

    @staticmethod
    def _format_fact(
        source: str,
        target: str,
        edge_data: dict[str, Any],
        *,
        reverse: bool,
    ) -> str:
        relation = edge_data.get("relation", "关联")
        prefix = "【反向事实】" if reverse else "【事实关系】"
        return f"{prefix}{source} ──({relation})──> {target}"

    def summary(self) -> dict[str, Any]:
        graph = self.graph
        weak_components = list(nx.weakly_connected_components(graph))
        degrees = dict(graph.degree())
        return {
            "node_count": graph.number_of_nodes(),
            "edge_count": graph.number_of_edges(),
            "weak_component_count": len(weak_components),
            "weak_components": [sorted(component) for component in weak_components],
            "degree": dict(sorted(degrees.items(), key=lambda item: (-item[1], item[0]))),
        }


RAW_TEXT = """
华科智造《多组织架构与跨部门审批流转制度》规定：周建华是华东交付一部的现场驻场实施组长，
其日常报销由交付总监王大明审批。若单笔金额超过 2 万元，或审批人与申请人为同一研发项目
利益相关方，必须由监察委员会主任陈梓豪联签代审。监察委员会 2024 年新增规定：若主任陈梓豪
出差，由副主任赵小雪执行最终否决权。周建华在华东项目申报了一笔 3 万元驻场补贴。
""".strip()


TRIPLES = [
    Triple(head="华科智造", relation="制定", tail="多组织架构与跨部门审批流转制度"),
    Triple(head="周建华", relation="隶属于", tail="华东交付一部"),
    Triple(head="周建华", relation="任职于", tail="现场驻场实施组长"),
    Triple(head="现场驻场实施组长", relation="直属主管", tail="王大明"),
    Triple(head="周建华", relation="直属主管", tail="王大明"),
    Triple(head="王大明", relation="职务", tail="交付总监"),
    Triple(head="王大明", relation="审批权限", tail="日常报销"),
    Triple(head="王大明", relation="利益回避转派", tail="陈梓豪"),
    Triple(head="多组织架构与跨部门审批流转制度", relation="规定", tail="大额申报利益冲突时转派监察委员会"),
    Triple(head="大额申报利益冲突时转派监察委员会", relation="触发条件", tail="单笔金额超过2万元"),
    Triple(head="大额申报利益冲突时转派监察委员会", relation="触发条件", tail="审批人与申请人存在利益冲突"),
    Triple(head="大额申报利益冲突时转派监察委员会", relation="主管审核人", tail="陈梓豪"),
    Triple(head="陈梓豪", relation="职务", tail="监察委员会主任"),
    Triple(head="监察委员会", relation="发布", tail="2024年新增规定"),
    Triple(head="2024年新增规定", relation="规定", tail="主任出差时由副主任执行最终否决权"),
    Triple(head="陈梓豪", relation="出差代签授权人", tail="赵小雪"),
    Triple(head="赵小雪", relation="职务", tail="监察委员会副主任"),
    Triple(head="赵小雪", relation="权限", tail="最终否决权"),
    Triple(head="周建华", relation="申报", tail="3万元驻场补贴"),
    Triple(head="3万元驻场补贴", relation="所属项目", tail="华东项目"),
    Triple(head="华东项目", relation="归属", tail="华东交付一部"),
    Triple(head="监察委员会", relation="负责", tail="合规回避与代签规则"),
]


def build_demo_graph() -> LightKnowledgeGraph:
    graph = LightKnowledgeGraph()
    graph.add_triples(TRIPLES)
    return graph


def export_graph(graph: LightKnowledgeGraph, export_dir: Path) -> dict[str, str]:
    export_dir.mkdir(parents=True, exist_ok=True)
    triples_path = export_dir / "light_graphrag_triples.json"
    graphml_path = export_dir / "light_graphrag_graph.graphml"

    payload = {
        "raw_text": RAW_TEXT,
        "triples": [triple.model_dump() for triple in TRIPLES],
        "summary": graph.summary(),
    }
    triples_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    nx.write_graphml(graph.graph, graphml_path)
    return {"triples": str(triples_path), "graphml": str(graphml_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Day22 轻量 GraphRAG NetworkX POC")
    parser.add_argument("--max-hops", type=int, default=2, help="子图遍历最大跳数")
    parser.add_argument(
        "--seed",
        nargs="*",
        default=["周建华", "陈梓豪"],
        help="种子实体，默认: 周建华 陈梓豪",
    )
    parser.add_argument(
        "--export-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "artifacts" / "graph",
        help="导出目录",
    )
    args = parser.parse_args()

    graph = build_demo_graph()
    summary = graph.summary()

    print("=" * 80)
    print("Day22 轻量 GraphRAG：NetworkX 实体三元组图谱")
    print("=" * 80)
    print(f"节点数: {summary['node_count']}")
    print(f"关系边数: {summary['edge_count']}")
    print(f"弱连通分量数: {summary['weak_component_count']}")
    print("\n节点度数:")
    for node, degree in summary["degree"].items():
        print(f"  - {node}: {degree}")

    print(f"\n{args.max_hops}-Hop 子图事实链，种子实体: {', '.join(args.seed)}")
    facts = graph.extract_subgraph_facts(args.seed, max_hops=args.max_hops)
    for fact in facts:
        print(f"  - {fact}")

    exported = export_graph(graph, args.export_dir)
    print("\n导出文件:")
    for label, path in exported.items():
        print(f"  - {label}: {path}")


if __name__ == "__main__":
    main()
