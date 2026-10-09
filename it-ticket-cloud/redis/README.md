# 项目 Redis 缓存服务

本地服务地址：`127.0.0.1:6379`，数据库 `0`。知识服务的 `spring.data.redis`
默认连接此地址，缓存键 `its:{env}:cache:ai-feedback:{interactionId}`，TTL 300 秒。
Redis 保存可重建的处理标记；反馈、知识版本和审核结果仍持久化到 MySQL。

## Windows 本地开发

从仓库根目录执行：

```powershell
# 首次自动下载、核验 SHA-256、解压并后台启动；重复执行会检查现有实例。
powershell -NoProfile -ExecutionPolicy Bypass -File it-ticket-cloud/scripts/start-redis.ps1 -EnableAutoStart

# PING、写入、读取、TTL 及持久化状态检查，测试键自动删除。
powershell -NoProfile -ExecutionPolicy Bypass -File it-ticket-cloud/scripts/check-redis.ps1

# 优雅停止并落盘；不清除数据。
powershell -NoProfile -ExecutionPolicy Bypass -File it-ticket-cloud/scripts/stop-redis.ps1

# 停止，同时取消当前用户登录自动启动。
powershell -NoProfile -ExecutionPolicy Bypass -File it-ticket-cloud/scripts/stop-redis.ps1 -DisableAutoStart
```

重启顺序为 `stop-redis.ps1` → `start-redis.ps1`。`start-all.cmd` 也会启动 Redis。
`-EnableAutoStart` 在当前用户 Startup 文件夹创建 `ITTicket-Redis.lnk`，登录后隐藏窗口启动；
这是用户级启动入口，不是 Windows 系统服务，也不会在未登录时启动。
脚本只管理本项目安装目录中的进程，其他进程占用端口时直接报错。
需要其他端口时，上述脚本均可传 `-Port 6380`，并设置知识服务 `REDIS_PORT=6380`。
非默认端口使用独立目录 `.devtools/redis-data-6380/` 和启动项 `ITTicket-Redis-6380.lnk`，
不会与 6379 实例共享 AOF、RDB 或日志。

| 内容 | 位置/默认值 |
| --- | --- |
| Windows 工具 | `.devtools/redis-8.2.9/` |
| 数据、实际配置、日志 | `.devtools/redis-data/` |
| 配置模板 | `it-ticket-cloud/redis/redis.conf` |
| 监听 | 仅 `127.0.0.1`，开启 protected-mode |
| 内存上限 / 淘汰策略 | `256mb` / `allkeys-lru` |
| 持久化 | AOF `everysec` + RDB；优雅停止时保存 |

配置模板会在启动时复制到数据目录；持久数据不会被覆盖。
本地默认无需密码，端口仅本机可访问。连接其他 Redis 时通过 `REDIS_HOST`、
`REDIS_PORT`、`REDIS_PASSWORD`、`REDIS_DATABASE` 配置知识服务。
不要直接修改本地配置以开放外部访问。

Windows 便携包使用 [redis-windows 8.2.9 社区构建](https://github.com/redis-windows/redis-windows/releases/tag/8.2.9)，
固定 SHA-256：`dcff676e861a4ae0a9854556239398e77a7469c9379af64a4a76798d166d1aa0`。
该构建适用于本地开发；Linux/Docker 环境使用下方官方镜像。

## Docker 环境

```sh
cd it-ticket-cloud
docker compose up -d redis
docker compose exec redis redis-cli ping
```

Compose 使用官方 `redis:8.2.9-alpine`，设置 `restart: unless-stopped`、健康检查及命名持久卷。
宿主机端口仅映射到 `127.0.0.1`，无需启动可选 MySQL 服务。
可通过 `REDIS_PASSWORD` 设置认证；配置密码后检查时使用
`docker compose exec redis sh -c 'REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli ping'`。
此环境尚未安装 Docker Desktop 时，请使用 Windows 本地脚本。

## 验证与故障恢复

真实 Spring Redis 客户端集成测试（使用独立随机测试键，不改变业务反馈）：

```powershell
$env:AI_FEEDBACK_REDIS_TEST = 'true'
mvn -f it-ticket-cloud/pom.xml -pl rag-service -am -Dtest=AiFeedbackRedisTest -Dsurefire.failIfNoSpecifiedTests=false test
```

Redis 故障时知识服务回退 MySQL，最多 30 秒后恢复尝试；Redis 恢复不需要重启业务服务。
当没有待消费反馈时，不会持续写入新的缓存键，这是正常行为。
排障先执行检查脚本，再查看 `.devtools/redis-data/redis.log` 和 `stderr.log`。
禁止使用 `FLUSHALL` / `FLUSHDB` 清理业务缓存。

参考：[Redis 持久化](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)、
[内存淘汰策略](https://redis.io/docs/latest/develop/reference/eviction/)。
