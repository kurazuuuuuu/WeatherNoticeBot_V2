"""
UserServiceのユニットテスト（データベース操作モック使用）

このテストファイルはデータベース操作をモック化してUserServiceの動作をテストします。
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.services.user_service import UserService
from src.models.user import User
from src.database import DatabaseConnectionError, MemoryUserData


class TestUserService:
    """UserServiceのユニットテストクラス"""
    
    @pytest.fixture
    def user_service(self):
        """UserServiceのインスタンスを作成"""
        return UserService()
    
    @pytest.fixture
    def mock_user(self):
        """モック用のUserオブジェクト"""
        user = MagicMock(spec=User)
        user.id = 1
        user.discord_id = 123456789
        user.area_code = "130000"
        user.area_name = "東京都"
        user.notification_hour = 9
        user.timezone = "Asia/Tokyo"
        user.is_notification_enabled = True
        user.created_at = datetime.now()
        user.updated_at = datetime.now()
        
        # メソッドをモック化
        user.set_location = MagicMock()
        user.has_location = MagicMock(return_value=True)
        user.set_notification_schedule = MagicMock()
        user.disable_notifications = MagicMock()
        user.has_notification_enabled = MagicMock(return_value=True)
        
        return user
    
    @pytest.fixture
    def mock_memory_user(self):
        """モック用のMemoryUserDataオブジェクト"""
        return MemoryUserData(
            discord_id=123456789,
            area_code="130000",
            area_name="東京都",
            notification_hour=9,
            timezone="Asia/Tokyo",
            is_notification_enabled=True
        )
    
    def test_memory_user_conversion(self, user_service, mock_user, mock_memory_user):
        """MemoryUserDataとUserモデル間の変換テスト"""
        # UserモデルからMemoryUserDataへの変換
        memory_user = user_service._user_model_to_memory_user(mock_user)
        assert memory_user.discord_id == mock_user.discord_id
        assert memory_user.area_code == mock_user.area_code
        assert memory_user.area_name == mock_user.area_name
        assert memory_user.notification_hour == mock_user.notification_hour
        assert memory_user.is_notification_enabled == mock_user.is_notification_enabled
        
        # MemoryUserDataからUserモデルへの変換
        user_model = user_service._memory_user_to_user_model(mock_memory_user)
        assert user_model.discord_id == mock_memory_user.discord_id
        assert user_model.area_code == mock_memory_user.area_code
        assert user_model.area_name == mock_memory_user.area_name
        assert user_model.notification_hour == mock_memory_user.notification_hour
        assert user_model.is_notification_enabled == mock_memory_user.is_notification_enabled
    
    @pytest.mark.asyncio
    async def test_create_user_success(self, user_service, mock_user):
        """ユーザー作成成功のテスト"""
        discord_id = 123456789
        
        with patch('src.services.user_service.get_db_session') as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__.return_value = mock_session
            
            # 既存ユーザーが存在しない場合
            with patch.object(user_service, 'get_user_by_discord_id', return_value=None):
                with patch('src.models.user.User.from_discord_id', return_value=mock_user):
                    result = await user_service.create_user(discord_id)
                    
                    assert result is not None
                    assert result.discord_id == discord_id
                    mock_session.add.assert_called_once()
                    mock_session.commit.assert_called_once()
                    mock_session.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_user_already_exists(self, user_service, mock_user):
        """既存ユーザー作成のテスト"""
        discord_id = 123456789
        
        # 既存ユーザーが存在する場合
        with patch.object(user_service, 'get_user_by_discord_id', new_callable=AsyncMock, return_value=mock_user):
            result = await user_service.create_user(discord_id)
            
            assert result == mock_user
    
    @pytest.mark.asyncio
    async def test_create_user_database_error(self, user_service):
        """データベースエラー時のユーザー作成テスト"""
        discord_id = 123456789
        
        with patch('src.services.user_service.get_db_session') as mock_session_ctx:
            mock_session_ctx.side_effect = DatabaseConnectionError("Connection failed")
            
            # メモリストレージのモック
            with patch('src.services.user_service.db_manager') as mock_db_manager:
                mock_memory_storage = MagicMock()
                mock_db_manager.memory_storage = mock_memory_storage
                mock_memory_storage.is_enabled.return_value = True
                mock_memory_storage.get_user.return_value = None
                
                result = await user_service.create_user(discord_id)
                
                # メモリストレージにフォールバックされることを確認
                mock_memory_storage.set_user.assert_called_once()
                assert result is not None
    
    @pytest.mark.asyncio
    async def test_create_user_integrity_error(self, user_service):
        """整合性エラー時のユーザー作成テスト"""
        discord_id = 123456789
        
        with patch('src.services.user_service.get_db_session') as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__.return_value = mock_session
            mock_session.commit.side_effect = IntegrityError("Duplicate key", None, None)
            
            with patch.object(user_service, 'get_user_by_discord_id', return_value=None):
                result = await user_service.create_user(discord_id)
                
                assert result is None
    
    @pytest.mark.asyncio
    async def test_get_user_by_discord_id_success(self, user_service, mock_user):
        """Discord IDでのユーザー取得成功テスト"""
        discord_id = 123456789
        
        with patch('src.services.user_service.get_db_session') as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__.return_value = mock_session
            
            # SQLAlchemyの結果をモック
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_session.execute.return_value = mock_result
            
            result = await user_service.get_user_by_discord_id(discord_id)
            
            assert result == mock_user
            mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_by_discord_id_not_found(self, user_service):
        """Discord IDでのユーザー取得（見つからない）テスト"""
        discord_id = 123456789
        
        with patch('src.services.user_service.get_db_session') as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__.return_value = mock_session
            
            # ユーザーが見つからない場合
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute.return_value = mock_result
            
            result = await user_service.get_user_by_discord_id(discord_id)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_user_by_discord_id_memory_storage(self, user_service, mock_memory_user):
        """メモリストレージでのユーザー取得テスト"""
        discord_id = 123456789
        
        with patch.object(user_service, '_use_memory_storage', return_value=True):
            with patch('src.services.user_service.db_manager') as mock_db_manager:
                mock_memory_storage = MagicMock()
                mock_db_manager.memory_storage = mock_memory_storage
                mock_memory_storage.get_user.return_value = mock_memory_user
                
                result = await user_service.get_user_by_discord_id(discord_id)
                
                assert result is not None
                assert result.discord_id == discord_id
                mock_memory_storage.get_user.assert_called_once_with(discord_id)
    
    @pytest.mark.asyncio
    async def test_set_user_location_success(self, user_service, mock_user):
        """ユーザー位置情報設定成功テスト"""
        discord_id = 123456789
        area_code = "270000"
        area_name = "大阪府"
        
        with patch('src.services.user_service.get_db_session') as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__.return_value = mock_session
            mock_session.merge.return_value = mock_user
            
            with patch.object(user_service, 'get_user_by_discord_id', new_callable=AsyncMock, return_value=mock_user):
                result = await user_service.set_user_location(discord_id, area_code, area_name)
                
                assert result is True
                mock_user.set_location.assert_called_once_with(area_code, area_name)
                mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_set_user_location_new_user(self, user_service, mock_user):
        """新規ユーザーの位置情報設定テスト"""
        discord_id = 123456789
        area_code = "270000"
        area_name = "大阪府"
        
        with patch('src.services.user_service.get_db_session') as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__.return_value = mock_session
            mock_session.merge.return_value = mock_user
            
            with patch.object(user_service, 'get_user_by_discord_id', new_callable=AsyncMock, return_value=None):
                with patch.object(user_service, 'create_user', new_callable=AsyncMock, return_value=mock_user):
                    result = await user_service.set_user_location(discord_id, area_code, area_name)
                    
                    assert result is True
                    mock_user.set_location.assert_called_once_with(area_code, area_name)
    
    @pytest.mark.asyncio
    async def test_set_user_location_memory_storage(self, user_service, mock_memory_user):
        """メモリストレージでの位置情報設定テスト"""
        discord_id = 123456789
        area_code = "270000"
        area_name = "大阪府"
        
        with patch.object(user_service, '_use_memory_storage', return_value=True):
            with patch('src.services.user_service.db_manager') as mock_db_manager:
                mock_memory_storage = MagicMock()
                mock_db_manager.memory_storage = mock_memory_storage
                mock_memory_storage.get_user.return_value = mock_memory_user
                
                result = await user_service.set_user_location(discord_id, area_code, area_name)
                
                assert result is True
                mock_memory_storage.set_user.assert_called()
                # メモリユーザーの位置情報が更新されることを確認
                assert mock_memory_user.area_code == area_code
                assert mock_memory_user.area_name == area_name
    
    @pytest.mark.asyncio
    async def test_get_user_location_success(self, user_service, mock_user):
        """ユーザー位置情報取得成功テスト"""
        discord_id = 123456789
        
        # ユーザーが位置情報を持っている場合
        mock_user.has_location.return_value = True
        
        with patch.object(user_service, 'get_user_by_discord_id', new_callable=AsyncMock, return_value=mock_user):
            result = await user_service.get_user_location(discord_id)
            
            assert result == (mock_user.area_code, mock_user.area_name)
    
    @pytest.mark.asyncio
    async def test_get_user_location_no_location(self, user_service, mock_user):
        """位置情報未設定ユーザーの取得テスト"""
        discord_id = 123456789
        
        # ユーザーが位置情報を持っていない場合
        mock_user.has_location.return_value = False
        
        with patch.object(user_service, 'get_user_by_discord_id', new_callable=AsyncMock, return_value=mock_user):
            result = await user_service.get_user_location(discord_id)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_user_location_user_not_found(self, user_service):
        """存在しないユーザーの位置情報取得テスト"""
        discord_id = 123456789
        
        with patch.object(user_service, 'get_user_by_discord_id', new_callable=AsyncMock, return_value=None):
            result = await user_service.get_user_location(discord_id)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_set_notification_schedule_success(self, user_service, mock_user):
        """通知スケジュール設定成功テスト"""
        discord_id = 123456789
        hour = 9
        
        with patch('src.services.user_service.get_db_session') as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__.return_value = mock_session
            mock_session.merge.return_value = mock_user
            
            with patch.object(user_service, 'get_user_by_discord_id', new_callable=AsyncMock, return_value=mock_user):
                result = await user_service.set_notification_schedule(discord_id, hour)
                
                assert result is True
                mock_user.set_notification_schedule.assert_called_once_with(hour)
                mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_set_notification_schedule_invalid_hour(self, user_service):
        """無効な時間での通知スケジュール設定テスト"""
        discord_id = 123456789
        
        # 無効な時間（24時以上）
        result = await user_service.set_notification_schedule(discord_id, 25)
        assert result is False
        
        # 無効な時間（負の値）
        result = await user_service.set_notification_schedule(discord_id, -1)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_disable_notifications_success(self, user_service, mock_user):
        """通知無効化成功テスト"""
        discord_id = 123456789
        
        with patch('src.services.user_service.get_db_session') as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__.return_value = mock_session
            mock_session.merge.return_value = mock_user
            
            with patch.object(user_service, 'get_user_by_discord_id', new_callable=AsyncMock, return_value=mock_user):
                result = await user_service.disable_notifications(discord_id)
                
                assert result is True
                mock_user.disable_notifications.assert_called_once()
                mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_disable_notifications_user_not_found(self, user_service):
        """存在しないユーザーの通知無効化テスト"""
        discord_id = 123456789
        
        with patch.object(user_service, 'get_user_by_discord_id', new_callable=AsyncMock, return_value=None):
            result = await user_service.disable_notifications(discord_id)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_get_user_settings_success(self, user_service, mock_user):
        """ユーザー設定取得成功テスト"""
        discord_id = 123456789
        
        # モックユーザーのメソッドを設定
        mock_user.has_location.return_value = True
        mock_user.has_notification_enabled.return_value = True
        
        with patch.object(user_service, 'get_user_by_discord_id', new_callable=AsyncMock, return_value=mock_user):
            result = await user_service.get_user_settings(discord_id)
            
            assert result is not None
            assert result['discord_id'] == mock_user.discord_id
            assert result['area_code'] == mock_user.area_code
            assert result['area_name'] == mock_user.area_name
            assert result['notification_hour'] == mock_user.notification_hour
            assert result['is_notification_enabled'] == mock_user.is_notification_enabled
            assert result['has_location'] is True
            assert result['has_notification_enabled'] is True
    
    @pytest.mark.asyncio
    async def test_get_user_settings_user_not_found(self, user_service):
        """存在しないユーザーの設定取得テスト"""
        discord_id = 123456789
        
        with patch.object(user_service, 'get_user_by_discord_id', new_callable=AsyncMock, return_value=None):
            result = await user_service.get_user_settings(discord_id)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_users_with_notifications_success(self, user_service):
        """通知有効ユーザー取得成功テスト"""
        mock_users = [MagicMock(), MagicMock()]
        
        with patch('src.services.user_service.get_db_session') as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__.return_value = mock_session
            
            # SQLAlchemyの結果をモック
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = mock_users
            mock_session.execute.return_value = mock_result
            
            result = await user_service.get_users_with_notifications()
            
            assert result == mock_users
            mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_users_with_notifications_specific_hour(self, user_service):
        """特定時間の通知有効ユーザー取得テスト"""
        hour = 9
        mock_users = [MagicMock()]
        
        with patch('src.services.user_service.get_db_session') as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__.return_value = mock_session
            
            # SQLAlchemyの結果をモック
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = mock_users
            mock_session.execute.return_value = mock_result
            
            result = await user_service.get_users_with_notifications(hour)
            
            assert result == mock_users
            mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_users_with_notifications_invalid_hour(self, user_service):
        """無効な時間での通知有効ユーザー取得テスト"""
        result = await user_service.get_users_with_notifications(25)
        assert result == []
        
        result = await user_service.get_users_with_notifications(-1)
        assert result == []
    
    @pytest.mark.asyncio
    async def test_get_users_with_notifications_memory_storage(self, user_service, mock_memory_user):
        """メモリストレージでの通知有効ユーザー取得テスト"""
        with patch.object(user_service, '_use_memory_storage', return_value=True):
            with patch('src.services.user_service.db_manager') as mock_db_manager:
                mock_memory_storage = MagicMock()
                mock_db_manager.memory_storage = mock_memory_storage
                mock_memory_storage.get_users_with_notifications.return_value = [mock_memory_user]
                
                result = await user_service.get_users_with_notifications()
                
                assert len(result) == 1
                assert result[0].discord_id == mock_memory_user.discord_id
    
    @pytest.mark.asyncio
    async def test_update_user_success(self, user_service, mock_user):
        """ユーザー情報更新成功テスト"""
        discord_id = 123456789
        update_data = {"area_code": "270000", "area_name": "大阪府"}
        
        with patch('src.services.user_service.get_db_session') as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__.return_value = mock_session
            mock_session.merge.return_value = mock_user
            
            with patch.object(user_service, 'get_user_by_discord_id', new_callable=AsyncMock, return_value=mock_user):
                result = await user_service.update_user(discord_id, **update_data)
                
                assert result is True
                mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_user_not_found(self, user_service):
        """存在しないユーザーの更新テスト"""
        discord_id = 123456789
        
        with patch.object(user_service, 'get_user_by_discord_id', new_callable=AsyncMock, return_value=None):
            result = await user_service.update_user(discord_id, area_code="270000")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_delete_user_success(self, user_service, mock_user):
        """ユーザー削除成功テスト"""
        discord_id = 123456789
        
        with patch('src.services.user_service.get_db_session') as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__.return_value = mock_session
            mock_session.merge.return_value = mock_user
            
            with patch.object(user_service, 'get_user_by_discord_id', new_callable=AsyncMock, return_value=mock_user):
                result = await user_service.delete_user(discord_id)
                
                assert result is True
                mock_session.delete.assert_called_once_with(mock_user)
                mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, user_service):
        """存在しないユーザーの削除テスト"""
        discord_id = 123456789
        
        with patch.object(user_service, 'get_user_by_discord_id', new_callable=AsyncMock, return_value=None):
            result = await user_service.delete_user(discord_id)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_get_user_count_success(self, user_service):
        """ユーザー数取得成功テスト"""
        expected_count = 42
        
        with patch('src.services.user_service.get_db_session') as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__.return_value = mock_session
            
            # SQLAlchemyの結果をモック
            mock_result = MagicMock()
            mock_result.scalar.return_value = expected_count
            mock_session.execute.return_value = mock_result
            
            result = await user_service.get_user_count()
            
            assert result == expected_count
    
    @pytest.mark.asyncio
    async def test_get_user_count_memory_storage(self, user_service):
        """メモリストレージでのユーザー数取得テスト"""
        expected_count = 10
        
        with patch.object(user_service, '_use_memory_storage', return_value=True):
            with patch('src.services.user_service.db_manager') as mock_db_manager:
                mock_memory_storage = MagicMock()
                mock_db_manager.memory_storage = mock_memory_storage
                mock_memory_storage.get_user_count.return_value = expected_count
                
                result = await user_service.get_user_count()
                
                assert result == expected_count
    
    @pytest.mark.asyncio
    async def test_validate_data_integrity_healthy(self, user_service):
        """データ整合性チェック（正常）テスト"""
        with patch('src.services.user_service.get_db_session') as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__.return_value = mock_session
            
            # 各チェックで問題なしの結果をモック
            mock_result = AsyncMock()
            mock_result.fetchall.return_value = []  # 重複なし
            mock_result.scalar.return_value = 0  # 無効データなし
            mock_session.execute.return_value = mock_result
            
            with patch.object(user_service, 'get_user_count', new_callable=AsyncMock, return_value=100):
                result = await user_service.validate_data_integrity()
                
                assert result["status"] == "healthy"
                assert len(result["errors"]) == 0
    
    @pytest.mark.asyncio
    async def test_validate_data_integrity_with_errors(self, user_service):
        """データ整合性チェック（エラーあり）テスト"""
        with patch('src.services.user_service.get_db_session') as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__.return_value = mock_session
            
            # 重複データがある場合をモック
            duplicate_result = MagicMock()
            duplicate_result.discord_id = 123456789
            duplicate_result.count = 2
            
            mock_result = AsyncMock()
            mock_result.fetchall.return_value = [duplicate_result]
            mock_session.execute.return_value = mock_result
            
            result = await user_service.validate_data_integrity()
            
            assert result["status"] == "error"
            assert len(result["errors"]) > 0
            assert "重複するDiscord ID" in result["errors"][0]
    
    @pytest.mark.asyncio
    async def test_get_service_health_success(self, user_service):
        """サービスヘルスチェック成功テスト"""
        with patch('src.services.user_service.db_manager') as mock_db_manager:
            mock_db_manager.health_check = AsyncMock(return_value={"status": "healthy"})
            
            with patch.object(user_service, 'get_user_count', new_callable=AsyncMock, return_value=100):
                with patch.object(user_service, 'get_users_with_notifications', new_callable=AsyncMock, return_value=[MagicMock()]):
                    with patch.object(user_service, 'validate_data_integrity', new_callable=AsyncMock, return_value={"status": "healthy"}):
                        result = await user_service.get_service_health()
                        
                        assert result["service_name"] == "UserService"
                        assert result["database_status"] == "healthy"
                        assert result["user_count"] == 100
                        assert result["notification_enabled_users"] == 1
                        assert result["overall_status"] == "healthy"


if __name__ == "__main__":
    pytest.main([__file__])