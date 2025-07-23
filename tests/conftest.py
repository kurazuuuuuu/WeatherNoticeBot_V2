"""
pytest設定ファイル

全テストで共通して使用されるフィクスチャとセットアップを定義します。
"""

import pytest
import asyncio
import os
import tempfile
from unittest.mock import MagicMock, patch


@pytest.fixture(scope="session")
def event_loop():
    """セッションスコープのイベントループ"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_config():
    """モック用のConfigオブジェクト"""
    config = MagicMock()
    config.GEMINI_API_KEY = "test_api_key"
    config.DATABASE_URL = "sqlite:///test.db"
    config.DISCORD_TOKEN = "test_discord_token"
    return config


@pytest.fixture
def mock_weather_data():
    """モック用の天気データ"""
    weather_data = MagicMock()
    weather_data.area_name = "東京都"
    weather_data.weather_description = "晴れ"
    weather_data.temperature = 25.0
    weather_data.precipitation_probability = 10
    weather_data.wind = "北の風 弱く"
    weather_data.timestamp = "2024-01-15T12:00:00+09:00"
    return weather_data


@pytest.fixture
def temp_database():
    """一時的なテスト用データベース"""
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()
    
    yield temp_db.name
    
    # クリーンアップ
    try:
        os.unlink(temp_db.name)
    except OSError:
        pass


@pytest.fixture(autouse=True)
def setup_test_environment():
    """テスト環境のセットアップ"""
    # テスト用の環境変数を設定
    original_env = {}
    test_env = {
        'TESTING': 'true',
        'LOG_LEVEL': 'ERROR',
        'DATABASE_URL': 'sqlite:///test.db'
    }
    
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield
    
    # 環境変数を復元
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture
def mock_discord_user():
    """モック用のDiscordユーザー"""
    user = MagicMock()
    user.id = 123456789
    user.name = "TestUser"
    user.discriminator = "1234"
    user.mention = "<@123456789>"
    return user


@pytest.fixture
def mock_discord_channel():
    """モック用のDiscordチャンネル"""
    channel = MagicMock()
    channel.id = 987654321
    channel.name = "test-channel"
    channel.send = MagicMock()
    return channel


@pytest.fixture
def mock_discord_guild():
    """モック用のDiscordギルド（サーバー）"""
    guild = MagicMock()
    guild.id = 111222333
    guild.name = "Test Server"
    guild.member_count = 100
    return guild


def pytest_configure(config):
    """pytest設定"""
    # カスタムマーカーの登録
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "api: mark test as requiring API access"
    )
    config.addinivalue_line(
        "markers", "database: mark test as requiring database access"
    )


def pytest_collection_modifyitems(config, items):
    """テスト収集時の処理"""
    # 統合テストにマーカーを自動追加
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)


@pytest.fixture
def suppress_logs():
    """ログ出力を抑制"""
    import logging
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


# 非同期テスト用のヘルパー関数
def async_test(coro):
    """非同期テストのデコレータ"""
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro(*args, **kwargs))
        finally:
            loop.close()
    return wrapper


# テストデータのファクトリ関数
class TestDataFactory:
    """テストデータ生成用のファクトリクラス"""
    
    @staticmethod
    def create_weather_context(area_name="東京都", weather="晴れ", temp=25.0, pop=10):
        """WeatherContextオブジェクトを作成"""
        from datetime import datetime
        
        # モック実装（実際のクラスが利用できない場合）
        class WeatherContext:
            def __init__(self, area_name, weather_description, temperature, 
                         precipitation_probability, wind, timestamp, 
                         is_alert=False, alert_description=None):
                self.area_name = area_name
                self.weather_description = weather_description
                self.temperature = temperature
                self.precipitation_probability = precipitation_probability
                self.wind = wind
                self.timestamp = timestamp
                self.is_alert = is_alert
                self.alert_description = alert_description
        
        return WeatherContext(
            area_name=area_name,
            weather_description=weather,
            temperature=temp,
            precipitation_probability=pop,
            wind="北の風",
            timestamp=datetime.now(),
            is_alert=False,
            alert_description=None
        )
    
    @staticmethod
    def create_user_data(discord_id=123456789, area_code="130000", area_name="東京都"):
        """ユーザーデータを作成"""
        from datetime import datetime
        
        # モック実装
        class User:
            def __init__(self):
                self.id = None
                self.discord_id = discord_id
                self.area_code = area_code
                self.area_name = area_name
                self.notification_hour = None
                self.timezone = "Asia/Tokyo"
                self.is_notification_enabled = False
                self.created_at = datetime.now()
                self.updated_at = datetime.now()
        
        return User()


@pytest.fixture
def test_data_factory():
    """テストデータファクトリのフィクスチャ"""
    return TestDataFactory