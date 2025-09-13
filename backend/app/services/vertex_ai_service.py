"""
Vertex AI統合サービス
"""

import json
from typing import Any, Dict, List, Optional

import structlog
from google.auth import default
from google.cloud import aiplatform
from google.cloud.aiplatform import gapic

from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class VertexAIService:
    """Vertex AI Claude Sonnet-4統合サービス"""

    def __init__(self):
        self.project_id = settings.GCP_PROJECT_ID
        self.location = settings.GCP_LOCATION or "us-central1"
        self.model_name = "claude-3-sonnet@20240229"

        # Vertex AI初期化
        aiplatform.init(project=self.project_id, location=self.location)

        # 認証情報取得
        try:
            self.credentials, _ = default()
            logger.info("Vertex AI service initialized", project=self.project_id)
        except Exception as e:
            logger.warning("Failed to initialize Vertex AI credentials", error=str(e))
            self.credentials = None

    async def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2048,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        チャット応答生成

        Args:
            messages: チャット履歴 [{"role": "user/assistant", "content": "..."}]
            max_tokens: 最大トークン数
            temperature: 温度パラメータ
            system_prompt: システムプロンプト

        Returns:
            str: 生成された応答
        """
        try:
            if not self.credentials:
                # 開発環境用の仮応答
                return self._get_mock_response(messages[-1]["content"] if messages else "")

            # システムプロンプトを設定
            if not system_prompt:
                system_prompt = self._get_default_system_prompt()

            # メッセージを Claude 形式に変換
            formatted_messages = self._format_messages_for_claude(messages, system_prompt)

            # Vertex AI API呼び出し
            client = gapic.PredictionServiceClient(credentials=self.credentials)
            endpoint = f"projects/{self.project_id}/locations/{self.location}/publishers/anthropic/models/{self.model_name}"

            request_data = {
                "anthropic_version": "vertex-2023-10-16",
                "messages": formatted_messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }

            response = client.predict(
                endpoint=endpoint,
                instances=[request_data],
            )

            # 応答を解析
            if response.predictions:
                prediction = response.predictions[0]
                content = prediction.get("content", [])
                if content and content[0].get("type") == "text":
                    generated_text = content[0]["text"]

                    logger.info(
                        "Chat response generated",
                        input_length=len(str(messages)),
                        output_length=len(generated_text),
                    )

                    return generated_text

            logger.warning("No valid response from Vertex AI")
            return "申し訳ございません。現在応答を生成できません。しばらく後に再試行してください。"

        except Exception as e:
            logger.error("Failed to generate chat response", error=str(e))
            return self._get_error_response(str(e))

    async def analyze_error_code(
        self,
        error_message: str,
        stack_trace: Optional[str] = None,
        file_path: Optional[str] = None,
        language: Optional[str] = None,
        context_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        エラーコード解析

        Args:
            error_message: エラーメッセージ
            stack_trace: スタックトレース
            file_path: ファイルパス
            language: プログラミング言語
            context_code: 関連コード

        Returns:
            Dict[str, Any]: 解析結果
        """
        try:
            # 解析用プロンプト構築
            analysis_prompt = self._build_error_analysis_prompt(
                error_message, stack_trace, file_path, language, context_code
            )

            messages = [{"role": "user", "content": analysis_prompt}]

            response = await self.generate_chat_response(
                messages=messages,
                system_prompt=self._get_error_analysis_system_prompt(),
                temperature=0.3,  # より確定的な応答のため低めに設定
            )

            # JSON形式の応答を解析
            try:
                analysis_result = json.loads(response)
                return analysis_result
            except json.JSONDecodeError:
                # JSON解析に失敗した場合はテキストとして返す
                return {
                    "error_category": "analysis_error",
                    "root_cause": "Failed to parse analysis result",
                    "description": response,
                    "recommendations": ["Manual investigation required"],
                    "confidence_score": 0.5,
                }

        except Exception as e:
            logger.error("Failed to analyze error code", error=str(e))
            return {
                "error_category": "service_error",
                "root_cause": f"Analysis service error: {str(e)}",
                "description": "Failed to analyze the error",
                "recommendations": ["Check service logs", "Retry analysis"],
                "confidence_score": 0.0,
            }

    async def generate_fix_code(
        self,
        error_analysis: Dict[str, Any],
        original_code: Optional[str] = None,
        file_path: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        修正コード生成

        Args:
            error_analysis: エラー解析結果
            original_code: 元のコード
            file_path: ファイルパス
            language: プログラミング言語

        Returns:
            Dict[str, Any]: 修正結果
        """
        try:
            fix_prompt = self._build_fix_generation_prompt(
                error_analysis, original_code, file_path, language
            )

            messages = [{"role": "user", "content": fix_prompt}]

            response = await self.generate_chat_response(
                messages=messages,
                system_prompt=self._get_fix_generation_system_prompt(),
                temperature=0.2,  # より安定した修正のため低く設定
            )

            # JSON形式の応答を解析
            try:
                fix_result = json.loads(response)
                return fix_result
            except json.JSONDecodeError:
                return {
                    "status": "error",
                    "fixed_code": response,
                    "explanation": "Generated fix (parsing failed)",
                    "changes": [],
                    "confidence_score": 0.6,
                }

        except Exception as e:
            logger.error("Failed to generate fix code", error=str(e))
            return {
                "status": "error",
                "error": str(e),
                "explanation": "Failed to generate fix",
                "confidence_score": 0.0,
            }

    def _format_messages_for_claude(
        self, messages: List[Dict[str, str]], system_prompt: str
    ) -> List[Dict[str, str]]:
        """Claude用メッセージフォーマット"""
        formatted = []

        # システムメッセージを最初に追加
        if system_prompt:
            formatted.append({"role": "user", "content": f"System: {system_prompt}"})

        # ユーザー・アシスタントメッセージを追加
        for msg in messages:
            role = "user" if msg["role"] == "user" else "assistant"
            formatted.append({"role": role, "content": msg["content"]})

        return formatted

    def _get_default_system_prompt(self) -> str:
        """デフォルトシステムプロンプト"""
        return """あなたは優秀なソフトウェアエンジニアリングアシスタントです。
コードの問題解決、エラー解析、システム改善に関する質問に対して、
正確で実用的な回答を提供してください。

回答の際は以下を心がけてください：
- 具体的で実行可能なソリューションを提供
- コード例がある場合は適切にフォーマット
- セキュリティとベストプラクティスを考慮
- 簡潔で分かりやすい説明"""

    def _get_error_analysis_system_prompt(self) -> str:
        """エラー解析用システムプロンプト"""
        return """あなたはエラー解析の専門家です。
提供されたエラー情報を分析し、以下のJSON形式で結果を返してください：

{
  "error_category": "エラーカテゴリ",
  "root_cause": "根本原因",
  "description": "詳細説明",
  "affected_components": ["影響を受けるコンポーネント"],
  "recommendations": ["推奨対応策"],
  "confidence_score": 0.0-1.0の信頼度
}"""

    def _get_fix_generation_system_prompt(self) -> str:
        """修正生成用システムプロンプト"""
        return """あなたはコード修正の専門家です。
エラー解析結果に基づいて修正コードを生成し、以下のJSON形式で返してください：

{
  "status": "success/partial/error",
  "fixed_code": "修正されたコード",
  "explanation": "修正内容の説明",
  "changes": ["変更点のリスト"],
  "test_suggestions": ["テスト提案"],
  "confidence_score": 0.0-1.0の信頼度
}"""

    def _build_error_analysis_prompt(
        self,
        error_message: str,
        stack_trace: Optional[str],
        file_path: Optional[str],
        language: Optional[str],
        context_code: Optional[str],
    ) -> str:
        """エラー解析プロンプト構築"""
        prompt = f"以下のエラーを解析してください：\n\nエラーメッセージ：\n{error_message}\n"

        if stack_trace:
            prompt += f"\nスタックトレース：\n{stack_trace}\n"

        if file_path:
            prompt += f"\nファイルパス：{file_path}\n"

        if language:
            prompt += f"\nプログラミング言語：{language}\n"

        if context_code:
            prompt += f"\n関連コード：\n```{language or ''}\n{context_code}\n```\n"

        return prompt

    def _build_fix_generation_prompt(
        self,
        error_analysis: Dict[str, Any],
        original_code: Optional[str],
        file_path: Optional[str],
        language: Optional[str],
    ) -> str:
        """修正生成プロンプト構築"""
        prompt = f"以下のエラー解析結果に基づいて修正コードを生成してください：\n\n"
        prompt += f"解析結果：\n{json.dumps(error_analysis, indent=2, ensure_ascii=False)}\n"

        if original_code:
            prompt += f"\n元のコード：\n```{language or ''}\n{original_code}\n```\n"

        if file_path:
            prompt += f"\nファイルパス：{file_path}\n"

        return prompt

    def _get_mock_response(self, user_message: str) -> str:
        """開発環境用モック応答"""
        return f"""ユーザーメッセージ「{user_message}」を受信しました。

現在はVertex AI統合の開発モードで動作しています。
実際のClaude Sonnet-4との連携は、GCP認証情報設定後に利用可能になります。

設定方法：
1. GCPプロジェクトでVertex AI APIを有効化
2. サービスアカウントキーを設定
3. 環境変数 GCP_PROJECT_ID を設定

ご質問があればお気軽にお聞かせください！"""

    def _get_error_response(self, error: str) -> str:
        """エラー時の応答"""
        return f"""申し訳ございません。現在システムに問題が発生しています。

エラー詳細: {error}

しばらく時間をおいて再試行していただくか、システム管理者にお問い合わせください。"""
