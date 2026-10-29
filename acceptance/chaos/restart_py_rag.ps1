# 重启 Python 检索内核（混沌演练 J3 恢复阶段用）
# 用法：powershell -NoProfile -ExecutionPolicy Bypass -File restart_py_rag.ps1
$ErrorActionPreference = 'Stop'
$chaosDir = $PSScriptRoot                      # acceptance/chaos
$repo     = Split-Path -Parent (Split-Path -Parent $chaosDir)

# dot-source 环境注入（模型凭据/端口），与 start-ai.ps1 同源
. (Join-Path $repo 'it-ticket-cloud\scripts\ai-env.ps1') -GatewayPort 8080 | Out-Null

$py  = Join-Path $repo 'services\python-retrieval'
$log = Join-Path $env:TEMP 'it-chaos'
New-Item -ItemType Directory -Force -Path $log | Out-Null

# 优先仓库 .venv（与 start-ai.ps1 / 日常联调运行时一致），退回系统 python
$venvPy = Join-Path $repo '.venv\Scripts\python.exe'
$pyExe  = if (Test-Path $venvPy) { $venvPy } else { 'python' }

Start-Process -FilePath $pyExe -ArgumentList '-m', 'rag_service' -WorkingDirectory $py `
  -RedirectStandardOutput (Join-Path $log 'py-rag.out.log') `
  -RedirectStandardError  (Join-Path $log 'py-rag.err.log') -WindowStyle Hidden | Out-Null

Write-Output "[restart-py-rag] started (log dir: $log)"
