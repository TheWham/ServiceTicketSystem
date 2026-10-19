# -*- coding: utf-8 -*-
"""day15 FastAPI 出口：交互式问答演示页 + 结构化 JSON 接口。

- GET  /                              → 单页演示页（提问 → 带角标答案 + 链路可视化 + 切片演示）
- POST /api/v1/knowledge/chat         → 主问答接口（answer / is_refused / citations / trace / latency_ms）
- GET  /api/v1/knowledge/chunk_demo   → 现场切一张卡，展示父子切片结构
- GET  /api/v1/knowledge/cards        → 卡片清单（供切片演示下拉）
- GET  /api/v1/knowledge/health       → 健康检查
"""

import json
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from .schemas import CardInfo, ChatRequest, ChatResponse, ChunkDemoResponse, HealthResponse

PRESET_QUESTIONS = [
    {"label": "正例 · 密码策略", "query": "公司密码策略要求每隔多少天定期更换密码？密码复杂度有什么要求？"},
    {"label": "版本冲突 · VPN 806", "query": "出差在酒店连公司 VPN 一直报错 806 无法连接，现行 v1.0 规范推荐改用哪种 VPN 协议穿透性最好？旧版 v0.9 推荐的 PPTP 协议是否依然有效？"},
    {"label": "越界拒答 · 住房公积金", "query": "公司目前是否允许员工使用个人住房公积金向财务部申请企业内部低息购房免息贷款？"},
]


def create_app(service=None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if service is not None:
            app.state.svc = service
        else:
            from .service import EnterpriseKnowledgeService
            app.state.svc = EnterpriseKnowledgeService()
        yield

    app = FastAPI(title="day15 · 企业知识库问答服务层", version="0.1.0", lifespan=lifespan)

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        return PAGE.replace("__PRESETS__", json.dumps(PRESET_QUESTIONS, ensure_ascii=False))

    @app.get("/chat", response_class=HTMLResponse)
    async def chat_page() -> str:
        return PAGE_CHAT.replace("__PRESETS__", json.dumps(PRESET_QUESTIONS, ensure_ascii=False))

    @app.get("/api/v1/knowledge/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return app.state.svc.health()

    @app.get("/api/v1/knowledge/cards", response_model=List[CardInfo])
    async def cards() -> List[CardInfo]:
        return app.state.svc.list_cards()

    @app.get("/api/v1/knowledge/chunk_demo", response_model=ChunkDemoResponse)
    async def chunk_demo(card: str) -> ChunkDemoResponse:
        try:
            return app.state.svc.chunk_demo(card)
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.post("/api/v1/knowledge/chat", response_model=ChatResponse)
    def chat(req: ChatRequest) -> ChatResponse:
        return app.state.svc.answer(req.query, top_k=req.top_k,
                                    metadata_filter=req.metadata_filter,
                                    include_trace=req.include_trace)

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
<title>企业IT知识库问答 · Day15 服务层演示</title>
<style>
  :root { --bg:#0f172a; --card:#1e293b; --line:#334155; --text:#e2e8f0; --dim:#94a3b8;
          --accent:#38bdf8; --ok:#34d399; --warn:#fbbf24; --bad:#f87171; }
  * { box-sizing: border-box; }
  body { margin:0; font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;
         background:var(--bg); color:var(--text); line-height:1.6; }
  header { padding:18px 28px; border-bottom:1px solid var(--line); display:flex;
           align-items:center; gap:16px; flex-wrap:wrap; }
  header h1 { font-size:18px; margin:0; font-weight:600; }
  header .sub { color:var(--dim); font-size:12px; }
  .status { margin-left:auto; font-size:12px; color:var(--dim); display:flex; gap:14px; flex-wrap:wrap; }
  .status b { color:var(--text); font-weight:600; }
  main { max-width:1080px; margin:0 auto; padding:22px; display:flex; flex-direction:column; gap:18px; }
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
  .badge { display:inline-block; background:rgba(56,189,248,.16); color:var(--accent);
           border:1px solid rgba(56,189,248,.4); border-radius:6px; padding:0 6px; font-size:12px;
           margin:0 2px; }
  .funnel { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:14px; }
  .stage { flex:1; min-width:120px; background:#0b1220; border:1px solid var(--line);
           border-radius:10px; padding:10px 12px; }
  .stage .n { font-size:20px; font-weight:700; color:var(--accent); }
  .stage .t { font-size:12px; color:var(--dim); }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th,td { text-align:left; padding:6px 8px; border-bottom:1px solid var(--line); }
  th { color:var(--dim); font-weight:500; font-size:12px; }
  tr.final td { background:rgba(52,211,153,.08); }
  .tag { font-size:11px; border-radius:5px; padding:1px 6px; margin-left:6px; }
  .tag.prot { background:rgba(251,191,36,.16); color:var(--warn); }
  .cite { border-left:3px solid var(--accent); padding:8px 12px; margin:8px 0;
          background:#0b1220; border-radius:0 8px 8px 0; }
  .cite .h { font-weight:600; font-size:14px; }
  .cite .m { font-size:12px; color:var(--dim); margin-top:2px; }
  .cite .s { font-size:13px; color:#cbd5e1; margin-top:6px; }
  .refused { color:var(--warn); font-weight:600; }
  #result { display:flex; flex-direction:column; gap:18px; }
  .hidden { display:none !important; }
  .chip { font-size:12px; color:var(--dim); border:1px solid var(--line); border-radius:999px;
          padding:1px 8px; }
  .kids { display:flex; flex-direction:column; gap:8px; margin-top:12px; }
  .kid { background:#0b1220; border:1px solid var(--line); border-radius:8px; padding:10px 12px; }
  .kid .h { font-size:13px; font-weight:600; }
  .kid .p { font-size:12px; color:var(--dim); margin-top:4px; }
  select { background:#0b1220; color:var(--text); border:1px solid var(--line); border-radius:8px;
           padding:8px 10px; font-size:14px; min-width:260px; }
</style>
</head>
<body>
<header>
  <h1>企业IT知识库问答</h1>
  <span class="sub">Day15 服务层 · 检索 + 受约束生成 + 溯源角标</span>
  <a href="/chat" style="color:var(--accent);font-size:13px;text-decoration:none">💬 聊天会话模式 →</a>
  <div class="status" id="status">加载中…</div>
</header>
<main>
  <section class="card">
    <div class="label">提问</div>
    <textarea id="q" placeholder="输入你的 IT 问题，例如：电脑蓝屏怎么办？"></textarea>
    <div class="row">
      <button id="askBtn" onclick="ask(this)">检索并回答</button>
      <span class="chip">检索参数全部出自 configs/pipeline.yaml</span>
    </div>
    <div class="presets" id="presets"></div>
  </section>

  <section id="result" class="hidden">
    <div class="card">
      <div class="label">答案（受约束生成 · 带溯源角标）</div>
      <div class="answer" id="answer"></div>
    </div>
    <div class="card">
      <div class="label">检索链路（双路召回 → RRF → Rerank → 门控 → 拒答门）</div>
      <div class="funnel" id="funnel"></div>
      <table>
        <thead><tr><th>#</th><th>子块</th><th>卡片</th><th>章节</th><th>RRF名次</th>
        <th>Rerank名次</th><th>Rerank分</th><th>融合分</th></tr></thead>
        <tbody id="cands"></tbody>
      </table>
    </div>
    <div class="card">
      <div class="label">来源（Citation · 结构化溯源）</div>
      <div id="cites"></div>
    </div>
  </section>

  <section class="card">
    <div class="label">切片演示（父子 Small-to-Big：子块做匹配 · 父卡做上下文）</div>
    <div class="row">
      <select id="cardSel"></select>
      <button class="ghost" onclick="loadChunk()">查看切片结构</button>
    </div>
    <div id="chunkOut"></div>
  </section>
</main>
<script>
const PRESETS = __PRESETS__;
const CITE_RE = /\[来源[:：]\s*(.+?)\s+[-—–]\s+(.+?)\]/g;

function esc(s){ return (s||"").replace(/[&<>]/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c])); }

function fmtAnswer(t){
  let h = esc(t);
  h = h.replace(CITE_RE, (m,cid,sec)=>'<span class="badge">来源: '+cid.trim()+' · '+sec.trim()+'</span>');
  return h;
}

async function loadHealth(){
  try{
    const r = await fetch('/api/v1/knowledge/health'); const d = await r.json();
    document.getElementById('status').innerHTML =
      '<span>状态 <b>'+d.status+'</b></span>'+
      '<span>切片 <b>'+d.chunk_count+'</b></span>'+
      '<span>卡片 <b>'+d.card_count+'</b></span>'+
      '<span>LLM <b>'+(d.llm_available?'在线':'离线')+'</b></span>'+
      '<span>缓存答案 <b>'+d.cached_answers+'</b></span>';
  }catch(e){ document.getElementById('status').textContent='健康检查失败: '+e; }
}

async function loadCards(){
  const r = await fetch('/api/v1/knowledge/cards'); const cards = await r.json();
  const sel = document.getElementById('cardSel');
  sel.innerHTML = cards.map(c=>'<option value="'+c.card_id+'">'+c.card_id+' · '+esc(c.title)+'</option>').join('');
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
  if(btn){ btn.disabled=true; btn.textContent='检索中…'; }
  try{
    const r = await fetch('/api/v1/knowledge/chat', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({query:q, include_trace:true})
    });
    const d = await r.json();
    render(d);
  }catch(e){ alert('请求失败: '+e); }
  finally{ if(btn){ btn.disabled=false; btn.textContent='检索并回答'; } }
}

function render(d){
  document.getElementById('result').classList.remove('hidden');
  const ansEl = document.getElementById('answer');
  if(d.is_refused){
    ansEl.innerHTML = '<span class="refused">🚫 诚实拒答：</span> '+esc(d.answer);
  }else{
    let head = d.offline ? '<div class="chip" style="margin-bottom:8px">离线兜底模式</div>' : '';
    ansEl.innerHTML = head + fmtAnswer(d.answer);
  }
  // 链路
  const t = d.trace || {};
  const stages = [
    ['向量召回', t.dense_count, 'Dense (Chroma 余弦)'],
    ['关键词召回', t.bm25_count, 'BM25'],
    ['RRF 融合', t.fused_count, '倒数排名 k=60'],
    ['精排', t.rerank_remote?'远程':'启发式', t.gate_mode==='off'?'Rerank 未门控':('门控 '+t.gate_mode+' · margin '+t.gate_margin)],
    ['最高精排分', t.max_rerank_score, '拒答阈值 '+(t.reject_threshold??'—')],
  ];
  document.getElementById('funnel').innerHTML = stages.map(s=>
    '<div class="stage"><div class="n">'+s[1]+'</div><div class="t">'+s[0]+'</div><div class="t">'+s[2]+'</div></div>').join('');
  const tb = document.getElementById('cands');
  tb.innerHTML = (t.candidates||[]).map((c,i)=>(
    '<tr class="'+(c.is_final?'final':'')+'"><td>'+(i+1)+'</td><td>'+esc(c.chunk_id)+
    (c.protected?'<span class="tag prot">双路共振</span>':'')+'</td><td>'+esc(c.card_id)+'</td><td>'+
    esc(c.section)+'</td><td>'+(c.rrf_rank??'-')+'</td><td>'+(c.rerank_rank??'-')+'</td><td>'+
    (c.rerank_score??'-')+'</td><td>'+(c.fused_score??'-')+'</td></tr>')).join('');
  // 来源
  document.getElementById('cites').innerHTML = (d.citations||[]).map(c=>
    '<div class="cite"><div class="h">'+esc(c.card_id)+' · '+esc(c.title)+
    (c.cited_inline?'<span class="tag" style="background:rgba(52,211,153,.16);color:var(--ok)">正文已引用</span>':'')+
    '</div><div class="m">章节：'+esc(c.section)+' ｜ 来源文件：'+esc(c.source_file)+
    ' ｜ 相关度：'+c.relevance_score+'</div><div class="s">'+esc(c.snippet)+'</div></div>'
  ).join('') || '<div class="chip">无来源</div>';
}

async function loadChunk(){
  const card = document.getElementById('cardSel').value;
  const out = document.getElementById('chunkOut');
  out.innerHTML = '<div class="chip">切分中…</div>';
  try{
    const r = await fetch('/api/v1/knowledge/chunk_demo?card='+encodeURIComponent(card));
    const d = await r.json();
    out.innerHTML =
      '<div class="row"><span class="chip">父卡 '+esc(d.card_id)+' · '+esc(d.title)+' · 整卡 '+d.parent_length+' 字符</span><span class="chip">子块 '+d.children.length+' 个</span></div>'+
      '<details class="kid" style="margin-top:10px"><summary style="cursor:pointer">📄 父卡全文（喂给 LLM 的上下文，点击展开）</summary>'+
      '<div class="p" style="white-space:pre-wrap">'+esc(d.parent_preview+' …（完整内容见原卡片文件 '+d.source_file+'）')+'</div></details>'+
      '<div class="kids">'+d.children.map(k=>
      '<details class="kid" open><summary style="cursor:pointer">'+esc(k.child_id)+' · '+esc(k.section)+
      (k.has_boost?'<span class="tag prot">含检索增强注入</span>':'')+' · '+k.length+' 字符</summary>'+
      '<div class="p" style="white-space:pre-wrap">'+esc(k.content)+'</div></details>').join('')+'</div>';
  }catch(e){ out.innerHTML='<div class="chip">加载失败: '+e+'</div>'; }
}

renderPresets(); loadHealth(); loadCards();
</script>
</body>
</html>
"""


PAGE_CHAT = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI 问答 · Day15 聊天会话</title>
<style>
  :root { --bg:#0f172a; --card:#1e293b; --line:#334155; --text:#e2e8f0; --dim:#94a3b8;
          --accent:#38bdf8; --ok:#34d399; --warn:#fbbf24; --bad:#f87171; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;
         background:var(--bg); color:var(--text); }
  .wrap { max-width:820px; margin:0 auto; height:100vh; display:flex; flex-direction:column; }
  header { padding:14px 20px; border-bottom:1px solid var(--line); display:flex;
           align-items:center; gap:12px; }
  header h1 { font-size:16px; margin:0; font-weight:600; }
  header a { color:var(--accent); font-size:13px; text-decoration:none; margin-left:auto; }
  #msgs { flex:1; overflow-y:auto; padding:20px; display:flex; flex-direction:column; gap:14px; }
  .msg { max-width:82%; padding:10px 14px; border-radius:12px; line-height:1.6;
         white-space:pre-wrap; font-size:14px; }
  .msg.user { align-self:flex-end; background:var(--accent); color:#04121f;
              border-bottom-right-radius:4px; }
  .msg.ai { align-self:flex-start; background:var(--card); border:1px solid var(--line);
            border-bottom-left-radius:4px; }
  .msg.typing { color:var(--dim); font-style:italic; }
  .badge { display:inline-block; background:rgba(56,189,248,.16); color:var(--accent);
           border:1px solid rgba(56,189,248,.4); border-radius:6px; padding:0 6px;
           font-size:12px; margin:0 2px; }
  .meta { font-size:11px; color:var(--dim); margin-top:6px; }
  .meta .tag { font-size:11px; border-radius:5px; padding:1px 6px; }
  .tag.ok { background:rgba(52,211,153,.16); color:var(--ok); }
  .tag.refused { background:rgba(251,191,36,.16); color:var(--warn); }
  .tag.offline { background:rgba(248,113,113,.16); color:var(--bad); }
  details { margin-top:8px; font-size:12px; }
  summary { cursor:pointer; color:var(--accent); }
  .cite { border-left:2px solid var(--accent); padding:4px 10px; margin:6px 0;
          background:#0b1220; border-radius:0 6px 6px 0; }
  .cite .h { font-weight:600; }
  .cite .m { color:var(--dim); font-size:11px; }
  .chips { display:flex; gap:8px; flex-wrap:wrap; padding:10px 20px; }
  .chips button { background:transparent; color:var(--accent); border:1px solid var(--line);
                  border-radius:999px; padding:6px 14px; font-size:13px; cursor:pointer; }
  .chips button:hover { background:rgba(56,189,248,.1); }
  .inputbar { display:flex; gap:10px; padding:14px 20px; border-top:1px solid var(--line); }
  #inp { flex:1; background:#0b1220; color:var(--text); border:1px solid var(--line);
         border-radius:10px; padding:12px 14px; font-size:15px; font-family:inherit; }
  button.send { background:var(--accent); color:#04121f; border:0; border-radius:10px;
                padding:0 20px; font-size:15px; font-weight:600; cursor:pointer; }
  button.send:disabled { opacity:.5; cursor:not-allowed; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>🤖 企业 IT 知识库 · AI 问答</h1>
    <a href="/">← 返回链路演示页</a>
  </header>
  <div id="msgs"></div>
  <div class="chips" id="chips"></div>
  <div class="inputbar">
    <input id="inp" placeholder="输入你的 IT 问题，回车发送…" />
    <button class="send" id="sendBtn" onclick="send()">发送</button>
  </div>
</div>
<script>
const PRESETS = __PRESETS__;
const CITE_RE = /\[来源[:：]\s*(.+?)\s+[-—–]\s+(.+?)\]/g;

function esc(s){ return (s||"").replace(/[&<>]/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c])); }
function fmtAnswer(t){
  let h = esc(t);
  h = h.replace(CITE_RE, (m,cid,sec)=>'<span class="badge">来源: '+cid.trim()+' · '+sec.trim()+'</span>');
  return h;
}
function el(html){ const d=document.createElement('div'); d.innerHTML=html; return d.firstElementChild; }

function addUser(text){
  document.getElementById('msgs').appendChild(
    el('<div class="msg user">'+esc(text)+'</div>'));
  scrollBottom();
}
function addTyping(){
  const t = el('<div class="msg ai typing" id="typing">思考中…</div>');
  document.getElementById('msgs').appendChild(t);
  scrollBottom();
  return t;
}
function scrollBottom(){ const m=document.getElementById('msgs'); m.scrollTop=m.scrollHeight; }

function renderAi(d){
  let body;
  if(d.is_refused){
    body = '<span class="tag refused">🚫 诚实拒答</span><br>'+esc(d.answer);
  }else{
    let head = d.offline ? '<span class="tag offline">离线兜底</span> ' :
              (d.mode==='cache' ? '<span class="tag ok">缓存命中</span> ' : '');
    body = head + fmtAnswer(d.answer);
  }
  let cites = '';
  if(d.citations && d.citations.length){
    cites = '<details><summary>查看来源（'+d.citations.length+'）</summary>'+
      d.citations.map(c=>'<div class="cite"><div class="h">'+esc(c.card_id)+' · '+esc(c.title)+
      (c.cited_inline?' <span class="tag ok">正文已引用</span>':'')+
      '</div><div class="m">章节：'+esc(c.section)+' ｜ 来源文件：'+esc(c.source_file)+
      ' ｜ 相关度：'+c.relevance_score+'</div></div>').join('')+'</details>';
  }
  const meta = '<div class="meta">⏱ '+d.latency_ms+'ms'+
    (d.trace ? ' ｜ 召回 BM25 '+d.trace.bm25_count+' / Dense '+d.trace.dense_count+
               ' ｜ 精排 '+(d.trace.rerank_remote?'远程':'启发式')+
               ' ｜ 门控 '+d.trace.gate_mode+' ｜ 最高分 '+d.trace.max_rerank_score : '')+'</div>';
  document.getElementById('msgs').appendChild(
    el('<div class="msg ai">'+body+cites+meta+'</div>'));
  scrollBottom();
}

async function send(){
  const inp = document.getElementById('inp');
  const q = inp.value.trim();
  if(!q) return;
  inp.value = '';
  addUser(q);
  const btn = document.getElementById('sendBtn');
  btn.disabled = true;
  const typing = addTyping();
  try{
    const r = await fetch('/api/v1/knowledge/chat', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({query:q, include_trace:true})
    });
    const d = await r.json();
    typing.remove();
    renderAi(d);
  }catch(e){
    typing.remove();
    document.getElementById('msgs').appendChild(
      el('<div class="msg ai"><span class="tag refused">请求失败</span> '+esc(String(e))+'</div>'));
    scrollBottom();
  }finally{ btn.disabled=false; }
}

document.getElementById('inp').addEventListener('keydown', e=>{ if(e.key==='Enter') send(); });
document.getElementById('chips').innerHTML = PRESETS.map((p,i)=>
  '<button onclick="document.getElementById(\'inp\').value=\''+
  p.query.replace(/'/g,"\\'")+'\';send()">'+esc(p.label)+'</button>').join('');

// 开场欢迎消息
document.getElementById('msgs').appendChild(
  el('<div class="msg ai">你好！我是企业 IT 知识库问答助手，基于检索增强生成（RAG）。\n\n'+
     '直接输入问题，或点下面的快捷问题试试。每条回答都会标注【来源】。\n\n'+
     '（正例 · 版本冲突 · 越界拒答 三种都能演示）</div>'));
</script>
</body>
</html>
"""

