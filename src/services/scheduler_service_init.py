"""
スケジューラーサービスの初期化と管理を行うモジュール
"""

import logging
from typing import Optional

import discord

from .scheduler_service import SchedulerService
from .user_service import UserService
from .notification_service import NotificationService

logger = logging.getLogger(__name__)

# グローバルなスケジューラーサービスのインスタンス
_scheduler_service: Optional[SchedulerService] = None


async def init_scheduler(bot_client: Optional[discord.Client] = None) -> SchedulerService:
    """
    スケジューラーサービスを初期化する
    
    Args:
        bot_client: Discordボットクライアント（オプション）
        
    Returns:
        初期化されたSchedulerServiceインスタンス
    """
    global _scheduler_service
    
    if _scheduler_service is None:
        logger.info("スケジューラーサービスを初期化しています...")
        
        # 依存サービスの初期化
        user_service = UserService()
        notification_service = NotificationService(bot_client=bot_client)
        
        # スケジューラーサービスの作成
        _scheduler_service = SchedulerService(
            user_service=user_service,
            notification_service=notification_service
        )
        
        logger.info("スケジューラーサービスが初期化されました")
    elif bot_client is not None:
        # ボットクライアントの更新
        _scheduler_service.notification_service.set_bot_client(bot_client)
        logger.info("スケジューラーサービスのボットクライアントを更新しました")
    
    return _scheduler_service


async def start_scheduler() -> bool:
    """
    スケジューラーサービスを開始する
    
    Returns:
        開始成功時はTrue、失敗時はFalse
    """
    global _scheduler_service
    
    if _scheduler_service is None:
        logger.error("スケジューラーサービスが初期化されていません")
        return False
    
    try:
        await _scheduler_service.start()
        logger.info("スケジューラーサービスを開始しました")
        return True
    except Exception as e:
        logger.error(f"スケジューラーサービスの開始に失敗しました: {e}")
        return False


async def stop_scheduler() -> bool:
    """
    スケジューラーサービスを停止する
    
    Returns:
        停止成功時はTrue、失敗時はFalse
    """
    global _scheduler_service
    
    if _scheduler_service is None:
        logger.warning("スケジューラーサービスが初期化されていません")
        return False
    
    try:
        await _scheduler_service.stop()
        logger.info("スケジューラーサービスを停止しました")
        return True
    except Exception as e:
        logger.error(f"スケジューラーサービスの停止に失敗しました: {e}")
        return False


def get_scheduler_service() -> Optional[SchedulerService]:
    """
    現在のスケジューラーサービスインスタンスを取得する
    
    Returns:
        SchedulerServiceインスタンス、初期化されていない場合はNone
    """
    return _scheduler_service