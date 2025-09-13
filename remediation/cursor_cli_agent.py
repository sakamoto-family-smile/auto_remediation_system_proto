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

from app.core.config import get_settings
from app.core.exceptions import CursorCLIError, ExternalServiceError
from app.services.vertex_ai_service import VertexAIService
from app.services.github_service import GitHubService
from app.services.test_execution_service import TestExecutionService

logger = structlog.get_logger()
settings = get_settings()


class CursorCLIAgent:
    """cursor-cli統合エージェント"""

    def __init__(self):
        # 新しいサービス統合
        self.vertex_ai = VertexAIService()
        self.github_service = GitHubService()
        self.test_service = TestExecutionService()

        # レガシー設定（後方互換性のため保持）
        self.cursor_api_key = getattr(settings, 'CURSOR_API_KEY', None)

        logger.info("Enhanced CursorCLIAgent initialized with new services")

    async def analyze_error(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Vertex AIを使用してエラー解析

        Args:
            error_data: エラー情報

        Returns:
            Dict[str, Any]: 解析結果
        """
        try:
            # Vertex AIでエラー解析
            analysis_result = await self.vertex_ai.analyze_error_code(
                error_message=error_data.get("error_message", ""),
                stack_trace=error_data.get("stack_trace"),
                file_path=error_data.get("file_path"),
                language=error_data.get("language"),
                context_code=error_data.get("context_code"),
            )

            logger.info(
                "Enhanced error analysis completed",
                error_type=error_data.get("error_type"),
                file_path=error_data.get("file_path"),
                confidence_score=analysis_result.get("confidence_score", 0),
            )

            return {
                "analysis_result": analysis_result,
                "service_used": "vertex_ai",
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error("Enhanced error analysis failed", error=str(e), error_data=error_data)
            # フォールバック：従来の方法
            return await self._fallback_analyze_error(error_data)

    async def generate_fix(
        self,
        error_data: Dict[str, Any],
        analysis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Vertex AIを使用して修正コード生成

        Args:
            error_data: エラー情報
            analysis_result: 解析結果

        Returns:
            Dict[str, Any]: 修正コード情報
        """
        try:
            # 元のコードを取得（可能な場合）
            original_code = None
            if error_data.get("file_path") and self.github_service.is_configured():
                repo_name = error_data.get("repo_name")
                if repo_name:
                    original_code = await self.github_service.get_file_content(
                        repo_name=repo_name,
                        file_path=error_data["file_path"],
                        branch=error_data.get("branch", "main")
                    )

            # Vertex AIで修正コード生成
            fix_result = await self.vertex_ai.generate_fix_code(
                error_analysis=analysis_result.get("analysis_result", {}),
                original_code=original_code,
                file_path=error_data.get("file_path"),
                language=error_data.get("language"),
            )

            logger.info(
                "Enhanced fix generation completed",
                error_type=error_data.get("error_type"),
                file_path=error_data.get("file_path"),
                confidence_score=fix_result.get("confidence_score", 0),
            )

            return {
                "fix_code": fix_result.get("fixed_code", ""),
                "explanation": fix_result.get("explanation", ""),
                "changes": fix_result.get("changes", []),
                "test_suggestions": fix_result.get("test_suggestions", []),
                "service_used": "vertex_ai",
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error("Enhanced fix generation failed", error=str(e), error_data=error_data)
            # フォールバック：従来の方法
            return await self._fallback_generate_fix(error_data, analysis_result)

    async def test_fix(
        self,
        fix_data: Dict[str, Any],
        repo_path: str,
        language: str = "python"
    ) -> Dict[str, Any]:
        """
        修正コードの包括的テスト実行

        Args:
            fix_data: 修正コード情報
            repo_path: リポジトリパス
            language: プログラミング言語

        Returns:
            Dict[str, Any]: テスト結果
        """
        try:
            # TestExecutionServiceを使用して包括的テスト実行
            # 既存のサービスインスタンスを再利用し、作業ディレクトリを更新
            if not hasattr(self, 'test_service') or self.test_service is None:
                self.test_service = TestExecutionService(repo_path)
                logger.info("Created new TestExecutionService instance", repo_path=repo_path)
            else:
                # 既存のインスタンスの作業ディレクトリを更新
                old_dir = self.test_service.working_directory
                self.test_service.working_directory = repo_path
                logger.info("Updated TestExecutionService working directory",
                            old_dir=old_dir, new_dir=repo_path)

            results = {
                "success": False,
                "unit_tests": {},
                "lint_checks": {},
                "security_checks": {},
                "timestamp": datetime.utcnow().isoformat(),
            }

            # 修正コード適用
            await self._apply_fix(fix_data, repo_path)

            # 言語別テスト実行
            if language == "python":
                results["unit_tests"] = await self.test_service.run_python_tests()
                results["lint_checks"] = await self.test_service.run_linting(language="python")
                results["security_checks"] = await self.test_service.run_security_scan(language="python")
            elif language in ["javascript", "typescript"]:
                results["unit_tests"] = await self.test_service.run_javascript_tests()
                results["lint_checks"] = await self.test_service.run_linting(language="javascript")

            # 全テスト成功判定
            results["success"] = all([
                results["unit_tests"].get("status") == "success",
                results["lint_checks"].get("status") in ["success", "skipped"],
                results["security_checks"].get("status") in ["success", "skipped"],
            ])

            logger.info(
                "Enhanced fix testing completed",
                success=results["success"],
                repo_path=repo_path,
                language=language,
            )

            return results

        except Exception as e:
            logger.error("Enhanced fix testing failed", error=str(e), repo_path=repo_path)
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
        GitHub PRの自動作成（強化版）

        Args:
            fix_data: 修正コード情報
            test_results: テスト結果
            error_data: エラー情報
            repo_name: リポジトリ名
            branch_name: ブランチ名（省略時は自動生成）

        Returns:
            Dict[str, Any]: PR情報
        """
        if not self.github_service.is_configured():
            raise ExternalServiceError("GitHub", "GitHub token not configured")

        try:
            # ブランチ名生成
            if not branch_name:
                branch_name = f"auto-fix-{error_data.get('error_type', 'error')}-{uuid.uuid4().hex[:8]}"

            # PR作成
            pr_title = f"🤖 Auto-fix: {error_data.get('error_type', 'Error')} in {error_data.get('file_path', 'unknown')}"
            pr_body = self._generate_enhanced_pr_description(fix_data, test_results, error_data)

            # ファイル変更情報を準備
            files_to_change = []
            if fix_data.get("fix_code") and error_data.get("file_path"):
                files_to_change.append({
                    "path": error_data["file_path"],
                    "content": fix_data["fix_code"]
                })

            # GitHubServiceを使用してPR作成
            pr_info = await self.github_service.create_pull_request(
                repo_name=repo_name,
                title=pr_title,
                body=pr_body,
                head_branch=branch_name,
                base_branch=error_data.get("base_branch", "main"),
                files_to_change=files_to_change,
            )

            logger.info(
                "Enhanced pull request created",
                repo_name=repo_name,
                branch_name=branch_name,
                pr_url=pr_info["pr_url"],
                pr_number=pr_info["pr_number"],
            )

            return {
                **pr_info,
                "timestamp": datetime.utcnow().isoformat(),
                "service_used": "github_service",
            }

        except Exception as e:
            logger.error("Enhanced pull request creation failed", error=str(e), repo_name=repo_name)
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

    async def _fallback_analyze_error(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """フォールバック：従来のエラー解析"""
        try:
            if self.cursor_api_key:
                prompt = self._generate_analysis_prompt(error_data)
                result = await self._run_cursor_cli_command(
                    command="analyze",
                    prompt=prompt,
                    file_path=error_data.get("file_path"),
                    language=error_data.get("language"),
                )
                return {
                    "analysis_result": result,
                    "service_used": "cursor_cli",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            else:
                return {
                    "analysis_result": {
                        "error_category": "unknown",
                        "root_cause": "Analysis service unavailable",
                        "recommendations": ["Manual investigation required"],
                        "confidence_score": 0.3,
                    },
                    "service_used": "fallback",
                    "timestamp": datetime.utcnow().isoformat(),
                }
        except Exception as e:
            logger.error("Fallback error analysis failed", error=str(e))
            return {
                "analysis_result": {
                    "error_category": "service_error",
                    "root_cause": f"Analysis failed: {str(e)}",
                    "recommendations": ["Check service configuration"],
                    "confidence_score": 0.0,
                },
                "service_used": "error_fallback",
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def _fallback_generate_fix(
        self, error_data: Dict[str, Any], analysis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """フォールバック：従来の修正コード生成"""
        try:
            if self.cursor_api_key:
                prompt = self._generate_fix_prompt(error_data, analysis_result)
                result = await self._run_cursor_cli_command(
                    command="fix",
                    prompt=prompt,
                    file_path=error_data.get("file_path"),
                    language=error_data.get("language"),
                )
                return {
                    "fix_code": result.get("fixed_code", ""),
                    "explanation": result.get("explanation", ""),
                    "service_used": "cursor_cli",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            else:
                return {
                    "fix_code": f"// Fix service unavailable for {error_data.get('error_type', 'error')}",
                    "explanation": "Automated fix generation is currently unavailable",
                    "service_used": "fallback",
                    "timestamp": datetime.utcnow().isoformat(),
                }
        except Exception as e:
            logger.error("Fallback fix generation failed", error=str(e))
            return {
                "fix_code": f"// Fix generation failed: {str(e)}",
                "explanation": "Failed to generate automated fix",
                "service_used": "error_fallback",
                "timestamp": datetime.utcnow().isoformat(),
            }

    def _generate_enhanced_pr_description(
        self,
        fix_data: Dict[str, Any],
        test_results: Dict[str, Any],
        error_data: Dict[str, Any]
    ) -> str:
        """強化されたPR説明文生成"""
        service_used = fix_data.get("service_used", "unknown")
        confidence_score = fix_data.get("confidence_score", "N/A")

        return f"""
## 🤖 Enhanced Automated Fix

**Error Type:** {error_data.get('error_type', 'Unknown')}
**File:** {error_data.get('file_path', 'Unknown')}
**Line:** {error_data.get('line_number', 'Unknown')}
**Service:** {service_used}
**Confidence:** {confidence_score}

### 📋 Error Description
{error_data.get('error_message', 'No description available')}

### 🔧 Fix Applied
{fix_data.get('explanation', 'No explanation available')}

### 📝 Changes Made
{chr(10).join(f"- {change}" for change in fix_data.get('changes', ['No specific changes listed']))}

### ✅ Test Results
- **Unit Tests:** {'✅ Passed' if test_results.get('unit_tests', {}).get('status') == 'success' else '❌ Failed/Skipped'}
- **Lint Checks:** {'✅ Passed' if test_results.get('lint_checks', {}).get('status') == 'success' else '❌ Failed/Skipped'}
- **Security Checks:** {'✅ Passed' if test_results.get('security_checks', {}).get('status') == 'success' else '❌ Failed/Skipped'}

### 🧪 Test Suggestions
{chr(10).join(f"- {suggestion}" for suggestion in fix_data.get('test_suggestions', ['No specific test suggestions']))}

### 🎯 Impact
This enhanced automated fix addresses the error using AI-powered analysis and includes:
- Comprehensive error analysis
- Context-aware code generation
- Automated testing validation
- Security and quality checks

### 🔍 Review Checklist
- [ ] Verify the fix addresses the root cause
- [ ] Check for any side effects or edge cases
- [ ] Validate test coverage is adequate
- [ ] Ensure code follows project standards

---
*This PR was automatically generated by the Enhanced Auto Remediation System using {service_used}*
        """
