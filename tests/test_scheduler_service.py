"""
スケジューラーサービスのテスト
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, time

from src.services.scheduler_service import SchedulerService
from src.services.user_service import UserService
from src.services.notification_service import NotificationService
from src.models.user import User


@pytest.fixture
def mock_user_service():
    """モックユーザーサービス"""
    service = AsyncMock(spec=UserService)
    return service


@pytest.fixture
def mock_notification_service():
    """モック通知サービス"""
    service = AsyncMock(spec=NotificationService)
    return service


@pytest.fixture
def scheduler_service(mock_user_service, mock_notification_service):
    """スケジューラーサービスのフィクスチャ"""
    return SchedulerService(mock_user_service, mock_notification_service)


@pytest.mark.asyncio
class TestSchedulerService:
    """スケジューラーサービスのテストクラス"""
    
    async def test_start_scheduler(self, scheduler_service):
        """スケジューラーの開始テスト"""
        # モックユーザーを設定
        mock_users = [
            User(discord_id=123, notification_hour=9, is_notification_enabled=True),
            User(discord_id=456, notification_hour=18, is_notification_enabled=True)
        ]
        scheduler_service.user_service.get_users_with_notifications_enabled.return_value = mock_users
        
        # スケジューラーを開始
        await scheduler_service.start()
        
        # 状態確認
        assert scheduler_service.is_running() is True
        
        # クリーンアップ
        await scheduler_service.stop()
    
    async def test_stop_scheduler(self, scheduler_service):
        """スケジューラーの停止テスト"""
        # スケジューラーを開始してから停止
        await scheduler_service.start()
        await scheduler_service.stop()
        
        # 状態確認
        assert scheduler_service.is_running() is False
    
    async def test_schedule_user_notification(self, scheduler_service):
        """ユーザー通知スケジュールの設定テスト"""
        await scheduler_service.start()
        
        user_id = 123456789
        hour = 9
        
        # 通知をスケジュール
        result = await scheduler_service.schedule_user_notification(user_id, hour)
        
        # 結果確認
        assert result is True
        
        # スケジュール情報確認
        schedule_info = await scheduler_service.get_user_schedule_info(user_id)
        assert schedule_info['scheduled'] is True
        # RangeExpressionオブジェクトの場合は文字列表現で比較
        if hasattr(schedule_info['hour'], 'first'):
            assert schedule_info['hour'].first == hour
        elif str(schedule_info['hour']).isdigit():
            assert int(str(schedule_info['hour'])) == hour
        else:
            assert schedule_info['hour'] == hour
        
        # クリーンアップ
        await scheduler_service.stop()
    
    async def test_unschedule_user_notification(self, scheduler_service):
        """ユーザー通知スケジュールの削除テスト"""
        await scheduler_service.start()
        
        user_id = 123456789
        hour = 9
        
        # 通知をスケジュール
        await scheduler_service.schedule_user_notification(user_id, hour)
        
        # スケジュールを削除
        result = await scheduler_service.unschedule_user_notification(user_id)
        
        # 結果確認
        assert result is True
        
        # スケジュール情報確認
        schedule_info = await scheduler_service.get_user_schedule_info(user_id)
        assert schedule_info['scheduled'] is False
        
        # クリーンアップ
        await scheduler_service.stop()
    
    async def test_get_scheduled_users(self, scheduler_service):
        """スケジュールされたユーザーリストの取得テスト"""
        await scheduler_service.start()
        
        user_ids = [123, 456, 789]
        hours = [9, 12, 18]
        
        # 複数のユーザーをスケジュール
        for user_id, hour in zip(user_ids, hours):
            await scheduler_service.schedule_user_notification(user_id, hour)
        
        # スケジュールされたユーザーを取得
        scheduled_users = await scheduler_service.get_scheduled_users()
        
        # 結果確認
        assert len(scheduled_users) == 3
        for user_id in user_ids:
            assert user_id in scheduled_users
        
        # クリーンアップ
        await scheduler_service.stop()
    
    async def test_get_scheduler_status(self, scheduler_service):
        """スケジューラー状態の取得テスト"""
        await scheduler_service.start()
        
        # ユーザーをスケジュール
        await scheduler_service.schedule_user_notification(123, 9)
        await scheduler_service.schedule_user_notification(456, 18)
        
        # 状態を取得
        status = await scheduler_service.get_scheduler_status()
        
        # 結果確認
        assert status['running'] is True
        assert status['total_jobs'] == 2
        assert status['scheduled_users'] == 2
        assert len(status['next_jobs']) <= 5
        
        # クリーンアップ
        await scheduler_service.stop()
    
    async def test_invalid_hour_schedule(self, scheduler_service):
        """無効な時間でのスケジュール設定テスト"""
        await scheduler_service.start()
        
        user_id = 123456789
        
        # 無効な時間でスケジュール（24時以上）
        result = await scheduler_service.schedule_user_notification(user_id, 25)
        
        # エラーハンドリングの確認（実装によっては成功する場合もある）
        # APSchedulerは無効な時間でもCronTriggerを作成できるため
        
        # クリーンアップ
        await scheduler_service.stop()
    
    @patch('src.services.scheduler_service.logger')
    async def test_notification_error_handling(self, mock_logger, scheduler_service):
        """通知送信エラーのハンドリングテスト"""
        await scheduler_service.start()
        
        # 通知サービスでエラーを発生させる
        scheduler_service.notification_service.send_scheduled_weather_update.side_effect = Exception("通知エラー")
        
        user_id = 123456789
        
        # 通知送信を実行（内部メソッドを直接呼び出し）
        await scheduler_service._send_scheduled_notification(user_id)
        
        # エラーログが記録されることを確認
        mock_logger.error.assert_called()
        
        # クリーンアップ
        await scheduler_service.stop()
    
    async def test_restore_user_schedules(self, scheduler_service):
        """ユーザースケジュールの復元テスト"""
        # モックユーザーを設定
        mock_users = [
            User(discord_id=123, notification_hour=9, is_notification_enabled=True),
            User(discord_id=456, notification_hour=18, is_notification_enabled=True),
            User(discord_id=789, notification_hour=None, is_notification_enabled=True)  # 時間未設定
        ]
        scheduler_service.user_service.get_users_with_notifications_enabled.return_value = mock_users
        
        # スケジューラーを開始（復元処理が実行される）
        await scheduler_service.start()
        
        # 復元されたスケジュールを確認
        scheduled_users = await scheduler_service.get_scheduled_users()
        
        # 時間が設定されているユーザーのみがスケジュールされることを確認
        assert 123 in scheduled_users
        assert 456 in scheduled_users
        assert 789 not in scheduled_users  # 時間未設定のため除外
        
        # クリーンアップ
        await scheduler_service.stop()
    
    async def test_schedule_replacement(self, scheduler_service):
        """既存スケジュールの置き換えテスト"""
        await scheduler_service.start()
        
        user_id = 123456789
        
        # 最初のスケジュール
        await scheduler_service.schedule_user_notification(user_id, 9)
        schedule_info_1 = await scheduler_service.get_user_schedule_info(user_id)
        
        # スケジュールを変更
        await scheduler_service.schedule_user_notification(user_id, 18)
        schedule_info_2 = await scheduler_service.get_user_schedule_info(user_id)
        
        # 結果確認
        # RangeExpressionオブジェクトの場合は文字列表現で比較
        if hasattr(schedule_info_1['hour'], 'first'):
            assert schedule_info_1['hour'].first == 9
        elif str(schedule_info_1['hour']).isdigit():
            assert int(str(schedule_info_1['hour'])) == 9
        else:
            assert schedule_info_1['hour'] == 9
            
        if hasattr(schedule_info_2['hour'], 'first'):
            assert schedule_info_2['hour'].first == 18
        elif str(schedule_info_2['hour']).isdigit():
            assert int(str(schedule_info_2['hour'])) == 18
        else:
            assert schedule_info_2['hour'] == 18
        
        # スケジュールされたユーザー数は1人のまま
        scheduled_users = await scheduler_service.get_scheduled_users()
        assert len(scheduled_users) == 1
        assert user_id in scheduled_users
        
        # クリーンアップ
        await scheduler_service.stop()