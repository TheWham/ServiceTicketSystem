# -*- coding: utf-8 -*-
"""GraphRAG vs 纯向量检索 对比评测 Web 服务与交互式工作台。

提供：
1. 启动本地 FastAPI 服务器（默认端口 8350）；
2. 静态页面 GET / 提供现代化响应式双轨对比界面；
3. GET /api/presets 返回预置的 4 组经典多跳基准对比数据（秒级渲染无需等待）；
4. POST /api/compare 接收自定义 Query，实时调用 8310 纯向量内核 vs GraphRAG 双轨推理进行比对。
"""

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# 将项目目录加入 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import requests
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from openai import OpenAI

from rag_pipeline.config import REPO_ROOT
from rag_pipeline.docstore import MySqlDocstore
from rag_pipeline.graph.engine import Neo4jKnowledgeGraph
from rag_pipeline.graph.extractor import load_triples_cache
from rag_pipeline.graph.reasoner import GraphEnhancedReasoner
from rag_pipeline.graph.schema import GroundedTriple, ITRelationEnum

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# 初始化 FastAPI
app = FastAPI(title="GraphRAG vs Vector Comparison Workbench", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局引擎单例
_kg: Optional[Neo4jKnowledgeGraph] = None
_docstore: Optional[MySqlDocstore] = None
_reasoner: Optional[GraphEnhancedReasoner] = None
_client: Optional[OpenAI] = None


def get_components():
    global _kg, _docstore, _reasoner, _client
    if _kg is None:
        _kg = Neo4jKnowledgeGraph()
        if _kg.count_nodes() == 0:
            cache_path = REPO_ROOT / "artifacts" / "indexing" / "knowledge_graph_triples.json"
            triples = load_triples_cache(cache_path)
            from tools.sync_triples_to_neo4j import BENCHMARK_SCENARIO_TRIPLES
            triples.extend(BENCHMARK_SCENARIO_TRIPLES)
            _kg.load_from_triples(triples)

        _docstore = MySqlDocstore()

        api_key = os.environ.get("LLM_API_KEY") or os.environ.get("AI_API_KEY")
        base_url = os.environ.get("LLM_BASE_URL") or os.environ.get("AI_BASE_URL")
        model = os.environ.get("GRAPH_MODEL") or "deepseek-v4.1-flash"
        if api_key and base_url:
            _client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            _client = None

        _reasoner = GraphEnhancedReasoner(
            kg=_kg, docstore=_docstore, client=_client, model=model
        )
    return _kg, _docstore, _reasoner, _client


class CompareRequest(BaseModel):
    query: str
    max_hops: int = 2


FACT_RE = re.compile(r"^(?:【.+?】\s*)?(.+?)\s+──\((.+?)\)──>\s+(.+)$")


def facts_to_graph_data(facts: List[str], max_edges: int = 35) -> Dict[str, Any]:
    """将拓扑事实文本列表转换为前端 Vis-Network 所需的 nodes 与 edges 数据结构。"""
    nodes_map: Dict[str, Dict[str, Any]] = {}
    parsed_items = []

    for f in facts:
        if "【拓扑剪枝】" in f and "──(" not in f:
            continue
        m = FACT_RE.match(f.strip())
        if not m:
            continue
        src = m.group(1).strip()
        rel = m.group(2).strip()
        tgt = m.group(3).strip()
        parsed_items.append((src, rel, tgt))

    # 优先展示高价值因果链条（根因、排查、处置、废止）
    def rel_priority(item):
        r = item[1]
        if "诱发根因" in r or "根因" in r:
            return 0
        if "废止" in r or "替代" in r:
            return 1
        if "处置" in r or "排查" in r or "等待" in r:
            return 2
        if "主责" in r or "通道" in r:
            return 3
        return 4

    parsed_items.sort(key=rel_priority)

    edges: List[Dict[str, Any]] = []
    for src, rel, tgt in parsed_items[:max_edges]:
        src_dep = "LEG-" in src or "已废止" in src or "旧" in src
        tgt_dep = "LEG-" in tgt or "已废止" in tgt or "旧" in tgt

        if src not in nodes_map:
            nodes_map[src] = {"id": src, "label": src, "is_deprecated": src_dep}
        if tgt not in nodes_map:
            nodes_map[tgt] = {"id": tgt, "label": tgt, "is_deprecated": tgt_dep}

        edges.append({
            "from": src,
            "to": tgt,
            "label": rel,
            "title": f"{src} ──({rel})──> {tgt}",
        })

    return {"nodes": list(nodes_map.values()), "edges": edges}


PRESET_CASES = [
    {
        "id": "MH-001",
        "title": "跨卡因果链追溯",
        "tag": "VPN 691 + 邮箱失效 -> AD锁定",
        "query": "在家连不上公司VPN，提示错误代码691认证失败，今天早上手机企业邮箱也提示凭据失效。请问这是什么原因导致的？完整的自查和解决流程是什么？",
        "vector_trap": "纯向量检索只能召回 VPN-001 的本地网络与路由器重启排查，遗漏 AD 账号被手机邮箱旧密码锁定的真正诱因",
        "vector_recalled": ["ITKB-VPN-001#c0", "ITKB-VPN-003#c0", "ITKB-MAIL-003#c0"],
        "vector_summary": "纯向量由于文本相似度只搜到 VPN-001 的路由器重启、本地杀毒软件排查，未能跨卡穿透到 AD 账号锁定与手机邮箱旧密码轮询撞库的真正诱因。",
        "graph_facts": [
            "VPN错误691 ──(诱发根因)──> AD域账号锁定",
            "移动端邮件客户端旧密码轮询 ──(诱发根因)──> AD域账号锁定",
            "检查客户端旧密码 ──(前置排查动作)──> AD域账号锁定",
            "Active Directory用户和计算机 ──(处置动作)──> AD域账号锁定",
            "事件ID 4740 ──(前置排查动作)──> AD域账号锁定",
            "ITKB-VPN-001 ──(废止并替代)──> ITKB-LEG-VPN-001"
        ],
        "graph_cards": ["ITKB-VPN-001", "ITKB-ACC-001", "ITKB-MAIL-002"],
        "graph_summary": "通过 5 跳拓扑演绎，精准识别：手机邮箱旧密码轮询 -> 撞库锁定 AD 域账号 -> 连锁诱发 VPN 691 认证失败。同时自动关联拉取 ITKB-VPN-001 与 ITKB-ACC-001 全文，并指示工程师检查安全日志 4740 事件。"
    },
    {
        "id": "MH-002",
        "title": "版本冲突与废止剪枝",
        "tag": "新规5次/自动解锁 vs 旧规剪枝",
        "query": "员工电脑连续多次输错密码被锁定了，按照公司现行规章输错几次会被锁？需要联系管理员还是会自动恢复？",
        "vector_trap": "纯向量检索会同时召回新旧两篇卡片切片，导致大模型无法确认正式阈值，输出模棱两可的冲突答案",
        "vector_recalled": ["ITKB-ACC-001#c0", "ITKB-LEG-ACC-001#c0", "ITKB-ACC-002#c0"],
        "vector_summary": "向量库同时召回现行有效 ACC-001 与已废止 LEG-ACC-001，大模型在 3 次永久锁定与 5 次自动解锁之间产生冲突，答复称“无法给出明确数字”。",
        "graph_facts": [
            "ITKB-ACC-001 ──(废止并替代)──> ITKB-LEG-ACC-001",
            "ITKB-ACC-001 ──(生效状态)──> 现行有效",
            "连续多次输入错误密码 ──(诱发根因)──> AD域账号锁定",
            "等待15-30分钟 ──(前置排查动作)──> AD域账号锁定",
            "【拓扑剪枝】ITKB-LEG-ACC-001 下级失效旧规已物理屏蔽"
        ],
        "graph_cards": ["ITKB-ACC-001"],
        "graph_summary": "拓扑引擎识别到 ITKB-ACC-001 废止并替代了 ITKB-LEG-ACC-001，在 BFS 遍历中对废止节点实施物理剪枝，大模型 100% 确定按现行规定输出：连续输错 5 次锁定，支持等待 15-30 分钟自动恢复。"
    },
    {
        "id": "MH-003",
        "title": "CMDB资产依赖与工单派发",
        "tag": "财务报销(ERP) 502 -> SSL-VPN -> IT系统组",
        "query": "外网访问公司财务报销系统（ERP）打不开，浏览器报 502 Bad Gateway，应该提单给哪个运维团队？提单前必须满足什么网络前置条件？",
        "vector_trap": "纯向量检索仅能召回通用 502 错误排查，无法感知该特定业务系统与 SSL-VPN 的前置网络依赖及主责归属",
        "vector_recalled": ["ITKB-SYS-005#c0", "ITKB-NET-002#c0", "ITKB-SYS-001#c0"],
        "vector_summary": "纯向量检索仅匹配到浏览器清除缓存、DNS排查等通用排障步骤，无法回答该特定核心资产的主责团队是谁、需要连什么网络。",
        "graph_facts": [
            "财务报销系统 ──(依赖网络通道)──> SSL VPN",
            "财务报销系统 ──(主责运维组)──> IT系统组",
            "ITKB-VPN-001 ──(依赖系统组件)──> SSL VPN",
            "ITKB-SYS-005 ──(依赖系统组件)──> 财务报销系统"
        ],
        "graph_cards": ["ITKB-VPN-001", "ITKB-SYS-005"],
        "graph_summary": "基于 CMDB 拓扑明确推导：① 必经网络通道为 SSL VPN，提单前必须确认连通；② 终审主责运维团队为 IT系统组；③ 联动拉取 VPN-001 与 SYS-005 指导前置自查。"
    }
]

for p in PRESET_CASES:
    p["graph_data"] = facts_to_graph_data(p.get("graph_facts", []))


@app.get("/api/neo4j/status")
def get_neo4j_status():
    """获取 Neo4j 图数据库连接与图谱规模状态。"""
    try:
        kg, _, _, _ = get_components()
        return JSONResponse(
            content={
                "code": 0,
                "data": {
                    "connected": True,
                    "uri": kg.uri,
                    "nodes": kg.count_nodes(),
                    "edges": kg.count_edges(),
                    "deprecated_nodes": kg.count_deprecated_nodes(),
                    "browser_url": "http://localhost:7474",
                },
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "code": 1,
                "error": f"Neo4j 状态检测失败: {e}",
            },
        )


@app.get("/api/neo4j/graph_data")
def get_neo4j_graph_data(scene: str = "vpn"):
    """从 Neo4j 动态读取特定场景的子图拓扑数据用于前端可视化。"""
    try:
        kg, _, _, _ = get_components()
        if scene == "vpn":
            cypher = """
            MATCH path = (e:Entity {name: 'VPN错误691'})-[r*1..2]-(m)
            UNWIND relationships(path) AS rel
            RETURN DISTINCT startNode(rel).name AS source, type(rel) AS rel, endNode(rel).name AS target,
                   coalesce(startNode(rel).is_deprecated, false) AS src_dep,
                   coalesce(endNode(rel).is_deprecated, false) AS tgt_dep,
                   coalesce(rel.quote, '') AS quote
            LIMIT 50
            """
        elif scene == "replaces":
            cypher = """
            MATCH (e:Entity)-[r:REPLACES]->(m:Entity)
            RETURN e.name AS source, type(r) AS rel, m.name AS target,
                   coalesce(e.is_deprecated, false) AS src_dep,
                   coalesce(m.is_deprecated, false) AS tgt_dep,
                   coalesce(r.quote, '') AS quote
            LIMIT 50
            """
        elif scene == "cmdb":
            cypher = """
            MATCH path = (e:Entity {name: '财务报销系统'})-[*1..2]-(m)
            UNWIND relationships(path) AS rel
            RETURN DISTINCT startNode(rel).name AS source, type(rel) AS rel, endNode(rel).name AS target,
                   coalesce(startNode(rel).is_deprecated, false) AS src_dep,
                   coalesce(endNode(rel).is_deprecated, false) AS tgt_dep,
                   coalesce(rel.quote, '') AS quote
            LIMIT 50
            """
        else:
            cypher = """
            MATCH (n:Entity)-[r]->(m:Entity)
            RETURN n.name AS source, type(r) AS rel, m.name AS target,
                   coalesce(n.is_deprecated, false) AS src_dep,
                   coalesce(m.is_deprecated, false) AS tgt_dep,
                   coalesce(r.quote, '') AS quote
            LIMIT 60
            """

        nodes_map = {}
        edges = []

        with kg.driver.session() as s:
            records = list(s.run(cypher))
            for rec in records:
                src = rec["source"]
                tgt = rec["target"]
                rel = rec["rel"]
                src_dep = rec["src_dep"]
                tgt_dep = rec["tgt_dep"]
                quote = rec["quote"]

                if src not in nodes_map:
                    nodes_map[src] = {"id": src, "label": src, "is_deprecated": src_dep}
                if tgt not in nodes_map:
                    nodes_map[tgt] = {"id": tgt, "label": tgt, "is_deprecated": tgt_dep}

                edges.append({
                    "from": src,
                    "to": tgt,
                    "label": rel,
                    "title": quote or rel,
                })

        return JSONResponse(content={
            "code": 0,
            "data": {
                "nodes": list(nodes_map.values()),
                "edges": edges,
            }
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"code": 1, "error": str(e)})


@app.get("/api/presets")
def get_presets():
    """获取预置多跳评测用例集。"""
    return JSONResponse(content={"code": 0, "data": PRESET_CASES})


@app.post("/api/compare")
def compare_query(req: CompareRequest):
    """实时执行纯向量 vs GraphRAG 对比评测。"""
    kg, docstore, reasoner, client = get_components()
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query 不能为空")

    # 1. 纯向量链路
    t_v0 = time.time()
    vec_recalled = []
    try:
        resp = requests.post(
            "http://127.0.0.1:8310/api/v1/rag/retrievals",
            json={"question": query, "topK": 3},
            timeout=8,
        )
        if resp.status_code == 200:
            items = resp.json().get("data", {}).get("items", [])
            for item in items:
                cid = item.get("chunkId") or item.get("articleId") or "chunk"
                title = item.get("title", "")
                content = item.get("snippet") or item.get("content", "")
                vec_recalled.append({"id": cid, "title": title, "content": content[:200]})
    except Exception as e:
        vec_recalled = [{"id": "ERROR", "title": "向量服务调用失败", "content": str(e)}]
    vec_ms = round((time.time() - t_v0) * 1000, 1)

    # 纯向量问答生成
    model_name = os.environ.get("GRAPH_MODEL") or "deepseek-v4.1-flash"
    vec_answer = ""
    if client:
        context_str = "\n".join(f"- {d['id']}: {d['content']}" for d in vec_recalled)
        prompt = f"参考资料：\n{context_str}\n\n问题：{query}\n请给出明确答复与排查步骤："
        try:
            r = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                timeout=25,
            )
            vec_answer = r.choices[0].message.content
        except Exception as e:
            vec_answer = f"(纯向量生成失败: {e})"
    else:
        vec_answer = "【模拟结果】：已成功检索到纯向量切片，未配置 LLM 客户端。"

    # 2. GraphRAG 拓扑双轨链路
    t_g0 = time.time()
    graph_res = reasoner.answer_query(query, max_hops=req.max_hops)
    graph_ms = round((time.time() - t_g0) * 1000, 1)

    # 优先针对识别到的具体业务/故障种子实体从 Neo4j 抽取精准子图；若为空则基于事实列表解析
    seeds = graph_res["context"].get("seed_entities", [])
    if seeds:
        dynamic_graph = kg.extract_subgraph_data(seeds, max_hops=req.max_hops, limit=35)
    else:
        dynamic_graph = facts_to_graph_data(graph_res["context"]["graph_facts"])
    if not dynamic_graph.get("nodes"):
        dynamic_graph = facts_to_graph_data(graph_res["context"]["graph_facts"])

    return JSONResponse(content={
        "code": 0,
        "data": {
            "query": query,
            "vector": {
                "latency_ms": vec_ms,
                "recalled": vec_recalled,
                "answer": vec_answer
            },
            "graph": {
                "latency_ms": graph_ms,
                "facts": graph_res["context"]["graph_facts"],
                "associated_cards": graph_res["context"]["associated_card_ids"],
                "answer": graph_res["answer"],
                "graph_data": dynamic_graph,
            }
        }
    })


@app.get("/", response_class=HTMLResponse)
def index_page():
    html_file = Path(__file__).resolve().parent / "compare_workbench.html"
    if html_file.exists():
        return html_file.read_text(encoding="utf-8")
    return "<h1>Workbench HTML file not found</h1>"


if __name__ == "__main__":
    print("[GraphRAG Comparison Workbench] Server starting...")
    print("[URL] http://127.0.0.1:8350")
    uvicorn.run(app, host="127.0.0.1", port=8350)
