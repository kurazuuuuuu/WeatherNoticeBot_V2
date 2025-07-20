"""
通知サービスのテスト
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import discord

from src.services.notification_service import NotificationService
from src.services.user_service import UserService
from src.services.weather_service import WeatherService, WeatherData
from src.services.ai_service import AIMessageService, WeatherContext


@pytest.fixture
def mock_bot_client():
    """モックDiscordボットクライアント"""
    client = AsyncMock(spec=discord.Client)
    return client


@pytest.fixture
def mock_user_service():
    """モックユーザーサービス"""
    service = AsyncMock(spec=UserService)
    return service


@pytest.fixture
def mock_weather_service():
    """モック天気サービス"""
    service = AsyncMock(spec=WeatherService)
    return service


@pytest.fixture
def mock_ai_service():
    """モックAIサービス"""
    service = AsyncMock(spec=AIMessageService)
    service.is_available.return_value = True
    return service


@pytest.fixture
def notification_service(mock_bot_client, mock_user_service, mock_weather_service, mock_ai_service):
    """通知サービスのフィクスチャ"""
    return NotificationService(
        bot_client=mock_bot_client,
        user_service=mock_user_service,
        weather_service=mock_weather_service,
        ai_service=mock_ai_service
    )


@pytest.fixture
def sample_weather_data():
    """サンプル天気データ"""
    return WeatherData(
        area_name="東京都",
        area_code="130010",
        weather_code="100",
        weather_description="晴れ",
        wind="北の風",
        wave="",
        temperature=20.5,
        precipitation_probability=10,
        timestamp=datetime.now(),
        publish_time=datetime.now()
    )


@pytest.fixture
def sample_user_settings():
    """サンプルユーザー設定"""
    return {
        'discord_id': 123456789,
        'area_code': '130010',
        'area_name': '東京都',
        'notification_hour': 9,
        'timezone': 'Asia/Tokyo',
        'is_notification_enabled': True,
        'has_location': True,
        'has_notification_enabled': True,
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }


@pytest.mark.asyncio
class TestNotificationService:
    """通知サービスのテストクラス"""
    
    async def test_send_scheduled_weather_update_success(
        self, 
        notification_service, 
        sample_user_settings, 
        sample_weather_data
    ):
        """定時天気情報送信の成功テスト"""
        user_id = 123456789
        
        # モックの設定
        notification_service.user_service.get_user_settings.return_value = sample_user_settings
        notification_service.weather_service.__aenter__.return_value = notification_service.weather_service
        notification_service.weather_service.__aexit__.return_value = None
        notification_service.weather_service.get_current_weather.return_value = sample_weather_data
        notification_service.ai_service.generate_positive_message.return_value = "今日も素晴らしい一日になりそうですね！ ☀️"
        
        # モックユーザーを設定
        mock_user = AsyncMock(spec=discord.User)
        mock_user.send = AsyncMock()
        notification_service.bot_client.fetch_user.return_value = mock_user
        
        # テスト実行
        result = await notification_service.send_scheduled_weather_update(user_id)
        
        # 結果確認
        assert result is True
        notification_service.user_service.get_user_settings.assert_called_once_with(user_id)
        notification_service.weather_service.get_current_weather.assert_called_once_with('130010')
        notification_service.ai_service.generate_positive_message.assert_called_once()
        notification_service.bot_client.fetch_user.assert_called_once_with(user_id)
        mock_user.send.assert_called_once()
    
    async def test_send_scheduled_weather_update_no_bot_client(self, notification_service):
        """ボットクライアントが設定されていない場合のテスト"""
        notification_service.bot_client = None
        
        result = await notification_service.send_scheduled_weather_update(123456789)
        
        assert result is False
    
    async def test_send_scheduled_weather_update_no_user_settings(self, notification_service):
        """ユーザー設定が見つからない場合のテスト"""
        user_id = 123456789
        
        notification_service.user_service.get_user_settings.return_value = None
        
        result = await notification_service.send_scheduled_weather_update(user_id)
        
        assert result is False
        notification_service.user_service.get_user_settings.assert_called_once_with(user_id)
    
    async def test_send_scheduled_weather_update_no_location(self, notification_service):
        """位置情報が設定されていない場合のテスト"""
        user_id = 123456789
        user_settings = {
            'discord_id': user_id,
            'area_code': None,
            'area_name': None,
            'notification_hour': 9,
            'is_notification_enabled': True
        }
        
        notification_service.user_service.get_user_settings.return_value = user_settings
        
        # モックユーザーを設定
        mock_user = AsyncMock(spec=discord.User)
        mock_user.send = AsyncMock()
        notification_service.bot_client.fetch_user.return_value = mock_user
        
        result = await notification_service.send_scheduled_weather_update(user_id)
        
        assert result is False
        # 位置情報設定メッセージが送信されることを確認
        mock_user.send.assert_called_once()
    
    async def test_send_scheduled_weather_update_weather_error(
        self, 
        notification_service, 
        sample_user_settings
    ):
        """天気情報取得エラーのテスト"""
        user_id = 123456789
        
        notification_service.user_service.get_user_settings.return_value = sample_user_settings
        notification_service.weather_service.__aenter__.return_value = notification_service.weather_service
        notification_service.weather_service.__aexit__.return_value = None
        notification_service.weather_service.get_current_weather.return_value = None
        
        # モックユーザーを設定
        mock_user = AsyncMock(spec=discord.User)
        mock_user.send = AsyncMock()
        notification_service.bot_client.fetch_user.return_value = mock_user
        
        result = await notification_service.send_scheduled_weather_update(user_id)
        
        assert result is False
        # エラーメッセージが送信されることを確認
        mock_user.send.assert_called_once()
    
    async def test_get_weather_data_with_retry_success(self, notification_service, sample_weather_data):
        """天気データ取得リトライの成功テスト"""
        area_code = "130010"
        
        notification_service.weather_service.__aenter__.return_value = notification_service.weather_service
        notification_service.weather_service.__aexit__.return_value = None
        notification_service.weather_service.get_current_weather.return_value = sample_weather_data
        
        result = await notification_service._get_weather_data_with_retry(area_code)
        
        assert result == sample_weather_data
        notification_service.weather_service.get_current_weather.assert_called_once_with(area_code)
    
    async def test_get_weather_data_with_retry_failure(self, notification_service):
        """天気データ取得リトライの失敗テスト"""
        area_code = "130010"
        
        notification_service.weather_service.__aenter__.return_value = notification_service.weather_service
        notification_service.weather_service.__aexit__.return_value = None
        notification_service.weather_service.get_current_weather.side_effect = Exception("API Error")
        
        # リトライ回数を1に設定してテストを高速化
        notification_service.MAX_RETRIES = 1
        
        result = await notification_service._get_weather_data_with_retry(area_code)
        
        assert result is None
        assert notification_service.weather_service.get_current_weather.call_count == 1
    
    async def test_generate_ai_message_with_retry_success(self, notification_service):
        """AIメッセージ生成リトライの成功テスト"""
        weather_context = WeatherContext(
            area_name="東京都",
            weather_description="晴れ",
            temperature=20.5,
            precipitation_probability=10,
            wind="北の風",
            timestamp=datetime.now()
        )
        
        expected_message = "今日も素晴らしい一日になりそうですね！ ☀️"
        notification_service.ai_service.generate_positive_message.return_value = expected_message
        
        result = await notification_service._generate_ai_message_with_retry(weather_context)
        
        assert result == expected_message
        notification_service.ai_service.generate_positive_message.assert_called_once()
    
    async def test_generate_ai_message_with_retry_fallback(self, notification_service):
        """AIメッセージ生成リトライのフォールバックテスト"""
        weather_context = WeatherContext(
            area_name="東京都",
            weather_description="晴れ",
            temperature=20.5,
            precipitation_probability=10,
            wind="北の風",
            timestamp=datetime.now()
        )
        
        notification_service.ai_service.generate_positive_message.side_effect = Exception("AI Error")
        notification_service.ai_service._get_fallback_message.return_value = "フォールバックメッセージ"
        
        # リトライ回数を1に設定してテストを高速化
        notification_service.MAX_RETRIES = 1
        
        result = await notification_service._generate_ai_message_with_retry(weather_context)
        
        assert result == "フォールバックメッセージ"
        notification_service.ai_service._get_fallback_message.assert_called_once()
    
    async def test_send_weather_dm_with_retry_success(
        self, 
        notification_service, 
        sample_weather_data
    ):
        """DM送信リトライの成功テスト"""
        user_id = 123456789
        ai_message = "今日も素晴らしい一日になりそうですね！ ☀️"
        
        # モックユーザーを設定
        mock_user = AsyncMock(spec=discord.User)
        mock_user.send = AsyncMock()
        notification_service.bot_client.fetch_user.return_value = mock_user
        
        result = await notification_service._send_weather_dm_with_retry(
            user_id, sample_weather_data, ai_message
        )
        
        assert result is True
        notification_service.bot_client.fetch_user.assert_called_once_with(user_id)
        mock_user.send.assert_called_once()
    
    async def test_send_weather_dm_with_retry_forbidden(
        self, 
        notification_service, 
        sample_weather_data
    ):
        """DM送信権限なしのテスト"""
        user_id = 123456789
        ai_message = "今日も素晴らしい一日になりそうですね！ ☀️"
        
        # モックユーザーを設定
        mock_user = AsyncMock(spec=discord.User)
        mock_user.send.side_effect = discord.Forbidden(MagicMock(), "Forbidden")
        notification_service.bot_client.fetch_user.return_value = mock_user
        
        result = await notification_service._send_weather_dm_with_retry(
            user_id, sample_weather_data, ai_message
        )
        
        assert result is False
    
    async def test_send_weather_dm_with_retry_user_not_found(
        self, 
        notification_service, 
        sample_weather_data
    ):
        """ユーザーが見つからない場合のテスト"""
        user_id = 123456789
        ai_message = "今日も素晴らしい一日になりそうですね！ ☀️"
        
        # モックユーザーを設定
        mock_user = AsyncMock(spec=discord.User)
        mock_user.send.side_effect = discord.NotFound(MagicMock(), "Not Found")
        notification_service.bot_client.fetch_user.return_value = mock_user
        
        result = await notification_service._send_weather_dm_with_retry(
            user_id, sample_weather_data, ai_message
        )
        
        assert result is False
    
    def test_create_weather_embed(self, notification_service, sample_weather_data):
        """天気Embed作成のテスト"""
        ai_message = "今日も素晴らしい一日になりそうですね！ ☀️"
        
        embed = notification_service._create_weather_embed(sample_weather_data, ai_message)
        
        assert isinstance(embed, discord.Embed)
        assert embed.title == "🌤️ 東京都の天気情報"
        assert embed.description == ai_message
        assert len(embed.fields) >= 4  # 天気、気温、降水確率、発表時刻
    
    def test_get_weather_color(self, notification_service):
        """天気色判定のテスト"""
        # 晴れ
        color = notification_service._get_weather_color("晴れ")
        assert color == 0xFFD700
        
        # 雨
        color = notification_service._get_weather_color("雨")
        assert color == 0x4682B4
        
        # 雪
        color = notification_service._get_weather_color("雪")
        assert color == 0xF0F8FF
        
        # 曇り
        color = notification_service._get_weather_color("曇り")
        assert color == 0x708090
        
        # デフォルト
        color = notification_service._get_weather_color("不明")
        assert color == 0x87CEEB
    
    async def test_send_test_notification(self, notification_service):
        """テスト通知送信のテスト"""
        user_id = 123456789
        
        # send_scheduled_weather_updateをモック化
        notification_service.send_scheduled_weather_update = AsyncMock(return_value=True)
        
        result = await notification_service.send_test_notification(user_id)
        
        assert result is True
        notification_service.send_scheduled_weather_update.assert_called_once_with(user_id)
    
    async def test_get_notification_stats(self, notification_service):
        """通知統計情報取得のテスト"""
        # モックユーザーリストを設定
        mock_users = [MagicMock(), MagicMock(), MagicMock()]
        notification_service.user_service.get_users_with_notifications_enabled.return_value = mock_users
        
        stats = await notification_service.get_notification_stats()
        
        assert stats['enabled_users_count'] == 3
        assert stats['weather_service_available'] is True
        assert stats['ai_service_available'] is True
        assert stats['bot_client_available'] is True
        assert 'last_check' in stats
    
    async def test_get_notification_stats_error(self, notification_service):
        """通知統計情報取得エラーのテスト"""
        notification_service.user_service.get_users_with_notifications_enabled.side_effect = Exception("DB Error")
        
        stats = await notification_service.get_notification_stats()
        
        assert 'error' in stats
        assert stats['error'] == "DB Error"
        assert 'last_check' in stats