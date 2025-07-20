"""通知スケジュール管理機能の詳細テスト"""

import asyncio
import os
import tempfile

from src.database import DatabaseManager, init_database, close_database
from src.services.user_service import UserService


class TestNotificationScheduleManagement:
    """通知スケジュール管理機能のテストクラス"""
    
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
        from src.database import db_manager
        await db_manager.drop_tables()
        await close_database()
    
    async def test_hourly_notification_schedule_setting(self):
        """1時間単位での通知時間設定機能のテスト（要件5.1対応）"""
        discord_id = 123456789
        
        # 0時から23時まで全ての時間で設定をテスト
        for hour in range(24):
            result = await self.user_service.set_notification_schedule(discord_id, hour)
            assert result is True, f"時間 {hour} の設定に失敗"
            
            # 設定が正しく保存されたことを確認
            user = await self.user_service.get_user_by_discord_id(discord_id)
            assert user is not None
            assert user.notification_hour == hour
            assert user.is_notification_enabled is True
            
            print(f"✓ {hour}時の通知設定が正常に動作")
        
        # 無効な時間での設定テスト
        invalid_hours = [-1, 24, 25, 100]
        for invalid_hour in invalid_hours:
            result = await self.user_service.set_notification_schedule(discord_id, invalid_hour)
            assert result is False, f"無効な時間 {invalid_hour} で設定が成功してしまった"
            print(f"✓ 無効な時間 {invalid_hour} が正しく拒否された")
    
    async def test_notification_enable_disable_functionality(self):
        """通知の有効化・無効化機能のテスト（要件5.1, 5.3対応）"""
        discord_id = 987654321
        
        # 初期状態では通知が無効であることを確認
        user = await self.user_service.get_user_by_discord_id(discord_id)
        if user is None:
            await self.user_service.create_user(discord_id)
            user = await self.user_service.get_user_by_discord_id(discord_id)
        
        assert user.is_notification_enabled is False
        assert user.notification_hour is None
        assert user.has_notification_enabled() is False
        print("✓ 初期状態で通知が無効であることを確認")
        
        # 通知を有効化
        result = await self.user_service.set_notification_schedule(discord_id, 9)
        assert result is True
        
        user = await self.user_service.get_user_by_discord_id(discord_id)
        assert user.is_notification_enabled is True
        assert user.notification_hour == 9
        assert user.has_notification_enabled() is True
        print("✓ 通知の有効化が正常に動作")
        
        # 通知を無効化
        result = await self.user_service.disable_notifications(discord_id)
        assert result is True
        
        user = await self.user_service.get_user_by_discord_id(discord_id)
        assert user.is_notification_enabled is False
        assert user.notification_hour is None
        assert user.has_notification_enabled() is False
        print("✓ 通知の無効化が正常に動作")
        
        # 再度有効化
        result = await self.user_service.set_notification_schedule(discord_id, 18)
        assert result is True
        
        user = await self.user_service.get_user_by_discord_id(discord_id)
        assert user.is_notification_enabled is True
        assert user.notification_hour == 18
        assert user.has_notification_enabled() is True
        print("✓ 通知の再有効化が正常に動作")
    
    async def test_user_settings_display_functionality(self):
        """ユーザー設定の表示機能のテスト（要件5.3対応）"""
        discord_id = 111222333
        area_code = "130010"
        area_name = "東京都東京"
        notification_hour = 8
        
        # ユーザーを作成し、各種設定を行う
        await self.user_service.create_user(discord_id)
        await self.user_service.set_user_location(discord_id, area_code, area_name)
        await self.user_service.set_notification_schedule(discord_id, notification_hour)
        
        # 設定情報を取得
        settings = await self.user_service.get_user_settings(discord_id)
        
        # 全ての設定項目が正しく表示されることを確認
        assert settings is not None
        assert settings['discord_id'] == discord_id
        assert settings['area_code'] == area_code
        assert settings['area_name'] == area_name
        assert settings['notification_hour'] == notification_hour
        assert settings['is_notification_enabled'] is True
        assert settings['has_location'] is True
        assert settings['has_notification_enabled'] is True
        assert settings['timezone'] == 'Asia/Tokyo'  # デフォルト値
        assert 'created_at' in settings
        assert 'updated_at' in settings
        
        print("✓ ユーザー設定の表示機能が正常に動作")
        
        # 通知を無効化した場合の設定表示
        await self.user_service.disable_notifications(discord_id)
        settings_disabled = await self.user_service.get_user_settings(discord_id)
        
        assert settings_disabled['is_notification_enabled'] is False
        assert settings_disabled['notification_hour'] is None
        assert settings_disabled['has_notification_enabled'] is False
        # 位置情報は保持されている
        assert settings_disabled['has_location'] is True
        assert settings_disabled['area_code'] == area_code
        
        print("✓ 通知無効化後の設定表示が正常に動作")
    
    async def test_multiple_users_notification_management(self):
        """複数ユーザーの通知管理テスト"""
        users_data = [
            (444555666, 7, "北海道札幌", "016010"),
            (777888999, 12, "大阪府大阪", "270000"),
            (101112131, 19, "福岡県福岡", "400010"),
            (141516171, 22, "沖縄県那覇", "471010"),
        ]
        
        # 複数ユーザーの通知設定
        for discord_id, hour, area_name, area_code in users_data:
            await self.user_service.create_user(discord_id)
            await self.user_service.set_user_location(discord_id, area_code, area_name)
            await self.user_service.set_notification_schedule(discord_id, hour)
        
        # 各時間帯の通知ユーザーを取得
        for discord_id, hour, area_name, area_code in users_data:
            hour_users = await self.user_service.get_users_with_notifications(hour)
            assert len(hour_users) == 1
            assert hour_users[0].discord_id == discord_id
            assert hour_users[0].notification_hour == hour
            print(f"✓ {hour}時の通知ユーザー取得が正常に動作")
        
        # 全通知ユーザーの取得
        all_notification_users = await self.user_service.get_users_with_notifications()
        assert len(all_notification_users) == len(users_data)
        print("✓ 全通知ユーザーの取得が正常に動作")
        
        # 一部のユーザーの通知を無効化
        await self.user_service.disable_notifications(users_data[0][0])
        await self.user_service.disable_notifications(users_data[2][0])
        
        # 通知有効ユーザー数の確認
        remaining_users = await self.user_service.get_users_with_notifications()
        assert len(remaining_users) == len(users_data) - 2
        print("✓ 一部ユーザーの通知無効化が正常に動作")
    
    async def test_notification_schedule_edge_cases(self):
        """通知スケジュールのエッジケーステスト"""
        discord_id = 181920212
        
        # 存在しないユーザーに対する通知設定（自動でユーザー作成される）
        result = await self.user_service.set_notification_schedule(discord_id, 10)
        assert result is True
        
        user = await self.user_service.get_user_by_discord_id(discord_id)
        assert user is not None
        assert user.notification_hour == 10
        print("✓ 存在しないユーザーへの通知設定で自動ユーザー作成が動作")
        
        # 同じ時間での重複設定
        result = await self.user_service.set_notification_schedule(discord_id, 10)
        assert result is True
        
        user = await self.user_service.get_user_by_discord_id(discord_id)
        assert user.notification_hour == 10
        print("✓ 同じ時間での重複設定が正常に動作")
        
        # 時間の変更
        result = await self.user_service.set_notification_schedule(discord_id, 15)
        assert result is True
        
        user = await self.user_service.get_user_by_discord_id(discord_id)
        assert user.notification_hour == 15
        print("✓ 通知時間の変更が正常に動作")
        
        # 存在しないユーザーの通知無効化
        non_existent_id = 999999999
        result = await self.user_service.disable_notifications(non_existent_id)
        assert result is False
        print("✓ 存在しないユーザーの通知無効化が正しく失敗")


async def run_notification_tests():
    """通知スケジュール管理テストを実行する関数"""
    test_instance = TestNotificationScheduleManagement()
    test_instance.setup_class()
    
    try:
        # 各テストメソッドを実行
        test_methods = [
            test_instance.test_hourly_notification_schedule_setting,
            test_instance.test_notification_enable_disable_functionality,
            test_instance.test_user_settings_display_functionality,
            test_instance.test_multiple_users_notification_management,
            test_instance.test_notification_schedule_edge_cases,
        ]
        
        for test_method in test_methods:
            print(f"\n実行中: {test_method.__name__}")
            await test_instance.setup_method()
            try:
                await test_method()
                print(f"✓ {test_method.__name__} - 成功")
            except Exception as e:
                print(f"✗ {test_method.__name__} - 失敗: {e}")
                raise
            finally:
                await test_instance.teardown_method()
        
        print("\n全ての通知スケジュール管理テストが成功しました！")
        print("\n要件5.1（定時通知設定）と要件5.3（通知設定変更）が正しく実装されています。")
        
    finally:
        test_instance.teardown_class()


if __name__ == "__main__":
    asyncio.run(run_notification_tests())