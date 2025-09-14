# Auto Remediation System - Backend Dockerfile
FROM python:3.11-slim

# 作業ディレクトリ設定
WORKDIR /app

# システムパッケージ更新とインストール
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Python依存関係インストール
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードコピー
COPY . .

# 非rootユーザー作成
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app
USER appuser

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ポート公開
EXPOSE 8000

# 起動コマンド
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
