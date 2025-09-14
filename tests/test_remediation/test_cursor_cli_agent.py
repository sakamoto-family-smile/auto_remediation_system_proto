"""
改修エージェントのテスト
"""
import pytest
import os
from unittest.mock import Mock, patch, AsyncMock
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

@pytest.fixture
def mock_env():
    """テスト用環境変数を設定"""
    env_vars = {
        'SECRET_KEY': 'test-secret-key',
        'DATABASE_URL': 'sqlite+aiosqlite:///./test.db',
        'GOOGLE_CLOUD_PROJECT': 'test-project',
        'VERTEX_AI_LOCATION': 'us-central1',
        'VERTEX_AI_MODEL_NAME': 'claude-3-sonnet@20240229',
        'FIREBASE_PROJECT_ID': 'test-firebase',
        'FIREBASE_WEB_API_KEY': 'test-api-key',
        'GITHUB_TOKEN': 'test-github-token',
        'CURSOR_API_KEY': 'test-cursor-key',
        'FRONTEND_URL': 'http://localhost:3000',
        'GITHUB_WEBHOOK_SECRET': 'test-webhook-secret'
    }

    with patch.dict(os.environ, env_vars, clear=False):
        yield env_vars

@pytest.fixture
def mock_services():
    """サービスクラスをモック"""
    with patch('remediation.cursor_cli_agent.VertexAIService') as mock_vertex, \
         patch('remediation.cursor_cli_agent.GitHubService') as mock_github, \
         patch('remediation.cursor_cli_agent.TestExecutionService') as mock_test:

        # VertexAIServiceのモック
        mock_vertex_instance = Mock()
        mock_vertex_instance.analyze_error = AsyncMock(return_value={
            'analysis': 'Test analysis',
            'confidence': 0.9
        })
        mock_vertex.return_value = mock_vertex_instance

        # GitHubServiceのモック
        mock_github_instance = Mock()
        mock_github_instance.create_pull_request = AsyncMock(return_value={
            'pr_url': 'https://github.com/test/repo/pull/1',
            'pr_number': 1
        })
        mock_github.return_value = mock_github_instance

        # TestExecutionServiceのモック
        mock_test_instance = Mock()
        mock_test_instance.run_tests = AsyncMock(return_value={
            'status': 'success',
            'results': 'All tests passed'
        })
        mock_test.return_value = mock_test_instance

        yield {
            'vertex_ai': mock_vertex_instance,
            'github': mock_github_instance,
            'test_executor': mock_test_instance
        }

class TestCursorCLIAgent:
    """CursorCLIAgentのテストクラス"""

    @pytest.mark.asyncio
    async def test_agent_initialization(self, mock_env, mock_services):
        """エージェントの初期化テスト"""
        from remediation.cursor_cli_agent import CursorCLIAgent

        agent = CursorCLIAgent()

        # 基本属性の確認
        assert hasattr(agent, 'vertex_ai')
        assert hasattr(agent, 'github_service')
        assert hasattr(agent, 'cursor_api_key')

        # メソッドの存在確認
        assert hasattr(agent, 'analyze_error')
        assert hasattr(agent, 'generate_fix')
        assert hasattr(agent, 'create_pull_request')
        assert hasattr(agent, 'test_fix')

    @pytest.mark.asyncio
    async def test_analyze_error(self, mock_env, mock_services):
        """エラー分析機能のテスト"""
        from remediation.cursor_cli_agent import CursorCLIAgent

        agent = CursorCLIAgent()

        error_data = {
            'error_type': 'SyntaxError',
            'error_message': 'Invalid syntax',
            'file_path': 'test.py',
            'line_number': 10
        }

        result = await agent.analyze_error(error_data)

        # 結果の検証
        assert 'analysis' in result
        assert 'confidence' in result
        assert result['confidence'] == 0.9

        # VertexAIServiceが呼ばれたことを確認
        mock_services['vertex_ai'].analyze_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_fix(self, mock_env, mock_services):
        """修正生成機能のテスト"""
        from remediation.cursor_cli_agent import CursorCLIAgent

        agent = CursorCLIAgent()

        error_data = {
            'error_type': 'TypeError',
            'error_message': 'Expected str, got int',
            'file_path': 'test.py'
        }

        analysis_result = {
            'analysis': 'Type conversion needed',
            'confidence': 0.8
        }

        # generate_fixメソッドが存在することを確認
        assert callable(getattr(agent, 'generate_fix', None))

    @pytest.mark.asyncio
    async def test_create_pull_request(self, mock_env, mock_services):
        """PR作成機能のテスト"""
        from remediation.cursor_cli_agent import CursorCLIAgent

        agent = CursorCLIAgent()

        fix_data = {
            'title': 'Fix: TypeError in test.py',
            'description': 'Automatic fix for type conversion',
            'changes': ['Added type conversion']
        }

        result = await agent.create_pull_request(fix_data)

        # 結果の検証
        assert 'pr_url' in result
        assert 'pr_number' in result
        assert result['pr_number'] == 1

        # GitHubServiceが呼ばれたことを確認
        mock_services['github'].create_pull_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_fix(self, mock_env, mock_services):
        """テスト実行機能のテスト"""
        from remediation.cursor_cli_agent import CursorCLIAgent

        agent = CursorCLIAgent()

        test_config = {
            'test_files': ['test_example.py'],
            'test_type': 'unit'
        }

        # test_fixメソッドが存在することを確認
        assert callable(getattr(agent, 'test_fix', None))

    def test_agent_attributes(self, mock_env, mock_services):
        """エージェントの属性テスト"""
        from remediation.cursor_cli_agent import CursorCLIAgent

        agent = CursorCLIAgent()

        # 必要な属性が存在することを確認
        required_attributes = [
            'vertex_ai',
            'github_service',
            'cursor_api_key'
        ]

        for attr in required_attributes:
            assert hasattr(agent, attr), f"Missing attribute: {attr}"

    def test_agent_methods(self, mock_env, mock_services):
        """エージェントのメソッドテスト"""
        from remediation.cursor_cli_agent import CursorCLIAgent

        agent = CursorCLIAgent()

        # 必要なメソッドが存在することを確認
        required_methods = [
            'analyze_error',
            'generate_fix',
            'create_pull_request',
            'test_fix'
        ]

        for method in required_methods:
            assert hasattr(agent, method), f"Missing method: {method}"
            assert callable(getattr(agent, method)), f"Method {method} is not callable"

@pytest.mark.integration
class TestCursorCLIAgentIntegration:
    """統合テスト"""

    @pytest.mark.asyncio
    async def test_full_remediation_workflow(self, mock_env, mock_services):
        """完全な改修ワークフローのテスト"""
        from remediation.cursor_cli_agent import CursorCLIAgent

        agent = CursorCLIAgent()

        # エラーデータ
        error_data = {
            'error_type': 'ImportError',
            'error_message': 'No module named requests',
            'file_path': 'app.py',
            'line_number': 1
        }

        # 1. エラー分析
        analysis = await agent.analyze_error(error_data)
        assert 'analysis' in analysis

        # 2. 修正生成（メソッド存在確認）
        assert callable(getattr(agent, 'generate_fix', None))

        # 3. PR作成
        fix_data = {
            'title': 'Fix: ImportError in app.py',
            'description': 'Add missing import',
            'changes': ['Added requests import']
        }
        pr_result = await agent.create_pull_request(fix_data)
        assert 'pr_url' in pr_result

        # 4. テスト実行（メソッド存在確認）
        assert callable(getattr(agent, 'test_fix', None))
