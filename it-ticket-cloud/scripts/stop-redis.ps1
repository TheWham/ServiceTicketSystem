param(
    [ValidateRange(1024, 65535)][int]$Port = 6379,
    [switch]$DisableAutoStart
)
. (Join-Path $PSScriptRoot 'redis-common.ps1')
Set-ProjectRedisPort $Port
$redisProcess = Get-ProjectRedisListener $Port
if ($null -ne $redisProcess) {
    Invoke-ProjectRedis $Port @('SHUTDOWN', 'SAVE') | Out-Null
    Wait-Process -Id $redisProcess.Id -Timeout 20 -ErrorAction SilentlyContinue
    if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
        throw "Redis is still listening on port $Port; check logs."
    }
    Write-Output 'Redis stopped gracefully; persisted data retained.'
} else {
    Write-Output 'Redis is already stopped.'
}
if ($DisableAutoStart -and (Test-Path -LiteralPath $script:RedisStartupLink)) {
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($script:RedisStartupLink)
    if (!$shortcut.Arguments.Contains((Join-Path $PSScriptRoot 'start-redis.ps1'))) {
        throw 'Startup shortcut belongs to a different project; it was not removed.'
    }
    Remove-Item -LiteralPath $script:RedisStartupLink
    Write-Output 'Current-user sign-in autostart disabled.'
}
