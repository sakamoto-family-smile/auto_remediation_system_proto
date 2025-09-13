# Auto Remediation System セットアップガイド

## 🚀 クイックスタート

### 前提条件
- Docker & Docker Compose
- cursor-cli（最新版）
- GitHub アカウント
- Google Cloud Platform アカウント（本番環境用）

### 1. リポジトリクローン
```bash
cd auto_remediation_system
```

### 2. 環境変数設定
```bash
# 環境変数ファイル作成
cp env.example .env

# 必要な値を設定
vim .env
```

**必須設定項目:**
- `CURSOR_API_KEY`: cursor-cli API キー
- `GITHUB_TOKEN`: GitHub Personal Access Token
- `SECRET_KEY`: JWT署名用秘密鍵（ランダム生成推奨）

### 3. 開発環境起動
```bash
# データベース・バックエンド起動
docker-compose up -d db redis backend

# ヘルスチェック
curl http://localhost:8000/health
```

### 4. cursor-cli接続テスト
```bash
# 改修エージェント起動（テスト）
docker-compose --profile remediation run --rm remediation-agent --test
```

## 📋 詳細セットアップ

### cursor-cli APIキー取得
1. Cursor ダッシュボードにログイン
2. API Keys セクションでキー生成
3. `.env` ファイルに `CURSOR_API_KEY` として設定

### GitHub トークン設定
1. GitHub Settings > Developer settings > Personal access tokens
2. 以下の権限で新規トークン作成:
   - `repo` (フルアクセス)
   - `pull_requests:write`
   - `contents:write`
3. `.env` ファイルに `GITHUB_TOKEN` として設定

### Slack連携（オプション）
1. Slack App作成
2. Bot Token取得
3. `.env` ファイルに設定:
   - `SLACK_BOT_TOKEN`
   - `SLACK_SIGNING_SECRET`

## 🔧 開発環境

### バックエンド開発
```bash
# 開発モードで起動（ホットリロード有効）
docker-compose up backend

# ログ確認
docker-compose logs -f backend

# API ドキュメント
open http://localhost:8000/docs
```

### データベース操作
```bash
# PostgreSQL接続
docker-compose exec db psql -U postgres -d auto_remediation

# マイグレーション実行（将来）
docker-compose exec backend alembic upgrade head
```

### 改修エージェントテスト
```bash
# 単体テスト
docker-compose --profile remediation run --rm remediation-agent python -m pytest

# 統合テスト（サンプルエラー処理）
docker-compose --profile remediation run --rm remediation-agent \
  python -m remediation.cursor_cli_agent test-fix
```

## 🏗️ 本番環境デプロイ

### Google Cloud準備
```bash
# プロジェクト作成
gcloud projects create your-project-id

# 必要なAPI有効化
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  cloudbuild.googleapis.com \
  aiplatform.googleapis.com
```

### Cloud Run デプロイ
```bash
# バックエンドビルド・デプロイ
gcloud run deploy auto-remediation-backend \
  --source . \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --set-env-vars DATABASE_URL=$DATABASE_URL,CURSOR_API_KEY=$CURSOR_API_KEY

# 改修エージェント（Cloud Run Jobs）
gcloud run jobs create auto-remediation-agent \
  --image gcr.io/your-project/remediation-agent \
  --region asia-northeast1 \
  --set-env-vars CURSOR_API_KEY=$CURSOR_API_KEY
```

### Cloud SQL セットアップ
```bash
# PostgreSQL インスタンス作成
gcloud sql instances create auto-remediation-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=asia-northeast1

# データベース作成
gcloud sql databases create auto_remediation \
  --instance=auto-remediation-db
```

## 🔍 トラブルシューティング

### cursor-cli接続エラー
```bash
# APIキー確認
echo $CURSOR_API_KEY

# cursor-cli バージョン確認
docker-compose exec remediation-agent cursor-agent --version

# 接続テスト
docker-compose exec remediation-agent cursor-agent --test-connection
```

### データベース接続エラー
```bash
# PostgreSQL状態確認
docker-compose ps db

# 接続テスト
docker-compose exec db pg_isready -U postgres

# ログ確認
docker-compose logs db
```

### GitHub API エラー
```bash
# トークン権限確認
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user

# レート制限確認
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/rate_limit
```

## 📊 監視・ログ

### ログ確認
```bash
# 全サービスログ
docker-compose logs -f

# 特定サービス
docker-compose logs -f backend
docker-compose logs -f remediation-agent
```

### メトリクス（本番環境）
- Cloud Monitoring ダッシュボード
- エラー率・レスポンス時間
- cursor-cli実行成功率
- PR作成・マージ率

### 監査ログ
```sql
-- 最近のユーザーアクション
SELECT * FROM audit_logs
WHERE created_at > NOW() - INTERVAL '1 day'
ORDER BY created_at DESC;

-- 改修成功率
SELECT
  status,
  COUNT(*) as count,
  COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentage
FROM remediation_attempts
GROUP BY status;
```

## 🔒 セキュリティ

### 推奨設定
- 強力な `SECRET_KEY` 設定
- GitHub トークンの最小権限
- Secret Manager 使用（本番環境）
- VPC内部通信（本番環境）

### 監査証跡
- 全ユーザーアクションのログ記録
- PR承認・却下履歴
- システム操作ログ（1年間保持）

## 📈 パフォーマンス最適化

### 推奨設定
```yaml
# docker-compose.override.yml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### 監視指標
- API レスポンス時間 < 3秒
- cursor-cli実行時間 < 5分
- データベース接続プール使用率
- メモリ・CPU使用率

## 🆘 サポート

### 問題報告
1. ログファイル収集
2. 環境情報（OS、Docker バージョン）
3. 再現手順
4. 期待動作 vs 実際の動作

### 開発者向けリソース
- [cursor-cli ドキュメント](https://docs.cursor.com/cli)
- [FastAPI ドキュメント](https://fastapi.tiangolo.com/)
- [Google Cloud Run](https://cloud.google.com/run/docs)
