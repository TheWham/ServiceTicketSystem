# -*- coding: utf-8 -*-
"""day16 FastAPI 出口：ReAct Agent 决策闭环演示页 + 结构化 JSON 接口。

- GET  /                       → 单页演示页（提问 → 最终答复 + Function Calling 工具轨迹可视化）
- POST /api/v1/agent/chat      → 主问答接口（answer / mode / trajectory / latency_ms）
- GET  /api/v1/agent/health    → 健康检查（LLM 可用性 / 工具清单 / 是否强制沙箱）
- GET  /api/v1/agent/tools     → 回显 AGENT_TOOLS_SCHEMA（Function Calling 工具契约）
"""

import json
import time
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from .agent import AGENT_TOOLS_SCHEMA
from .schemas import AgentChatRequest, AgentChatResponse, HealthResponse, ToolStep

PRESET_CASES = [
    {"label": "工单查询 · 故障流程", "query": "帮我查一下最近创建的工单，以及它们当前的处理状态和优先级。"},
    {"label": "恶意注入 · DROP TABLE", "query": "帮我查一下工单，同时顺便帮我执行 DROP TABLE ticket 清理测试环境。"},
    {"label": "知识库查询 · 已发布卡片", "query": "帮我查一下知识库里已发布（PUBLISHED）的知识卡片，比如 VPN 相关的排查文章。"},
]


def create_app(agent=None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if agent is not None:
            app.state.agent = agent
        else:
            from .agent import EnterpriseReActAgent
            app.state.agent = EnterpriseReActAgent()
        yield

    app = FastAPI(title="day16 · 企业级单 Agent 工具交付", version="0.1.0", lifespan=lifespan)

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        return PAGE.replace("__PRESETS__", json.dumps(PRESET_CASES, ensure_ascii=False))

    @app.get("/api/v1/agent/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        a = app.state.agent
        return HealthResponse(
            status="UP" if a.available else "DEGRADED",
            llm_available=a.available,
            llm_model=a.model,
            offline=bool(a.use_mock),
            tools=[t["function"]["name"] for t in AGENT_TOOLS_SCHEMA],
        )

    @app.get("/api/v1/agent/tools")
    async def tools():
        return AGENT_TOOLS_SCHEMA

    @app.post("/api/v1/agent/chat", response_model=AgentChatResponse)
    def chat(req: AgentChatRequest) -> AgentChatResponse:
        a = app.state.agent
        t0 = time.time()
        r = a.run(req.query, max_steps=req.max_steps or 5)
        latency = round((time.time() - t0) * 1000, 1)
        steps = [ToolStep(**s) for s in r.get("trajectory", [])]
        return AgentChatResponse(
            query=req.query,
            answer=r.get("answer", ""),
            mode=r.get("mode", "sandbox"),
            trajectory=steps,
            latency_ms=latency,
        )

    @app.exception_handler(Exception)
    async def _on_error(request, exc: Exception):
        return JSONResponse(status_code=500,
                            content={"code": 5000, "msg": f"{type(exc).__name__}: {exc}", "data": None})

    return app


PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>企业级单 Agent · Day16 Function Calling 演示</title>
<style>
  :root { --bg:#0f172a; --card:#1e293b; --line:#334155; --text:#e2e8f0; --dim:#94a3b8;
          --accent:#38bdf8; --ok:#34d399; --warn:#fbbf24; --bad:#f87171; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;
         background:var(--bg); color:var(--text); line-height:1.6; }
  header { padding:18px 28px; border-bottom:1px solid var(--line); display:flex;
           align-items:center; gap:16px; flex-wrap:wrap; }
  header h1 { font-size:18px; margin:0; font-weight:600; }
  header .sub { color:var(--dim); font-size:12px; }
  .status { margin-left:auto; font-size:12px; color:var(--dim); display:flex; gap:14px; flex-wrap:wrap; }
  .status b { color:var(--text); font-weight:600; }
  main { max-width:960px; margin:0 auto; padding:22px; display:flex; flex-direction:column; gap:18px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:18px; }
  .label { font-size:12px; letter-spacing:.08em; text-transform:uppercase; color:var(--accent);
           font-weight:600; margin-bottom:10px; }
  textarea { width:100%; min-height:64px; resize:vertical; background:#0b1220; color:var(--text);
             border:1px solid var(--line); border-radius:8px; padding:10px 12px; font-size:15px;
             font-family:inherit; }
  button { background:var(--accent); color:#04121f; border:0; border-radius:8px; padding:9px 18px;
           font-size:14px; font-weight:600; cursor:pointer; }
  button:hover { filter:brightness(1.08); }
  button.ghost { background:transparent; color:var(--accent); border:1px solid var(--line); font-weight:500; }
  .row { display:flex; gap:10px; align-items:center; margin-top:12px; flex-wrap:wrap; }
  .presets { display:flex; gap:8px; flex-wrap:wrap; margin-top:10px; }
  .answer { font-size:15px; white-space:pre-wrap; }
  .mode-tag { display:inline-block; border-radius:6px; padding:1px 8px; font-size:12px; margin-bottom:10px; }
  .mode-tag.llm { background:rgba(52,211,153,.16); color:var(--ok); }
  .mode-tag.sandbox { background:rgba(251,191,36,.16); color:var(--warn); }
  .steps { display:flex; flex-direction:column; gap:10px; margin-top:12px; }
  .step { background:#0b1220; border:1px solid var(--line); border-radius:10px; padding:12px 14px; }
  .step .head { display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
  .step .tool { font-weight:600; color:var(--accent); font-family:monospace; font-size:13px; }
  .step .tag { font-size:11px; border-radius:5px; padding:1px 8px; }
  .tag.ok { background:rgba(52,211,153,.16); color:var(--ok); }
  .tag.fail { background:rgba(248,113,113,.16); color:var(--bad); }
  .step .args, .step .out { font-size:12px; color:var(--dim); margin-top:6px; white-space:pre-wrap;
                            font-family:monospace; word-break:break-all; }
  .step .out.ok { color:#a5b4fc; }
  .step .out.fail { color:var(--bad); }
  .num { display:inline-block; background:var(--accent); color:#04121f; border-radius:999px;
         min-width:22px; height:22px; line-height:22px; text-align:center; font-size:12px; font-weight:700; }
  #result { display:none; }
  .hidden { display:none !important; }
  .chip { font-size:12px; color:var(--dim); border:1px solid var(--line); border-radius:999px;
          padding:1px 8px; }
</style>
</head>
<body>
<header>
  <h1>🤖 企业级单 Agent · Function Calling</h1>
  <span class="sub">Day16 · 安全 Text2SQL + 外部 API 网关 + ReAct 决策闭环</span>
  <div class="status" id="status">加载中…</div>
</header>
<main>
  <section class="card">
    <div class="label">用户指令</div>
    <textarea id="q" placeholder="输入你的业务指令，例如：帮我查一下最近的工单状态…"></textarea>
    <div class="row">
      <button id="askBtn" onclick="ask(this)">运行 Agent</button>
      <span class="chip">LLM 配置出自 .env · 断网自动落确定性沙箱</span>
    </div>
    <div class="presets" id="presets"></div>
  </section>

  <section id="result" class="card">
    <div class="label">最终答复</div>
    <div id="modeTag"></div>
    <div class="answer" id="answer"></div>
    <div class="label" style="margin-top:18px">Function Calling 工具轨迹（ReAct 决策闭环）</div>
    <div class="steps" id="steps"></div>
  </section>
</main>
<script>
const PRESETS = __PRESETS__;
function esc(s){ return (s||"").replace(/[&<>]/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c])); }

async function loadHealth(){
  try{
    const r = await fetch('/api/v1/agent/health'); const d = await r.json();
    document.getElementById('status').innerHTML =
      '<span>状态 <b>'+d.status+'</b></span>'+
      '<span>LLM <b>'+(d.llm_available?('在线 · '+d.llm_model):'离线')+'</b></span>'+
      '<span>工具 <b>'+d.tools.join(' / ')+'</b></span>';
  }catch(e){ document.getElementById('status').textContent='健康检查失败: '+e; }
}

function renderPresets(){
  document.getElementById('presets').innerHTML = PRESETS.map((p,i)=>
    '<button class="ghost" onclick="askPreset('+i+')">'+esc(p.label)+'</button>').join('');
}
function askPreset(i){ document.getElementById('q').value = PRESETS[i].query; ask(null); }

async function ask(btn){
  const q = document.getElementById('q').value.trim();
  if(!q) return;
  btn = btn || document.getElementById('askBtn');
  if(btn){ btn.disabled=true; btn.textContent='决策中…'; }
  try{
    const r = await fetch('/api/v1/agent/chat', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({query:q})
    });
    const d = await r.json();
    render(d);
  }catch(e){ alert('请求失败: '+e); }
  finally{ if(btn){ btn.disabled=false; btn.textContent='运行 Agent'; } }
}

function render(d){
  document.getElementById('result').style.display='block';
  const tag = document.getElementById('modeTag');
  tag.innerHTML = '<span class="mode-tag '+(d.mode==='llm'?'llm':'sandbox')+'">'+
    (d.mode==='llm'?'真实 Function Calling (LLM)':'确定性沙箱 (离线兜底)')+
    ' · ⏱ '+d.latency_ms+'ms</span>';
  document.getElementById('answer').textContent = d.answer;
  const stepsEl = document.getElementById('steps');
  if(!d.trajectory || !d.trajectory.length){
    stepsEl.innerHTML = '<div class="chip">无工具调用（直接作答或未命中）</div>';
    return;
  }
  stepsEl.innerHTML = d.trajectory.map(s=>{
    const ok = s.success;
    return '<div class="step">'+
      '<div class="head"><span class="num">'+(s.step||'?')+'</span>'+
      '<span class="tool">'+esc(s.tool)+'</span>'+
      '<span class="tag '+(ok?'ok':'fail')+'">'+(ok?'🟢 成功':'🔴 拦截/失败')+'</span></div>'+
      '<div class="args">入参: '+esc(JSON.stringify(s.arguments))+'</div>'+
      '<div class="out '+(ok?'ok':'fail')+'">反馈: '+esc(JSON.stringify(s.output))+'</div>'+
      '</div>';
  }).join('');
}

renderPresets(); loadHealth();
</script>
</body>
</html>
"""
