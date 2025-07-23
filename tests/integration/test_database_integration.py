"""
データベース統合テスト

実際のデータベースとの統合テストを実行します。
このテストはテスト用データベースを使用します。
"""

import pytest
import asyncio
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch

# テスト対象のインポート（モック化対応）
try:
    from src.services.user_service import UserService
    from src.models.user import User
    from src.database import get_db_session, db_manager, DatabaseConnectionError
    from sqlalchemy.exc import IntegrityError, SQLAlchemyError
except ImportError:
    # 依存関係が不足している場合はスキップ
    pytest.skip("Database dependencies not available", allow_module_level=True)


@pytest.mark.integration
class TestDatabaseIntegration:
    """データベース統合テストクラス"""
    
    @pytest.fixture(scope="function")
    async def test_db_setup(self):
        """テスト用データベースのセットアップ"""
        # テスト用の一時データベースファイルを作成
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        # 環境変数を一時的に変更
        original_db_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{temp_db.name}'
        
        try:
            # データベースを初期化
            await db_manager.initialize()
            yield temp_db.name
        finally:
            # クリーンアップ
            await db_manager.close()
            if original_db_url:
                os.environ['DATABASE_URL'] = original_db_url
            else:
                os.environ.pop('DATABASE_URL', None)
            
            # 一時ファイルを削除
            try:
                os.unlink(temp_db.name)
            except OSError:
                pass
    
    @pytest.fixture
    def user_service(self):
        """UserServiceのインスタンスを作成"""
        return UserService()
    
    @pytest.mark.asyncio
    async def test_user_crud_operations(self, test_db_setup, user_service):
        """ユーザーCRUD操作の統合テスト"""
        discord_id = 123456789
        
        # 1. ユーザー作成
        created_user = await user_service.create_user(discord_id)
        assert created_user is not None
        assert created_user.discord_id == discord_id
        assert created_user.id is not None
        
        # 2. ユーザー取得
        retrieved_user = await user_service.get_user_by_discord_id(discord_id)
        assert retrieved_user is not None
        assert retrieved_user.discord_id == discord_id
        assert retrieved_user.id == created_user.id
        
        # 3. ユーザー更新（位置情報設定）
        area_code = "130000"
        area_name = "東京都"
        update_result = await user_service.set_user_location(discord_id, area_code, area_name)
        assert update_result is True
        
        # 更新後の確認
        updated_user = await user_service.get_user_by_discord_id(discord_id)
        assert updated_user.area_code == area_code
        assert updated_user.area_name == area_name
        
        # 4. 通知設定
        notification_hour = 9
        notification_result = await user_service.set_notification_schedule(discord_id, notification_hour)
        assert notification_result is True
        
        # 通知設定後の確認
        notified_user = await user_service.get_user_by_discord_id(discord_id)
        assert notified_user.notification_hour == notification_hour
        assert notified_user.is_notification_enabled is True
        
        # 5. ユーザー削除
        delete_result = await user_service.delete_user(discord_id)
        assert delete_result is True
        
        # 削除後の確認
        deleted_user = await user_service.get_user_by_discord_id(discord_id)
        assert deleted_user is None
    
    @pytest.mark.asyncio
    async def test_multiple_users_operations(self, test_db_setup, user_service):
        """複数ユーザー操作の統合テスト"""
        discord_ids = [111111, 222222, 333333, 444444, 555555]
        created_users = []
        
        # 複数ユーザーを作成
        for discord_id in discord_ids:
            user = await user_service.create_user(discord_id)
            assert user is not None
            created_users.append(user)
        
        # ユーザー数の確認
        user_count = await user_service.get_user_count()
        assert user_count == len(discord_ids)
        
        # 全ユーザーの取得
        all_users = await user_service.get_all_users()
        assert len(all_users) == len(discord_ids)
        
        # 各ユーザーに異なる設定を適用
        for i, discord_id in enumerate(discord_ids):
            area_code = f"13000{i}"
            area_name = f"テスト地域{i}"
            notification_hour = (i * 3) % 24
            
            # 位置情報設定
            await user_service.set_user_location(discord_id, area_code, area_name)
            
            # 通知設定（偶数番目のユーザーのみ）
            if i % 2 == 0:
                await user_service.set_notification_schedule(discord_id, notification_hour)
        
        # 通知有効ユーザーの取得
        notification_users = await user_service.get_users_with_notifications()
        expected_notification_count = len([i for i in range(len(discord_ids)) if i % 2 == 0])
        assert len(notification_users) == expected_notification_count
        
        # 特定時間の通知ユーザー取得
        specific_hour_users = await user_service.get_users_with_notifications(0)
        assert len(specific_hour_users) <= expected_notification_count
        
        # クリーンアップ
        for discord_id in discord_ids:
            await user_service.delete_user(discord_id)
    
    @pytest.mark.asyncio
    async def test_user_settings_comprehensive(self, test_db_setup, user_service):
        """ユーザー設定の包括的統合テスト"""
        discord_id = 987654321
        
        # ユーザー作成
        user = await user_service.create_user(discord_id)
        assert user is not None
        
        # 初期設定の確認
        initial_settings = await user_service.get_user_settings(discord_id)
        assert initial_settings is not None
        assert initial_settings['discord_id'] == discord_id
        assert initial_settings['area_code'] is None
        assert initial_settings['area_name'] is None
        assert initial_settings['notification_hour'] is None
        assert initial_settings['is_notification_enabled'] is False
        assert initial_settings['has_location'] is False
        assert initial_settings['has_notification_enabled'] is False
        
        # 位置情報設定
        area_code = "270000"
        area_name = "大阪府"
        await user_service.set_user_location(discord_id, area_code, area_name)
        
        # 位置情報設定後の確認
        location_settings = await user_service.get_user_settings(discord_id)
        assert location_settings['area_code'] == area_code
        assert location_settings['area_name'] == area_name
        assert location_settings['has_location'] is True
        
        # 位置情報の直接取得
        location = await user_service.get_user_location(discord_id)
        assert location == (area_code, area_name)
        
        # 通知設定
        notification_hour = 15
        await user_service.set_notification_schedule(discord_id, notification_hour)
        
        # 通知設定後の確認
        notification_settings = await user_service.get_user_settings(discord_id)
        assert notification_settings['notification_hour'] == notification_hour
        assert notification_settings['is_notification_enabled'] is True
        assert notification_settings['has_notification_enabled'] is True
        
        # 通知無効化
        await user_service.disable_notifications(discord_id)
        
        # 通知無効化後の確認
        disabled_settings = await user_service.get_user_settings(discord_id)
        assert disabled_settings['is_notification_enabled'] is False
        assert disabled_settings['has_notification_enabled'] is False
        
        # クリーンアップ
        await user_service.delete_user(discord_id)
    
    @pytest.mark.asyncio
    async def test_data_integrity_validation(self, test_db_setup, user_service):
        """データ整合性検証の統合テスト"""
        # 正常なユーザーを作成
        normal_users = []
        for i in range(5):
            discord_id = 100000 + i
            user = await user_service.create_user(discord_id)
            await user_service.set_user_location(discord_id, f"13000{i}", f"地域{i}")
            await user_service.set_notification_schedule(discord_id, (i * 4) % 24)
            normal_users.append(user)
        
        # データ整合性チェック
        integrity_result = await user_service.validate_data_integrity()
        
        assert integrity_result['status'] in ['healthy', 'warning']
        assert isinstance(integrity_result['checks'], list)
        assert isinstance(integrity_result['errors'], list)
        assert isinstance(integrity_result['warnings'], list)
        
        # 正常な状態では重大なエラーがないことを確認
        assert len(integrity_result['errors']) == 0
        
        # チェック項目が実行されていることを確認
        check_names = [check['name'] for check in integrity_result['checks']]
        expected_checks = [
            'duplicate_discord_id_check',
            'notification_hour_check',
            'notification_consistency_check',
            'old_data_check',
            'total_user_count'
        ]
        
        for expected_check in expected_checks:
            assert expected_check in check_names
        
        # クリーンアップ
        for user in normal_users:
            await user_service.delete_user(user.discord_id)
    
    @pytest.mark.asyncio
    async def test_service_health_check(self, test_db_setup, user_service):
        """サービスヘルスチェックの統合テスト"""
        # テストユーザーを作成
        test_users = []
        for i in range(3):
            discord_id = 200000 + i
            user = await user_service.create_user(discord_id)
            if i % 2 == 0:  # 偶数番目のユーザーに通知設定
                await user_service.set_notification_schedule(discord_id, 10)
            test_users.append(user)
        
        # ヘルスチェック実行
        health_info = await user_service.get_service_health()
        
        # 基本的な構造の確認
        assert 'service_name' in health_info
        assert 'timestamp' in health_info
        assert 'database_status' in health_info
        assert 'user_count' in health_info
        assert 'notification_enabled_users' in health_info
        assert 'overall_status' in health_info
        
        # 値の確認
        assert health_info['service_name'] == 'UserService'
        assert health_info['user_count'] >= 3
        assert health_info['notification_enabled_users'] >= 1
        assert health_info['overall_status'] in ['healthy', 'warning', 'error']
        
        # データベース状態の確認
        assert 'database_details' in health_info
        assert isinstance(health_info['database_details'], dict)
        
        # データ整合性情報の確認
        assert 'data_integrity' in health_info
        assert isinstance(health_info['data_integrity'], dict)
        
        # クリーンアップ
        for user in test_users:
            await user_service.delete_user(user.discord_id)
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, test_db_setup, user_service):
        """並行操作の統合テスト"""
        discord_ids = [300000 + i for i in range(10)]
        
        # 並行でユーザー作成
        create_tasks = [user_service.create_user(discord_id) for discord_id in discord_ids]
        created_users = await asyncio.gather(*create_tasks, return_exceptions=True)
        
        # 例外が発生していないことを確認
        successful_users = []
        for result in created_users:
            if not isinstance(result, Exception):
                successful_users.append(result)
        
        assert len(successful_users) == len(discord_ids)
        
        # 並行で位置情報設定
        location_tasks = [
            user_service.set_user_location(discord_id, f"13000{i%5}", f"地域{i%5}")
            for i, discord_id in enumerate(discord_ids)
        ]
        location_results = await asyncio.gather(*location_tasks, return_exceptions=True)
        
        # 並行で通知設定
        notification_tasks = [
            user_service.set_notification_schedule(discord_id, (i * 2) % 24)
            for i, discord_id in enumerate(discord_ids)
        ]
        notification_results = await asyncio.gather(*notification_tasks, return_exceptions=True)
        
        # 結果の確認
        successful_locations = [r for r in location_results if r is True]
        successful_notifications = [r for r in notification_results if r is True]
        
        assert len(successful_locations) == len(discord_ids)
        assert len(successful_notifications) == len(discord_ids)
        
        # 並行でユーザー取得
        get_tasks = [user_service.get_user_by_discord_id(discord_id) for discord_id in discord_ids]
        retrieved_users = await asyncio.gather(*get_tasks, return_exceptions=True)
        
        # 取得されたユーザーの確認
        valid_users = [u for u in retrieved_users if u is not None and not isinstance(u, Exception)]
        assert len(valid_users) == len(discord_ids)
        
        # クリーンアップ
        delete_tasks = [user_service.delete_user(discord_id) for discord_id in discord_ids]
        await asyncio.gather(*delete_tasks, return_exceptions=True)
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, test_db_setup, user_service):
        """エラーハンドリングの統合テスト"""
        discord_id = 400000
        
        # 存在しないユーザーの操作
        nonexistent_user = await user_service.get_user_by_discord_id(999999)
        assert nonexistent_user is None
        
        nonexistent_location = await user_service.get_user_location(999999)
        assert nonexistent_location is None
        
        nonexistent_settings = await user_service.get_user_settings(999999)
        assert nonexistent_settings is None
        
        # 無効な通知時間
        user = await user_service.create_user(discord_id)
        assert user is not None
        
        invalid_hour_result = await user_service.set_notification_schedule(discord_id, 25)
        assert invalid_hour_result is False
        
        invalid_negative_hour = await user_service.set_notification_schedule(discord_id, -1)
        assert invalid_negative_hour is False
        
        # 重複ユーザー作成の試行
        duplicate_user = await user_service.create_user(discord_id)
        assert duplicate_user is not None  # 既存ユーザーが返される
        assert duplicate_user.discord_id == discord_id
        
        # クリーンアップ
        await user_service.delete_user(discord_id)
    
    @pytest.mark.asyncio
    async def test_database_connection_recovery(self, test_db_setup, user_service):
        """データベース接続回復の統合テスト"""
        discord_id = 500000
        
        # 正常な操作
        user = await user_service.create_user(discord_id)
        assert user is not None
        
        # データベース接続を一時的に無効化（モック）
        with patch('src.services.user_service.get_db_session') as mock_session:
            mock_session.side_effect = DatabaseConnectionError("Connection lost")
            
            # メモリストレージが有効でない場合、操作は失敗する
            if not user_service._use_memory_storage():
                failed_user = await user_service.create_user(discord_id + 1)
                assert failed_user is None
        
        # 接続回復後の操作
        recovered_user = await user_service.get_user_by_discord_id(discord_id)
        assert recovered_user is not None
        assert recovered_user.discord_id == discord_id
        
        # クリーンアップ
        await user_service.delete_user(discord_id)
    
    @pytest.mark.asyncio
    async def test_user_timestamps(self, test_db_setup, user_service):
        """ユーザータイムスタンプの統合テスト"""
        discord_id = 600000
        
        # ユーザー作成
        creation_time = datetime.now()
        user = await user_service.create_user(discord_id)
        assert user is not None
        
        # 作成時刻の確認
        assert user.created_at is not None
        assert user.updated_at is not None
        assert abs((user.created_at - creation_time).total_seconds()) < 5  # 5秒以内
        
        # 更新操作
        await asyncio.sleep(1)  # 1秒待機
        update_time = datetime.now()
        await user_service.set_user_location(discord_id, "130000", "東京都")
        
        # 更新後のタイムスタンプ確認
        updated_user = await user_service.get_user_by_discord_id(discord_id)
        assert updated_user.updated_at > user.updated_at
        assert abs((updated_user.updated_at - update_time).total_seconds()) < 5
        
        # 作成時刻は変更されない
        assert updated_user.created_at == user.created_at
        
        # クリーンアップ
        await user_service.delete_user(discord_id)


if __name__ == "__main__":
    # 統合テストのみを実行
    pytest.main([__file__, "-v", "-m", "integration"])