# Auto Remediation System - Frontend Dockerfile
# Multi-stage build

# Build stage
FROM node:18-alpine AS builder

WORKDIR /app

# パッケージファイルコピー
COPY package.json package-lock.json* ./

# 依存関係インストール
RUN npm ci --only=production

# ソースコードコピー
COPY . .

# ビルド実行
RUN npm run build

# Production stage
FROM nginx:alpine

# Nginxカスタム設定
COPY nginx.conf /etc/nginx/nginx.conf

# ビルド成果物コピー
COPY --from=builder /app/dist /usr/share/nginx/html

# 非rootユーザーで実行
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nextjs -u 1001
RUN chown -R nextjs:nodejs /usr/share/nginx/html
RUN chown -R nextjs:nodejs /var/cache/nginx
RUN chown -R nextjs:nodejs /var/log/nginx
RUN chown -R nextjs:nodejs /etc/nginx/conf.d
RUN touch /var/run/nginx.pid
RUN chown -R nextjs:nodejs /var/run/nginx.pid

USER nextjs

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

# ポート公開
EXPOSE 3000

# 起動コマンド
CMD ["nginx", "-g", "daemon off;"]
