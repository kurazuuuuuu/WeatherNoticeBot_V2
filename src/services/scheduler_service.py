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

from ..models.user import User
from ..services.user_service import UserService
from ..services.notification_service import NotificationService

logger = logging.getLogger(__name__)


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
            self.scheduler.start()
            self._is_running = True
            logger.info("スケジューラーサービスを開始しました")
            
            # 既存のユーザーの通知スケジュールを復元
            await self._restore_user_schedules()
    
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
            
            logger.info(f"ユーザー {user_id} の定時通知を {hour}:00 にスケジュールしました")
            return True
            
        except Exception as e:
            logger.error(f"ユーザー {user_id} の通知スケジュール設定に失敗: {e}")
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
            await self.notification_service.send_scheduled_weather_update(user_id)
            logger.info(f"ユーザー {user_id} への定時通知を送信完了")
            
        except Exception as e:
            logger.error(f"ユーザー {user_id} への定時通知送信に失敗: {e}")
            # エラーが発生してもスケジュールは継続
    
    async def _restore_user_schedules(self) -> None:
        """
        データベースから既存のユーザースケジュールを復元
        """
        try:
            # 通知が有効になっているユーザーを取得
            users = await self.user_service.get_users_with_notifications_enabled()
            
            restored_count = 0
            for user in users:
                if user.notification_hour is not None:
                    success = await self.schedule_user_notification(
                        user.discord_id, 
                        user.notification_hour
                    )
                    if success:
                        restored_count += 1
            
            logger.info(f"{restored_count} 人のユーザーの通知スケジュールを復元しました")
            
        except Exception as e:
            logger.error(f"ユーザースケジュールの復元に失敗: {e}")
    
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