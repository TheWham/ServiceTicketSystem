# semantic_cache_fastapi_server.py
# 生产级带语义缓存加速与 SSE 流式输出的高并发 FastAPI 智能体服务
import math
import time
import json
import asyncio
from typing import List, Dict, Any, Tuple, Optional
from pydantic import BaseModel, Field
import requests

# 引入 FastAPI 核心组件
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

# ==============================================================================
# 1. 语义缓存核心引擎 (基于 Embedding 余弦相似度)
# ==============================================================================

class CacheEntry(BaseModel):
    query_text: str
    query_vector: List[float]
    response_text: str
    created_at: float = Field(default_factory=time.time)
    hit_count: int = 0

class SemanticCacheManager:
    """
    轻量高性能语义缓存管理器
    （底层使用向量空间搜索，生产环境可平滑迁移至 Redis-VSS / Milvus）
    """
    def __init__(self, threshold: float = 0.92, embed_url: str = "http://localhost:11434/api/embeddings"):
        self.threshold = threshold
        self.embed_url = embed_url
        self.cache_pool: List[CacheEntry] = []
        self.stats = {"hits": 0, "misses": 0, "saved_tokens": 0}

    def _get_embedding(self, text: str) -> List[float]:
        """优先调用本地 Ollama 获取向量，若无外部环境则使用轻量自适应模拟"""
        try:
            resp = requests.post(
                self.embed_url,
                json={"model": "nomic-embed-text:latest", "prompt": text},
                timeout=2
            )
            if resp.status_code == 200:
                return resp.json().get("embedding", [])
        except Exception:
            pass

        # 兜底轻量级字符频次语义向量（确保无网络离线环境绝对可跑通）
        vec = [0.0] * 64
        for char in text:
            vec[ord(char) % 64] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    @staticmethod
    def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return max(0.0, min(1.0, dot / (norm1 * norm2)))

    def search_cache(self, query: str) -> Tuple[Optional[str], float]:
        """查询语义缓存，若存在大于阈值的条目则命中"""
        q_vec = self._get_embedding(query)
        best_score = 0.0
        matched_entry: Optional[CacheEntry] = None

        for entry in self.cache_pool:
            sim = self._cosine_similarity(q_vec, entry.query_vector)
            if sim > best_score:
                best_score = sim
                matched_entry = entry

        if matched_entry and best_score >= self.threshold:
            self.stats["hits"] += 1
            matched_entry.hit_count += 1
            # 估算节省的 Token（按平均 1500 Token / 次）
            self.stats["saved_tokens"] += 1500
            return matched_entry.response_text, best_score

        self.stats["misses"] += 1
        return None, best_score

    def set_cache(self, query: str, response: str):
        """将新生成的回答异步写入语义缓存"""
        q_vec = self._get_embedding(query)
        entry = CacheEntry(
            query_text=query,
            query_vector=q_vec,
            response_text=response
        )
        self.cache_pool.append(entry)

# ==============================================================================
# 2. FastAPI 服务与 API 契约模型
# ==============================================================================

app = FastAPI(
    title="华科智造生产级企业 AI 智能体微服务",
    version="1.0.0",
    description="搭载语义缓存 (Semantic Cache) 与 SSE 流式打字输出的高并发服务"
)

# 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

cache_manager = SemanticCacheManager(threshold=0.91)

class ChatRequest(BaseModel):
    query: str = Field(..., example="一线城市普通员工住宿报销上限是多少？")
    user_id: Optional[str] = "GUEST"
    stream: bool = Field(default=False, description="是否采用 SSE 流式打字机传输")

class ChatResponse(BaseModel):
    query: str
    answer: str
    latency_ms: float
    cache_hit: bool
    similarity_score: float

# ==============================================================================
# 3. 模拟后端重型智能体推理中枢
# ==============================================================================

async def mock_agent_reasoning(query: str) -> str:
    """模拟复杂的 RAG 知识图谱检索与大模型链式推理（耗时约 1.5 秒）"""
    await asyncio.sleep(1.5)
    return (
        f"【权威审计裁决】根据《华科智造2024差旅合规规范》：\n"
        f"针对您所咨询的有关事项，一线城市（北京/上海/深圳）普通员工住宿上限调整为 450 元/天；"
        f"二线省会城市为 350 元/天。单笔报销超额部分需大区总监邮件特批，否则财务系统强制拦截。"
    )

# ==============================================================================
# 4. 路由定义：常规接口、SSE 流式接口与运维监控大盘
# ==============================================================================

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    """标准同步问答接口（自动透明启用语义缓存）"""
    t0 = time.time()

    # 1. 尝试检索语义缓存
    cached_ans, score = cache_manager.search_cache(req.query)
    if cached_ans:
        latency = round((time.time() - t0) * 1000, 2)
        return ChatResponse(
            query=req.query,
            answer=cached_ans,
            latency_ms=latency,
            cache_hit=True,
            similarity_score=round(score, 4)
        )

    # 2. 缓存击穿，穿透至重型智能体推理
    agent_answer = await mock_agent_reasoning(req.query)

    # 3. 异步落盘语义缓存
    cache_manager.set_cache(req.query, agent_answer)

    latency = round((time.time() - t0) * 1000, 2)
    return ChatResponse(
        query=req.query,
        answer=agent_answer,
        latency_ms=latency,
        cache_hit=False,
        similarity_score=round(score, 4)
    )

@app.post("/api/v1/chat/stream")
async def chat_stream_endpoint(req: ChatRequest):
    """SSE (Server-Sent Events) 流式打字机传输接口"""
    t0 = time.time()
    cached_ans, score = cache_manager.search_cache(req.query)

    async def sse_event_generator():
        # 如果命中缓存，极速流式打字输出
        if cached_ans:
            yield f"data: {json.dumps({'type': 'meta', 'cache_hit': True, 'score': round(score, 3)})}\n\n"
            for word in cached_ans:
                yield f"data: {json.dumps({'type': 'token', 'content': word})}\n\n"
                await asyncio.sleep(0.01)  # 模拟丝滑打字感
            yield "data: [DONE]\n\n"
            return

        # 若未命中缓存，等待推理并流式输出
        yield f"data: {json.dumps({'type': 'meta', 'cache_hit': False, 'score': round(score, 3)})}\n\n"
        full_text = await mock_agent_reasoning(req.query)
        cache_manager.set_cache(req.query, full_text)

        for word in full_text:
            yield f"data: {json.dumps({'type': 'token', 'content': word})}\n\n"
            await asyncio.sleep(0.02)
        yield "data: [DONE]\n\n"

    return StreamingResponse(sse_event_generator(), media_type="text/event-stream")

@app.get("/api/v1/cache/stats")
async def cache_stats_endpoint():
    """运维监控指标接口：获取当前语义缓存池运行大盘与降本指标"""
    total = cache_manager.stats["hits"] + cache_manager.stats["misses"]
    hit_rate = (cache_manager.stats["hits"] / total * 100) if total > 0 else 0.0
    return {
        "status": "UP",
        "cached_entries_count": len(cache_manager.cache_pool),
        "total_requests": total,
        "cache_hits": cache_manager.stats["hits"],
        "cache_misses": cache_manager.stats["misses"],
        "cache_hit_rate": f"{hit_rate:.1f}%",
        "estimated_tokens_saved": cache_manager.stats["saved_tokens"]
    }

# ==============================================================================
# 5. 本地自动化性能压测自检
# ==============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("🚀 Day 29 降本增效与服务化：FastAPI 与语义缓存 (Semantic Cache) 生产自测")
    print("=" * 80)

    # 模拟真实高频并发测试用例集
    test_queries = [
        "普通员工在一线城市出差单晚住宿上限是多少？",                  # 第 1 次问：必然 Cache Miss，穿透推理
        "请问一线城市普通员工出差单晚住宿报销上限是多少元？",          # 同义改写问：测试语义缓存命中
        "普通员工在上海出差住一晚最多报销多少？",                      # 泛化问法：测试语义向量相似度判定
        "员工加班打车超过晚上九点能否报销？"                           # 全新领域问题：应当未命中
    ]

    async def run_benchmark_simulation():
        print("▶️ [压测阶段 1] 预热与第 1 次冷启动请求...")
        ans1, score1 = cache_manager.search_cache(test_queries[0])
        print(f"  • 提问: \"{test_queries[0]}\"")
        print(f"    ➔ 缓存判定: {'🎯 命中' if ans1 else '❌ 未命中 (穿透推理)'} (相似度: {score1:.3f})")
        # 模拟生成并写入缓存
        real_ans = await mock_agent_reasoning(test_queries[0])
        cache_manager.set_cache(test_queries[0], real_ans)
        print("    ➔ 后端完成生成并成功写入语义缓存！\n")

        print("▶️ [压测阶段 2] 模拟同义改写提问，检验语义泛化命中率...")
        for q in test_queries[1:]:
            t_start = time.time()
            hit_ans, sim_score = cache_manager.search_cache(q)
            latency = (time.time() - t_start) * 1000
            status_text = "🎯 语义命中！(极速 0 Token)" if hit_ans else "❌ 穿透智能体"
            print(f"  • 提问: \"{q}\"")
            print(f"    ➔ 相似度评分: {sim_score:.4f} | 状态: {status_text} | 检索耗时: {latency:.2f}ms")
            if not hit_ans:
                new_ans = await mock_agent_reasoning(q)
                cache_manager.set_cache(q, new_ans)

        print("\n" + "-" * 60)
        print("📊 [生产降本效能审计大盘]")
        print("-" * 60)
        stats = await cache_stats_endpoint()
        for k, v in stats.items():
            print(f"  • {k:25}: {v}")
        print("-" * 60)

    asyncio.run(run_benchmark_simulation())
    print("\n💡 提示：如需对外暴露生产微服务，执行以下命令即可启动：")
    print("   uvicorn semantic_cache_fastapi_server:app --host 0.0.0.0 --port 8000 --workers 4")
    print("=" * 80)

