# ============================================================
# IT 工单系统前端生产镜像（多阶段构建）
# 阶段 1：Node 构建静态产物（vite build → dist/）
# 阶段 2：nginx 托管静态资源，并把 /api 反向代理到后端 gateway
# 构建上下文：frontend/
# ============================================================

# ---------- 阶段 1：构建 ----------
FROM node:20-alpine AS builder
WORKDIR /app

# 1) 先拷 package 清单，利用缓存安装依赖
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

# 2) 拷贝源码并构建
COPY . .
RUN npm run build

# ---------- 阶段 2：运行 ----------
FROM nginx:1.27-alpine
LABEL org.opencontainers.image.title="it-ticket-frontend"

# 自定义 nginx 站点配置（含 /api 反代）
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 静态产物
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
