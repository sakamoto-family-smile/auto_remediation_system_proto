#!/usr/bin/env python3
"""
SECRET_KEY生成スクリプト
"""

import secrets
import base64
import sys
from pathlib import Path


def generate_secret_key(method: str = "urlsafe") -> str:
    """
    SECRET_KEYを生成する

    Args:
        method: 生成方法 ("urlsafe", "base64", "hex")

    Returns:
        str: 生成されたSECRET_KEY
    """
    if method == "urlsafe":
        # URL-safeな文字列（推奨）
        return secrets.token_urlsafe(64)
    elif method == "base64":
        # Base64エンコード（32バイト = 256ビット）
        key = secrets.token_bytes(32)
        return base64.b64encode(key).decode('utf-8')
    elif method == "hex":
        # 16進数表記
        return secrets.token_hex(32)
    else:
        raise ValueError("method must be 'urlsafe', 'base64', or 'hex'")


def main():
    """メイン処理"""
    print("🔐 SECRET_KEY Generator")
    print("=" * 50)

    # 複数の形式で生成
    methods = [
        ("URL-Safe (推奨)", "urlsafe"),
        ("Base64", "base64"),
        ("Hex", "hex")
    ]

    for name, method in methods:
        key = generate_secret_key(method)
        print(f"\n{name}:")
        print(f"SECRET_KEY={key}")
        print(f"Length: {len(key)} characters")

    print("\n" + "=" * 50)
    print("📝 使用方法:")
    print("1. 上記のいずれかのSECRET_KEYをコピー")
    print("2. backend/.env ファイルに設定")
    print("3. 本番環境では必ず異なるキーを使用")

    # 環境変数ファイルのサンプル出力
    recommended_key = generate_secret_key("urlsafe")

    print(f"\n📄 .env ファイル例:")
    print(f"SECRET_KEY={recommended_key}")

    # セキュリティ警告
    print("\n⚠️  セキュリティ注意事項:")
    print("- SECRET_KEYは絶対にコードにハードコーディングしない")
    print("- 環境ごとに異なるキーを使用する")
    print("- 定期的にローテーション（更新）する")
    print("- GitHubなどに公開しない")


if __name__ == "__main__":
    main()
