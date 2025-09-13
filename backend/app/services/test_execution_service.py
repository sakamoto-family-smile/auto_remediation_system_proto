"""
テスト実行サービス
"""

import asyncio
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger()


class TestExecutionService:
    """自動テスト実行サービス"""

    def __init__(self, working_directory: Optional[str] = None):
        """
        テスト実行サービス初期化

        Args:
            working_directory: 作業ディレクトリ
        """
        self.working_directory = working_directory or os.getcwd()
        logger.info("Test execution service initialized", cwd=self.working_directory)

    async def run_python_tests(
        self,
        test_paths: Optional[List[str]] = None,
        test_framework: str = "pytest",
        coverage: bool = True,
        timeout: int = 300,
    ) -> Dict[str, Any]:
        """
        Python テスト実行

        Args:
            test_paths: テストファイル/ディレクトリパス
            test_framework: テストフレームワーク (pytest/unittest)
            coverage: カバレッジ測定するか
            timeout: タイムアウト秒数

        Returns:
            Dict[str, Any]: テスト結果
        """
        try:
            if test_framework == "pytest":
                return await self._run_pytest(test_paths, coverage, timeout)
            elif test_framework == "unittest":
                return await self._run_unittest(test_paths, timeout)
            else:
                raise ValueError(f"Unsupported test framework: {test_framework}")

        except Exception as e:
            logger.error("Failed to run Python tests", error=str(e))
            return {
                "status": "error",
                "error": str(e),
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "execution_time": 0,
                "coverage": None,
            }

    async def run_javascript_tests(
        self,
        test_paths: Optional[List[str]] = None,
        test_framework: str = "jest",
        coverage: bool = True,
        timeout: int = 300,
    ) -> Dict[str, Any]:
        """
        JavaScript テスト実行

        Args:
            test_paths: テストファイル/ディレクトリパス
            test_framework: テストフレームワーク (jest/mocha)
            coverage: カバレッジ測定するか
            timeout: タイムアウト秒数

        Returns:
            Dict[str, Any]: テスト結果
        """
        try:
            if test_framework == "jest":
                return await self._run_jest(test_paths, coverage, timeout)
            elif test_framework == "mocha":
                return await self._run_mocha(test_paths, timeout)
            else:
                raise ValueError(f"Unsupported test framework: {test_framework}")

        except Exception as e:
            logger.error("Failed to run JavaScript tests", error=str(e))
            return {
                "status": "error",
                "error": str(e),
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "execution_time": 0,
                "coverage": None,
            }

    async def run_linting(
        self,
        file_paths: Optional[List[str]] = None,
        language: str = "python",
    ) -> Dict[str, Any]:
        """
        コードリンティング実行

        Args:
            file_paths: 対象ファイルパス
            language: プログラミング言語

        Returns:
            Dict[str, Any]: リンティング結果
        """
        try:
            if language == "python":
                return await self._run_python_linting(file_paths)
            elif language == "javascript":
                return await self._run_javascript_linting(file_paths)
            else:
                raise ValueError(f"Unsupported language for linting: {language}")

        except Exception as e:
            logger.error("Failed to run linting", error=str(e))
            return {
                "status": "error",
                "error": str(e),
                "issues": [],
                "total_issues": 0,
            }

    async def run_security_scan(
        self,
        target_paths: Optional[List[str]] = None,
        language: str = "python",
    ) -> Dict[str, Any]:
        """
        セキュリティスキャン実行

        Args:
            target_paths: 対象パス
            language: プログラミング言語

        Returns:
            Dict[str, Any]: スキャン結果
        """
        try:
            if language == "python":
                return await self._run_bandit_scan(target_paths)
            else:
                return {
                    "status": "skipped",
                    "message": f"Security scan not implemented for {language}",
                    "vulnerabilities": [],
                    "total_vulnerabilities": 0,
                }

        except Exception as e:
            logger.error("Failed to run security scan", error=str(e))
            return {
                "status": "error",
                "error": str(e),
                "vulnerabilities": [],
                "total_vulnerabilities": 0,
            }

    async def _run_pytest(
        self, test_paths: Optional[List[str]], coverage: bool, timeout: int
    ) -> Dict[str, Any]:
        """pytest 実行"""
        cmd = ["python", "-m", "pytest"]

        if coverage:
            cmd.extend(["--cov=.", "--cov-report=json"])

        cmd.extend(["-v", "--tb=short"])

        if test_paths:
            cmd.extend(test_paths)

        result = await self._run_command(cmd, timeout)

        # カバレッジ情報を読み込み
        coverage_data = None
        if coverage and result["exit_code"] == 0:
            coverage_data = await self._read_coverage_json()

        # pytest出力を解析
        test_summary = self._parse_pytest_output(result["stdout"])

        return {
            "status": "success" if result["exit_code"] == 0 else "failure",
            "exit_code": result["exit_code"],
            "execution_time": result["execution_time"],
            "coverage": coverage_data,
            **test_summary,
        }

    async def _run_unittest(
        self, test_paths: Optional[List[str]], timeout: int
    ) -> Dict[str, Any]:
        """unittest 実行"""
        cmd = ["python", "-m", "unittest"]

        if test_paths:
            cmd.extend(test_paths)
        else:
            cmd.append("discover")

        cmd.extend(["-v"])

        result = await self._run_command(cmd, timeout)
        test_summary = self._parse_unittest_output(result["stderr"])

        return {
            "status": "success" if result["exit_code"] == 0 else "failure",
            "exit_code": result["exit_code"],
            "execution_time": result["execution_time"],
            "coverage": None,
            **test_summary,
        }

    async def _run_jest(
        self, test_paths: Optional[List[str]], coverage: bool, timeout: int
    ) -> Dict[str, Any]:
        """Jest 実行"""
        cmd = ["npx", "jest"]

        if coverage:
            cmd.append("--coverage")

        cmd.extend(["--verbose", "--json"])

        if test_paths:
            cmd.extend(test_paths)

        result = await self._run_command(cmd, timeout)

        # Jest JSON出力を解析
        try:
            jest_result = json.loads(result["stdout"])
            test_summary = self._parse_jest_output(jest_result)
        except json.JSONDecodeError:
            test_summary = {
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "test_suites": 0,
            }

        return {
            "status": "success" if result["exit_code"] == 0 else "failure",
            "exit_code": result["exit_code"],
            "execution_time": result["execution_time"],
            "coverage": None,  # Jest coverage handling would go here
            **test_summary,
        }

    async def _run_mocha(
        self, test_paths: Optional[List[str]], timeout: int
    ) -> Dict[str, Any]:
        """Mocha 実行"""
        cmd = ["npx", "mocha"]

        if test_paths:
            cmd.extend(test_paths)

        cmd.extend(["--reporter", "json"])

        result = await self._run_command(cmd, timeout)

        # Mocha JSON出力を解析
        try:
            mocha_result = json.loads(result["stdout"])
            test_summary = self._parse_mocha_output(mocha_result)
        except json.JSONDecodeError:
            test_summary = {
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "test_suites": 0,
            }

        return {
            "status": "success" if result["exit_code"] == 0 else "failure",
            "exit_code": result["exit_code"],
            "execution_time": result["execution_time"],
            "coverage": None,
            **test_summary,
        }

    async def _run_python_linting(
        self, file_paths: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Python リンティング実行"""
        results = {}

        # flake8
        flake8_cmd = ["python", "-m", "flake8"]
        if file_paths:
            flake8_cmd.extend(file_paths)
        else:
            flake8_cmd.append(".")

        flake8_result = await self._run_command(flake8_cmd, 60)
        results["flake8"] = self._parse_flake8_output(flake8_result["stdout"])

        # mypy (型チェック)
        mypy_cmd = ["python", "-m", "mypy"]
        if file_paths:
            mypy_cmd.extend(file_paths)
        else:
            mypy_cmd.append(".")

        mypy_result = await self._run_command(mypy_cmd, 60)
        results["mypy"] = self._parse_mypy_output(mypy_result["stdout"])

        total_issues = sum(len(result["issues"]) for result in results.values())

        return {
            "status": "success" if total_issues == 0 else "issues_found",
            "total_issues": total_issues,
            "results": results,
        }

    async def _run_javascript_linting(
        self, file_paths: Optional[List[str]]
    ) -> Dict[str, Any]:
        """JavaScript リンティング実行"""
        cmd = ["npx", "eslint", "--format", "json"]

        if file_paths:
            cmd.extend(file_paths)
        else:
            cmd.extend(["src/**/*.{js,jsx,ts,tsx}"])

        result = await self._run_command(cmd, 60)

        try:
            eslint_result = json.loads(result["stdout"])
            issues = self._parse_eslint_output(eslint_result)
        except json.JSONDecodeError:
            issues = []

        return {
            "status": "success" if len(issues) == 0 else "issues_found",
            "total_issues": len(issues),
            "issues": issues,
        }

    async def _run_bandit_scan(
        self, target_paths: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Bandit セキュリティスキャン実行"""
        cmd = ["python", "-m", "bandit", "-f", "json"]

        if target_paths:
            for path in target_paths:
                cmd.extend(["-r", path])
        else:
            cmd.extend(["-r", "."])

        result = await self._run_command(cmd, 60)

        try:
            bandit_result = json.loads(result["stdout"])
            vulnerabilities = self._parse_bandit_output(bandit_result)
        except json.JSONDecodeError:
            vulnerabilities = []

        return {
            "status": "success" if len(vulnerabilities) == 0 else "vulnerabilities_found",
            "total_vulnerabilities": len(vulnerabilities),
            "vulnerabilities": vulnerabilities,
        }

    async def _run_command(
        self, cmd: List[str], timeout: int
    ) -> Dict[str, Any]:
        """コマンド実行"""
        import time

        start_time = time.time()

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.working_directory,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            execution_time = time.time() - start_time

            logger.debug(
                "Command executed",
                cmd=" ".join(cmd),
                exit_code=process.returncode,
                execution_time=execution_time,
            )

            return {
                "exit_code": process.returncode,
                "stdout": stdout.decode("utf-8"),
                "stderr": stderr.decode("utf-8"),
                "execution_time": execution_time,
            }

        except asyncio.TimeoutError:
            logger.warning("Command timeout", cmd=" ".join(cmd), timeout=timeout)
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": "Command timed out",
                "execution_time": timeout,
            }
        except Exception as e:
            logger.error("Command execution failed", cmd=" ".join(cmd), error=str(e))
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "execution_time": time.time() - start_time,
            }

    async def _read_coverage_json(self) -> Optional[Dict[str, Any]]:
        """カバレッジJSONファイル読み込み"""
        coverage_file = Path(self.working_directory) / "coverage.json"

        try:
            if coverage_file.exists():
                with open(coverage_file, "r") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning("Failed to read coverage file", error=str(e))

        return None

    def _parse_pytest_output(self, output: str) -> Dict[str, Any]:
        """pytest出力解析"""
        # 簡単な解析（実際の実装ではより詳細に解析）
        lines = output.split("\n")
        summary_line = ""

        for line in lines:
            if "passed" in line and ("failed" in line or "error" in line):
                summary_line = line
                break

        if summary_line:
            # "5 passed, 2 failed in 1.23s" のような形式を解析
            parts = summary_line.split()
            tests_passed = 0
            tests_failed = 0

            for i, part in enumerate(parts):
                if part == "passed":
                    tests_passed = int(parts[i-1])
                elif part == "failed":
                    tests_failed = int(parts[i-1])
        else:
            tests_passed = 0
            tests_failed = 0

        return {
            "tests_run": tests_passed + tests_failed,
            "tests_passed": tests_passed,
            "tests_failed": tests_failed,
        }

    def _parse_unittest_output(self, output: str) -> Dict[str, Any]:
        """unittest出力解析"""
        # 簡単な解析
        lines = output.split("\n")
        tests_run = 0
        tests_failed = 0

        for line in lines:
            if "Ran" in line and "test" in line:
                parts = line.split()
                if len(parts) >= 2:
                    tests_run = int(parts[1])
            elif "FAILED" in line:
                parts = line.split("=")
                if len(parts) >= 2:
                    failure_info = parts[1].strip()
                    if "failures" in failure_info:
                        tests_failed = int(failure_info.split()[1])

        return {
            "tests_run": tests_run,
            "tests_passed": tests_run - tests_failed,
            "tests_failed": tests_failed,
        }

    def _parse_jest_output(self, jest_result: Dict[str, Any]) -> Dict[str, Any]:
        """Jest出力解析"""
        return {
            "tests_run": jest_result.get("numTotalTests", 0),
            "tests_passed": jest_result.get("numPassedTests", 0),
            "tests_failed": jest_result.get("numFailedTests", 0),
            "test_suites": jest_result.get("numTotalTestSuites", 0),
        }

    def _parse_mocha_output(self, mocha_result: Dict[str, Any]) -> Dict[str, Any]:
        """Mocha出力解析"""
        stats = mocha_result.get("stats", {})
        return {
            "tests_run": stats.get("tests", 0),
            "tests_passed": stats.get("passes", 0),
            "tests_failed": stats.get("failures", 0),
            "test_suites": stats.get("suites", 0),
        }

    def _parse_flake8_output(self, output: str) -> Dict[str, Any]:
        """flake8出力解析"""
        issues = []
        for line in output.strip().split("\n"):
            if line.strip():
                issues.append({"tool": "flake8", "message": line})

        return {"issues": issues}

    def _parse_mypy_output(self, output: str) -> Dict[str, Any]:
        """mypy出力解析"""
        issues = []
        for line in output.strip().split("\n"):
            if line.strip() and "error:" in line:
                issues.append({"tool": "mypy", "message": line})

        return {"issues": issues}

    def _parse_eslint_output(self, eslint_result: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """ESLint出力解析"""
        issues = []
        for file_result in eslint_result:
            for message in file_result.get("messages", []):
                issues.append({
                    "file": file_result["filePath"],
                    "line": message.get("line"),
                    "column": message.get("column"),
                    "severity": message.get("severity"),
                    "message": message.get("message"),
                    "rule": message.get("ruleId"),
                })

        return issues

    def _parse_bandit_output(self, bandit_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Bandit出力解析"""
        vulnerabilities = []
        for result in bandit_result.get("results", []):
            vulnerabilities.append({
                "file": result.get("filename"),
                "line": result.get("line_number"),
                "severity": result.get("issue_severity"),
                "confidence": result.get("issue_confidence"),
                "message": result.get("issue_text"),
                "test": result.get("test_name"),
            })

        return vulnerabilities
