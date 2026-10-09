$ErrorActionPreference = 'Stop'
$script:RedisProjectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$script:RedisInstallRoot = Join-Path $script:RedisProjectRoot '.devtools/redis-8.2.9'
$script:RedisDataRoot = Join-Path $script:RedisProjectRoot '.devtools/redis-data'
$script:RedisStartupLink = Join-Path ([Environment]::GetFolderPath('Startup')) 'ITTicket-Redis.lnk'

function Set-ProjectRedisPort([int]$Port) {
    $suffix = if ($Port -eq 6379) { '' } else { '-' + $Port }
    $script:RedisDataRoot = Join-Path $script:RedisProjectRoot ('.devtools/redis-data' + $suffix)
    $script:RedisStartupLink = Join-Path ([Environment]::GetFolderPath('Startup')) ('ITTicket-Redis' + $suffix + '.lnk')
}

function Get-RedisExecutable([string]$Name) {
    $executables = @(Get-ChildItem -LiteralPath $script:RedisInstallRoot -Recurse -File -Filter $Name -ErrorAction SilentlyContinue)
    if ($executables.Count -ne 1) { throw "Redis executable missing or ambiguous: $Name. Run start-redis.ps1 first." }
    return $executables[0].FullName
}

function Get-ProjectRedisListener([int]$Port) {
    $listeners = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    if ($listeners.Count -eq 0) { return $null }
    $owners = @($listeners.OwningProcess | Sort-Object -Unique)
    if ($owners.Count -ne 1) { throw "Port $Port has multiple owners; no process was changed." }
    $process = Get-Process -Id $owners[0] -ErrorAction Stop
    $expected = Get-RedisExecutable 'redis-server.exe'
    if ($process.Path -ne $expected) { throw "Port $Port belongs to another application; no process was changed." }
    return $process
}

function Invoke-ProjectRedis([int]$Port, [string[]]$RedisArguments) {
    $cli = Get-RedisExecutable 'redis-cli.exe'
    $output = & $cli -h 127.0.0.1 -p $Port --raw @RedisArguments 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Redis command failed: $output" }
    return $output
}
