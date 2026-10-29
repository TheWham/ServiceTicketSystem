#Requires -Version 5.1
<#
  AI 客服 · 环境变量注入（PowerShell）
  ============================================================
  这是整套配置的核心：模型凭据与工具地址全部以「环境变量」注入，
  仓库里没有 ai-secrets.yml，也不依赖它。

  用法（放在仓库根目录或 it-ticket-cloud/scripts/ 下都可以）：
      . .\ai-env.ps1                 # 注意：点 + 空格，dot-source 到当前会话
      . .\ai-env.ps1 -GatewayPort 8080

  注入后再启动服务，变量会被子进程继承：
      java -jar consultation-service/target/it-ticket-consultation-service-1.0.0.jar
      cd services/python-retrieval; python -m agent_service

  或者直接跑同目录的 start-ai.ps1（它会自动 dot-source 本文件）。
#>
param(
    # 网关端口：我的机器 8080 被 Dify 占用，所以网关跑在 28080。你用自己的端口。
    [int]$GatewayPort = 28080
)

# ---- 模型端点与密钥（三项服务共用同一把 key，只有 LLM_CHAT_MODEL 那个坑要避开）----
$ModelBaseUrl = 'https://kspmas.ksyun.com/v1'
$ModelApiKey = $env:IT_MODEL_API_KEY
if (-not $ModelApiKey) {
    $localEnv = Join-Path $PSScriptRoot 'ai-env.local.ps1'
    if (Test-Path -LiteralPath $localEnv) {
        . $localEnv
        $ModelApiKey = $env:IT_MODEL_API_KEY
    }
}
if (-not $ModelApiKey) {
    throw "未设置 IT_MODEL_API_KEY。请设置环境变量，或创建并填写 $PSScriptRoot\ai-env.local.ps1。"
}

# ============================================================
# 1) consultation-service（AI 客服主服务，:8301）
# ============================================================
$env:AI_PROVIDER   = 'openai-compatible'
$env:AI_BASE_URL   = $ModelBaseUrl
$env:AI_API_KEY    = $ModelApiKey
# 必须用 deepseek-v4-flash：consultation 硬编码 temperature=0.0 + response_format=json_object，
# kimi-k3 只接受 temperature=1，会吃 400 → 全量 MODEL_UNAVAILABLE 拒答（costMs=0，很误导）。
$env:AI_MODEL      = 'deepseek-v4-flash'

# 检索走 rag-service；工单走 ticket-service（咨询域不跨库读工单）
$env:RAG_BASE_URL            = 'http://127.0.0.1:8302'
$env:TICKET_SERVICE_BASE_URL = 'http://127.0.0.1:8201'

# 生成侧下沉 Python 智能体（ReAct + 白名单工具：查本人工单 / 产建单草稿 / 补搜知识）
$env:AI_AGENT_ENABLED       = 'true'
$env:AGENT_SERVICE_BASE_URL = 'http://127.0.0.1:8320'

# ============================================================
# 2) rag-service（检索编排，:8302）
# ============================================================
$env:EMBEDDING_BASE_URL  = $ModelBaseUrl
$env:EMBEDDING_API_KEY   = $ModelApiKey
$env:EMBEDDING_MODEL     = 'qwen3-embedding-8b'
$env:EMBEDDING_DIMENSIONS = '1024'          # 必须与 ES 里现有知识索引维度一致
# 检索内核默认 provider=python，且 python 分支失败【不回落 ES】——8310 必须起着
$env:RAG_RETRIEVAL_PROVIDER = 'python'
$env:RAG_PYTHON_BASE_URL    = 'http://127.0.0.1:8310'

# ============================================================
# 3) agent_service（Python，:8320）
# ============================================================
$env:AGENT_LLM_BASE_URL = $ModelBaseUrl
$env:AGENT_LLM_API_KEY  = $ModelApiKey
$env:AGENT_LLM_MODEL    = 'deepseek-v4-flash'   # 不支持原生 tools 的模型会退化成只会说话
$env:AGENT_SERVICE_PORT = '8320'
$env:KNOWLEDGE_SEARCH_BASE_URL = 'http://127.0.0.1:8301'
# TICKET_SERVICE_BASE_URL 见上（consultation 小节已设，agent_service 共用同一个变量名）

# ============================================================
# 4) Python 检索内核（:8310）—— 注意命名和 Java 侧不同
# ============================================================
# Java 侧读 EMBEDDING_*，Python 侧读 EMBED_*/RERANK_*/LLM_*，同一把 key 要写两遍。
$env:EMBED_BASE_URL  = $ModelBaseUrl
$env:EMBED_API_KEY   = $ModelApiKey
$env:EMBED_MODEL     = 'qwen3-embedding-8b'
$env:RERANK_BASE_URL = $ModelBaseUrl
$env:RERANK_API_KEY  = $ModelApiKey
$env:RERANK_MODEL    = 'qwen3-reranker-8b'
$env:LLM_BASE_URL    = $ModelBaseUrl
$env:LLM_API_KEY     = $ModelApiKey

# ============================================================
# 5) 路径与端口（按仓库位置自动解析，换机器不用改）
# ============================================================
# RAG_HOME：Python 检索服务的「仓库根」，决定了它去哪读 artifacts/ 与 configs/
$repoRoot = $PSScriptRoot
for ($i = 0; $i -lt 4 -and $repoRoot; $i++) {
    if (Test-Path (Join-Path $repoRoot 'services\python-retrieval')) { break }
    $repoRoot = Split-Path $repoRoot -Parent
}
if (-not $repoRoot -or -not (Test-Path (Join-Path $repoRoot 'services\python-retrieval'))) {
    throw "找不到仓库根目录（应包含 services\python-retrieval）；请把本文件放回仓库内再 dot-source。"
}
$env:RAG_HOME      = Join-Path $repoRoot 'services\python-retrieval'
$env:IT_GATEWAY_PORT = "$GatewayPort"

Write-Host "[ai-env] 已注入环境变量：AI_MODEL=$($env:AI_MODEL)  AI_AGENT_ENABLED=$($env:AI_AGENT_ENABLED)"
Write-Host "[ai-env] RAG_HOME=$($env:RAG_HOME)"
Write-Host "[ai-env] 网关端口假定为 $GatewayPort（前端 .env.local 的 API_PROXY_TARGET 要与之对齐）"