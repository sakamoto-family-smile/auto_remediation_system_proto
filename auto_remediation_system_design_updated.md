# エラー自動調査・改修システム設計書（更新版）

## 1. システム概要

GCP上でWebサービスのエラーを自動検知し、cursor-cli（Claude Sonnet-4）を使用してコード改修を行い、GitHub上にPRを自動作成するシステムを構築します。

### 1.1 確定仕様
- **LLMプロバイダー**: Vertex AI API
- **cursor-cli**: 最新版 + Claude Sonnet-4
- **対応言語**: Python + JavaScript/TypeScript
- **改修範囲**: テスト・本番両方（PRマージ後自動デプロイ）
- **承認者**: 開発者
- **エラー対象**: 全てのエラー（構文・論理・パフォーマンス等）
- **認証**: Google アカウント
- **予算上限**: 10万円/月

### 1.2 主要コンポーネント
- **Webサービス**: Python（バックエンド）+ TypeScript/React（フロントエンド）
- **エラー監視システム**: GCP Cloud Monitoring + Cloud Logging
- **自動改修エージェント**: cursor-cli + Vertex AI（Claude Sonnet-4）
- **通知・対話システム**: Slack Bot
- **CI/CD**: Cloud Build + GitHub Actions
- **認証システム**: Firebase Auth（Google OAuth）

---

## 2. 要件定義（更新版）

### 2.1 機能要件

#### 2.1.1 Webサービス機能
- **チャットインターフェース**: ユーザーとLLMの対話
- **LLM統合**: バックエンドでのVertex AI処理
- **セッション管理**: ユーザーセッションとチャット履歴の管理
- **認証・認可**: Google アカウントによる認証システム
- **アカウント管理**: 組織・チーム単位のアクセス制御

#### 2.1.2 エラー監視・検知機能
- **リアルタイム監視**: 全エラー（構文・論理・パフォーマンス）の即座検知
- **エラー分類**: エラーの重要度・種類・言語による自動分類
- **閾値監視**: エラー発生率・レスポンス時間の監視
- **アラート配信**: Slackへのエラー通知
- **対象言語**: Python + JavaScript/TypeScript

#### 2.1.3 自動改修機能
- **エラー解析**: ログとコードの自動解析（cursor-cli + Sonnet-4）
- **改修提案**: 全エラータイプに対応した改修コード生成
- **テスト実行**: 改修後の自動テスト（テスト・本番両環境）
- **PR作成**: GitHub上への自動PR作成（開発者承認必須）
- **自動デプロイ**: PRマージ後の自動デプロイメント

#### 2.1.4 Slack統合機能
- **エラー通知**: エラー発生時の自動通知
- **対話インターフェース**: エージェントとの対話
- **承認フロー**: 開発者による改修内容の承認・却下
- **ステータス更新**: 改修進捗の自動更新

#### 2.1.5 監査・ログ機能
- **改修履歴**: 全改修内容の詳細ログ
- **レビュー履歴**: PRレビューコメントと対応履歴
- **エラー対応履歴**: エラー発生から解決までの全工程
- **ユーザー操作ログ**: 全ユーザー操作の監査証跡

### 2.2 非機能要件

#### 2.2.1 パフォーマンス
- **レスポンス時間**: チャット応答 < 3秒
- **同時接続数**: 100ユーザー同時対応（予算考慮）
- **エラー検知時間**: < 30秒
- **改修完了時間**: < 15分（簡単なエラー）

#### 2.2.2 可用性
- **サービス稼働率**: 99.5%以上（24/7運用不要）
- **障害復旧時間**: < 2時間（営業時間内）
- **データ保持**: 監査ログ1年間、チャット履歴30日間

#### 2.2.3 セキュリティ
- **データ暗号化**: 通信・保存データの暗号化
- **アクセス制御**: Google OAuth + 組織単位のアクセス制御
- **監査ログ**: 全操作の監査証跡（1年間保持）

#### 2.2.4 コスト制約
- **月額上限**: 10万円/月
- **リソース最適化**: 使用量ベースの自動スケーリング
- **コスト監視**: 予算アラート設定

---

## 3. システム構成（更新版）

### 3.1 アーキテクチャ概要

```
┌─────────────────────────────────────────────────────────────┐
│                     GCP Environment                          │
│                   （予算: 10万円/月）                         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐                │
│  │   Frontend      │    │   Backend       │                │
│  │ (Cloud Run)     │◄──►│ (Cloud Run)     │                │
│  │ React/TypeScript│    │ Python/FastAPI  │                │
│  │ Google OAuth    │    │ Vertex AI       │                │
│  └─────────────────┘    └─────────────────┘                │
│           │                       │                         │
│           ▼                       ▼                         │
│  ┌─────────────────┐    ┌─────────────────┐                │
│  │ Firebase Auth   │    │ Cloud SQL       │                │
│  │ (Google OAuth)  │    │ (PostgreSQL)    │                │
│  └─────────────────┘    └─────────────────┘                │
├─────────────────────────────────────────────────────────────┤
│                    Monitoring & Logging                      │
│  ┌─────────────────┐    ┌─────────────────┐                │
│  │ Cloud Monitoring│    │ Cloud Logging   │                │
│  │ (All Errors)    │◄──►│ (Audit Trail)   │                │
│  └─────────────────┘    └─────────────────┘                │
├─────────────────────────────────────────────────────────────┤
│              Auto-Remediation Agent (cursor-cli)             │
│  ┌─────────────────┐    ┌─────────────────┐                │
│  │ Cloud Functions │    │ Cloud Run Jobs  │                │
│  │ (Error Trigger) │◄──►│ (Sonnet-4 +     │                │
│  │                 │    │  cursor-cli)    │                │
│  └─────────────────┘    └─────────────────┘                │
├─────────────────────────────────────────────────────────────┤
│                    External Integrations                     │
│  ┌─────────────────┐    ┌─────────────────┐                │
│  │ Slack API       │    │ GitHub API      │                │
│  │ (Dev Approval)  │    │ (Auto PR)       │                │
│  └─────────────────┘    └─────────────────┘                │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 詳細コンポーネント設計

#### 3.2.1 Webサービス層

**フロントエンド (Cloud Run) - コスト最適化**
- **技術スタック**: React 18 + TypeScript + Vite
- **UI Framework**: Material-UI（軽量化）
- **状態管理**: React Query（Redux より軽量）
- **認証**: Firebase Auth（Google OAuth）
- **リソース設定**:
  ```yaml
  memory: "256Mi"  # コスト削減
  cpu: "0.5"       # 最小構成
  minInstances: 0  # コールドスタート許容
  maxInstances: 10 # 予算制約
  ```

**バックエンド (Cloud Run) - Vertex AI統合**
- **技術スタック**: Python 3.11 + FastAPI
- **LLM統合**: Vertex AI API（Claude Sonnet-4）
- **データベース**: Cloud SQL (PostgreSQL)
- **認証**: Firebase Admin SDK
- **リソース設定**:
  ```yaml
  memory: "1Gi"
  cpu: "1"
  minInstances: 1  # レスポンス重視
  maxInstances: 5  # 予算制約
  ```

#### 3.2.2 データ層（監査対応）

**Cloud SQL (PostgreSQL) - 監査ログ対応**
```sql
-- ユーザー・組織管理
CREATE TABLE organizations (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    google_domain VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE users (
    id UUID PRIMARY KEY,
    google_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    organization_id UUID REFERENCES organizations(id),
    role VARCHAR(50) DEFAULT 'developer',
    created_at TIMESTAMP DEFAULT NOW()
);

-- チャット管理
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE chat_messages (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES chat_sessions(id),
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- エラー・改修管理
CREATE TABLE error_incidents (
    id UUID PRIMARY KEY,
    error_type VARCHAR(100),
    error_message TEXT,
    stack_trace TEXT,
    file_path VARCHAR(500),
    line_number INTEGER,
    language VARCHAR(50), -- 'python', 'javascript', 'typescript'
    severity VARCHAR(20),
    service_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'detected' -- detected, analyzing, fixing, pr_created, resolved
);

CREATE TABLE remediation_attempts (
    id UUID PRIMARY KEY,
    incident_id UUID REFERENCES error_incidents(id),
    cursor_cli_version VARCHAR(50),
    analysis_prompt TEXT,
    fix_suggestion TEXT,
    test_results JSONB,
    github_pr_url VARCHAR(500),
    status VARCHAR(50), -- started, analyzed, fixed, tested, pr_created, approved, failed
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- 監査ログ（1年間保持）
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- PRレビュー履歴
CREATE TABLE pr_reviews (
    id UUID PRIMARY KEY,
    remediation_attempt_id UUID REFERENCES remediation_attempts(id),
    github_pr_number INTEGER,
    reviewer_github_id VARCHAR(255),
    review_status VARCHAR(50), -- approved, changes_requested, commented
    review_comments TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 3.2.3 自動改修エージェント（cursor-cli + Sonnet-4）

**Cloud Functions (エラートリガー)**
```python
# main.py
import functions_framework
from google.cloud import run_v2
from google.cloud import logging as cloud_logging
import json
import os

@functions_framework.cloud_event
def error_handler(cloud_event):
    """全エラータイプの検知・トリガー"""
    try:
        error_data = json.loads(cloud_event.data)
        
        # エラー分析・分類
        error_analysis = analyze_error(error_data)
        
        # 対象言語チェック
        if error_analysis.language in ['python', 'javascript', 'typescript']:
            # 改修ジョブ起動
            trigger_remediation_job(error_analysis)
            
            # 監査ログ記録
            log_audit_event('error_detected', error_analysis)
            
    except Exception as e:
        # エラーハンドリング
        cloud_logging.Client().logger('error-handler').log_struct({
            'error': str(e),
            'cloud_event': cloud_event.data
        })

def analyze_error(error_data):
    """エラーの詳細分析"""
    return {
        'type': detect_error_type(error_data),
        'language': detect_language(error_data),
        'severity': calculate_severity(error_data),
        'file_path': error_data.get('source_location', {}).get('file'),
        'line_number': error_data.get('source_location', {}).get('line'),
        'message': error_data.get('message', ''),
        'stack_trace': error_data.get('stack_trace', '')
    }

def detect_error_type(error_data):
    """エラータイプ検出（構文・論理・パフォーマンス等）"""
    message = error_data.get('message', '').lower()
    
    if any(keyword in message for keyword in ['syntax', 'syntaxerror', 'unexpected token']):
        return 'syntax_error'
    elif any(keyword in message for keyword in ['timeout', 'slow', 'performance']):
        return 'performance_error'
    elif any(keyword in message for keyword in ['null', 'undefined', 'reference']):
        return 'logic_error'
    else:
        return 'runtime_error'

def detect_language(error_data):
    """言語検出"""
    file_path = error_data.get('source_location', {}).get('file', '')
    
    if file_path.endswith('.py'):
        return 'python'
    elif file_path.endswith('.js'):
        return 'javascript'
    elif file_path.endswith('.ts') or file_path.endswith('.tsx'):
        return 'typescript'
    else:
        return 'unknown'
```

**Cloud Run Jobs (cursor-cli実行環境)**
```python
# remediation_agent.py
import subprocess
import os
import json
from google.cloud import sql
from github import Github
from slack_sdk import WebClient
from vertexai.generative_models import GenerativeModel

class RemediationAgent:
    def __init__(self):
        self.github = Github(os.environ['GITHUB_TOKEN'])
        self.slack = WebClient(token=os.environ['SLACK_TOKEN'])
        self.vertex_model = GenerativeModel('claude-3-sonnet@001')  # Vertex AI
        
    def analyze_and_fix(self, incident_data):
        """包括的エラー解析・修正"""
        try:
            # 1. 改修試行記録開始
            attempt_id = self.log_remediation_start(incident_data)
            
            # 2. リポジトリクローン
            repo_path = self.clone_repository()
            
            # 3. cursor-cli + Sonnet-4 でエラー解析
            analysis = self.run_cursor_analysis(incident_data, repo_path)
            
            # 4. 修正コード生成
            fix = self.generate_comprehensive_fix(analysis, incident_data)
            
            # 5. テスト実行（テスト・本番環境両方）
            test_results = self.run_comprehensive_tests(fix, repo_path)
            
            if test_results['success']:
                # 6. PR作成
                pr = self.create_pull_request(fix, incident_data, test_results)
                
                # 7. Slack通知（開発者承認要求）
                self.notify_developers_for_approval(pr, incident_data)
                
                # 8. 監査ログ記録
                self.log_remediation_success(attempt_id, pr, test_results)
            else:
                self.log_remediation_failure(attempt_id, test_results)
                
        except Exception as e:
            self.log_remediation_error(attempt_id, str(e))
    
    def run_cursor_analysis(self, incident_data, repo_path):
        """cursor-cli + Sonnet-4 による高度解析"""
        
        # エラータイプ別の解析プロンプト
        analysis_prompts = {
            'syntax_error': f"""
            Analyze this syntax error and provide a fix:
            File: {incident_data['file_path']}
            Line: {incident_data['line_number']}
            Error: {incident_data['error_message']}
            Language: {incident_data['language']}
            
            Provide:
            1. Root cause analysis
            2. Exact fix with line numbers
            3. Prevention recommendations
            """,
            
            'logic_error': f"""
            Analyze this logic error and provide a comprehensive fix:
            Error: {incident_data['error_message']}
            Stack trace: {incident_data['stack_trace']}
            
            Consider:
            1. Data flow analysis
            2. Edge cases
            3. Error handling improvements
            """,
            
            'performance_error': f"""
            Analyze this performance issue:
            Error: {incident_data['error_message']}
            
            Provide:
            1. Performance bottleneck identification
            2. Optimization strategies
            3. Monitoring improvements
            """
        }
        
        prompt = analysis_prompts.get(
            incident_data['error_type'], 
            analysis_prompts['syntax_error']
        )
        
        # cursor-cli実行
        cmd = [
            'cursor-cli',
            'analyze',
            '--model', 'sonnet-4',
            '--prompt', prompt,
            '--file', incident_data['file_path'],
            '--repo-path', repo_path,
            '--language', incident_data['language']
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=repo_path)
        
        if result.returncode != 0:
            raise Exception(f"cursor-cli failed: {result.stderr}")
        
        return json.loads(result.stdout)
    
    def generate_comprehensive_fix(self, analysis, incident_data):
        """包括的な修正コード生成"""
        
        # Vertex AI (Sonnet-4) で修正コード生成
        fix_prompt = f"""
        Based on the analysis: {json.dumps(analysis)}
        
        Generate a comprehensive fix for this {incident_data['language']} error:
        - Error type: {incident_data['error_type']}
        - File: {incident_data['file_path']}
        - Line: {incident_data['line_number']}
        
        Requirements:
        1. Fix the immediate error
        2. Add proper error handling
        3. Include unit tests
        4. Add logging for monitoring
        5. Follow best practices for {incident_data['language']}
        
        Return JSON with:
        - fixed_code: the corrected code
        - test_code: unit tests
        - explanation: detailed explanation
        """
        
        response = self.vertex_model.generate_content(fix_prompt)
        return json.loads(response.text)
    
    def run_comprehensive_tests(self, fix, repo_path):
        """包括的テスト実行"""
        results = {
            'success': False,
            'unit_tests': {},
            'integration_tests': {},
            'lint_checks': {},
            'security_checks': {}
        }
        
        try:
            # 1. 修正コード適用
            self.apply_fix(fix, repo_path)
            
            # 2. 単体テスト
            results['unit_tests'] = self.run_unit_tests(repo_path)
            
            # 3. 統合テスト
            results['integration_tests'] = self.run_integration_tests(repo_path)
            
            # 4. Lintチェック
            results['lint_checks'] = self.run_lint_checks(repo_path)
            
            # 5. セキュリティチェック
            results['security_checks'] = self.run_security_checks(repo_path)
            
            # 全テスト成功判定
            results['success'] = all([
                results['unit_tests'].get('passed', False),
                results['integration_tests'].get('passed', False),
                results['lint_checks'].get('passed', False),
                results['security_checks'].get('passed', False)
            ])
            
        except Exception as e:
            results['error'] = str(e)
        
        return results
```

#### 3.2.4 Slack統合（開発者承認フロー）

```python
# slack_bot.py
from slack_bolt import App
from slack_bolt.adapter.google_cloud_functions import SlackRequestHandler
import json

app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)

@app.event("app_mention")
def handle_mention(event, say, client):
    """エージェントとの対話"""
    user_message = event['text']
    
    # Vertex AI で応答生成
    response = process_with_vertex_ai(user_message)
    
    say(response)

def notify_developers_for_approval(pr_data, incident_data):
    """開発者への承認要求通知"""
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🚨 自動修正PR作成: {incident_data['error_type']}"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*エラー:* {incident_data['error_message'][:100]}..."
                },
                {
                    "type": "mrkdwn",
                    "text": f"*ファイル:* {incident_data['file_path']}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*言語:* {incident_data['language']}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*PR:* <{pr_data['url']}|{pr_data['title']}>"
                }
            ]
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "✅ 承認してマージ"
                    },
                    "style": "primary",
                    "action_id": "approve_pr",
                    "value": json.dumps({
                        "pr_url": pr_data['url'],
                        "incident_id": incident_data['id']
                    })
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "💬 レビューコメント"
                    },
                    "action_id": "review_pr",
                    "value": pr_data['url']
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "❌ 却下"
                    },
                    "style": "danger",
                    "action_id": "reject_pr",
                    "value": pr_data['url']
                }
            ]
        }
    ]
    
    # 開発者チャンネルに通知
    client.chat_postMessage(
        channel="#dev-auto-fixes",
        blocks=blocks
    )

@app.action("approve_pr")
def handle_approve_pr(ack, body, client):
    """PR承認・自動マージ"""
    ack()
    
    pr_data = json.loads(body['actions'][0]['value'])
    
    # GitHub PR承認・マージ
    success = approve_and_merge_pr(pr_data['pr_url'])
    
    if success:
        client.chat_postMessage(
            channel=body['channel']['id'],
            text=f"✅ PR承認・マージ完了: {pr_data['pr_url']}\n自動デプロイが開始されます。"
        )
        
        # 監査ログ記録
        log_audit_event('pr_approved', {
            'pr_url': pr_data['pr_url'],
            'incident_id': pr_data['incident_id'],
            'approved_by': body['user']['id']
        })
```

---

## 4. GCPインフラ設計（コスト最適化版）

### 4.1 月額10万円予算配分

```yaml
# 予算配分（月額10万円）
budget_allocation:
  compute:
    cloud_run: "40,000円"      # 40%
    cloud_functions: "10,000円" # 10%
    cloud_run_jobs: "15,000円"  # 15%
  
  storage:
    cloud_sql: "20,000円"      # 20%
    cloud_storage: "3,000円"   # 3%
  
  ai_services:
    vertex_ai: "10,000円"      # 10%
  
  networking:
    load_balancer: "2,000円"   # 2%
    
  total: "100,000円"
```

### 4.2 リソース構成（コスト最適化）

#### 4.2.1 コンピューティング
```yaml
compute:
  cloudRun:
    frontend:
      name: "chat-frontend"
      memory: "256Mi"        # 最小構成
      cpu: "0.5"
      minInstances: 0        # コールドスタート許容
      maxInstances: 10       # 予算制約
      
    backend:
      name: "chat-backend"
      memory: "1Gi"
      cpu: "1"
      minInstances: 1        # レスポンス重視
      maxInstances: 5        # 予算制約
      
  cloudRunJobs:
    remediationAgent:
      name: "remediation-agent"
      memory: "2Gi"          # cursor-cli用
      cpu: "2"
      taskTimeout: "1800s"
      maxRetries: 3
      
  cloudFunctions:
    errorHandler:
      name: "error-handler"
      runtime: "python311"
      memory: "256MB"        # 最小構成
      timeout: "60s"
      maxInstances: 100      # バースト対応
```

#### 4.2.2 データベース（監査対応）
```yaml
database:
  cloudSQL:
    instance:
      name: "chat-db-instance"
      tier: "db-f1-micro"    # 最小構成
      region: "asia-northeast1"
      storage: "20GB"        # 監査ログ考慮
      backupConfig:
        enabled: true
        retentionPeriod: "365d"  # 監査要件
        
    databases:
      - name: "chatdb"
      - name: "audit_db"     # 監査専用DB
```

### 4.3 監視・アラート設計（コスト監視含む）

#### 4.3.1 コスト監視
```yaml
cost_monitoring:
  budgets:
    - name: "monthly-budget"
      amount: 100000  # 10万円
      alerts:
        - threshold: 0.5   # 50%で警告
          channels: ["slack"]
        - threshold: 0.8   # 80%で重要警告
          channels: ["slack", "email"]
        - threshold: 0.95  # 95%で緊急警告
          channels: ["slack", "email", "sms"]
          
  cost_optimization:
    - schedule_shutdown:
        services: ["non-critical"]
        time: "22:00-06:00"  # 夜間停止
    - auto_scaling:
        min_instances: 0     # 未使用時は0
        scale_down_delay: "5m"
```

#### 4.3.2 アラート設定
```yaml
alerts:
  - name: "High Error Rate"
    condition: "error_rate > 3%"
    severity: "CRITICAL"
    
  - name: "Cost Alert 50%"
    condition: "monthly_cost > 50000"
    severity: "WARNING"
    
  - name: "Remediation Job Failed"
    condition: "job_failure_rate > 10%"
    severity: "HIGH"
    
  - name: "Vertex AI Quota Exceeded"
    condition: "vertex_ai_quota > 80%"
    severity: "WARNING"
```

---

## 5. 開発・運用計画（更新版）

### 5.1 開発フェーズ（TypeScript知見考慮）

#### Phase 1: 基盤構築 (4週間)
- GCPインフラセットアップ
- **Python重点**: バックエンドAPI完成度重視
- **TypeScript**: 基本的なReactアプリ（シンプル構成）
- Firebase Auth設定
- 基本的な監視設定

#### Phase 2: コア機能実装 (6週間)
- **Python**: チャット機能・Vertex AI統合（完全実装）
- **TypeScript**: 基本UI（Material-UI活用で開発効率化）
- Google OAuth認証
- データベース設計・実装

#### Phase 3: 自動改修機能 (8週間) - **最重要フェーズ**
- **Python重点**: エラー検知システム
- cursor-cli統合・テスト
- 自動改修エージェント開発
- GitHub統合・PR自動化

#### Phase 4: Slack統合・TypeScript改善 (6週間)
- **Python**: Slack Bot実装
- 承認フロー構築
- **TypeScript**: UI/UX改善（外部支援検討）
- 監査ログ機能

#### Phase 5: テスト・本番リリース (4週間)
- 統合テスト
- コスト最適化
- セキュリティテスト
- 本番環境デプロイ

### 5.2 技術スタック（知見レベル考慮）

#### 5.2.1 フロントエンド（TypeScript知見浅い対応）
```json
{
  "strategy": "既存ライブラリ最大活用",
  "dependencies": {
    "react": "^18.2.0",
    "typescript": "^5.0.0",
    "@mui/material": "^5.11.0",    // 完成されたコンポーネント
    "@mui/icons-material": "^5.11.0",
    "react-query": "^3.39.0",      // Redux より簡単
    "firebase": "^10.0.0",         // 認証簡単
    "axios": "^1.4.0"
  },
  "development_approach": {
    "use_templates": true,          // Material-UI テンプレート活用
    "minimal_custom_css": true,     // カスタムCSS最小限
    "focus_on_functionality": true  // 見た目より機能重視
  }
}
```

#### 5.2.2 バックエンド（Python強み活用）
```txt
# 高度な機能をPythonで実装
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
alembic==1.13.0
psycopg2-binary==2.9.9
google-cloud-aiplatform==1.38.1  # Vertex AI
google-cloud-logging==3.8.0
google-cloud-monitoring==2.16.0
slack-bolt==1.18.0
PyGithub==1.59.1
```

---

## 6. 監査・コンプライアンス設計

### 6.1 監査ログ設計

#### 6.1.1 記録対象
```python
# 監査対象イベント
AUDIT_EVENTS = {
    'user_actions': [
        'login', 'logout', 'chat_message', 'pr_approval', 'pr_rejection'
    ],
    'system_actions': [
        'error_detected', 'remediation_started', 'pr_created', 
        'auto_deployment', 'test_execution'
    ],
    'admin_actions': [
        'user_management', 'config_change', 'manual_override'
    ]
}

# 監査ログ形式
audit_log_format = {
    "timestamp": "2024-01-15T10:30:00Z",
    "event_id": "uuid",
    "user_id": "uuid",
    "event_type": "pr_approved",
    "resource_type": "pull_request",
    "resource_id": "pr-123",
    "details": {
        "pr_url": "https://github.com/...",
        "incident_id": "uuid",
        "error_type": "syntax_error",
        "language": "python"
    },
    "ip_address": "192.168.1.1",
    "user_agent": "Chrome/...",
    "result": "success"
}
```

#### 6.1.2 保持・アクセス制御
```yaml
audit_retention:
  period: "1年間"
  storage: "Cloud Storage (Coldline)"
  access_control:
    - role: "audit_viewer"
      permissions: ["read"]
      members: ["admin@company.com"]
    - role: "audit_admin"
      permissions: ["read", "export"]
      members: ["security@company.com"]
      
export_capabilities:
  formats: ["JSON", "CSV", "PDF"]
  filters: ["date_range", "user", "event_type"]
  encryption: "AES-256"
```

---

## 7. 実装優先度・リスク分析

### 7.1 実装優先度

#### 高優先度（必須）
1. **エラー検知・通知システム** - コア機能
2. **cursor-cli統合** - 差別化要素
3. **GitHub PR自動化** - ワークフロー中核
4. **基本認証・アクセス制御** - セキュリティ必須

#### 中優先度（重要）
5. **Slack統合・承認フロー** - UX向上
6. **監査ログ・コンプライアンス** - 企業要件
7. **コスト監視・最適化** - 運用安定性

#### 低優先度（改善）
8. **高度なUI/UX** - 後回し可能
9. **パフォーマンス最適化** - 必要時対応
10. **マルチリージョン対応** - 将来対応

### 7.2 主要リスク・対策

#### 7.2.1 技術リスク
```yaml
risks:
  typescript_complexity:
    probability: "HIGH"
    impact: "MEDIUM"
    mitigation: 
      - "Material-UI テンプレート活用"
      - "外部支援検討"
      - "機能最小化"
      
  cursor_cli_integration:
    probability: "MEDIUM"
    impact: "HIGH"
    mitigation:
      - "早期プロトタイプ検証"
      - "フォールバック機構"
      - "手動修正オプション"
      
  cost_overrun:
    probability: "MEDIUM"
    impact: "HIGH"
    mitigation:
      - "リアルタイム監視"
      - "自動スケールダウン"
      - "使用量アラート"
```

#### 7.2.2 運用リスク
```yaml
operational_risks:
  false_positive_fixes:
    mitigation: 
      - "包括的テスト"
      - "開発者承認必須"
      - "ロールバック機能"
      
  security_vulnerabilities:
    mitigation:
      - "IAM最小権限"
      - "定期セキュリティ監査"
      - "暗号化徹底"
```

---

## 8. 次ステップ・推奨アクション

### 8.1 即座に開始すべき項目

1. **GCPプロジェクト作成・予算設定**
   - 予算アラート設定
   - IAM基本設定

2. **cursor-cli検証環境構築**
   - 最新版インストール
   - Sonnet-4接続テスト
   - 基本的な修正テスト

3. **GitHub・Slack連携準備**
   - API トークン取得
   - Webhook設定

### 8.2 設計検証項目

1. **cursor-cliの実際の修正能力確認**
2. **Vertex AI（Sonnet-4）のコスト試算**
3. **TypeScript開発支援の必要性判断**

この更新された設計書は、いただいた要件を全て反映し、特にコスト制約とチームの技術スキルを考慮した実装可能な設計となっています。