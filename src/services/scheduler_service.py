"""
スケジューラーサービス
APSchedulerを使用してユーザーごとの定時通知を管理する
"""

import asyncio
import logging
from datetime import datetime, time
from typing import Dict, List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

import discord

from ..models.user import User
from ..services.user_service import UserService
from ..services.notification_service import NotificationService

logger = logging.getLogger(__name__)

# グローバルなスケジューラーサービスのインスタンス
_scheduler_service: Optional['SchedulerService'] = None


class SchedulerService:
    """定時通知のスケジュール管理を行うサービス"""
    
    def __init__(self, user_service: UserService, notification_service: NotificationService):
        """
        スケジューラーサービスを初期化
        
        Args:
            user_service: ユーザー管理サービス
            notification_service: 通知サービス
        """
        self.user_service = user_service
        self.notification_service = notification_service
        
        # APSchedulerの設定
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': AsyncIOExecutor()
        }
        job_defaults = {
            'coalesce': False,
            'max_instances': 3
        }
        
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='Asia/Tokyo'
        )
        
        self._is_running = False
        
    async def start(self) -> None:
        """スケジューラーを開始"""
        if not self._is_running:
            try:
                self.scheduler.start()
                self._is_running = True
                logger.info("スケジューラーサービスを開始しました")
                
                # 既存のユーザーの通知スケジュールを復元
                logger.info("ユーザースケジュールの復元処理を開始します")
                await self._restore_user_schedules()
                logger.info("ユーザースケジュールの復元処理が完了しました")
                
                # スケジューラーの状態を確認
                status = await self.get_scheduler_status()
                logger.info(f"スケジューラー状態: {status}")
                
            except Exception as e:
                logger.error(f"スケジューラーの開始に失敗しました: {e}")
                self._is_running = False
                raise
    
    async def stop(self) -> None:
        """スケジューラーを停止"""
        if self._is_running:
            self.scheduler.shutdown()
            self._is_running = False
            logger.info("スケジューラーサービスを停止しました")
    
    async def schedule_user_notification(self, user_id: int, hour: int) -> bool:
        """
        ユーザーの定時通知をスケジュール
        
        Args:
            user_id: DiscordユーザーID
            hour: 通知時間（0-23時）
            
        Returns:
            bool: スケジュール設定の成功/失敗
        """
        try:
            # 時間の妥当性チェック
            if not 0 <= hour <= 23:
                logger.error(f"無効な時間が指定されました: {hour}")
                return False
            
            # スケジューラーが実行中かチェック
            if not self.is_running():
                logger.error("スケジューラーが実行されていません")
                return False
            
            # 既存のジョブがあれば削除
            await self.unschedule_user_notification(user_id)
            
            # 新しいジョブを追加
            job_id = f"weather_notification_{user_id}"
            
            # 毎日指定時間に実行するCronトリガーを作成
            trigger = CronTrigger(
                hour=hour,
                minute=0,
                second=0,
                timezone='Asia/Tokyo'
            )
            
            self.scheduler.add_job(
                func=self._send_scheduled_notification,
                trigger=trigger,
                args=[user_id],
                id=job_id,
                name=f"Weather notification for user {user_id}",
                replace_existing=True
            )
            
            # ジョブが正常に追加されたか確認
            job = self.scheduler.get_job(job_id)
            if job:
                next_run = job.next_run_time
                logger.info(f"ユーザー {user_id} の定時通知を {hour}:00 にスケジュールしました (次回実行: {next_run})")
                return True
            else:
                logger.error(f"ジョブの追加に失敗しました: {job_id}")
                return False
            
        except Exception as e:
            logger.error(f"ユーザー {user_id} の通知スケジュール設定に失敗: {e}", exc_info=True)
            return False
    
    async def unschedule_user_notification(self, user_id: int) -> bool:
        """
        ユーザーの定時通知スケジュールを削除
        
        Args:
            user_id: DiscordユーザーID
            
        Returns:
            bool: スケジュール削除の成功/失敗
        """
        try:
            job_id = f"weather_notification_{user_id}"
            
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"ユーザー {user_id} の定時通知スケジュールを削除しました")
                return True
            else:
                logger.info(f"ユーザー {user_id} の定時通知スケジュールは存在しません")
                return True
                
        except Exception as e:
            logger.error(f"ユーザー {user_id} の通知スケジュール削除に失敗: {e}")
            return False
    
    async def get_scheduled_users(self) -> List[int]:
        """
        スケジュールされているユーザーのリストを取得
        
        Returns:
            List[int]: スケジュールされているユーザーIDのリスト
        """
        scheduled_users = []
        
        for job in self.scheduler.get_jobs():
            if job.id.startswith("weather_notification_"):
                user_id = int(job.id.replace("weather_notification_", ""))
                scheduled_users.append(user_id)
        
        return scheduled_users
    
    async def get_user_schedule_info(self, user_id: int) -> Optional[Dict]:
        """
        ユーザーのスケジュール情報を取得
        
        Args:
            user_id: DiscordユーザーID
            
        Returns:
            Optional[Dict]: スケジュール情報（時間、次回実行時刻など）
        """
        job_id = f"weather_notification_{user_id}"
        job = self.scheduler.get_job(job_id)
        
        if job:
            next_run = job.next_run_time
            trigger = job.trigger
            
            # Cronトリガーから時間を取得
            hour = None
            try:
                if hasattr(trigger, 'hour') and trigger.hour is not None:
                    # CronTriggerのhour属性から直接取得
                    hour_expr = trigger.hour
                    # RangeExpressionオブジェクトから値を抽出
                    if hasattr(hour_expr, 'first'):
                        hour = hour_expr.first
                    elif hasattr(hour_expr, 'value'):
                        hour = hour_expr.value
                    elif str(hour_expr).isdigit():
                        hour = int(str(hour_expr))
                    else:
                        # 文字列表現から数値を抽出
                        import re
                        match = re.search(r'\d+', str(hour_expr))
                        if match:
                            hour = int(match.group())
                elif hasattr(trigger, 'fields') and trigger.fields:
                    # fieldsがリストの場合の処理
                    for field in trigger.fields:
                        if hasattr(field, 'name') and field.name == 'hour':
                            if hasattr(field, 'expressions') and field.expressions:
                                hour = list(field.expressions)[0]
                            break
            except Exception as e:
                logger.warning(f"時間情報の取得に失敗: {e}")
            
            return {
                'scheduled': True,
                'hour': hour,
                'next_run': next_run,
                'job_name': job.name
            }
        
        return {
            'scheduled': False,
            'hour': None,
            'next_run': None,
            'job_name': None
        }
    
    async def _send_scheduled_notification(self, user_id: int) -> None:
        """
        スケジュールされた通知を送信（内部メソッド）
        
        Args:
            user_id: DiscordユーザーID
        """
        try:
            logger.info(f"ユーザー {user_id} への定時通知を送信開始")
            
            # 通知サービスが利用可能かチェック
            if not self.notification_service:
                logger.error("通知サービスが初期化されていません")
                return
            
            # 通知を送信
            success = await self.notification_service.send_scheduled_weather_update(user_id)
            
            if success:
                logger.info(f"ユーザー {user_id} への定時通知を送信完了")
            else:
                logger.warning(f"ユーザー {user_id} への定時通知送信が失敗しました")
            
        except Exception as e:
            logger.error(f"ユーザー {user_id} への定時通知送信に失敗: {e}", exc_info=True)
            # エラーが発生してもスケジュールは継続
    
    async def _restore_user_schedules(self) -> None:
        """
        データベースから既存のユーザースケジュールを復元
        """
        try:
            logger.info("ユーザースケジュールの復元を開始します")
            
            # 通知が有効になっているユーザーを取得
            users = await self.user_service.get_users_with_notifications_enabled()
            logger.info(f"通知有効ユーザー数: {len(users)}人")
            
            # ユーザーの詳細をログ出力
            for user in users:
                logger.info(f"通知有効ユーザー: ID={user.discord_id}, 時間={user.notification_hour}, 地域={user.area_name}")
            
            restored_count = 0
            failed_count = 0
            
            for user in users:
                if user.notification_hour is not None:
                    logger.debug(f"ユーザー {user.discord_id} のスケジュール復元を試行: {user.notification_hour}時")
                    success = await self.schedule_user_notification(
                        user.discord_id, 
                        user.notification_hour
                    )
                    if success:
                        restored_count += 1
                    else:
                        failed_count += 1
                        logger.warning(f"ユーザー {user.discord_id} のスケジュール復元に失敗")
                else:
                    logger.warning(f"ユーザー {user.discord_id} は通知が有効ですが、通知時間が設定されていません")
            
            logger.info(f"スケジュール復元完了: 成功 {restored_count}人, 失敗 {failed_count}人")
            
        except Exception as e:
            logger.error(f"ユーザースケジュールの復元に失敗: {e}", exc_info=True)
    
    def is_running(self) -> bool:
        """
        スケジューラーが実行中かどうかを確認
        
        Returns:
            bool: 実行中の場合True
        """
        return self._is_running and self.scheduler.running
    
    async def get_scheduler_status(self) -> Dict:
        """
        スケジューラーの状態情報を取得
        
        Returns:
            Dict: スケジューラーの状態情報
        """
        jobs = self.scheduler.get_jobs()
        
        return {
            'running': self.is_running(),
            'total_jobs': len(jobs),
            'scheduled_users': len([job for job in jobs if job.id.startswith("weather_notification_")]),
            'next_jobs': [
                {
                    'job_id': job.id,
                    'next_run': job.next_run_time,
                    'name': job.name
                }
                for job in sorted(jobs, key=lambda x: x.next_run_time or datetime.max)[:5]
            ]
        }
# グローバル関数

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
    
    logger.info("start_scheduler()関数が呼び出されました")
    
    if _scheduler_service is None:
        logger.error("スケジューラーサービスが初期化されていません")
        return False
    
    logger.info("スケジューラーサービスが存在します")
    
    try:
        logger.info("スケジューラーサービスの開始を試行します")
        logger.info("スケジューラーサービスのstart()メソッドを呼び出します")
        await _scheduler_service.start()
        logger.info("スケジューラーサービスのstart()メソッドが完了しました")
        
        # 開始後の状態を確認
        if _scheduler_service.is_running():
            logger.info("スケジューラーサービスが正常に開始されました")
            return True
        else:
            logger.error("スケジューラーサービスの開始に失敗しました（実行状態ではありません）")
            return False
            
    except Exception as e:
        logger.error(f"スケジューラーサービスの開始に失敗しました: {e}", exc_info=True)
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