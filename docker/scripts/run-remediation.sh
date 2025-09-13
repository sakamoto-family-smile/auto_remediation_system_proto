#!/bin/bash

# Auto Remediation Agent起動スクリプト

set -e

echo "Starting Auto Remediation Agent..."

# 環境変数チェック
if [ -z "$CURSOR_API_KEY" ]; then
    echo "ERROR: CURSOR_API_KEY environment variable is required"
    exit 1
fi

if [ -z "$GITHUB_TOKEN" ]; then
    echo "ERROR: GITHUB_TOKEN environment variable is required"
    exit 1
fi

# cursor-cli接続テスト
echo "Testing cursor-cli connection..."
if ! cursor-agent --version; then
    echo "ERROR: cursor-cli is not properly installed"
    exit 1
fi

echo "cursor-cli connection successful"

# Python改修エージェント起動
echo "Starting remediation agent..."
cd /app
python -m remediation.cursor_cli_agent "$@"
