"""
GitHub統合サービス
"""

import base64
from typing import Any, Dict, List, Optional

import structlog
from github import Github
from github.GithubException import GithubException

from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class GitHubService:
    """GitHub API統合サービス"""

    def __init__(self, access_token: Optional[str] = None):
        """
        GitHub サービス初期化

        Args:
            access_token: GitHub アクセストークン
        """
        self.access_token = access_token or settings.GITHUB_ACCESS_TOKEN

        if self.access_token:
            self.github = Github(self.access_token)
            logger.info("GitHub service initialized")
        else:
            self.github = None
            logger.warning("GitHub access token not provided")

    async def create_pull_request(
        self,
        repo_name: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
        files_to_change: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        プルリクエスト作成

        Args:
            repo_name: リポジトリ名 (owner/repo形式)
            title: PR タイトル
            body: PR 説明
            head_branch: ソースブランチ
            base_branch: ターゲットブランチ
            files_to_change: 変更するファイル情報

        Returns:
            Dict[str, Any]: PR情報
        """
        try:
            if not self.github:
                raise ValueError("GitHub access token not configured")

            repo = self.github.get_repo(repo_name)

            # ファイル変更がある場合は新しいブランチを作成
            if files_to_change:
                # ベースブランチの最新コミットを取得
                base_ref = repo.get_git_ref(f"heads/{base_branch}")
                base_sha = base_ref.object.sha

                # 新しいブランチを作成
                try:
                    repo.create_git_ref(
                        ref=f"refs/heads/{head_branch}",
                        sha=base_sha,
                    )
                    logger.info(f"Created branch {head_branch}")
                except GithubException as e:
                    if e.status != 422:  # ブランチが既に存在する場合以外はエラー
                        raise

                # ファイル変更をコミット
                commit_message = f"Auto-fix: {title}"
                await self._commit_files(repo, head_branch, files_to_change, commit_message)

            # プルリクエスト作成
            pr = repo.create_pull(
                title=title,
                body=body,
                head=head_branch,
                base=base_branch,
            )

            logger.info(
                "Pull request created",
                repo=repo_name,
                pr_number=pr.number,
                pr_url=pr.html_url,
            )

            return {
                "pr_number": pr.number,
                "pr_url": pr.html_url,
                "title": pr.title,
                "body": pr.body,
                "head_branch": head_branch,
                "base_branch": base_branch,
                "state": pr.state,
                "created_at": pr.created_at.isoformat(),
            }

        except Exception as e:
            logger.error("Failed to create pull request", error=str(e))
            raise

    async def get_file_content(
        self, repo_name: str, file_path: str, branch: str = "main"
    ) -> Optional[str]:
        """
        ファイル内容取得

        Args:
            repo_name: リポジトリ名
            file_path: ファイルパス
            branch: ブランチ名

        Returns:
            Optional[str]: ファイル内容
        """
        try:
            if not self.github:
                raise ValueError("GitHub access token not configured")

            repo = self.github.get_repo(repo_name)
            file = repo.get_contents(file_path, ref=branch)

            if file.encoding == "base64":
                content = base64.b64decode(file.content).decode("utf-8")
            else:
                content = file.content

            logger.debug(
                "File content retrieved",
                repo=repo_name,
                file_path=file_path,
                content_length=len(content),
            )

            return content

        except Exception as e:
            logger.error(
                "Failed to get file content",
                repo=repo_name,
                file_path=file_path,
                error=str(e),
            )
            return None

    async def create_issue(
        self,
        repo_name: str,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Issue作成

        Args:
            repo_name: リポジトリ名
            title: Issue タイトル
            body: Issue 説明
            labels: ラベル
            assignees: アサイニー

        Returns:
            Dict[str, Any]: Issue情報
        """
        try:
            if not self.github:
                raise ValueError("GitHub access token not configured")

            repo = self.github.get_repo(repo_name)

            issue = repo.create_issue(
                title=title,
                body=body,
                labels=labels or [],
                assignees=assignees or [],
            )

            logger.info(
                "Issue created",
                repo=repo_name,
                issue_number=issue.number,
                issue_url=issue.html_url,
            )

            return {
                "issue_number": issue.number,
                "issue_url": issue.html_url,
                "title": issue.title,
                "body": issue.body,
                "state": issue.state,
                "created_at": issue.created_at.isoformat(),
            }

        except Exception as e:
            logger.error("Failed to create issue", error=str(e))
            raise

    async def get_repository_info(self, repo_name: str) -> Dict[str, Any]:
        """
        リポジトリ情報取得

        Args:
            repo_name: リポジトリ名

        Returns:
            Dict[str, Any]: リポジトリ情報
        """
        try:
            if not self.github:
                raise ValueError("GitHub access token not configured")

            repo = self.github.get_repo(repo_name)

            return {
                "name": repo.name,
                "full_name": repo.full_name,
                "description": repo.description,
                "language": repo.language,
                "default_branch": repo.default_branch,
                "clone_url": repo.clone_url,
                "html_url": repo.html_url,
                "created_at": repo.created_at.isoformat(),
                "updated_at": repo.updated_at.isoformat(),
            }

        except Exception as e:
            logger.error("Failed to get repository info", error=str(e))
            raise

    async def list_branches(self, repo_name: str) -> List[str]:
        """
        ブランチ一覧取得

        Args:
            repo_name: リポジトリ名

        Returns:
            List[str]: ブランチ名リスト
        """
        try:
            if not self.github:
                raise ValueError("GitHub access token not configured")

            repo = self.github.get_repo(repo_name)
            branches = [branch.name for branch in repo.get_branches()]

            logger.debug(
                "Branches retrieved",
                repo=repo_name,
                branch_count=len(branches),
            )

            return branches

        except Exception as e:
            logger.error("Failed to list branches", error=str(e))
            return []

    async def _commit_files(
        self,
        repo: Any,
        branch: str,
        files_to_change: List[Dict[str, Any]],
        commit_message: str,
    ) -> None:
        """
        ファイル変更をコミット（内部メソッド）

        Args:
            repo: GitHub リポジトリオブジェクト
            branch: ブランチ名
            files_to_change: 変更するファイル情報
            commit_message: コミットメッセージ
        """
        try:
            for file_info in files_to_change:
                file_path = file_info["path"]
                new_content = file_info["content"]

                try:
                    # 既存ファイルを取得
                    file = repo.get_contents(file_path, ref=branch)

                    # ファイルを更新
                    repo.update_file(
                        path=file_path,
                        message=commit_message,
                        content=new_content,
                        sha=file.sha,
                        branch=branch,
                    )

                    logger.info(f"Updated file {file_path}")

                except GithubException as e:
                    if e.status == 404:
                        # ファイルが存在しない場合は新規作成
                        repo.create_file(
                            path=file_path,
                            message=commit_message,
                            content=new_content,
                            branch=branch,
                        )

                        logger.info(f"Created file {file_path}")
                    else:
                        raise

        except Exception as e:
            logger.error("Failed to commit files", error=str(e))
            raise

    async def add_pr_comment(
        self, repo_name: str, pr_number: int, comment: str
    ) -> Dict[str, Any]:
        """
        PRにコメント追加

        Args:
            repo_name: リポジトリ名
            pr_number: PR番号
            comment: コメント内容

        Returns:
            Dict[str, Any]: コメント情報
        """
        try:
            if not self.github:
                raise ValueError("GitHub access token not configured")

            repo = self.github.get_repo(repo_name)
            pr = repo.get_pull(pr_number)

            comment_obj = pr.create_issue_comment(comment)

            logger.info(
                "PR comment added",
                repo=repo_name,
                pr_number=pr_number,
                comment_id=comment_obj.id,
            )

            return {
                "comment_id": comment_obj.id,
                "comment_url": comment_obj.html_url,
                "body": comment_obj.body,
                "created_at": comment_obj.created_at.isoformat(),
            }

        except Exception as e:
            logger.error("Failed to add PR comment", error=str(e))
            raise

    def is_configured(self) -> bool:
        """
        GitHub サービスが設定されているかチェック

        Returns:
            bool: 設定済みの場合True
        """
        return self.github is not None
