# Auto Remediation System デモ・テスト手順

## 🎯 デモシナリオ

### シナリオ1: Python構文エラーの自動修正

#### 1. エラー発生シミュレーション
```bash
# サンプルエラーデータ作成
curl -X POST http://localhost:8000/api/v1/errors/incidents \
  -H "Content-Type: application/json" \
  -d '{
    "error_type": "syntax_error",
    "error_message": "SyntaxError: invalid syntax at line 42",
    "file_path": "/app/main.py",
    "line_number": 42,
    "language": "python",
    "severity": "high",
    "service_name": "web-service",
    "stack_trace": "File \"/app/main.py\", line 42\n    if user = None:\n           ^\nSyntaxError: invalid syntax"
  }'
```

#### 2. 自動改修プロセス実行
```bash
# 改修エージェント手動実行
docker-compose --profile remediation run --rm remediation-agent \
  python -c "
import asyncio
from remediation.cursor_cli_agent import CursorCLIAgent

async def demo_fix():
    agent = CursorCLIAgent()

    error_data = {
        'error_type': 'syntax_error',
        'error_message': 'SyntaxError: invalid syntax at line 42',
        'file_path': '/app/main.py',
        'line_number': 42,
        'language': 'python'
    }

    # エラー解析
    analysis = await agent.analyze_error(error_data)
    print('Analysis Result:', analysis)

    # 修正コード生成
    fix = await agent.generate_fix(error_data, analysis)
    print('Fix Result:', fix)

asyncio.run(demo_fix())
"
```

#### 3. 結果確認
```bash
# データベースで結果確認
docker-compose exec db psql -U postgres -d auto_remediation -c "
SELECT
  ei.error_type,
  ei.status,
  ra.status as remediation_status,
  ra.github_pr_url
FROM error_incidents ei
LEFT JOIN remediation_attempts ra ON ei.id = ra.incident_id
ORDER BY ei.created_at DESC
LIMIT 5;
"
```

### シナリオ2: JavaScript論理エラーの修正

#### 1. エラーデータ投入
```bash
curl -X POST http://localhost:8000/api/v1/errors/incidents \
  -H "Content-Type: application/json" \
  -d '{
    "error_type": "logic_error",
    "error_message": "TypeError: Cannot read property \"length\" of undefined",
    "file_path": "/app/utils.js",
    "line_number": 15,
    "language": "javascript",
    "severity": "medium",
    "service_name": "frontend",
    "stack_trace": "TypeError: Cannot read property \"length\" of undefined\n    at processArray (/app/utils.js:15:25)"
  }'
```

#### 2. 改修フロー実行
```bash
# フル改修フロー実行
docker-compose --profile remediation run --rm remediation-agent \
  python -m remediation.full_remediation_demo
```

## 🧪 機能別テスト

### 認証システムテスト

#### 1. Firebase認証シミュレーション
```bash
# 開発環境では認証をスキップ
export TEST_MODE=true

# ユーザー作成テスト
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "firebase_token": "test-token-for-dev"
  }'
```

#### 2. JWT認証テスト
```bash
# JWTトークン取得
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"firebase_token": "test-token"}' | jq -r '.access_token')

# 認証が必要なエンドポイントテスト
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/auth/me
```

### データベース操作テスト

#### 1. CRUD操作確認
```bash
# エラーインシデント一覧取得
curl http://localhost:8000/api/v1/errors/incidents

# 特定インシデント詳細
curl http://localhost:8000/api/v1/errors/incidents/{incident_id}

# 改修履歴確認
curl http://localhost:8000/api/v1/remediation/attempts
```

#### 2. 監査ログ確認
```sql
-- PostgreSQL直接接続
docker-compose exec db psql -U postgres -d auto_remediation

-- 最近のアクション確認
SELECT
  al.action,
  al.resource_type,
  al.created_at,
  u.email
FROM audit_logs al
LEFT JOIN users u ON al.user_id = u.id
ORDER BY al.created_at DESC
LIMIT 10;
```

### cursor-cli統合テスト

#### 1. 接続テスト
```bash
# cursor-cli バージョン確認
docker-compose --profile remediation run --rm remediation-agent \
  cursor-agent --version

# APIキー認証テスト
docker-compose --profile remediation run --rm remediation-agent \
  cursor-agent --test-auth
```

#### 2. 解析テスト
```bash
# サンプルコード解析
docker-compose --profile remediation run --rm remediation-agent \
  python -c "
import asyncio
from remediation.cursor_cli_agent import CursorCLIAgent

async def test_analysis():
    agent = CursorCLIAgent()

    # 簡単な構文エラー
    result = await agent._run_cursor_cli_command(
        command='analyze',
        prompt='Fix this Python syntax error: if x = 5:',
        language='python'
    )
    print('Analysis result:', result)

asyncio.run(test_analysis())
"
```

## 📊 パフォーマンステスト

### 1. 負荷テスト
```bash
# 並行エラー処理テスト
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/v1/errors/incidents \
    -H "Content-Type: application/json" \
    -d "{
      \"error_type\": \"test_error_$i\",
      \"error_message\": \"Test error $i\",
      \"file_path\": \"/app/test$i.py\",
      \"language\": \"python\"
    }" &
done
wait
```

### 2. レスポンス時間測定
```bash
# API レスポンス時間測定
time curl http://localhost:8000/api/v1/errors/incidents

# cursor-cli実行時間測定
time docker-compose --profile remediation run --rm remediation-agent \
  cursor-agent "Fix this simple Python error: print 'hello'"
```

## 🔍 デバッグ・トラブルシューティング

### 1. ログレベル調整
```bash
# デバッグモードで起動
LOG_LEVEL=DEBUG docker-compose up backend

# 詳細ログ出力
docker-compose logs -f --tail=100 backend
```

### 2. 個別コンポーネントテスト
```bash
# データベース接続テスト
docker-compose exec backend python -c "
import asyncio
from app.core.database import init_db
asyncio.run(init_db())
print('Database connection successful')
"

# cursor-cli単体テスト
docker-compose --profile remediation run --rm remediation-agent \
  python -m pytest remediation/tests/ -v
```

### 3. エラー再現テスト
```bash
# 特定エラーパターンの再現
docker-compose --profile remediation run --rm remediation-agent \
  python -c "
from remediation.cursor_cli_agent import CursorCLIAgent
import asyncio

async def reproduce_error():
    agent = CursorCLIAgent()

    # 実際に発生したエラーデータ
    error_data = {
        'error_type': 'syntax_error',
        'error_message': 'your actual error message',
        'file_path': '/path/to/your/file.py',
        'line_number': 42,
        'language': 'python'
    }

    try:
        result = await agent.analyze_error(error_data)
        print('Success:', result)
    except Exception as e:
        print('Error:', e)

asyncio.run(reproduce_error())
"
```

## 📈 成功指標

### 1. 技術指標
- **API レスポンス時間**: < 3秒
- **cursor-cli実行成功率**: > 80%
- **修正コード品質**: Lint通過率 > 90%
- **テスト実行成功率**: > 95%

### 2. ビジネス指標
- **エラー解決時間**: < 15分（簡単なエラー）
- **PR作成成功率**: > 70%
- **開発者承認率**: > 60%
- **自動デプロイ成功率**: > 90%

### 3. 測定方法
```sql
-- 改修成功率
SELECT
  COUNT(CASE WHEN status = 'approved' THEN 1 END) * 100.0 / COUNT(*) as success_rate
FROM remediation_attempts
WHERE created_at > NOW() - INTERVAL '1 day';

-- 平均処理時間
SELECT
  AVG(EXTRACT(EPOCH FROM (completed_at - created_at))/60) as avg_duration_minutes
FROM remediation_attempts
WHERE completed_at IS NOT NULL;
```

## 🎉 デモプレゼンテーション

### 1. 準備
```bash
# デモ環境クリーンアップ
docker-compose down -v
docker-compose up -d db redis backend

# サンプルデータ投入
docker-compose exec db psql -U postgres -d auto_remediation -f /docker-entrypoint-initdb.d/init.sql
```

### 2. ライブデモ手順
1. エラー発生シミュレーション
2. 自動検知・解析プロセス
3. cursor-cli による修正コード生成
4. テスト実行・PR作成
5. 結果確認・承認フロー

### 3. 質疑応答準備
- cursor-cli統合の技術的詳細
- スケーラビリティ・コスト最適化
- セキュリティ・監査機能
- 将来拡張計画
