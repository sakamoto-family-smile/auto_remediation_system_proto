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

# ポート公開（Cloud Runでは動的に設定される）
EXPOSE $PORT

# 起動コマンド（Cloud RunのPORT環境変数を使用）
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
