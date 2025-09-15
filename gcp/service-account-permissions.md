# GCP Service Account 必要権限

## 🎯 基本権限（必須）

### **Vertex AI関連**
- `aiplatform.endpoints.predict` - Vertex AI予測API呼び出し
- `aiplatform.models.predict` - モデル予測実行
- `ml.models.predict` - ML予測API（レガシー）

**推奨IAMロール:**
- `roles/aiplatform.user` - Vertex AI ユーザー

### **Cloud Monitoring関連**
- `monitoring.metricDescriptors.create` - メトリクス定義作成
- `monitoring.metricDescriptors.get` - メトリクス定義取得
- `monitoring.timeSeries.create` - メトリクスデータ書き込み
- `monitoring.timeSeries.list` - メトリクスデータ読み取り

**推奨IAMロール:**
- `roles/monitoring.metricWriter` - メトリクス書き込み
- `roles/monitoring.viewer` - メトリクス読み取り

### **Cloud Logging関連**
- `logging.logEntries.create` - ログエントリ作成
- `logging.logEntries.list` - ログエントリ読み取り
- `logging.logs.list` - ログ一覧取得

**推奨IAMロール:**
- `roles/logging.logWriter` - ログ書き込み
- `roles/logging.viewer` - ログ読み取り

### **Cloud SQL関連**
- `cloudsql.instances.connect` - Cloud SQLインスタンス接続
- `cloudsql.instances.get` - インスタンス情報取得

**推奨IAMロール:**
- `roles/cloudsql.client` - Cloud SQL クライアント

### **Secret Manager関連**
- `secretmanager.versions.access` - シークレットアクセス
- `secretmanager.secrets.get` - シークレット情報取得

**推奨IAMロール:**
- `roles/secretmanager.secretAccessor` - シークレットアクセサー

### **Firebase関連**
- `firebase.projects.get` - Firebaseプロジェクト情報
- `identitytoolkit.tenants.get` - Identity Toolkit（Firebase Auth）

**推奨IAMロール:**
- `roles/firebase.admin` - Firebase管理者（開発環境）
- `roles/firebase.viewer` - Firebase閲覧者（本番環境推奨）

## 🔧 カスタムロール（推奨）

より細かい権限制御のため、カスタムロールを作成することを推奨：

```yaml
title: "Auto Remediation Service Account"
description: "Custom role for Auto Remediation System"
stage: "GA"
includedPermissions:
  # Vertex AI
  - aiplatform.endpoints.predict
  - aiplatform.models.predict

  # Monitoring
  - monitoring.metricDescriptors.create
  - monitoring.metricDescriptors.get
  - monitoring.timeSeries.create
  - monitoring.timeSeries.list

  # Logging
  - logging.logEntries.create
  - logging.logEntries.list

  # Cloud SQL
  - cloudsql.instances.connect
  - cloudsql.instances.get

  # Secret Manager
  - secretmanager.versions.access
  - secretmanager.secrets.get

  # Firebase
  - firebase.projects.get
  - identitytoolkit.tenants.get
```

## 🌍 環境別権限設定

### **開発環境**
- より広い権限（デバッグ・テスト用）
- `roles/editor`（開発段階のみ）

### **本番環境**
- 最小権限の原則
- カスタムロールまたは個別ロール組み合わせ

## 🔐 セキュリティベストプラクティス

1. **最小権限の原則**: 必要最小限の権限のみ付与
2. **定期的な権限見直し**: 3-6ヶ月ごとに権限監査
3. **環境分離**: 開発・本番で異なるサービスアカウント
4. **キーローテーション**: 定期的なサービスアカウントキー更新
5. **監査ログ**: Cloud Audit Logsでアクセス監視
