param(
    [ValidateRange(1024, 65535)][int]$Port = 6379,
    [switch]$EnableAutoStart
)
. (Join-Path $PSScriptRoot 'redis-common.ps1')
Set-ProjectRedisPort $Port

# Pinned development build. Never execute a package before verifying its digest.
$archiveName = 'Redis-8.2.9-Windows-x64-msys2.zip'
$archivePath = Join-Path $script:RedisProjectRoot ('.devtools/' + $archiveName)
$sha256 = 'dcff676e861a4ae0a9854556239398e77a7469c9379af64a4a76798d166d1aa0'
$installed = @(Get-ChildItem -LiteralPath $script:RedisInstallRoot -Recurse -File -Filter redis-server.exe -ErrorAction SilentlyContinue)
if ($installed.Count -eq 0) {
    New-Item -ItemType Directory -Force -Path (Split-Path $archivePath) | Out-Null
    if (!(Test-Path -LiteralPath $archivePath)) {
        Write-Output 'Downloading Redis 8.2.9 for local Windows development...'
        $downloadPath = $archivePath + '.download'
        & curl.exe --fail --location --silent --show-error --retry 2 --connect-timeout 15 --max-time 300 `
            --continue-at - --output $downloadPath ("https://github.com/redis-windows/redis-windows/releases/download/8.2.9/$archiveName")
        if ($LASTEXITCODE -ne 0) { throw "Redis download failed; retry the script to resume: $downloadPath" }
        if ((Get-FileHash -LiteralPath $downloadPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $sha256) {
            throw "Redis download checksum mismatch. Package was not extracted: $downloadPath"
        }
        Move-Item -LiteralPath $downloadPath -Destination $archivePath
    }
    if ((Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $sha256) {
        throw "Redis download checksum mismatch. Package was not extracted: $archivePath"
    }
    Expand-Archive -LiteralPath $archivePath -DestinationPath $script:RedisInstallRoot -Force
}

$redisProcess = Get-ProjectRedisListener $Port
if ($null -eq $redisProcess) {
    New-Item -ItemType Directory -Force -Path $script:RedisDataRoot | Out-Null
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot '../redis/redis.conf') -Destination (Join-Path $script:RedisDataRoot 'redis.conf') -Force
    $redisProcess = Start-Process -FilePath (Get-RedisExecutable 'redis-server.exe') `
        -ArgumentList @('redis.conf', '--port', $Port) -WorkingDirectory $script:RedisDataRoot -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $script:RedisDataRoot 'stdout.log') `
        -RedirectStandardError (Join-Path $script:RedisDataRoot 'stderr.log') -PassThru
    $ready = $false
    $deadline = [DateTime]::UtcNow.AddSeconds(20)
    while ([DateTime]::UtcNow -lt $deadline) {
        $redisProcess.Refresh()
        if ($redisProcess.HasExited) { throw "Redis exited. Check $script:RedisDataRoot/redis.log and stderr.log" }
        try { $ready = (Invoke-ProjectRedis $Port @('PING')) -eq 'PONG' } catch { $ready = $false }
        if ($ready) { break }
        Start-Sleep -Milliseconds 250
    }
    if (!$ready) { throw "Redis did not become ready within 20 seconds. Check $script:RedisDataRoot" }
}
if ((Invoke-ProjectRedis $Port @('PING')) -ne 'PONG') { throw 'Redis health check failed.' }

if ($EnableAutoStart) {
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($script:RedisStartupLink)
    if ((Test-Path -LiteralPath $script:RedisStartupLink) -and
            !$shortcut.Arguments.Contains((Join-Path $PSScriptRoot 'start-redis.ps1'))) {
        throw 'Startup shortcut belongs to a different project; it was not replaced.'
    }
    $shortcut.TargetPath = Join-Path $PSHOME 'powershell.exe'
    $shortcut.Arguments = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{0}" -Port {1}' -f (Join-Path $PSScriptRoot 'start-redis.ps1'), $Port
    $shortcut.WorkingDirectory = $script:RedisProjectRoot
    $shortcut.WindowStyle = 7
    $shortcut.Description = 'Start the IT ticket project Redis cache after sign-in'
    $shortcut.Save()
    Write-Output "Current-user sign-in autostart enabled: $script:RedisStartupLink"
}
Write-Output "Redis ready at 127.0.0.1:$Port (PID $($redisProcess.Id)); data/logs: $script:RedisDataRoot"
