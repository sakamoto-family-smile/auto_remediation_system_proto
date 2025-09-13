# エラー自動調査・改修システム プロトタイプ

## 概要
GCP上でWebサービスのエラーを自動検知し、cursor-cli（Claude Sonnet-4）を使用してコード改修を行い、GitHub上にPRを自動作成するシステムのプロトタイプです。

## アーキテクチャ
```
├── backend/           # Python FastAPI バックエンド
├── frontend/          # React TypeScript フロントエンド
├── remediation/       # cursor-cli 自動改修エージェント
├── infrastructure/    # GCP インフラ設定（Terraform）
├── database/          # データベーススキーマ・マイグレーション
├── monitoring/        # エラー監視・通知システム
├── slack-bot/         # Slack統合・承認フロー
└── docker/           # Docker設定ファイル
```

## 技術スタック

### バックエンド
- **Python 3.11** + **FastAPI**
- **SQLAlchemy** + **PostgreSQL**
- **Vertex AI API**（Claude Sonnet-4）
- **Firebase Auth**

### フロントエンド
- **React 18** + **TypeScript**
- **Material-UI**
- **React Query**

### インフラ
- **GCP Cloud Run**（フロント・バックエンド）
- **Cloud Run Jobs**（改修エージェント）
- **Cloud Functions**（エラートリガー）
- **Cloud SQL**（PostgreSQL）

### 統合サービス
- **cursor-cli** + **Claude Sonnet-4**
- **GitHub API**
- **Slack API**

## 開発フェーズ

### Phase 1: 基盤構築 ✅
- [x] プロジェクト構造作成
- [ ] バックエンドAPI基盤
- [ ] データベーススキーマ
- [ ] 基本認証機能

### Phase 2: コア機能実装
- [ ] cursor-cli統合
- [ ] エラー検知・分析
- [ ] 基本UI実装

### Phase 3: 自動改修機能
- [ ] 改修エージェント
- [ ] GitHub PR自動化
- [ ] テスト実行機能

### Phase 4: 統合・UX改善
- [ ] Slack統合
- [ ] 承認フロー
- [ ] 監査ログ

## セットアップ

### 前提条件
- Python 3.11+
- Node.js 18+
- Docker
- GCP CLI
- cursor-cli

### 開発環境構築
```bash
# バックエンド
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# フロントエンド
cd frontend
npm install

# Docker環境
docker-compose up -d
```

## 予算制約
- 月額上限: 10万円
- リソース最適化設定済み
- コスト監視アラート設定

## セキュリティ
- Google OAuth認証
- Secret Manager使用
- 監査ログ完備
- データ暗号化

## 監査・コンプライアンス
- 全操作の監査証跡（1年間保持）
- PRレビュー履歴
- エラー対応履歴
- ユーザー操作ログ
