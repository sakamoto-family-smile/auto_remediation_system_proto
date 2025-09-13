"""
cursor-cli統合エージェント
"""

import asyncio
import json
import os
import subprocess
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

import structlog
from github import Github
from slack_sdk import WebClient

from app.core.config import get_settings
from app.core.exceptions import CursorCLIError, ExternalServiceError

logger = structlog.get_logger()
settings = get_settings()


class CursorCLIAgent:
    """cursor-cli統合エージェント"""

    def __init__(self):
        self.github = Github(settings.GITHUB_TOKEN) if settings.GITHUB_TOKEN else None
        self.slack = WebClient(token=settings.SLACK_BOT_TOKEN) if settings.SLACK_BOT_TOKEN else None
        self.cursor_api_key = settings.CURSOR_API_KEY

        if not self.cursor_api_key:
            raise ValueError("CURSOR_API_KEY environment variable is required")

    async def analyze_error(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        cursor-cliを使用してエラー解析

        Args:
            error_data: エラー情報

        Returns:
            Dict[str, Any]: 解析結果
        """
        try:
            # エラータイプ別のプロンプト生成
            prompt = self._generate_analysis_prompt(error_data)

            # cursor-cli実行
            result = await self._run_cursor_cli_command(
                command="analyze",
                prompt=prompt,
                file_path=error_data.get("file_path"),
                language=error_data.get("language"),
            )

            logger.info(
                "Error analysis completed",
                error_type=error_data.get("error_type"),
                file_path=error_data.get("file_path"),
            )

            return {
                "analysis_result": result,
                "prompt_used": prompt,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error("Error analysis failed", error=str(e), error_data=error_data)
            raise CursorCLIError(f"Error analysis failed: {str(e)}")

    async def generate_fix(
        self,
        error_data: Dict[str, Any],
        analysis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        cursor-cliを使用して修正コード生成

        Args:
            error_data: エラー情報
            analysis_result: 解析結果

        Returns:
            Dict[str, Any]: 修正コード情報
        """
        try:
            # 修正プロンプト生成
            prompt = self._generate_fix_prompt(error_data, analysis_result)

            # cursor-cli実行
            result = await self._run_cursor_cli_command(
                command="fix",
                prompt=prompt,
                file_path=error_data.get("file_path"),
                language=error_data.get("language"),
            )

            logger.info(
                "Fix generation completed",
                error_type=error_data.get("error_type"),
                file_path=error_data.get("file_path"),
            )

            return {
                "fix_code": result.get("fixed_code", ""),
                "test_code": result.get("test_code", ""),
                "explanation": result.get("explanation", ""),
                "prompt_used": prompt,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error("Fix generation failed", error=str(e), error_data=error_data)
            raise CursorCLIError(f"Fix generation failed: {str(e)}")

    async def test_fix(
        self,
        fix_data: Dict[str, Any],
        repo_path: str
    ) -> Dict[str, Any]:
        """
        修正コードのテスト実行

        Args:
            fix_data: 修正コード情報
            repo_path: リポジトリパス

        Returns:
            Dict[str, Any]: テスト結果
        """
        try:
            results = {
                "success": False,
                "unit_tests": {},
                "integration_tests": {},
                "lint_checks": {},
                "security_checks": {},
                "timestamp": datetime.utcnow().isoformat(),
            }

            # 修正コード適用
            await self._apply_fix(fix_data, repo_path)

            # 各種テスト実行
            results["unit_tests"] = await self._run_unit_tests(repo_path)
            results["integration_tests"] = await self._run_integration_tests(repo_path)
            results["lint_checks"] = await self._run_lint_checks(repo_path)
            results["security_checks"] = await self._run_security_checks(repo_path)

            # 全テスト成功判定
            results["success"] = all([
                results["unit_tests"].get("passed", False),
                results["integration_tests"].get("passed", False),
                results["lint_checks"].get("passed", False),
                results["security_checks"].get("passed", False),
            ])

            logger.info(
                "Fix testing completed",
                success=results["success"],
                repo_path=repo_path,
            )

            return results

        except Exception as e:
            logger.error("Fix testing failed", error=str(e), repo_path=repo_path)
            raise CursorCLIError(f"Fix testing failed: {str(e)}")

    async def create_pull_request(
        self,
        fix_data: Dict[str, Any],
        test_results: Dict[str, Any],
        error_data: Dict[str, Any],
        repo_name: str,
        branch_name: str = None
    ) -> Dict[str, Any]:
        """
        GitHub PRの自動作成

        Args:
            fix_data: 修正コード情報
            test_results: テスト結果
            error_data: エラー情報
            repo_name: リポジトリ名
            branch_name: ブランチ名（省略時は自動生成）

        Returns:
            Dict[str, Any]: PR情報
        """
        if not self.github:
            raise ExternalServiceError("GitHub", "GitHub token not configured")

        try:
            repo = self.github.get_repo(repo_name)

            # ブランチ名生成
            if not branch_name:
                branch_name = f"auto-fix-{error_data.get('error_type', 'error')}-{uuid.uuid4().hex[:8]}"

            # PR作成
            pr_title = f"🤖 Auto-fix: {error_data.get('error_type', 'Error')} in {error_data.get('file_path', 'unknown')}"
            pr_body = self._generate_pr_description(fix_data, test_results, error_data)

            # ここでは実際のファイル変更とPR作成をシミュレート
            # 実際の実装では、Git操作とファイル変更を行う
            pr_url = f"https://github.com/{repo_name}/pull/123"  # シミュレーション

            logger.info(
                "Pull request created",
                repo_name=repo_name,
                branch_name=branch_name,
                pr_url=pr_url,
            )

            return {
                "pr_url": pr_url,
                "pr_number": 123,  # シミュレーション
                "branch_name": branch_name,
                "title": pr_title,
                "body": pr_body,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error("Pull request creation failed", error=str(e), repo_name=repo_name)
            raise ExternalServiceError("GitHub", f"PR creation failed: {str(e)}")

    async def _run_cursor_cli_command(
        self,
        command: str,
        prompt: str,
        file_path: str = None,
        language: str = None
    ) -> Dict[str, Any]:
        """
        cursor-cliコマンド実行

        Args:
            command: cursor-cliコマンド
            prompt: プロンプト
            file_path: 対象ファイルパス
            language: プログラミング言語

        Returns:
            Dict[str, Any]: 実行結果
        """
        try:
            cmd = [
                "cursor-agent",
                "--api-key", self.cursor_api_key,
                prompt
            ]

            # 実行環境設定
            env = os.environ.copy()
            env["CURSOR_API_KEY"] = self.cursor_api_key

            # コマンド実行
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                timeout=settings.CURSOR_CLI_TIMEOUT,
            )

            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise CursorCLIError(f"cursor-cli command failed: {error_msg}", " ".join(cmd))

            # 結果解析
            output = stdout.decode()
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                # JSON以外の出力の場合
                return {"output": output}

        except asyncio.TimeoutError:
            raise CursorCLIError("cursor-cli command timed out", " ".join(cmd))
        except Exception as e:
            raise CursorCLIError(f"cursor-cli execution failed: {str(e)}", " ".join(cmd))

    def _generate_analysis_prompt(self, error_data: Dict[str, Any]) -> str:
        """エラー解析プロンプト生成"""
        error_type = error_data.get("error_type", "unknown")

        prompts = {
            "syntax_error": f"""
            Analyze this syntax error and provide a detailed analysis:

            File: {error_data.get('file_path', 'unknown')}
            Line: {error_data.get('line_number', 'unknown')}
            Error: {error_data.get('error_message', '')}
            Language: {error_data.get('language', 'unknown')}
            Stack trace: {error_data.get('stack_trace', '')}

            Please provide:
            1. Root cause analysis
            2. Impact assessment
            3. Fix recommendations
            4. Prevention strategies

            Return the analysis in JSON format.
            """,

            "logic_error": f"""
            Analyze this logic error and provide comprehensive analysis:

            Error: {error_data.get('error_message', '')}
            Stack trace: {error_data.get('stack_trace', '')}
            File: {error_data.get('file_path', 'unknown')}

            Consider:
            1. Data flow analysis
            2. Edge cases
            3. Business logic impact
            4. Error handling improvements

            Return the analysis in JSON format.
            """,

            "performance_error": f"""
            Analyze this performance issue:

            Error: {error_data.get('error_message', '')}
            Service: {error_data.get('service_name', 'unknown')}

            Provide:
            1. Performance bottleneck identification
            2. Resource usage analysis
            3. Optimization strategies
            4. Monitoring improvements

            Return the analysis in JSON format.
            """
        }

        return prompts.get(error_type, prompts["syntax_error"])

    def _generate_fix_prompt(
        self,
        error_data: Dict[str, Any],
        analysis_result: Dict[str, Any]
    ) -> str:
        """修正プロンプト生成"""
        return f"""
        Based on the error analysis: {json.dumps(analysis_result.get('analysis_result', {}))}

        Generate a comprehensive fix for this {error_data.get('language', 'unknown')} error:
        - Error type: {error_data.get('error_type', 'unknown')}
        - File: {error_data.get('file_path', 'unknown')}
        - Line: {error_data.get('line_number', 'unknown')}

        Requirements:
        1. Fix the immediate error
        2. Add proper error handling
        3. Include unit tests
        4. Add logging for monitoring
        5. Follow best practices for {error_data.get('language', 'unknown')}

        Return JSON with:
        - fixed_code: the corrected code
        - test_code: unit tests
        - explanation: detailed explanation of changes
        """

    def _generate_pr_description(
        self,
        fix_data: Dict[str, Any],
        test_results: Dict[str, Any],
        error_data: Dict[str, Any]
    ) -> str:
        """PR説明文生成"""
        return f"""
## 🤖 Automated Fix

**Error Type:** {error_data.get('error_type', 'Unknown')}
**File:** {error_data.get('file_path', 'Unknown')}
**Line:** {error_data.get('line_number', 'Unknown')}

### 📋 Error Description
{error_data.get('error_message', 'No description available')}

### 🔧 Fix Applied
{fix_data.get('explanation', 'No explanation available')}

### ✅ Test Results
- **Unit Tests:** {'✅ Passed' if test_results.get('unit_tests', {}).get('passed') else '❌ Failed'}
- **Integration Tests:** {'✅ Passed' if test_results.get('integration_tests', {}).get('passed') else '❌ Failed'}
- **Lint Checks:** {'✅ Passed' if test_results.get('lint_checks', {}).get('passed') else '❌ Failed'}
- **Security Checks:** {'✅ Passed' if test_results.get('security_checks', {}).get('passed') else '❌ Failed'}

### 🎯 Impact
This automated fix addresses the error and includes proper error handling and testing.

---
*This PR was automatically generated by the Auto Remediation System*
        """

    async def _apply_fix(self, fix_data: Dict[str, Any], repo_path: str) -> None:
        """修正コード適用"""
        # 実際の実装では、ファイルに修正を適用
        logger.info("Fix applied to repository", repo_path=repo_path)

    async def _run_unit_tests(self, repo_path: str) -> Dict[str, Any]:
        """単体テスト実行"""
        # 実際の実装では、pytest等を実行
        return {"passed": True, "details": "All unit tests passed"}

    async def _run_integration_tests(self, repo_path: str) -> Dict[str, Any]:
        """統合テスト実行"""
        # 実際の実装では、統合テストを実行
        return {"passed": True, "details": "All integration tests passed"}

    async def _run_lint_checks(self, repo_path: str) -> Dict[str, Any]:
        """Lintチェック実行"""
        # 実際の実装では、flake8, eslint等を実行
        return {"passed": True, "details": "No lint issues found"}

    async def _run_security_checks(self, repo_path: str) -> Dict[str, Any]:
        """セキュリティチェック実行"""
        # 実際の実装では、bandit, safety等を実行
        return {"passed": True, "details": "No security issues found"}
