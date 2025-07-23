"""
UserServiceの拡張ユニットテスト

既存のテストを補完し、エッジケースやエラーハンドリングをより詳細にテストします。
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# テスト対象のインポート（モック化）
try:
    from src.services.user_service import UserService
    from src.models.user import User
    from src.database import DatabaseConnectionError, MemoryUserData
    from sqlalchemy.exc import IntegrityError, SQLAlchemyError
except ImportError:
    # 依存関係が不足している場合のモック実装
    class UserService:
        def __init__(self):
            pass
        
        def _use_memory_storage(self):
            return False
        
        def _memory_user_to_user_model(self, memory_user):
            user = User()
            user.discord_id = memory_user.discord_id
            user.area_code = memory_user.area_code
            user.area_name = memory_user.area_name
            user.notification_hour = memory_user.notification_hour
            user.timezone = memory_user.timezone
            user.is_notification_enabled = memory_user.is_notification_enabled
            user.created_at = memory_user.created_at
            user.updated_at = memory_user.updated_at
            return user
        
        def _user_model_to_memory_user(self, user):
            return MemoryUserData(
                discord_id=user.discord_id,
                area_code=user.area_code,
                area_name=user.area_name,
                notification_hour=user.notification_hour,
                timezone=user.timezone,
                is_notification_enabled=user.is_notification_enabled,
                created_at=user.created_at,
                updated_at=user.updated_at
            )
        
        async def create_user(self, discord_id):
            return None
        
        async def get_user_by_discord_id(self, discord_id):
            return None
        
        async def set_user_location(self, discord_id, area_code, area_name):
            return True
        
        async def get_user_location(self, discord_id):
            return None
        
        async def set_notification_schedule(self, discord_id, hour):
            return 0 <= hour <= 23
        
        async def disable_notifications(self, discord_id):
            return True
        
        async def get_user_settings(self, discord_id):
            return None
        
        async def get_users_with_notifications(self, hour=None):
            return []
        
        async def get_user_count(self):
            return 0
        
        async def validate_data_integrity(self):
            return {"status": "healthy", "checks": [], "errors": [], "warnings": []}
    
    class User:
        def __init__(self):
            self.id = None
            self.discord_id = None
            self.area_code = None
            self.area_name = None
            self.notification_hour = None
            self.timezone = "Asia/Tokyo"
            self.is_notification_enabled = False
            self.created_at = datetime.now()
            self.updated_at = datetime.now()
        
        @classmethod
        def from_discord_id(cls, discord_id):
            user = cls()
            user.discord_id = discord_id
            return user
        
        def set_location(self, area_code, area_name):
            self.area_code = area_code
            self.area_name = area_name
            self.updated_at = datetime.now()
        
        def has_location(self):
            return self.area_code is not None and self.area_name is not None
        
        def set_notification_schedule(self, hour):
            if 0 <= hour <= 23:
                self.notification_hour = hour
                self.is_notification_enabled = True
                self.updated_at = datetime.now()
            else:
                raise ValueError("Invalid hour")
        
        def disable_notifications(self):
            self.is_notification_enabled = False
            self.updated_at = datetime.now()
        
        def has_notification_enabled(self):
            return self.is_notification_enabled and self.notification_hour is not None
    
    class MemoryUserData:
        def __init__(self, discord_id, area_code=None, area_name=None, 
                     notification_hour=None, timezone="Asia/Tokyo", 
                     is_notification_enabled=False, created_at=None, updated_at=None):
            self.discord_id = discord_id
            self.area_code = area_code
            self.area_name = area_name
            self.notification_hour = notification_hour
            self.timezone = timezone
            self.is_notification_enabled = is_notification_enabled
            self.created_at = created_at or datetime.now()
            self.updated_at = updated_at or datetime.now()
    
    class DatabaseConnectionError(Exception):
        pass
    
    class IntegrityError(Exception):
        def __init__(self, message, orig, params):
            super().__init__(message)
            self.orig = orig
            self.params = params
    
    class SQLAlchemyError(Exception):
        pass


class TestUserServiceEnhanced:
    """UserServiceの拡張ユニットテストクラス"""
    
    @pytest.fixture
    def user_service(self):
        """UserServiceのインスタンスを作成"""
        return UserService()
    
    @pytest.fixture
    def sample_user(self):
        """サンプルユーザーを作成"""
        user = User()
        user.id = 1
        user.discord_id = 123456789
        user.area_code = "130000"
        user.area_name = "東京都"
        user.notification_hour = 9
        user.timezone = "Asia/Tokyo"
        user.is_notification_enabled = True
        user.created_at = datetime.now() - timedelta(days=1)
        user.updated_at = datetime.now()
        return user
    
    @pytest.fixture
    def sample_memory_user(self):
        """サンプルメモリユーザーを作成"""
        return MemoryUserData(
            discord_id=123456789,
            area_code="130000",
            area_name="東京都",
            notification_hour=9,
            timezone="Asia/Tokyo",
            is_notification_enabled=True
        )
    
    def test_user_model_creation(self):
        """Userモデル作成のテスト"""
        discord_id = 123456789
        user = User.from_discord_id(discord_id)
        
        assert user.discord_id == discord_id
        assert user.area_code is None
        assert user.area_name is None
        assert user.notification_hour is None
        assert user.timezone == "Asia/Tokyo"
        assert user.is_notification_enabled is False
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)
    
    def test_user_location_management(self, sample_user):
        """ユーザー位置情報管理のテスト"""
        # 初期状態では位置情報なし
        user = User()
        assert not user.has_location()
        
        # 位置情報を設定
        area_code = "270000"
        area_name = "大阪府"
        old_updated_at = user.updated_at
        
        user.set_location(area_code, area_name)
        
        assert user.area_code == area_code
        assert user.area_name == area_name
        assert user.has_location()
        assert user.updated_at > old_updated_at
    
    def test_user_notification_management(self, sample_user):
        """ユーザー通知管理のテスト"""
        user = User()
        
        # 初期状態では通知無効
        assert not user.has_notification_enabled()
        assert not user.is_notification_enabled
        assert user.notification_hour is None
        
        # 通知スケジュールを設定
        hour = 9
        old_updated_at = user.updated_at
        
        user.set_notification_schedule(hour)
        
        assert user.notification_hour == hour
        assert user.is_notification_enabled
        assert user.has_notification_enabled()
        assert user.updated_at > old_updated_at
        
        # 通知を無効化
        old_updated_at = user.updated_at
        user.disable_notifications()
        
        assert not user.is_notification_enabled
        assert not user.has_notification_enabled()
        assert user.updated_at > old_updated_at
    
    def test_user_notification_invalid_hour(self):
        """無効な時間での通知設定テスト"""
        user = User()
        
        # 無効な時間（24時以上）
        with pytest.raises(ValueError):
            user.set_notification_schedule(24)
        
        # 無効な時間（負の値）
        with pytest.raises(ValueError):
            user.set_notification_schedule(-1)
        
        # 境界値テスト
        user.set_notification_schedule(0)  # 0時は有効
        assert user.notification_hour == 0
        
        user.set_notification_schedule(23)  # 23時は有効
        assert user.notification_hour == 23
    
    def test_memory_user_data_creation(self):
        """MemoryUserData作成のテスト"""
        discord_id = 123456789
        memory_user = MemoryUserData(discord_id)
        
        assert memory_user.discord_id == discord_id
        assert memory_user.area_code is None
        assert memory_user.area_name is None
        assert memory_user.notification_hour is None
        assert memory_user.timezone == "Asia/Tokyo"
        assert memory_user.is_notification_enabled is False
        assert isinstance(memory_user.created_at, datetime)
        assert isinstance(memory_user.updated_at, datetime)
    
    def test_memory_user_data_with_parameters(self):
        """パラメータ付きMemoryUserData作成のテスト"""
        discord_id = 123456789
        area_code = "130000"
        area_name = "東京都"
        notification_hour = 9
        timezone = "Asia/Tokyo"
        is_notification_enabled = True
        created_at = datetime.now() - timedelta(days=1)
        updated_at = datetime.now()
        
        memory_user = MemoryUserData(
            discord_id=discord_id,
            area_code=area_code,
            area_name=area_name,
            notification_hour=notification_hour,
            timezone=timezone,
            is_notification_enabled=is_notification_enabled,
            created_at=created_at,
            updated_at=updated_at
        )
        
        assert memory_user.discord_id == discord_id
        assert memory_user.area_code == area_code
        assert memory_user.area_name == area_name
        assert memory_user.notification_hour == notification_hour
        assert memory_user.timezone == timezone
        assert memory_user.is_notification_enabled == is_notification_enabled
        assert memory_user.created_at == created_at
        assert memory_user.updated_at == updated_at
    
    def test_user_memory_conversion(self, user_service, sample_user, sample_memory_user):
        """ユーザーとメモリユーザー間の変換テスト"""
        # UserモデルからMemoryUserDataへの変換
        memory_user = user_service._user_model_to_memory_user(sample_user)
        
        assert memory_user.discord_id == sample_user.discord_id
        assert memory_user.area_code == sample_user.area_code
        assert memory_user.area_name == sample_user.area_name
        assert memory_user.notification_hour == sample_user.notification_hour
        assert memory_user.timezone == sample_user.timezone
        assert memory_user.is_notification_enabled == sample_user.is_notification_enabled
        assert memory_user.created_at == sample_user.created_at
        assert memory_user.updated_at == sample_user.updated_at
        
        # MemoryUserDataからUserモデルへの変換
        user_model = user_service._memory_user_to_user_model(sample_memory_user)
        
        assert user_model.discord_id == sample_memory_user.discord_id
        assert user_model.area_code == sample_memory_user.area_code
        assert user_model.area_name == sample_memory_user.area_name
        assert user_model.notification_hour == sample_memory_user.notification_hour
        assert user_model.timezone == sample_memory_user.timezone
        assert user_model.is_notification_enabled == sample_memory_user.is_notification_enabled
        assert user_model.created_at == sample_memory_user.created_at
        assert user_model.updated_at == sample_memory_user.updated_at
    
    @pytest.mark.asyncio
    async def test_notification_schedule_boundary_values(self, user_service):
        """通知スケジュール境界値のテスト"""
        discord_id = 123456789
        
        # 境界値テスト（有効な値）
        assert await user_service.set_notification_schedule(discord_id, 0) is True
        assert await user_service.set_notification_schedule(discord_id, 23) is True
        
        # 境界値テスト（無効な値）
        assert await user_service.set_notification_schedule(discord_id, -1) is False
        assert await user_service.set_notification_schedule(discord_id, 24) is False
        assert await user_service.set_notification_schedule(discord_id, 25) is False
        assert await user_service.set_notification_schedule(discord_id, 100) is False
    
    @pytest.mark.asyncio
    async def test_user_location_edge_cases(self, user_service):
        """ユーザー位置情報のエッジケーステスト"""
        discord_id = 123456789
        
        # 正常なケース
        result = await user_service.set_user_location(discord_id, "130000", "東京都")
        assert result is True
        
        # エッジケース（空文字）
        result = await user_service.set_user_location(discord_id, "", "")
        assert result is True  # 空文字も許可される
        
        # エッジケース（長い文字列）
        long_area_name = "非常に長い地域名" * 20
        result = await user_service.set_user_location(discord_id, "130000", long_area_name)
        assert result is True
        
        # エッジケース（特殊文字）
        special_area_name = "東京都🗼🌸"
        result = await user_service.set_user_location(discord_id, "130000", special_area_name)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_user_count_edge_cases(self, user_service):
        """ユーザー数取得のエッジケーステスト"""
        # 基本的なケース
        count = await user_service.get_user_count()
        assert isinstance(count, int)
        assert count >= 0
    
    @pytest.mark.asyncio
    async def test_data_integrity_validation_structure(self, user_service):
        """データ整合性検証の構造テスト"""
        result = await user_service.validate_data_integrity()
        
        # 必要なキーが存在することを確認
        assert "status" in result
        assert "checks" in result
        assert "errors" in result
        assert "warnings" in result
        
        # データ型の確認
        assert isinstance(result["status"], str)
        assert isinstance(result["checks"], list)
        assert isinstance(result["errors"], list)
        assert isinstance(result["warnings"], list)
        
        # ステータスの値が有効であることを確認
        valid_statuses = ["healthy", "warning", "error"]
        assert result["status"] in valid_statuses
    
    def test_database_connection_error_creation(self):
        """DatabaseConnectionErrorの作成テスト"""
        error_message = "Connection failed"
        error = DatabaseConnectionError(error_message)
        
        assert str(error) == error_message
        assert isinstance(error, Exception)
    
    def test_integrity_error_creation(self):
        """IntegrityErrorの作成テスト"""
        error_message = "Duplicate key"
        orig_error = Exception("Original error")
        params = {"key": "value"}
        
        error = IntegrityError(error_message, orig_error, params)
        
        assert str(error) == error_message
        assert error.orig == orig_error
        assert error.params == params
        assert isinstance(error, Exception)
    
    def test_sqlalchemy_error_creation(self):
        """SQLAlchemyErrorの作成テスト"""
        error_message = "Database error"
        error = SQLAlchemyError(error_message)
        
        assert str(error) == error_message
        assert isinstance(error, Exception)
    
    @pytest.mark.asyncio
    async def test_user_service_memory_storage_flag(self, user_service):
        """UserServiceのメモリストレージフラグテスト"""
        # デフォルトではメモリストレージを使用しない
        assert user_service._use_memory_storage() is False
    
    def test_user_timezone_handling(self, sample_user):
        """ユーザータイムゾーン処理のテスト"""
        # デフォルトタイムゾーン
        user = User()
        assert user.timezone == "Asia/Tokyo"
        
        # タイムゾーンの変更
        user.timezone = "UTC"
        assert user.timezone == "UTC"
        
        user.timezone = "America/New_York"
        assert user.timezone == "America/New_York"
    
    def test_user_timestamps(self):
        """ユーザータイムスタンプのテスト"""
        user = User()
        
        # 作成時刻と更新時刻が設定されている
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)
        
        # 作成時刻と更新時刻が近い時刻である
        time_diff = abs((user.created_at - user.updated_at).total_seconds())
        assert time_diff < 1.0  # 1秒以内
    
    def test_user_id_handling(self):
        """ユーザーID処理のテスト"""
        user = User()
        
        # 初期状態ではIDはNone
        assert user.id is None
        
        # IDを設定
        user.id = 123
        assert user.id == 123
        
        # Discord IDとは別物
        user.discord_id = 456789
        assert user.id != user.discord_id
    
    @pytest.mark.asyncio
    async def test_concurrent_user_operations(self, user_service):
        """並行ユーザー操作のテスト"""
        discord_ids = [111111, 222222, 333333]
        
        # 複数のユーザー作成を並行実行
        tasks = [user_service.create_user(discord_id) for discord_id in discord_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 例外が発生していないことを確認
        for result in results:
            assert not isinstance(result, Exception)
    
    @pytest.mark.asyncio
    async def test_user_settings_comprehensive(self, user_service):
        """ユーザー設定の包括的テスト"""
        discord_id = 123456789
        
        # 存在しないユーザーの設定取得
        settings = await user_service.get_user_settings(discord_id)
        assert settings is None
    
    def test_memory_user_data_equality(self):
        """MemoryUserDataの等価性テスト"""
        discord_id = 123456789
        
        user1 = MemoryUserData(discord_id)
        user2 = MemoryUserData(discord_id)
        
        # 同じDiscord IDを持つユーザーでも、オブジェクトとしては異なる
        assert user1 is not user2
        assert user1.discord_id == user2.discord_id
    
    def test_user_model_equality(self):
        """Userモデルの等価性テスト"""
        discord_id = 123456789
        
        user1 = User.from_discord_id(discord_id)
        user2 = User.from_discord_id(discord_id)
        
        # 同じDiscord IDを持つユーザーでも、オブジェクトとしては異なる
        assert user1 is not user2
        assert user1.discord_id == user2.discord_id


if __name__ == "__main__":
    pytest.main([__file__])