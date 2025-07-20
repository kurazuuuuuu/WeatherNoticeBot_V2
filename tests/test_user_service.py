"""ユーザーサービスのテスト"""

import asyncio
import os
import tempfile
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from src.database import DatabaseManager, init_database, close_database
from src.models.user import User
from src.services.user_service import UserService


class TestUserService:
    """ユーザーサービスのテストクラス"""
    
    @classmethod
    def setup_class(cls):
        """テストクラスのセットアップ"""
        # テスト用の一時データベースファイルを作成
        cls.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        cls.temp_db.close()
        cls.test_db_url = f"sqlite:///{cls.temp_db.name}"
        
        # テスト用のデータベースマネージャーを設定
        from src.database import db_manager
        db_manager.database_url = cls.test_db_url
        
        # ユーザーサービスのインスタンスを作成
        cls.user_service = UserService()
    
    @classmethod
    def teardown_class(cls):
        """テストクラスのクリーンアップ"""
        # 一時データベースファイルを削除
        if os.path.exists(cls.temp_db.name):
            os.unlink(cls.temp_db.name)
    
    async def setup_method(self):
        """各テストメソッドの前に実行"""
        await init_database()
    
    async def teardown_method(self):
        """各テストメソッドの後に実行"""
        # データベースのテーブルをドロップしてクリーンアップ
        from src.database import db_manager
        await db_manager.drop_tables()
        await close_database()
    
    async def test_create_user(self):
        """ユーザー作成のテスト"""
        discord_id = 123456789
        
        # ユーザーを作成
        user = await self.user_service.create_user(discord_id)
        
        assert user is not None
        assert user.discord_id == discord_id
        assert user.area_code is None
        assert user.area_name is None
        assert user.is_notification_enabled is False
        
        # 同じDiscord IDで再度作成を試行（既存ユーザーが返される）
        existing_user = await self.user_service.create_user(discord_id)
        assert existing_user is not None
        assert existing_user.discord_id == discord_id
    
    async def test_get_user_by_discord_id(self):
        """Discord IDでのユーザー取得テスト"""
        discord_id = 987654321
        
        # 存在しないユーザーの取得
        user = await self.user_service.get_user_by_discord_id(discord_id)
        assert user is None
        
        # ユーザーを作成
        created_user = await self.user_service.create_user(discord_id)
        assert created_user is not None
        
        # 作成したユーザーを取得
        retrieved_user = await self.user_service.get_user_by_discord_id(discord_id)
        assert retrieved_user is not None
        assert retrieved_user.discord_id == discord_id
    
    async def test_set_user_location(self):
        """ユーザー位置情報設定のテスト"""
        discord_id = 111222333
        area_code = "130010"
        area_name = "東京都東京"
        
        # 位置情報を設定
        result = await self.user_service.set_user_location(discord_id, area_code, area_name)
        assert result is True
        
        # 設定された位置情報を確認
        user = await self.user_service.get_user_by_discord_id(discord_id)
        assert user is not None
        assert user.area_code == area_code
        assert user.area_name == area_name
        assert user.has_location() is True
    
    async def test_get_user_location(self):
        """ユーザー位置情報取得のテスト"""
        discord_id = 444555666
        area_code = "270000"
        area_name = "大阪府"
        
        # 位置情報が設定されていない場合
        location = await self.user_service.get_user_location(discord_id)
        assert location is None
        
        # 位置情報を設定
        await self.user_service.set_user_location(discord_id, area_code, area_name)
        
        # 位置情報を取得
        location = await self.user_service.get_user_location(discord_id)
        assert location is not None
        assert location[0] == area_code
        assert location[1] == area_name
    
    async def test_set_notification_schedule(self):
        """通知スケジュール設定のテスト"""
        discord_id = 777888999
        hour = 9
        
        # 通知スケジュールを設定
        result = await self.user_service.set_notification_schedule(discord_id, hour)
        assert result is True
        
        # 設定された通知スケジュールを確認
        user = await self.user_service.get_user_by_discord_id(discord_id)
        assert user is not None
        assert user.notification_hour == hour
        assert user.is_notification_enabled is True
        assert user.has_notification_enabled() is True
        
        # 無効な時間での設定テスト
        invalid_result = await self.user_service.set_notification_schedule(discord_id, 25)
        assert invalid_result is False
        
        invalid_result = await self.user_service.set_notification_schedule(discord_id, -1)
        assert invalid_result is False
    
    async def test_disable_notifications(self):
        """通知無効化のテスト"""
        discord_id = 101112131
        
        # 通知スケジュールを設定
        await self.user_service.set_notification_schedule(discord_id, 10)
        
        # 通知を無効化
        result = await self.user_service.disable_notifications(discord_id)
        assert result is True
        
        # 無効化されたことを確認
        user = await self.user_service.get_user_by_discord_id(discord_id)
        assert user is not None
        assert user.is_notification_enabled is False
        assert user.notification_hour is None
        assert user.has_notification_enabled() is False
    
    async def test_get_user_settings(self):
        """ユーザー設定取得のテスト"""
        discord_id = 141516171
        area_code = "130010"
        area_name = "東京都東京"
        hour = 8
        
        # 存在しないユーザーの設定取得
        settings = await self.user_service.get_user_settings(discord_id)
        assert settings is None
        
        # ユーザーを作成し、設定を行う
        await self.user_service.create_user(discord_id)
        await self.user_service.set_user_location(discord_id, area_code, area_name)
        await self.user_service.set_notification_schedule(discord_id, hour)
        
        # 設定を取得
        settings = await self.user_service.get_user_settings(discord_id)
        assert settings is not None
        assert settings['discord_id'] == discord_id
        assert settings['area_code'] == area_code
        assert settings['area_name'] == area_name
        assert settings['notification_hour'] == hour
        assert settings['is_notification_enabled'] is True
        assert settings['has_location'] is True
        assert settings['has_notification_enabled'] is True
    
    async def test_get_users_with_notifications(self):
        """通知有効ユーザー取得のテスト"""
        # テスト用ユーザーを作成
        users_data = [
            (181920212, 9),   # 9時通知
            (222324252, 9),   # 9時通知
            (262728293, 18),  # 18時通知
            (303132333, None) # 通知無効
        ]
        
        for discord_id, hour in users_data:
            await self.user_service.create_user(discord_id)
            if hour is not None:
                await self.user_service.set_notification_schedule(discord_id, hour)
        
        # 全ての通知有効ユーザーを取得
        all_notification_users = await self.user_service.get_users_with_notifications()
        notification_count = len([u for u in users_data if u[1] is not None])
        print(f"実際の通知有効ユーザー数: {len(all_notification_users)}, 期待値: {notification_count}")
        assert len(all_notification_users) == notification_count
        
        # 9時通知のユーザーのみを取得
        hour_9_users = await self.user_service.get_users_with_notifications(9)
        hour_9_count = len([u for u in users_data if u[1] == 9])
        assert len(hour_9_users) == hour_9_count
        
        # 18時通知のユーザーのみを取得
        hour_18_users = await self.user_service.get_users_with_notifications(18)
        hour_18_count = len([u for u in users_data if u[1] == 18])
        assert len(hour_18_users) == hour_18_count
        
        # 存在しない時間での取得
        hour_12_users = await self.user_service.get_users_with_notifications(12)
        assert len(hour_12_users) == 0
    
    async def test_update_user(self):
        """ユーザー情報更新のテスト"""
        discord_id = 343536373
        
        # ユーザーを作成
        await self.user_service.create_user(discord_id)
        
        # ユーザー情報を更新
        result = await self.user_service.update_user(
            discord_id,
            area_code="470010",
            area_name="沖縄県那覇",
            timezone="Asia/Tokyo"
        )
        assert result is True
        
        # 更新されたことを確認
        user = await self.user_service.get_user_by_discord_id(discord_id)
        assert user is not None
        assert user.area_code == "470010"
        assert user.area_name == "沖縄県那覇"
        assert user.timezone == "Asia/Tokyo"
    
    async def test_delete_user(self):
        """ユーザー削除のテスト"""
        discord_id = 383940414
        
        # ユーザーを作成
        await self.user_service.create_user(discord_id)
        
        # ユーザーが存在することを確認
        user = await self.user_service.get_user_by_discord_id(discord_id)
        assert user is not None
        
        # ユーザーを削除
        result = await self.user_service.delete_user(discord_id)
        assert result is True
        
        # ユーザーが削除されたことを確認
        deleted_user = await self.user_service.get_user_by_discord_id(discord_id)
        assert deleted_user is None
    
    async def test_get_user_count(self):
        """ユーザー数取得のテスト"""
        # 初期状態のユーザー数
        initial_count = await self.user_service.get_user_count()
        
        # ユーザーを追加
        test_users = [424344454, 464748495, 505152535]
        for discord_id in test_users:
            await self.user_service.create_user(discord_id)
        
        # ユーザー数が増加したことを確認
        final_count = await self.user_service.get_user_count()
        assert final_count == initial_count + len(test_users)


async def run_tests():
    """テストを実行する関数"""
    test_instance = TestUserService()
    test_instance.setup_class()
    
    try:
        # 各テストメソッドを実行
        test_methods = [
            test_instance.test_create_user,
            test_instance.test_get_user_by_discord_id,
            test_instance.test_set_user_location,
            test_instance.test_get_user_location,
            test_instance.test_set_notification_schedule,
            test_instance.test_disable_notifications,
            test_instance.test_get_user_settings,
            test_instance.test_get_users_with_notifications,
            test_instance.test_update_user,
            test_instance.test_delete_user,
            test_instance.test_get_user_count,
        ]
        
        for test_method in test_methods:
            print(f"実行中: {test_method.__name__}")
            await test_instance.setup_method()
            try:
                await test_method()
                print(f"✓ {test_method.__name__} - 成功")
            except Exception as e:
                print(f"✗ {test_method.__name__} - 失敗: {e}")
                raise
            finally:
                await test_instance.teardown_method()
        
        print("\n全てのテストが成功しました！")
        
    finally:
        test_instance.teardown_class()


if __name__ == "__main__":
    asyncio.run(run_tests())