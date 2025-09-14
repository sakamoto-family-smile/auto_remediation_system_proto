"""
Slack統合サービス
"""

import json
from typing import Any, Dict, List, Optional

import structlog
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class SlackService:
    """Slack API統合サービス"""

    def __init__(self, bot_token: Optional[str] = None):
        """
        Slack サービス初期化

        Args:
            bot_token: Slack Bot Token
        """
        self.bot_token = bot_token
        if self.bot_token is None:
            self.bot_token = getattr(settings, 'SLACK_BOT_TOKEN', None)
        
        # 空文字列もNoneとして扱う
        if self.bot_token and self.bot_token.strip():
            self.client = WebClient(token=self.bot_token)
            logger.info("Slack service initialized")
        else:
            self.client = None
            logger.warning("Slack bot token not provided")

    async def send_error_notification(
        self,
        channel: str,
        incident_data: Dict[str, Any],
        severity: str = "medium"
    ) -> Dict[str, Any]:
        """
        エラー通知送信

        Args:
            channel: 送信先チャンネル
            incident_data: インシデントデータ
            severity: 重要度

        Returns:
            Dict[str, Any]: 送信結果
        """
        try:
            if not self.client:
                raise ValueError("Slack client not initialized")

            # 重要度に応じた色とアイコンを設定
            color, icon = self._get_severity_style(severity)

            # ブロック形式のメッセージを構築
            blocks = self._build_error_notification_blocks(incident_data, severity, icon)

            # メッセージ送信
            response = self.client.chat_postMessage(
                channel=channel,
                blocks=blocks,
                text=f"🚨 {severity.upper()}: {incident_data.get('error_type', 'Error')}",
            )

            logger.info(
                "Error notification sent to Slack",
                channel=channel,
                message_ts=response["ts"],
                incident_id=incident_data.get("id"),
            )

            return {
                "success": True,
                "channel": channel,
                "timestamp": response["ts"],
                "permalink": response.get("permalink"),
            }

        except SlackApiError as e:
            logger.error("Slack API error", error=str(e), response=e.response)
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error("Failed to send Slack notification", error=str(e))
            return {"success": False, "error": str(e)}

    async def send_remediation_notification(
        self,
        channel: str,
        incident_data: Dict[str, Any],
        remediation_data: Dict[str, Any],
        status: str = "completed"
    ) -> Dict[str, Any]:
        """
        改修完了通知送信

        Args:
            channel: 送信先チャンネル
            incident_data: インシデントデータ
            remediation_data: 改修データ
            status: 改修ステータス

        Returns:
            Dict[str, Any]: 送信結果
        """
        try:
            if not self.client:
                raise ValueError("Slack client not initialized")

            # ステータスに応じたアイコンを設定
            icon = "✅" if status == "completed" else "🔧"

            # ブロック形式のメッセージを構築
            blocks = self._build_remediation_notification_blocks(
                incident_data, remediation_data, status, icon
            )

            # メッセージ送信
            response = self.client.chat_postMessage(
                channel=channel,
                blocks=blocks,
                text=f"{icon} 改修{status}: {incident_data.get('error_type', 'Error')}",
            )

            logger.info(
                "Remediation notification sent to Slack",
                channel=channel,
                message_ts=response["ts"],
                incident_id=incident_data.get("id"),
                status=status,
            )

            return {
                "success": True,
                "channel": channel,
                "timestamp": response["ts"],
                "permalink": response.get("permalink"),
            }

        except SlackApiError as e:
            logger.error("Slack API error", error=str(e), response=e.response)
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error("Failed to send remediation notification", error=str(e))
            return {"success": False, "error": str(e)}

    async def send_approval_request(
        self,
        channel: str,
        incident_data: Dict[str, Any],
        remediation_data: Dict[str, Any],
        approvers: List[str]
    ) -> Dict[str, Any]:
        """
        承認リクエスト送信

        Args:
            channel: 送信先チャンネル
            incident_data: インシデントデータ
            remediation_data: 改修データ
            approvers: 承認者リスト

        Returns:
            Dict[str, Any]: 送信結果
        """
        try:
            if not self.client:
                raise ValueError("Slack client not initialized")

            # 承認リクエストブロックを構築
            blocks = self._build_approval_request_blocks(
                incident_data, remediation_data, approvers
            )

            # メッセージ送信
            response = self.client.chat_postMessage(
                channel=channel,
                blocks=blocks,
                text=f"🔍 承認リクエスト: {incident_data.get('error_type', 'Error')}の自動改修",
            )

            logger.info(
                "Approval request sent to Slack",
                channel=channel,
                message_ts=response["ts"],
                incident_id=incident_data.get("id"),
                approvers=approvers,
            )

            return {
                "success": True,
                "channel": channel,
                "timestamp": response["ts"],
                "permalink": response.get("permalink"),
            }

        except SlackApiError as e:
            logger.error("Slack API error", error=str(e), response=e.response)
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error("Failed to send approval request", error=str(e))
            return {"success": False, "error": str(e)}

    async def update_message(
        self,
        channel: str,
        timestamp: str,
        blocks: List[Dict[str, Any]],
        text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        メッセージ更新

        Args:
            channel: チャンネル
            timestamp: メッセージタイムスタンプ
            blocks: 新しいブロック
            text: 新しいテキスト

        Returns:
            Dict[str, Any]: 更新結果
        """
        try:
            if not self.client:
                raise ValueError("Slack client not initialized")

            response = self.client.chat_update(
                channel=channel,
                ts=timestamp,
                blocks=blocks,
                text=text,
            )

            logger.info(
                "Slack message updated",
                channel=channel,
                timestamp=timestamp,
            )

            return {"success": True, "timestamp": response["ts"]}

        except SlackApiError as e:
            logger.error("Slack API error", error=str(e), response=e.response)
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error("Failed to update Slack message", error=str(e))
            return {"success": False, "error": str(e)}

    async def add_reaction(
        self, channel: str, timestamp: str, reaction: str
    ) -> Dict[str, Any]:
        """
        リアクション追加

        Args:
            channel: チャンネル
            timestamp: メッセージタイムスタンプ
            reaction: リアクション名

        Returns:
            Dict[str, Any]: 追加結果
        """
        try:
            if not self.client:
                raise ValueError("Slack client not initialized")

            response = self.client.reactions_add(
                channel=channel,
                timestamp=timestamp,
                name=reaction,
            )

            return {"success": True}

        except SlackApiError as e:
            logger.error("Slack API error", error=str(e), response=e.response)
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error("Failed to add reaction", error=str(e))
            return {"success": False, "error": str(e)}

    def _get_severity_style(self, severity: str) -> tuple[str, str]:
        """重要度に応じたスタイル取得"""
        styles = {
            "critical": ("danger", "🔥"),
            "high": ("warning", "⚠️"),
            "medium": ("good", "🟡"),
            "low": ("#36a64f", "🟢"),
        }
        return styles.get(severity, ("good", "🔵"))

    def _build_error_notification_blocks(
        self, incident_data: Dict[str, Any], severity: str, icon: str
    ) -> List[Dict[str, Any]]:
        """エラー通知ブロック構築"""
        color, _ = self._get_severity_style(severity)

        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{icon} エラーインシデント発生"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*エラータイプ:*\n{incident_data.get('error_type', 'Unknown')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*重要度:*\n{severity.upper()}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*サービス:*\n{incident_data.get('service_name', 'Unknown')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*環境:*\n{incident_data.get('environment', 'Unknown')}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*エラーメッセージ:*\n```{incident_data.get('error_message', 'No message')}```"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "詳細を確認"
                        },
                        "style": "primary",
                        "url": f"{settings.FRONTEND_URL}/errors/{incident_data.get('id')}",
                        "action_id": "view_incident"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "自動改修実行"
                        },
                        "style": "danger" if severity in ["critical", "high"] else "default",
                        "action_id": f"remediate_{incident_data.get('id')}",
                        "value": json.dumps({"incident_id": incident_data.get("id")})
                    }
                ]
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"インシデントID: {incident_data.get('id', 'Unknown')} | 発生時刻: {incident_data.get('created_at', 'Unknown')}"
                    }
                ]
            }
        ]

    def _build_remediation_notification_blocks(
        self,
        incident_data: Dict[str, Any],
        remediation_data: Dict[str, Any],
        status: str,
        icon: str
    ) -> List[Dict[str, Any]]:
        """改修通知ブロック構築"""
        status_text = {
            "completed": "完了",
            "failed": "失敗",
            "in_progress": "実行中"
        }.get(status, status)

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{icon} 自動改修{status_text}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*エラータイプ:*\n{incident_data.get('error_type', 'Unknown')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*改修ステータス:*\n{status_text}"
                    }
                ]
            }
        ]

        # 改修完了の場合は詳細情報を追加
        if status == "completed":
            blocks.extend([
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*改修内容:*\n{remediation_data.get('explanation', 'No explanation available')}"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "PRを確認"
                            },
                            "style": "primary",
                            "url": remediation_data.get('pr_url', '#'),
                            "action_id": "view_pr"
                        }
                    ]
                }
            ])

        return blocks

    def _build_approval_request_blocks(
        self,
        incident_data: Dict[str, Any],
        remediation_data: Dict[str, Any],
        approvers: List[str]
    ) -> List[Dict[str, Any]]:
        """承認リクエストブロック構築"""
        approver_mentions = " ".join([f"<@{approver}>" for approver in approvers])

        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🔍 改修承認リクエスト"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"以下のエラーに対する自動改修の承認をお願いします。\n承認者: {approver_mentions}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*エラータイプ:*\n{incident_data.get('error_type', 'Unknown')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*サービス:*\n{incident_data.get('service_name', 'Unknown')}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*提案された修正:*\n```{remediation_data.get('explanation', 'No explanation available')}```"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "承認"
                        },
                        "style": "primary",
                        "action_id": f"approve_{incident_data.get('id')}",
                        "value": json.dumps({
                            "incident_id": incident_data.get("id"),
                            "action": "approve"
                        })
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "却下"
                        },
                        "style": "danger",
                        "action_id": f"reject_{incident_data.get('id')}",
                        "value": json.dumps({
                            "incident_id": incident_data.get("id"),
                            "action": "reject"
                        })
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "詳細確認"
                        },
                        "url": f"{settings.FRONTEND_URL}/errors/{incident_data.get('id')}",
                        "action_id": "view_details"
                    }
                ]
            }
        ]

    def is_configured(self) -> bool:
        """
        Slack サービスが設定されているかチェック

        Returns:
            bool: 設定済みの場合True
        """
        return self.client is not None
