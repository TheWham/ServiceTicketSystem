# Nacos 配置中心接入说明

## 已完成改造（代码侧）

1. **三个模块 pom.xml**：`spring-cloud-starter-alibaba-nacos-discovery` 旁新增 `spring-cloud-starter-alibaba-nacos-config` 依赖
2. **三个 application.yml 瘦身**：只留 `server.port` + 应用名 + Nacos 地址 + `spring.config.import`；业务配置全部上收 Nacos

## Nacos 控制台导入步骤

Nacos 地址：`http://127.0.0.1:8848/nacos`（默认账号 nacos/nacos）

进入 **配置管理 → 配置列表 → + 新建配置**，逐个创建以下 4 个配置：

| DataId | Group | 配置格式 | 内容来源 |
|---|---|---|---|
| `common-config.yaml` | DEFAULT_GROUP | YAML | `nacos-config/common-config.yaml` |
| `gateway.yaml` | DEFAULT_GROUP | YAML | `nacos-config/gateway.yaml` |
| `ticket-service.yaml` | DEFAULT_GROUP | YAML | `nacos-config/ticket-service.yaml` |
| `user-service.yaml` | DEFAULT_GROUP | YAML | `nacos-config/user-service.yaml` |

**一键导入（推荐）**：已打好 `nacos-config-import.zip`（Nacos 要求的 `DEFAULT_GROUP/{dataId}` 结构）。控制台 → 配置管理 → 配置列表 → **导入配置** → 选择该 zip → 一次导入 4 个配置。

重新打包命令（改动配置后）：
```bash
cd nacos-config
python -c "import zipfile; [zipfile.ZipFile('nacos-config-import.zip','a',zipfile.ZIP_DEFLATED).write(f, f'DEFAULT_GROUP/{f}') for f in ['common-config.yaml','gateway.yaml','ticket-service.yaml','user-service.yaml']]"
```

## DataId 命名规则

```
${spring.application.name}-${spring.profiles.active}.${file-extension}
```

- 当前无 profile → 拉取 `gateway.yaml`
- 启动加 `-Dspring.profiles.active=dev` → 拉取 `gateway-dev.yaml`（多环境时按此建 dev/prod 两套）

## 配置优先级（高 → 低）

1. Nacos 远程配置（gateway.yaml 等）
2. shared-configs（common-config.yaml）
3. 本地 application.yml（只剩启动必需项，基本不再写业务配置）

## 动态刷新

- `@Value` / `@ConfigurationProperties` 标注的 Bean，加 `@RefreshScope` 后改 Nacos 配置**免重启生效**
- gateway 路由（spring.cloud.gateway.routes）天然支持动态刷新——**改路由不用重启 gateway**，这是本次接入最直接的收益

## 注意事项

1. **本地 yml 必须保留**：`server.port`、`spring.application.name`、`spring.cloud.nacos.*`、`spring.config.import`——这些是「连得上 Nacos」的前提，删了就连不上配置中心了
2. **`optional:nacos:` 前缀**：Nacos 连不上时不阻断启动（用本地兜底）；生产建议去掉 `optional:` 让配置缺失直接失败，避免静默用错配置
3. **敏感配置**：数据库密码、JWT 密钥现在走 `${MYSQL_PASSWORD}` / `${JWT_SECRET}` 环境变量注入，**不要**把真实密码硬编码进 Nacos
4. 首次启动前**先在 Nacos 建好 4 个配置**，否则服务会用本地空配置启动（数据源等都缺失）
