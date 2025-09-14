# 🐳 Docker Compose 起動ガイド

## 📋 概要

このシステムは`docker-compose up`一つのコマンドで全てのコンポーネントを起動できます。

## 🚀 起動パターン

### 1. 基本システム（推奨）
```bash
docker-compose up
```
**含まれるサービス:**
- ✅ PostgreSQL データベース
- ✅ Redis キャッシュ
- ✅ FastAPI バックエンド（ポート: 8000）
- ✅ 改修エージェント

### 2. フロントエンド付き
```bash
docker-compose --profile frontend up
```
**追加で含まれるサービス:**
- ✅ React フロントエンド（ポート: 3000）

### 3. 全コンポーネント
```bash
docker-compose --profile full up
```
**全てのサービスが起動します**

## 🔧 環境変数（オプション）

実際のAPI連携をテストする場合は、以下の環境変数を設定：

```bash
# .env ファイルを作成
cat > .env << EOF
CURSOR_API_KEY=your-cursor-api-key
GITHUB_TOKEN=your-github-token
SLACK_BOT_TOKEN=your-slack-bot-token
SLACK_VERIFICATION_TOKEN=your-slack-verification-token
EOF

# 起動
docker-compose up
```

## 📊 サービス確認

### API エンドポイント
- **バックエンド**: http://localhost:8000
- **API ドキュメント**: http://localhost:8000/docs
- **ヘルスチェック**: http://localhost:8000/health

### フロントエンド（--profile frontend使用時）
- **React アプリ**: http://localhost:3000

### データベース
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## 🤖 改修エージェント

改修エージェントは自動的に起動し、以下の機能を提供：

- ✅ **エラー分析**: AI駆動の根本原因分析
- ✅ **修正生成**: コンテキスト理解による適切な修正
- ✅ **GitHub統合**: 自動PR作成・管理
- ✅ **テスト実行**: 修正後の品質チェック

## 🔄 ログ確認

```bash
# 全サービスのログ
docker-compose logs -f

# 特定サービスのログ
docker-compose logs -f backend
docker-compose logs -f remediation-agent
```

## 🛑 停止・クリーンアップ

```bash
# 停止
docker-compose down

# データも削除
docker-compose down -v

# イメージも削除
docker-compose down -v --rmi all
```

## 🚨 トラブルシューティング

### ポート競合
```bash
# 使用中のポートを確認
lsof -i :8000
lsof -i :5432
lsof -i :6379
```

### データベース接続エラー
```bash
# データベースの状態確認
docker-compose ps db
docker-compose logs db
```

### ビルドエラー
```bash
# クリーンビルド
docker-compose build --no-cache
```

## 🎯 開発ワークフロー

1. **起動**: `docker-compose up`
2. **確認**: http://localhost:8000/docs でAPI確認
3. **テスト**: 改修エージェントの動作確認
4. **開発**: コードを編集（ホットリロード対応）
5. **停止**: `Ctrl+C` または `docker-compose down`

---

**💡 ヒント**: 初回起動時はDockerイメージのビルドに時間がかかります。2回目以降は高速に起動します。
