-- Auto Remediation System データベース初期化スクリプト

-- 拡張機能有効化
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ユーザー・組織管理
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    google_domain VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    google_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    organization_id UUID REFERENCES organizations(id),
    role VARCHAR(50) DEFAULT 'developer',
    created_at TIMESTAMP DEFAULT NOW()
);

-- チャット管理
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES chat_sessions(id),
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- エラー・改修管理
CREATE TABLE error_incidents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id UUID REFERENCES error_incidents(id),
    cursor_cli_version VARCHAR(50),
    analysis_prompt TEXT,
    fix_suggestion TEXT,
    test_results JSONB,
    github_pr_url VARCHAR(500),
    status VARCHAR(50) DEFAULT 'started', -- started, analyzed, fixed, tested, pr_created, approved, failed
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- 監査ログ（1年間保持）
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    remediation_attempt_id UUID REFERENCES remediation_attempts(id),
    github_pr_number INTEGER,
    reviewer_github_id VARCHAR(255),
    review_status VARCHAR(50), -- approved, changes_requested, commented
    review_comments TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- インデックス作成
CREATE INDEX idx_users_google_id ON users(google_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_error_incidents_status ON error_incidents(status);
CREATE INDEX idx_error_incidents_created_at ON error_incidents(created_at);
CREATE INDEX idx_remediation_attempts_incident_id ON remediation_attempts(incident_id);
CREATE INDEX idx_remediation_attempts_status ON remediation_attempts(status);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);

-- サンプルデータ挿入（開発環境用）
INSERT INTO organizations (id, name, google_domain) VALUES
    ('550e8400-e29b-41d4-a716-446655440000', 'Example Corp', 'example.com');

INSERT INTO users (id, google_id, email, organization_id, role) VALUES
    ('550e8400-e29b-41d4-a716-446655440001', 'google123', 'developer@example.com', '550e8400-e29b-41d4-a716-446655440000', 'developer'),
    ('550e8400-e29b-41d4-a716-446655440002', 'google456', 'admin@example.com', '550e8400-e29b-41d4-a716-446655440000', 'admin');

-- サンプルエラーインシデント
INSERT INTO error_incidents (id, error_type, error_message, file_path, line_number, language, severity, service_name, status) VALUES
    ('550e8400-e29b-41d4-a716-446655440010', 'syntax_error', 'SyntaxError: invalid syntax', '/app/main.py', 42, 'python', 'high', 'web-service', 'detected'),
    ('550e8400-e29b-41d4-a716-446655440011', 'logic_error', 'TypeError: cannot read property of undefined', '/app/utils.js', 15, 'javascript', 'medium', 'frontend', 'analyzing');

COMMIT;
