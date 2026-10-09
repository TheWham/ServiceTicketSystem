param([ValidateRange(1024, 65535)][int]$Port = 6379)
. (Join-Path $PSScriptRoot 'redis-common.ps1')
Set-ProjectRedisPort $Port
$redisProcess = Get-ProjectRedisListener $Port
if ($null -eq $redisProcess) { throw "Project Redis is not running on 127.0.0.1:$Port" }
if ((Invoke-ProjectRedis $Port @('PING')) -ne 'PONG') { throw 'Redis PING failed.' }
$probe = 'its:dev:health:redis:' + [guid]::NewGuid().ToString('N')
try {
    if ((Invoke-ProjectRedis $Port @('SET', $probe, 'ok', 'EX', '10')) -ne 'OK') { throw 'Redis SET failed.' }
    if ((Invoke-ProjectRedis $Port @('GET', $probe)) -ne 'ok') { throw 'Redis GET failed.' }
    $ttl = [int](Invoke-ProjectRedis $Port @('TTL', $probe))
    if ($ttl -le 0 -or $ttl -gt 10) { throw 'Redis TTL is invalid.' }
    Write-Output "Redis healthy: PING/SET/GET/TTL passed; PID $($redisProcess.Id), port $Port."
    Invoke-ProjectRedis $Port @('INFO', 'server') | Select-String '^redis_version:'
    Invoke-ProjectRedis $Port @('INFO', 'memory') | Select-String '^(used_memory_human|maxmemory_human|maxmemory_policy):'
    Invoke-ProjectRedis $Port @('INFO', 'persistence') | Select-String '^(aof_enabled|aof_last_write_status|rdb_last_bgsave_status):'
} finally {
    Invoke-ProjectRedis $Port @('DEL', $probe) | Out-Null
}
