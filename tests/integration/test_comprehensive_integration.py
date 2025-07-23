"""
包括的統合テスト

全システムコンポーネントの統合テストを実行します。
実際のAPI、データベース、AIサービスを組み合わせたエンドツーエンドテストです。
"""

import pytest
import asyncio
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# テスト対象のインポート（モック化対応）
try:
    from src.services.weather_service import WeatherService
    from src.services.user_service import UserService
    from src.services.ai_service import AIMessageService, WeatherContext
    from src.config import Config
    from src.database import db_manager
except ImportError:
    # 依存関係が不足している場合はスキップ
    pytest.skip("Integration test dependencies not available", allow_module_level=True)


@pytest.mark.integration
@pytest.mark.slow
class TestComprehensiveIntegration:
    """包括的統合テストクラス"""
    
    @pytest.fixture(scope="class")
    async def test_environment_setup(self):
        """テスト環境の包括的セットアップ"""
        # テスト用データベース
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        # 環境変数の設定
        original_env = {}
        test_env = {
            'DATABASE_URL': f'sqlite:///{temp_db.name}',
            'TESTING': 'true',
            'LOG_LEVEL': 'ERROR'
        }
        
        for key, value in test_env.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        try:
            # データベース初期化
            await db_manager.initialize()
            
            yield {
                'db_path': temp_db.name,
                'original_env': original_env
            }
        finally:
            # クリーンアップ
            await db_manager.close()
            
            # 環境変数復元
            for key, value in original_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            
            # 一時ファイル削除
            try:
                os.unlink(temp_db.name)
            except OSError:
                pass
    
    @pytest.fixture
    def config(self):
        """テスト用設定"""
        config = Config()
        # 実際のAPIキーがある場合は使用、なければモック
        config.GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'mock_key')
        return config
    
    @pytest.fixture
    def services(self, config):
        """サービスインスタンス"""
        return {
            'weather': WeatherService(),
            'user': UserService(),
            'ai': AIMessageService(config)
        }
    
    @pytest.mark.asyncio
    async def test_complete_user_weather_flow(self, test_environment_setup, services):
        """完全なユーザー天気情報フローの統合テスト"""
        weather_service = services['weather']
        user_service = services['user']
        ai_service = services['ai']
        
        discord_id = 123456789
        
        try:
            # 1. ユーザー作成
            user = await user_service.create_user(discord_id)
            assert user is not None
            assert user.discord_id == discord_id
            
            # 2. 地域検索と設定
            async with weather_service:
                # 地域検索
                search_results = await weather_service.search_area_by_name("東京")
                if not search_results:
                    pytest.skip("地域検索結果が取得できませんでした")
                
                area_info = search_results[0]
                area_code = area_info.code
                area_name = area_info.name
                
                # ユーザーに位置情報を設定
                location_result = await user_service.set_user_location(
                    discord_id, area_code, area_name
                )
                assert location_result is True
                
                # 3. 天気情報取得
                current_weather = await weather_service.get_current_weather(area_code)
                if current_weather:
                    assert current_weather.area_code == area_code
                    assert isinstance(current_weather.weather_description, str)
                    
                    # 4. AIメッセージ生成
                    weather_context = WeatherContext(
                        area_name=current_weather.area_name,
                        weather_description=current_weather.weather_description,
                        temperature=current_weather.temperature,
                        precipitation_probability=current_weather.precipitation_probability,
                        wind=current_weather.wind,
                        timestamp=current_weather.timestamp
                    )
                    
                    # AIメッセージ生成（フォールバック含む）
                    ai_message = await ai_service.generate_positive_message(weather_context)
                    assert isinstance(ai_message, str)
                    assert len(ai_message) > 0
                    
                    print(f"Generated AI message: {ai_message}")
                
                # 5. 天気予報取得
                forecast = await weather_service.get_forecast(area_code, 3)
                if forecast:
                    assert isinstance(forecast, list)
                    assert len(forecast) <= 3
                    
                    for f in forecast:
                        assert isinstance(f.weather_description, str)
                        assert 0 <= f.precipitation_probability <= 100
            
            # 6. 通知設定
            notification_result = await user_service.set_notification_schedule(discord_id, 9)
            assert notification_result is True
            
            # 7. ユーザー設定確認
            user_settings = await user_service.get_user_settings(discord_id)
            assert user_settings is not None
            assert user_settings['has_location'] is True
            assert user_settings['has_notification_enabled'] is True
            assert user_settings['area_code'] == area_code
            assert user_settings['notification_hour'] == 9
            
            # 8. 通知有効ユーザーリスト確認
            notification_users = await user_service.get_users_with_notifications(9)
            user_found = any(u.discord_id == discord_id for u in notification_users)
            assert user_found is True
            
        except Exception as e:
            pytest.fail(f"Complete user weather flow failed: {e}")
        finally:
            # クリーンアップ
            await user_service.delete_user(discord_id)
    
    @pytest.mark.asyncio
    async def test_multiple_users_concurrent_operations(self, test_environment_setup, services):
        """複数ユーザーの並行操作統合テスト"""
        user_service = services['user']
        weather_service = services['weather']
        
        discord_ids = [200000 + i for i in range(5)]
        
        try:
            # 1. 並行ユーザー作成
            create_tasks = [user_service.create_user(discord_id) for discord_id in discord_ids]
            created_users = await asyncio.gather(*create_tasks, return_exceptions=True)
            
            successful_users = [u for u in created_users if not isinstance(u, Exception)]
            assert len(successful_users) == len(discord_ids)
            
            # 2. 地域情報取得
            async with weather_service:
                search_results = await weather_service.search_area_by_name("東京")
                if not search_results:
                    pytest.skip("地域検索結果が取得できませんでした")
                
                area_code = search_results[0].code
                area_name = search_results[0].name
                
                # 3. 並行位置情報設定
                location_tasks = [
                    user_service.set_user_location(discord_id, area_code, area_name)
                    for discord_id in discord_ids
                ]
                location_results = await asyncio.gather(*location_tasks, return_exceptions=True)
                
                successful_locations = [r for r in location_results if r is True]
                assert len(successful_locations) == len(discord_ids)
                
                # 4. 並行通知設定
                notification_tasks = [
                    user_service.set_notification_schedule(discord_id, (i * 2) % 24)
                    for i, discord_id in enumerate(discord_ids)
                ]
                notification_results = await asyncio.gather(*notification_tasks, return_exceptions=True)
                
                successful_notifications = [r for r in notification_results if r is True]
                assert len(successful_notifications) == len(discord_ids)
                
                # 5. 並行ユーザー設定取得
                settings_tasks = [
                    user_service.get_user_settings(discord_id)
                    for discord_id in discord_ids
                ]
                settings_results = await asyncio.gather(*settings_tasks, return_exceptions=True)
                
                valid_settings = [s for s in settings_results if s is not None and not isinstance(s, Exception)]
                assert len(valid_settings) == len(discord_ids)
                
                # 6. 全ユーザーの設定確認
                for settings in valid_settings:
                    assert settings['has_location'] is True
                    assert settings['has_notification_enabled'] is True
                    assert settings['area_code'] == area_code
            
        except Exception as e:
            pytest.fail(f"Multiple users concurrent operations failed: {e}")
        finally:
            # クリーンアップ
            delete_tasks = [user_service.delete_user(discord_id) for discord_id in discord_ids]
            await asyncio.gather(*delete_tasks, return_exceptions=True)
    
    @pytest.mark.asyncio
    async def test_weather_ai_integration_comprehensive(self, test_environment_setup, services):
        """天気情報とAI統合の包括的テスト"""
        weather_service = services['weather']
        ai_service = services['ai']
        
        try:
            async with weather_service:
                # 複数地域での天気情報取得とAIメッセージ生成
                cities = ["東京", "大阪", "名古屋"]
                
                for city in cities:
                    # 地域検索
                    search_results = await weather_service.search_area_by_name(city)
                    if not search_results:
                        continue
                    
                    area_code = search_results[0].code
                    
                    # 現在の天気取得
                    current_weather = await weather_service.get_current_weather(area_code)
                    if not current_weather:
                        continue
                    
                    # WeatherContextに変換
                    weather_context = WeatherContext(
                        area_name=current_weather.area_name,
                        weather_description=current_weather.weather_description,
                        temperature=current_weather.temperature,
                        precipitation_probability=current_weather.precipitation_probability,
                        wind=current_weather.wind,
                        timestamp=current_weather.timestamp
                    )
                    
                    # 各種メッセージタイプでAI生成
                    message_types = ["general", "morning", "evening"]
                    
                    for msg_type in message_types:
                        ai_message = await ai_service.generate_positive_message(
                            weather_context, msg_type
                        )
                        
                        assert isinstance(ai_message, str)
                        assert len(ai_message) > 0
                        
                        # 地域名が含まれていることを確認
                        area_name_base = current_weather.area_name.replace("都", "").replace("府", "").replace("県", "")
                        assert (area_name_base in ai_message or 
                               current_weather.area_name in ai_message)
                        
                        print(f"{city} {msg_type}: {ai_message}")
                        
                        # レート制限を避けるため待機
                        await asyncio.sleep(1)
                    
                    # 要約メッセージ生成
                    summary = await ai_service.generate_weather_summary_message(weather_context)
                    assert isinstance(summary, str)
                    assert len(summary) > 0
                    
                    print(f"{city} summary: {summary}")
                    
                    # 天気予報取得
                    forecast = await weather_service.get_forecast(area_code, 3)
                    if forecast:
                        print(f"{city} forecast: {len(forecast)} days")
                        for i, f in enumerate(forecast):
                            print(f"  Day {i+1}: {f.weather_description} ({f.precipitation_probability}%)")
                    
                    # API制限を避けるため待機
                    await asyncio.sleep(2)
                    
        except Exception as e:
            pytest.fail(f"Weather AI integration test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_error_recovery_and_fallback(self, test_environment_setup, services):
        """エラー回復とフォールバック機能の統合テスト"""
        weather_service = services['weather']
        user_service = services['user']
        ai_service = services['ai']
        
        discord_id = 300000
        
        try:
            # 1. 正常なユーザー作成
            user = await user_service.create_user(discord_id)
            assert user is not None
            
            # 2. 無効な地域コードでのエラーハンドリング
            try:
                async with weather_service:
                    await weather_service.get_current_weather("invalid")
                    pytest.fail("Invalid area code should raise an error")
            except Exception:
                # エラーが発生することを期待
                pass
            
            # 3. AIサービスのフォールバック機能
            weather_context = WeatherContext(
                area_name="テスト地域",
                weather_description="晴れ",
                temperature=25.0,
                precipitation_probability=10,
                wind="北の風",
                timestamp=datetime.now()
            )
            
            # AIサービスが利用できない場合でもフォールバックメッセージが生成される
            fallback_message = await ai_service.generate_positive_message(weather_context)
            assert isinstance(fallback_message, str)
            assert len(fallback_message) > 0
            assert "テスト地域" in fallback_message
            
            # 4. データベース操作のエラー回復
            # 無効な通知時間設定
            invalid_result = await user_service.set_notification_schedule(discord_id, 25)
            assert invalid_result is False
            
            # 有効な通知時間設定
            valid_result = await user_service.set_notification_schedule(discord_id, 9)
            assert valid_result is True
            
            # 5. 存在しないユーザーの操作
            nonexistent_settings = await user_service.get_user_settings(999999)
            assert nonexistent_settings is None
            
            nonexistent_location = await user_service.get_user_location(999999)
            assert nonexistent_location is None
            
        except Exception as e:
            pytest.fail(f"Error recovery and fallback test failed: {e}")
        finally:
            # クリーンアップ
            await user_service.delete_user(discord_id)
    
    @pytest.mark.asyncio
    async def test_system_health_monitoring(self, test_environment_setup, services):
        """システムヘルス監視の統合テスト"""
        user_service = services['user']
        ai_service = services['ai']
        
        try:
            # 1. ユーザーサービスのヘルスチェック
            user_health = await user_service.get_service_health()
            
            assert 'service_name' in user_health
            assert 'overall_status' in user_health
            assert 'user_count' in user_health
            assert 'database_status' in user_health
            
            print(f"User service health: {user_health['overall_status']}")
            
            # 2. AIサービスのヘルスチェック
            ai_health = await ai_service.health_check()
            
            assert 'status' in ai_health
            assert 'fallback_available' in ai_health
            
            print(f"AI service health: {ai_health['status']}")
            
            # 3. データ整合性チェック
            integrity_result = await user_service.validate_data_integrity()
            
            assert 'status' in integrity_result
            assert 'checks' in integrity_result
            assert 'errors' in integrity_result
            assert 'warnings' in integrity_result
            
            print(f"Data integrity: {integrity_result['status']}")
            
            # 4. サービス統計情報
            ai_stats = ai_service.get_service_stats()
            
            assert 'is_available' in ai_stats
            assert 'consecutive_errors' in ai_stats
            assert 'requests_in_last_minute' in ai_stats
            
            print(f"AI service stats: {ai_stats}")
            
            # 5. ユーザー数統計
            user_count = await user_service.get_user_count()
            assert isinstance(user_count, int)
            assert user_count >= 0
            
            print(f"Total users: {user_count}")
            
        except Exception as e:
            pytest.fail(f"System health monitoring test failed: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_performance_and_scalability(self, test_environment_setup, services):
        """パフォーマンスとスケーラビリティの統合テスト"""
        user_service = services['user']
        weather_service = services['weather']
        
        # 大量ユーザーでのテスト
        user_count = 20
        discord_ids = [400000 + i for i in range(user_count)]
        
        try:
            # 1. 大量ユーザー作成のパフォーマンス
            start_time = asyncio.get_event_loop().time()
            
            create_tasks = [user_service.create_user(discord_id) for discord_id in discord_ids]
            created_users = await asyncio.gather(*create_tasks, return_exceptions=True)
            
            create_time = asyncio.get_event_loop().time() - start_time
            successful_users = [u for u in created_users if not isinstance(u, Exception)]
            
            print(f"Created {len(successful_users)} users in {create_time:.2f} seconds")
            assert len(successful_users) == user_count
            assert create_time < 30  # 30秒以内
            
            # 2. 大量データ取得のパフォーマンス
            start_time = asyncio.get_event_loop().time()
            
            get_tasks = [user_service.get_user_by_discord_id(discord_id) for discord_id in discord_ids]
            retrieved_users = await asyncio.gather(*get_tasks, return_exceptions=True)
            
            get_time = asyncio.get_event_loop().time() - start_time
            valid_users = [u for u in retrieved_users if u is not None and not isinstance(u, Exception)]
            
            print(f"Retrieved {len(valid_users)} users in {get_time:.2f} seconds")
            assert len(valid_users) == user_count
            assert get_time < 10  # 10秒以内
            
            # 3. 大量更新のパフォーマンス
            start_time = asyncio.get_event_loop().time()
            
            update_tasks = [
                user_service.set_user_location(discord_id, "130000", f"地域{i}")
                for i, discord_id in enumerate(discord_ids)
            ]
            update_results = await asyncio.gather(*update_tasks, return_exceptions=True)
            
            update_time = asyncio.get_event_loop().time() - start_time
            successful_updates = [r for r in update_results if r is True]
            
            print(f"Updated {len(successful_updates)} users in {update_time:.2f} seconds")
            assert len(successful_updates) == user_count
            assert update_time < 20  # 20秒以内
            
            # 4. 通知ユーザー検索のパフォーマンス
            # 半数のユーザーに通知設定
            notification_tasks = [
                user_service.set_notification_schedule(discord_id, 9)
                for i, discord_id in enumerate(discord_ids)
                if i % 2 == 0
            ]
            await asyncio.gather(*notification_tasks, return_exceptions=True)
            
            start_time = asyncio.get_event_loop().time()
            notification_users = await user_service.get_users_with_notifications(9)
            search_time = asyncio.get_event_loop().time() - start_time
            
            print(f"Found {len(notification_users)} notification users in {search_time:.2f} seconds")
            assert len(notification_users) >= user_count // 2
            assert search_time < 5  # 5秒以内
            
        except Exception as e:
            pytest.fail(f"Performance and scalability test failed: {e}")
        finally:
            # クリーンアップ
            delete_tasks = [user_service.delete_user(discord_id) for discord_id in discord_ids]
            await asyncio.gather(*delete_tasks, return_exceptions=True)


if __name__ == "__main__":
    # 包括的統合テストのみを実行
    pytest.main([__file__, "-v", "-m", "integration and slow"])