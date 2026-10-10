# ==============================================================================
# IT 工单系统微服务通用镜像
# 一个 Dockerfile 构建全部 5 个服务，用 build-arg 选择模块：
#   docker build --build-arg MODULE=gateway --build-arg SERVICE_PORT=8080 \
#                -t it-ticket-gateway .
#
# 多阶段构建：
#   1) deps    — 只拷 pom，预热整个 Maven 本地仓库（pom 不变则此层长期缓存）
#   2) build   — 拷源码，-pl <MODULE> -am 打 boot jar（跳测试，测试在 CI 单独跑）
#   3) runtime — JRE 17 精简运行时，非 root，tini 优雅停机
# ==============================================================================

# ---------- 阶段 1：依赖预热（层缓存） ----------
FROM maven:3.9-eclipse-temurin-17 AS deps
WORKDIR /build

# 只拷 pom：源码改动不会让下载依赖的层失效
COPY pom.xml .
COPY common/pom.xml common/
COPY common-web/pom.xml common-web/
COPY gateway/pom.xml gateway/
COPY user-service/pom.xml user-service/
COPY ticket-service/pom.xml ticket-service/
COPY rag-service/pom.xml rag-service/
COPY consultation-service/pom.xml consultation-service/

# 预热依赖到 /root/.m2（ai-service 是遗留目录，不在 <modules>，不会进 reactor）
RUN mvn -q dependency:go-offline -DskipTests || true

# ---------- 阶段 2：构建 ----------
FROM maven:3.9-eclipse-temurin-17 AS build
ARG MODULE
WORKDIR /build

# MODULE 未传时立即失败，避免空跑
RUN test -n "$MODULE" || { echo "ERROR: build-arg MODULE is required" \
  "(gateway|user-service|ticket-service|rag-service|consultation-service)" >&2; exit 1; }

# 复用阶段 1 预热的本地仓库
COPY --from=deps /root/.m2 /root/.m2

COPY . .
RUN mvn -q -pl "$MODULE" -am package -DskipTests -T 1C

# ---------- 阶段 3：运行时 ----------
FROM eclipse-temurin:17-jre-jammy AS runtime
ARG MODULE
ARG SERVICE_PORT=8080
WORKDIR /app

# 时区固定为业务时区；tini 转发信号让 docker stop 触发 Spring 优雅停机
RUN apt-get update \
 && apt-get install -y --no-install-recommends tini tzdata \
 && rm -rf /var/lib/apt/lists/* \
 && ln -snf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
 && echo "Asia/Shanghai" > /etc/timezone

# 非 root 运行；附件目录预授权
RUN groupadd -r app && useradd -r -g app app \
 && mkdir -p /app/data/attachments && chown -R app:app /app

# repackaged boot jar 是 target 下唯一的 *.jar（原始 jar 会改名为 .jar.original）
COPY --from=build --chown=app:app /build/${MODULE}/target/*.jar app.jar

USER app
EXPOSE ${SERVICE_PORT}
ENTRYPOINT ["/usr/bin/tini", "--", "java", "-XX:MaxRAMPercentage=75", "-jar", "app.jar"]
