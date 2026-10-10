# 服务器部署指南（Docker Compose + GHCR）

> 目标拓扑：GitHub Actions 构建镜像推到 GHCR → 服务器 `/opt/it-ticket` 下 `docker compose` 拉取启动全部微服务；MySQL 沿用远程库（不起本地容器）；服务器上自建 Nacos + Redis + Elasticsearch；**两个模型服务（consultation-service 对话模型、rag-service 向量模型）的 base-url 和 api-key 只写在服务器本地的 `.env`，不进仓库、不进镜像**。

## 一、前置条件

服务器（Linux x86_64）上需要：

```bash
# Docker 20.10+ 与 compose v2 插件（官方源安装自带）
docker --version && docker compose version
```

首次登录 GHCR（私有镜像需要 PAT 拉取）：

```bash
# PAT 创建：GitHub → Settings → Developer settings → Personal access tokens (classic)
# 勾选 read:packages 即可，其他权限都不用给
echo "ghp_xxxxxxxxxxxx" | docker login ghcr.io -u <GitHub用户名> --password-stdin
```

> 登录态存在 `~/.docker/config.json`，长期有效；换 PAT 后重新 login 覆盖。

## 二、首次部署

```bash
# 1. 建目录并上传文件（deploy/docker-compose.yml、deploy/.env.example）
mkdir -p /opt/it-ticket
# 从本机推送（示例）：
# scp it-ticket-cloud/deploy/docker-compose.yml root@<服务器>:/opt/it-ticket/
# scp it-ticket-cloud/deploy/.env.example            root@<服务器>:/opt/it-ticket/
cd /opt/it-ticket

# 2. 生成并填写 .env（模型 key 只在这里）
cp .env.example .env
chmod 600 .env
vim .env    # 填 IMAGE_PREFIX / MYSQL_PASSWORD / JWT_SECRET / REDIS_PASSWORD / 模型 key

# 3. 启动全部服务（基础设施 + 微服务）
docker compose up -d

# 4. 观察启动
docker compose ps
docker compose logs -f gateway consultation-service rag-service
```

启动顺序由 `depends_on` 编排：Nacos → 各微服务；rag-service 额外等 ES 与 Redis 健康。

## 三、验证

```bash
# 网关健康
curl http://127.0.0.1:28080/api/health
# 登录接口（种子账号见主 README）
curl -X POST http://127.0.0.1:28080/api/v1/users/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"..."}'

# AI 客服是否拿到模型凭据：未配置 key 时回答会降级为 NOT_CONFIGURED
docker compose logs consultation-service | grep -i "ai\|model"
```

端口暴露情况：

| 端口 | 服务 | 绑定 |
|---|---|---|
| 28080 | gateway（唯一对外入口） | 0.0.0.0 |
| 8848/9848 | Nacos 控制台 | 127.0.0.1（SSH 隧道访问） |
| 6379 | Redis | 127.0.0.1 |
| 9200 | Elasticsearch | 127.0.0.1 |

在本地机器访问 Nacos 控制台：`ssh -L 8848:127.0.0.1:8848 root@<服务器>` 后打开 `http://localhost:8848/nacos`。

## 四、日常更新（代码合并到 main 后）

```bash
cd /opt/it-ticket
docker compose pull          # 拉最新镜像
docker compose up -d         # 只重建镜像变化了的容器
docker image prune -f        # 清理旧镜像层
```

CI 侧无需操作：push 到 main 且改动了 `it-ticket-cloud/` 会自动构建 5 个镜像并打 `latest` + 短 sha 两个 tag。

回滚到某次提交（sha tag 保留在 GHCR）：

```bash
docker compose pull && IMAGE_TAG=<sha> docker compose up -d
```

> 注：compose 里镜像写死 `:latest`；如需按 sha 回滚，临时改 `docker-compose.yml` 里的 tag，或用 `docker tag` 覆盖本地 latest。

## 五、模型凭据的脱敏边界

- 仓库内：只有 `.env.example` 模板（占位符），`ai-secrets.yml` 已 gitignore。
- 镜像内：`.dockerignore` 排除 `**/ai-secrets.yml`；Spring 的 `optional:file:` 导入在文件缺失时静默跳过，环境变量注入优先级足以生效。
- 服务器上：真实值只在 `/opt/it-ticket/.env`（权限 600，root 可读）。`docker compose config` 会展开变量，注意不要把输出贴给别人。
- 换 key：改 `.env` → `docker compose up -d consultation-service rag-service`。

## 六、常见问题

**容器起不来，日志 `MYSQL_PASSWORD ... 请在 .env`** —— `.env` 没填或不在 compose 同目录。

**consultation 回答 NOT_CONFIGURED** —— `AI_BASE_URL`/`AI_API_KEY` 未注入。`docker compose exec consultation-service env | grep AI_` 检查。

**rag 检索报 ES 连接失败** —— `docker compose ps` 看 elasticsearch 是否 healthy；ES 首启需要 30 秒+。

**拉镜像 401** —— PAT 过期或没勾 `read:packages`，重新登录 GHCR。

**Nacos 起了但服务注册不上** —— 确认 `NACOS_ADDR=nacos:8848` 已在 compose 的公共环境里（默认已配）。

**想换远程库地址** —— 只改 `.env` 的 `MYSQL_HOST/PORT/DB/USERNAME/PASSWORD`，重启全部：`docker compose up -d`。
