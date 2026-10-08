# 本地开发用：启动项目目录内的 Elasticsearch，不安装 Windows 系统服务。
# 执行：powershell -ExecutionPolicy Bypass -File .\it-ticket-cloud\scripts\start-elasticsearch.ps1
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$esInstallRoot = Join-Path $projectRoot '.devtools/elasticsearch-8.11.3'
$launcher = Join-Path $esInstallRoot 'bin/elasticsearch.bat'
if (!(Test-Path -LiteralPath $launcher)) {
    throw "Elasticsearch installation not found: $esInstallRoot"
}

$existing = Get-NetTCPConnection -LocalPort 9200 -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    $health = Invoke-RestMethod 'http://127.0.0.1:9200' -TimeoutSec 5
    if ($health.cluster_name -ne 'it-ticket-local') {
        throw 'Port 9200 belongs to another cluster; no process was changed.'
    }
    Write-Output 'Elasticsearch is already running at http://127.0.0.1:9200'
    exit 0
}

$logDirectory = Join-Path $projectRoot 'logs'
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
$env:ES_JAVA_OPTS = '-Xms512m -Xmx512m'
$process = Start-Process -FilePath $env:ComSpec -ArgumentList ('/d /s /c ""{0}""' -f $launcher) `
    -WorkingDirectory $esInstallRoot -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logDirectory 'elasticsearch.out.log') `
    -RedirectStandardError (Join-Path $logDirectory 'elasticsearch.err.log') -PassThru
Write-Output "Elasticsearch starting (launcher PID $($process.Id)); logs: $logDirectory"
Write-Output 'Check readiness: http://127.0.0.1:9200/_cluster/health'
