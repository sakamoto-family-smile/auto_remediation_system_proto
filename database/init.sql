-- Auto Remediation System Database Initialization
-- PostgreSQL用の初期化スクリプト

-- データベース設定
SET timezone = 'UTC';

-- 拡張機能の有効化
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- インデックス作成（パフォーマンス向上）
-- SQLAlchemyがテーブルを作成した後に実行されるため、
-- 実際のインデックス作成は後で行う

-- ログ出力
\echo 'Database initialization script completed.'
\echo 'Tables will be created automatically by SQLAlchemy.'