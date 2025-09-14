#!/bin/bash

# 改修エージェント起動スクリプト

set -e

echo "🤖 Auto Remediation Agent Starting..."

# 環境変数チェック
if [ -z "$CURSOR_API_KEY" ]; then
    echo "Warning: CURSOR_API_KEY is not set"
fi

if [ -z "$GITHUB_TOKEN" ]; then
    echo "Warning: GITHUB_TOKEN is not set"
fi

# データベース接続待機
echo "Waiting for database connection..."
python -c "
import asyncio
import sys
import os
sys.path.append('/app')

from app.core.database import engine

async def wait_for_db():
    max_retries = 30
    retry_count = 0

    while retry_count < max_retries:
        try:
            async with engine.begin() as conn:
                await conn.execute('SELECT 1')
            print('✅ Database connection successful')
            return
        except Exception as e:
            retry_count += 1
            print(f'Database connection attempt {retry_count}/{max_retries} failed: {e}')
            await asyncio.sleep(2)

    print('❌ Failed to connect to database after 30 attempts')
    sys.exit(1)

asyncio.run(wait_for_db())
"

# 改修エージェントを起動
echo "🚀 Starting remediation agent..."
cd /app
python -m remediation.cursor_cli_agent

# ログ出力（デバッグ用）
echo "Remediation agent process completed"