#Requires -Version 5.1
<#
  AI 客服 · 一键启动四个 AI 相关服务（Windows PowerShell）
  ============================================================
  启动顺序：Python 检索内核(8310) → agent_service(8320) → rag-service(8302) → consultation-service(8301)
  每个服务开一个独立窗口，日志直接看得到。

  前置条件（不满足的话 AI 客服会拒答或者报依赖不可用）：
    - Redis :6379、Nacos :8848 已起（我这边是 Docker：it-ticket-redis / it-ticket-nacos）
    - MySQL 不用管，yml 里内置了远程库地址与口令
    - 五个后端 jar 已 mvn package 过；前端另行 npm run dev

  用法：
      pwsh -File .\start-ai.ps1                     # 网关端口默认 28080
      pwsh -File .\start-ai.ps1 -GatewayPort 8080
      pwsh -File .\start-ai.ps1 -SkipBuild          # 默认就会跳过构建，此参数仅为显式说明
#>
param(
    [int]$GatewayPort = 28080
)

$ErrorActionPreference = 'Stop'

# 注入全部模型凭据 / 工具地址 / RAG_HOME（核心步骤，见 ai-env.ps1）
. (Join-Path $PSScriptRoot 'ai-env.ps1') -GatewayPort $GatewayPort

$repoRoot  = Split-Path (Join-Path $PSScriptRoot 'services\python-retrieval') -Parent
if (-not (Test-Path (Join-Path $repoRoot 'services\python-retrieval'))) {
    $repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}
$pyDir   = Join-Path $repoRoot 'services\python-retrieval'
$javaDir = Join-Path $repoRoot 'it-ticket-cloud'

function Start-ServiceWindow {
    param([string]$Title, [string]$WorkDir, [string]$Command)
    Write-Host "[start-ai] $Title  (cwd=$WorkDir)"
    Start-Process -FilePath 'powershell' -ArgumentList @(
        '-NoExit', '-Command',
        "`$host.UI.RawUI.WindowTitle='$Title'; Set-Location -LiteralPath '$WorkDir'; $Command"
    ) | Out-Null
}

# 1) Python 检索内核：rag-service 默认 provider=python 且失败不回落 ES，必须最先起
Start-ServiceWindow 'py-rag-8310' $pyDir 'python -m rag_service'
Start-Sleep -Seconds 4

# 2) Function Calling 智能体
Start-ServiceWindow 'agent-8320' $pyDir 'python -m agent_service'
Start-Sleep -Seconds 2

# 3) 检索编排
Start-ServiceWindow 'rag-service-8302' $javaDir 'java -jar rag-service\target\it-ticket-rag-service-1.0.0.jar'
Start-Sleep -Seconds 6

# 4) AI 客服主服务
Start-ServiceWindow 'consultation-8301' $javaDir 'java -jar consultation-service\target\it-ticket-consultation-service-1.0.0.jar'

Write-Host ''
Write-Host '[start-ai] 四个服务已拉起。等 20~30 秒（Spring 启动 + 建连），然后自检：'
Write-Host '  curl http://127.0.0.1:8320/api/health   # 期望 model_configured:true'
Write-Host '  curl http://127.0.0.1:8310/api/health   # 期望 status:UP, chunkCount>0'
Write-Host '  curl http://127.0.0.1:8302/api/health   # 期望 status:UP'
Write-Host ''
Write-Host '端到端冒烟（需网关已起）：'
Write-Host '  $env:IT_GATEWAY_URL="http://127.0.0.1:' + $GatewayPort + '"'
Write-Host '  node acceptance/ai-rag-smoke.mjs         # 期望四行全 PASS（OFF_TOPIC / HIGH_RISK / UNCERTAIN / 真答案）'