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

### Phase 1: 基盤構築 ✅ (完了)
- [x] プロジェクト構造作成
- [x] バックエンドAPI基盤（FastAPI + PostgreSQL）
- [x] データベーススキーマ（User, Organization, Chat, Error, Audit models）
- [x] 基本認証機能（Firebase Auth + JWT）
- [x] テスト環境構築（pytest + テストケース）
- [x] 開発ツール設定（black, isort, mypy, pre-commit）

### Phase 2: コア機能実装 ✅ (完了)
- [x] cursor-cli統合（基本エージェント実装済み）
- [x] エラー検知・分析（モデル実装済み）
- [x] 基本UI実装（React + Material-UI）
- [x] チャット機能API（完全実装）
- [x] エラー管理API（完全実装）
- [x] Firebase認証統合

### Phase 3: 自動改修機能 🚧 (部分実装)
- [x] 改修エージェント（cursor-cli統合部分実装済み）
- [ ] GitHub PR自動化（未実装）
- [ ] テスト実行機能（未実装）
- [ ] 改修API エンドポイント（未実装）

### Phase 4: 統合・UX改善 ❌ (未実装)
- [ ] Slack統合（基本構造のみ）
- [ ] 承認フロー
- [ ] 監査ログ（モデルのみ）
- [ ] フロントエンド実装
- [ ] GCP デプロイメント設定

## 現在の実装状況詳細

### ✅ 実装完了
- **認証システム**: Firebase Auth + JWT完全実装
- **データベース**: 全モデル（User, Chat, Error, Audit等）実装
- **バックエンド基盤**: FastAPI + SQLAlchemy + 設定管理
- **テスト環境**: 包括的テストスイート + CI/CD設定
- **開発環境**: コード品質ツール完備
- **APIエンドポイント**: 認証・チャット・エラー管理完全実装
- **フロントエンド**: React + Material-UI基本UI実装
- **cursor-cli エージェント**: エラー解析・修正生成の基本機能

### 🚧 部分実装
- **LLM統合**: チャット機能でのVertex AI連携（準備済み、接続待ち）

### ❌ 未実装
- **GitHub統合**: PR自動作成機能
- **Slack統合**: 通知・承認フロー
- **エラー監視**: リアルタイム検知システム
- **GCPデプロイ**: インフラ設定
- **エラー管理UI**: フロントエンドエラー管理画面

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
