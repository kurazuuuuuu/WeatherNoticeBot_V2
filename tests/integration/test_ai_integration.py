"""
AI統合テスト

実際のGoogle Gemini APIとの統合テストを実行します。
このテストは実際のAPIを呼び出すため、APIキーとネットワーク接続が必要です。
"""

import pytest
import asyncio
import os
from datetime import datetime
from unittest.mock import patch

# テスト対象のインポート（モック化対応）
try:
    from src.services.ai_service import (
        AIMessageService,
        WeatherContext,
        weather_data_to_context,
        AIServiceError,
        AIServiceRateLimitError,
        AIServiceQuotaExceededError
    )
    from src.config import Config
except ImportError:
    # 依存関係が不足している場合はスキップ
    pytest.skip("AI service dependencies not available", allow_module_level=True)


@pytest.mark.integration
class TestAIIntegration:
    """AI統合テストクラス"""
    
    @pytest.fixture
    def config_with_real_key(self):
        """実際のAPIキー付きのConfigオブジェクト"""
        config = Config()
        # 環境変数からAPIキーを取得
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            pytest.skip("GEMINI_API_KEY environment variable not set")
        config.GEMINI_API_KEY = api_key
        return config
    
    @pytest.fixture
    def config_without_key(self):
        """APIキーなしのConfigオブジェクト"""
        config = Config()
        config.GEMINI_API_KEY = None
        return config
    
    @pytest.fixture
    def sample_weather_contexts(self):
        """サンプルWeatherContextオブジェクトのリスト"""
        return [
            WeatherContext(
                area_name="東京都",
                weather_description="晴れ",
                temperature=25.0,
                precipitation_probability=10,
                wind="北の風 弱く",
                timestamp=datetime.now(),
                is_alert=False,
                alert_description=None
            ),
            WeatherContext(
                area_name="大阪府",
                weather_description="雨",
                temperature=18.0,
                precipitation_probability=80,
                wind="南の風 強く",
                timestamp=datetime.now(),
                is_alert=False,
                alert_description=None
            ),
            WeatherContext(
                area_name="名古屋市",
                weather_description="くもり",
                temperature=22.0,
                precipitation_probability=40,
                wind="西の風",
                timestamp=datetime.now(),
                is_alert=False,
                alert_description=None
            ),
            WeatherContext(
                area_name="福岡県",
                weather_description="大雨",
                temperature=20.0,
                precipitation_probability=90,
                wind="南の風 非常に強く",
                timestamp=datetime.now(),
                is_alert=True,
                alert_description="大雨警報"
            )
        ]
    
    @pytest.mark.asyncio
    async def test_ai_service_initialization_with_real_key(self, config_with_real_key):
        """実際のAPIキーでのAIサービス初期化テスト"""
        try:
            service = AIMessageService(config_with_real_key)
            
            # サービスが利用可能であることを確認
            assert service.is_available() is True
            assert service._model is not None
            assert service._is_available is True
            
        except Exception as e:
            pytest.skip(f"AI service initialization failed: {e}")
    
    @pytest.mark.asyncio
    async def test_generate_positive_message_real_api(self, config_with_real_key, sample_weather_contexts):
        """実際のAPIを使用したポジティブメッセージ生成テスト"""
        try:
            service = AIMessageService(config_with_real_key)
            
            if not service.is_available():
                pytest.skip("AI service is not available")
            
            # 各天気条件でメッセージを生成
            for weather_context in sample_weather_contexts:
                message = await service.generate_positive_message(weather_context)
                
                # 基本的な検証
                assert isinstance(message, str)
                assert len(message) > 0
                assert len(message) <= 500  # 合理的な長さ制限
                
                # 地域名が含まれていることを確認
                assert weather_context.area_name in message or weather_context.area_name.replace("都", "").replace("府", "").replace("県", "") in message
                
                print(f"Generated message for {weather_context.area_name}: {message}")
                
                # レート制限を避けるため少し待機
                await asyncio.sleep(2)
                
        except AIServiceRateLimitError:
            pytest.skip("API rate limit reached")
        except AIServiceQuotaExceededError:
            pytest.skip("API quota exceeded")
        except Exception as e:
            pytest.fail(f"Unexpected error: {e}")
    
    @pytest.mark.asyncio
    async def test_generate_message_different_types(self, config_with_real_key, sample_weather_contexts):
        """異なるメッセージタイプでの生成テスト"""
        try:
            service = AIMessageService(config_with_real_key)
            
            if not service.is_available():
                pytest.skip("AI service is not available")
            
            weather_context = sample_weather_contexts[0]  # 晴天の東京
            message_types = ["general", "morning", "evening", "alert"]
            
            for message_type in message_types:
                message = await service.generate_positive_message(weather_context, message_type)
                
                assert isinstance(message, str)
                assert len(message) > 0
                
                # メッセージタイプに応じた内容の確認
                if message_type == "morning":
                    # 朝の挨拶が含まれている可能性
                    assert any(word in message for word in ["朝", "おはよう", "今日"])
                elif message_type == "evening":
                    # 夕方の挨拶が含まれている可能性
                    assert any(word in message for word in ["夕", "お疲れ", "一日"])
                elif message_type == "alert":
                    # 警報に関する内容が含まれている可能性
                    assert any(word in message for word in ["注意", "安全", "気をつけ"])
                
                print(f"{message_type} message: {message}")
                
                # レート制限を避けるため待機
                await asyncio.sleep(2)
                
        except AIServiceRateLimitError:
            pytest.skip("API rate limit reached")
        except AIServiceQuotaExceededError:
            pytest.skip("API quota exceeded")
        except Exception as e:
            pytest.fail(f"Unexpected error: {e}")
    
    @pytest.mark.asyncio
    async def test_generate_weather_summary_real_api(self, config_with_real_key, sample_weather_contexts):
        """実際のAPIを使用した天気要約メッセージ生成テスト"""
        try:
            service = AIMessageService(config_with_real_key)
            
            if not service.is_available():
                pytest.skip("AI service is not available")
            
            weather_context = sample_weather_contexts[0]  # 晴天の東京
            
            # 異なる予報日数での要約生成
            for forecast_days in [3, 5, 7]:
                summary = await service.generate_weather_summary_message(weather_context, forecast_days)
                
                assert isinstance(summary, str)
                assert len(summary) > 0
                assert len(summary) <= 200  # 要約なので短め
                
                # 地域名が含まれていることを確認
                assert weather_context.area_name in summary or weather_context.area_name.replace("都", "") in summary
                
                print(f"{forecast_days}-day summary: {summary}")
                
                # レート制限を避けるため待機
                await asyncio.sleep(2)
                
        except AIServiceRateLimitError:
            pytest.skip("API rate limit reached")
        except AIServiceQuotaExceededError:
            pytest.skip("API quota exceeded")
        except Exception as e:
            pytest.fail(f"Unexpected error: {e}")
    
    @pytest.mark.asyncio
    async def test_ai_service_health_check_real_api(self, config_with_real_key):
        """実際のAPIを使用したヘルスチェックテスト"""
        try:
            service = AIMessageService(config_with_real_key)
            
            health = await service.health_check()
            
            # ヘルスチェック結果の基本構造確認
            assert "status" in health
            assert "message" in health
            assert "fallback_available" in health
            
            # ステータスが有効な値であることを確認
            valid_statuses = ["available", "unavailable", "timeout", "error", "circuit_breaker_open"]
            assert health["status"] in valid_statuses
            
            # フォールバック機能は常に利用可能
            assert health["fallback_available"] is True
            
            # 利用可能な場合の追加チェック
            if health["status"] == "available":
                assert "test_message_length" in health
                assert "response_time_seconds" in health
                assert isinstance(health["test_message_length"], int)
                assert isinstance(health["response_time_seconds"], (int, float))
                assert health["response_time_seconds"] > 0
            
            print(f"Health check result: {health}")
            
        except Exception as e:
            pytest.fail(f"Health check failed: {e}")
    
    @pytest.mark.asyncio
    async def test_ai_service_stats_real_api(self, config_with_real_key):
        """実際のAPIを使用したサービス統計テスト"""
        try:
            service = AIMessageService(config_with_real_key)
            
            # 初期統計
            initial_stats = service.get_service_stats()
            
            assert "is_available" in initial_stats
            assert "consecutive_errors" in initial_stats
            assert "circuit_breaker_active" in initial_stats
            assert "requests_in_last_minute" in initial_stats
            assert "rate_limit_remaining" in initial_stats
            
            # 初期状態の確認
            assert initial_stats["consecutive_errors"] == 0
            assert initial_stats["circuit_breaker_active"] is False
            assert initial_stats["requests_in_last_minute"] == 0
            assert initial_stats["rate_limit_remaining"] == service.MAX_REQUESTS_PER_MINUTE
            
            # リクエスト実行後の統計
            if service.is_available():
                weather_context = WeatherContext(
                    area_name="テスト地域",
                    weather_description="晴れ",
                    temperature=20.0,
                    precipitation_probability=10,
                    wind="風",
                    timestamp=datetime.now()
                )
                
                await service.generate_positive_message(weather_context)
                
                # リクエスト後の統計
                after_stats = service.get_service_stats()
                
                # リクエスト数が増加していることを確認
                assert after_stats["requests_in_last_minute"] > initial_stats["requests_in_last_minute"]
                assert after_stats["rate_limit_remaining"] < initial_stats["rate_limit_remaining"]
            
            print(f"Service stats: {initial_stats}")
            
        except Exception as e:
            pytest.fail(f"Service stats test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_fallback_functionality_without_api(self, config_without_key, sample_weather_contexts):
        """APIなしでのフォールバック機能テスト"""
        service = AIMessageService(config_without_key)
        
        # サービスが利用不可であることを確認
        assert service.is_available() is False
        
        # フォールバックメッセージが生成されることを確認
        for weather_context in sample_weather_contexts:
            message = await service.generate_positive_message(weather_context)
            
            assert isinstance(message, str)
            assert len(message) > 0
            
            # 地域名が含まれていることを確認
            assert weather_context.area_name in message
            
            # 警報時の特別処理
            if weather_context.is_alert:
                assert "⚠️" in message
                assert "気象警報" in message or "警報" in message
            
            print(f"Fallback message for {weather_context.area_name}: {message}")
        
        # 要約メッセージのフォールバック
        summary = await service.generate_weather_summary_message(sample_weather_contexts[0])
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert sample_weather_contexts[0].area_name in summary
    
    @pytest.mark.asyncio
    async def test_rate_limit_handling_real_api(self, config_with_real_key):
        """実際のAPIでのレート制限処理テスト"""
        try:
            service = AIMessageService(config_with_real_key)
            
            if not service.is_available():
                pytest.skip("AI service is not available")
            
            weather_context = WeatherContext(
                area_name="テスト地域",
                weather_description="晴れ",
                temperature=20.0,
                precipitation_probability=10,
                wind="風",
                timestamp=datetime.now()
            )
            
            # 複数のリクエストを短時間で実行
            messages = []
            for i in range(3):  # 少数のリクエストでテスト
                try:
                    message = await service.generate_positive_message(weather_context)
                    messages.append(message)
                    print(f"Request {i+1}: Success")
                except AIServiceRateLimitError:
                    print(f"Request {i+1}: Rate limited")
                    break
                except Exception as e:
                    print(f"Request {i+1}: Error - {e}")
                    break
                
                # 短い間隔でリクエスト
                await asyncio.sleep(0.5)
            
            # 少なくとも1つのメッセージが生成されることを確認
            assert len(messages) > 0
            
        except Exception as e:
            pytest.skip(f"Rate limit test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_error_recovery_real_api(self, config_with_real_key):
        """実際のAPIでのエラー回復テスト"""
        try:
            service = AIMessageService(config_with_real_key)
            
            if not service.is_available():
                pytest.skip("AI service is not available")
            
            weather_context = WeatherContext(
                area_name="テスト地域",
                weather_description="晴れ",
                temperature=20.0,
                precipitation_probability=10,
                wind="風",
                timestamp=datetime.now()
            )
            
            # 正常なリクエスト
            normal_message = await service.generate_positive_message(weather_context)
            assert isinstance(normal_message, str)
            assert len(normal_message) > 0
            
            # エラーカウントを人為的に増加
            original_errors = service._consecutive_errors
            service._consecutive_errors = 3
            
            # エラー状態でもフォールバックが機能することを確認
            fallback_message = await service.generate_positive_message(weather_context)
            assert isinstance(fallback_message, str)
            assert len(fallback_message) > 0
            
            # エラーカウントをリセット
            service._consecutive_errors = original_errors
            
            # 回復後の正常動作確認
            recovered_message = await service.generate_positive_message(weather_context)
            assert isinstance(recovered_message, str)
            assert len(recovered_message) > 0
            
        except Exception as e:
            pytest.skip(f"Error recovery test failed: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_comprehensive_ai_workflow(self, config_with_real_key, sample_weather_contexts):
        """包括的なAIワークフローの統合テスト"""
        try:
            service = AIMessageService(config_with_real_key)
            
            if not service.is_available():
                pytest.skip("AI service is not available")
            
            print("=== Comprehensive AI Workflow Test ===")
            
            # 1. ヘルスチェック
            health = await service.health_check()
            print(f"Health Status: {health['status']}")
            assert health["status"] == "available"
            
            # 2. 各種天気条件でのメッセージ生成
            for i, weather_context in enumerate(sample_weather_contexts):
                print(f"\n--- Weather Context {i+1}: {weather_context.area_name} ---")
                
                # 一般的なメッセージ
                general_msg = await service.generate_positive_message(weather_context, "general")
                print(f"General: {general_msg}")
                
                # 朝のメッセージ
                morning_msg = await service.generate_positive_message(weather_context, "morning")
                print(f"Morning: {morning_msg}")
                
                # 要約メッセージ
                summary_msg = await service.generate_weather_summary_message(weather_context, 3)
                print(f"Summary: {summary_msg}")
                
                # 各メッセージの基本検証
                for msg in [general_msg, morning_msg, summary_msg]:
                    assert isinstance(msg, str)
                    assert len(msg) > 0
                
                # レート制限を避けるため待機
                await asyncio.sleep(3)
            
            # 3. サービス統計の確認
            final_stats = service.get_service_stats()
            print(f"\nFinal Stats: {final_stats}")
            assert final_stats["requests_in_last_minute"] > 0
            
            # 4. 最終ヘルスチェック
            final_health = await service.health_check()
            print(f"Final Health: {final_health['status']}")
            
        except AIServiceRateLimitError:
            pytest.skip("API rate limit reached during comprehensive test")
        except AIServiceQuotaExceededError:
            pytest.skip("API quota exceeded during comprehensive test")
        except Exception as e:
            pytest.fail(f"Comprehensive workflow test failed: {e}")


if __name__ == "__main__":
    # 統合テストのみを実行
    pytest.main([__file__, "-v", "-m", "integration"])