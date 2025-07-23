"""
AIServiceのユニットテスト（Gemini APIモック使用）

このテストファイルはGoogle Gemini APIをモック化してAIServiceの動作をテストします。
"""

import pytest
import asyncio
import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from google.api_core import exceptions as google_exceptions

from src.services.ai_service import (
    AIMessageService,
    WeatherContext,
    weather_data_to_context,
    AIServiceError,
    AIServiceRateLimitError,
    AIServiceQuotaExceededError
)
from src.config import Config


class TestAIMessageService:
    """AIMessageServiceのユニットテストクラス"""
    
    @pytest.fixture
    def mock_config(self):
        """モック用のConfigオブジェクト"""
        config = MagicMock(spec=Config)
        config.GEMINI_API_KEY = "test_api_key"
        return config
    
    @pytest.fixture
    def mock_config_no_key(self):
        """APIキーなしのモック用Configオブジェクト"""
        config = MagicMock(spec=Config)
        config.GEMINI_API_KEY = None
        return config
    
    @pytest.fixture
    def weather_context(self):
        """テスト用のWeatherContextオブジェクト"""
        return WeatherContext(
            area_name="東京都",
            weather_description="晴れ",
            temperature=25.0,
            precipitation_probability=10,
            wind="北の風 弱く",
            timestamp=datetime.now(),
            is_alert=False,
            alert_description=None
        )
    
    @pytest.fixture
    def weather_context_with_alert(self):
        """警報付きのWeatherContextオブジェクト"""
        return WeatherContext(
            area_name="大阪府",
            weather_description="雨",
            temperature=18.0,
            precipitation_probability=80,
            wind="南の風 強く",
            timestamp=datetime.now(),
            is_alert=True,
            alert_description="大雨警報"
        )
    
    @pytest.fixture
    def mock_weather_data(self):
        """モック用のWeatherDataオブジェクト"""
        weather_data = MagicMock()
        weather_data.area_name = "東京都"
        weather_data.weather_description = "晴れ"
        weather_data.temperature = 25.0
        weather_data.precipitation_probability = 10
        weather_data.wind = "北の風 弱く"
        weather_data.timestamp = datetime.now()
        return weather_data
    
    def test_weather_data_to_context_conversion(self, mock_weather_data):
        """WeatherDataからWeatherContextへの変換テスト"""
        context = weather_data_to_context(mock_weather_data)
        
        assert isinstance(context, WeatherContext)
        assert context.area_name == mock_weather_data.area_name
        assert context.weather_description == mock_weather_data.weather_description
        assert context.temperature == mock_weather_data.temperature
        assert context.precipitation_probability == mock_weather_data.precipitation_probability
        assert context.wind == mock_weather_data.wind
        assert context.timestamp == mock_weather_data.timestamp
        assert context.is_alert is False
        assert context.alert_description is None
    
    def test_ai_service_initialization_with_api_key(self, mock_config):
        """APIキーありでのAIサービス初期化テスト"""
        with patch('google.generativeai.configure') as mock_configure:
            with patch('google.generativeai.GenerativeModel') as mock_model_class:
                mock_model = MagicMock()
                mock_model_class.return_value = mock_model
                
                service = AIMessageService(mock_config)
                
                assert service._is_available is True
                assert service._model == mock_model
                assert service._consecutive_errors == 0
                mock_configure.assert_called_once_with(api_key="test_api_key")
    
    def test_ai_service_initialization_without_api_key(self, mock_config_no_key):
        """APIキーなしでのAIサービス初期化テスト"""
        service = AIMessageService(mock_config_no_key)
        
        assert service._is_available is False
        assert service._model is None
    
    def test_ai_service_initialization_error(self, mock_config):
        """初期化エラーのテスト"""
        with patch('google.generativeai.configure', side_effect=Exception("Init error")):
            service = AIMessageService(mock_config)
            
            assert service._is_available is False
            assert service._model is None
    
    def test_circuit_breaker_functionality(self, mock_config):
        """サーキットブレーカー機能のテスト"""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                service = AIMessageService(mock_config)
                
                # 正常状態
                assert service._check_circuit_breaker() is True
                
                # 連続エラーを発生させる
                service._consecutive_errors = 5
                service._last_error_time = time.time()
                
                # サーキットブレーカーが開く
                assert service._check_circuit_breaker() is False
                
                # 時間経過後にリセット
                service._last_error_time = time.time() - 400  # 400秒前
                assert service._check_circuit_breaker() is True
                assert service._consecutive_errors == 0
    
    def test_rate_limit_check(self, mock_config):
        """レート制限チェックのテスト"""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                service = AIMessageService(mock_config)
                
                # 通常の状態では例外が発生しない
                service._check_rate_limit()
                
                # レート制限に達するまでリクエストを追加
                current_time = time.time()
                service._request_times = [current_time] * service.MAX_REQUESTS_PER_MINUTE
                
                # レート制限例外が発生することを確認
                with pytest.raises(AIServiceRateLimitError):
                    service._check_rate_limit()
    
    def test_api_error_handling(self, mock_config):
        """APIエラーハンドリングのテスト"""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                service = AIMessageService(mock_config)
                
                # ResourceExhaustedエラー
                with pytest.raises(AIServiceQuotaExceededError):
                    service._handle_api_error(google_exceptions.ResourceExhausted("Quota exceeded"))
                
                # TooManyRequestsエラー
                with pytest.raises(AIServiceRateLimitError):
                    service._handle_api_error(google_exceptions.TooManyRequests("Rate limit"))
                
                # DeadlineExceededエラー
                with pytest.raises(AIServiceError, match="タイムアウト"):
                    service._handle_api_error(google_exceptions.DeadlineExceeded("Timeout"))
                
                # ServiceUnavailableエラー
                with pytest.raises(AIServiceError, match="一時的に利用できません"):
                    service._handle_api_error(google_exceptions.ServiceUnavailable("Service down"))
                
                # その他のエラー
                with pytest.raises(AIServiceError, match="予期しないAPIエラー"):
                    service._handle_api_error(Exception("Unknown error"))
    
    def test_create_prompt_general(self, mock_config, weather_context):
        """一般的なプロンプト作成のテスト"""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                service = AIMessageService(mock_config)
                
                prompt = service._create_prompt(weather_context, "general")
                
                assert "東京都" in prompt
                assert "晴れ" in prompt
                assert "25.0°C" in prompt
                assert "10%" in prompt
                assert "北の風 弱く" in prompt
                assert "前向きで励ましのメッセージ" in prompt
    
    def test_create_prompt_morning(self, mock_config, weather_context):
        """朝のプロンプト作成のテスト"""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                service = AIMessageService(mock_config)
                
                prompt = service._create_prompt(weather_context, "morning")
                
                assert "朝の挨拶" in prompt
                assert "今日一日を前向きに" in prompt
    
    def test_create_prompt_alert(self, mock_config, weather_context_with_alert):
        """警報時のプロンプト作成のテスト"""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                service = AIMessageService(mock_config)
                
                prompt = service._create_prompt(weather_context_with_alert, "alert")
                
                assert "大雨警報" in prompt
                assert "気象警報が出ています" in prompt
                assert "安全に過ごすため" in prompt
    
    def test_fallback_message_sunny(self, mock_config, weather_context):
        """晴天時のフォールバックメッセージテスト"""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                service = AIMessageService(mock_config)
                
                message = service._get_fallback_message(weather_context, "general")
                
                assert "東京都" in message
                assert any(emoji in message for emoji in ["☀️", "🌞", "✨"])
    
    def test_fallback_message_rainy(self, mock_config):
        """雨天時のフォールバックメッセージテスト"""
        rainy_context = WeatherContext(
            area_name="大阪府",
            weather_description="雨",
            temperature=18.0,
            precipitation_probability=80,
            wind="南の風",
            timestamp=datetime.now()
        )
        
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                service = AIMessageService(mock_config)
                
                message = service._get_fallback_message(rainy_context, "general")
                
                assert "大阪府" in message
                assert any(emoji in message for emoji in ["☔", "🌂", "🌧️"])
    
    def test_fallback_message_with_alert(self, mock_config, weather_context_with_alert):
        """警報時のフォールバックメッセージテスト"""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                service = AIMessageService(mock_config)
                
                message = service._get_fallback_message(weather_context_with_alert, "general")
                
                assert "⚠️" in message
                assert "気象警報" in message
                assert "安全第一" in message
    
    def test_fallback_message_morning(self, mock_config, weather_context):
        """朝のフォールバックメッセージテスト"""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                service = AIMessageService(mock_config)
                
                message = service._get_fallback_message(weather_context, "morning")
                
                assert message.startswith("おはようございます！")
    
    def test_fallback_message_evening(self, mock_config, weather_context):
        """夕方のフォールバックメッセージテスト"""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                service = AIMessageService(mock_config)
                
                message = service._get_fallback_message(weather_context, "evening")
                
                assert message.startswith("お疲れ様です！")
    
    @pytest.mark.asyncio
    async def test_generate_positive_message_success(self, mock_config, weather_context):
        """ポジティブメッセージ生成成功のテスト"""
        mock_response = MagicMock()
        mock_response.text = "今日は素晴らしい天気ですね！☀️"
        
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel', return_value=mock_model):
                service = AIMessageService(mock_config)
                
                message = await service.generate_positive_message(weather_context)
                
                assert message == "今日は素晴らしい天気ですね！☀️"
                assert service._consecutive_errors == 0
    
    @pytest.mark.asyncio
    async def test_generate_positive_message_empty_response(self, mock_config, weather_context):
        """空のレスポンス時のテスト"""
        mock_response = MagicMock()
        mock_response.text = ""
        
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel', return_value=mock_model):
                service = AIMessageService(mock_config)
                
                message = await service.generate_positive_message(weather_context)
                
                # フォールバックメッセージが返される
                assert "東京都" in message
                assert len(message) > 0
    
    @pytest.mark.asyncio
    async def test_generate_positive_message_timeout(self, mock_config, weather_context):
        """タイムアウト時のテスト"""
        mock_model = MagicMock()
        
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel', return_value=mock_model):
                service = AIMessageService(mock_config)
                
                # asyncio.wait_forがタイムアウトするようにモック
                with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError()):
                    message = await service.generate_positive_message(weather_context)
                    
                    # フォールバックメッセージが返される
                    assert "東京都" in message
                    assert len(message) > 0
    
    @pytest.mark.asyncio
    async def test_generate_positive_message_rate_limit_retry(self, mock_config, weather_context):
        """レート制限時のリトライテスト"""
        mock_model = MagicMock()
        
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel', return_value=mock_model):
                service = AIMessageService(mock_config)
                
                # 最初はレート制限エラー、2回目は成功
                service._check_rate_limit = MagicMock(side_effect=[
                    AIServiceRateLimitError("Rate limit"),
                    None  # 2回目は成功
                ])
                
                mock_response = MagicMock()
                mock_response.text = "リトライ成功メッセージ"
                mock_model.generate_content.return_value = mock_response
                
                with patch('asyncio.sleep', new_callable=AsyncMock):
                    message = await service.generate_positive_message(weather_context)
                    
                    assert message == "リトライ成功メッセージ"
    
    @pytest.mark.asyncio
    async def test_generate_positive_message_circuit_breaker_open(self, mock_config, weather_context):
        """サーキットブレーカー開放時のテスト"""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                service = AIMessageService(mock_config)
                
                # サーキットブレーカーを開く
                service._consecutive_errors = 5
                service._last_error_time = time.time()
                
                message = await service.generate_positive_message(weather_context)
                
                # フォールバックメッセージが返される
                assert "東京都" in message
                assert len(message) > 0
    
    @pytest.mark.asyncio
    async def test_generate_positive_message_service_unavailable(self, mock_config_no_key, weather_context):
        """サービス利用不可時のテスト"""
        service = AIMessageService(mock_config_no_key)
        
        message = await service.generate_positive_message(weather_context)
        
        # フォールバックメッセージが返される
        assert "東京都" in message
        assert len(message) > 0
    
    @pytest.mark.asyncio
    async def test_generate_weather_summary_message_success(self, mock_config, weather_context):
        """天気要約メッセージ生成成功のテスト"""
        mock_response = MagicMock()
        mock_response.text = "今後3日間は晴れが続きます☀️"
        
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel', return_value=mock_model):
                service = AIMessageService(mock_config)
                
                message = await service.generate_weather_summary_message(weather_context)
                
                assert message == "今後3日間は晴れが続きます☀️"
    
    @pytest.mark.asyncio
    async def test_generate_weather_summary_message_error(self, mock_config, weather_context):
        """天気要約メッセージ生成エラー時のテスト"""
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API Error")
        
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel', return_value=mock_model):
                service = AIMessageService(mock_config)
                
                message = await service.generate_weather_summary_message(weather_context)
                
                # フォールバック要約メッセージが返される
                assert "東京都" in message
                assert len(message) > 0
    
    def test_get_summary_fallback_message_rainy(self, mock_config):
        """雨天時の要約フォールバックメッセージテスト"""
        rainy_context = WeatherContext(
            area_name="大阪府",
            weather_description="雨",
            temperature=18.0,
            precipitation_probability=70,
            wind="南の風",
            timestamp=datetime.now()
        )
        
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                service = AIMessageService(mock_config)
                
                message = service._get_summary_fallback_message(rainy_context)
                
                assert "🌧️" in message
                assert "雨の可能性が高め" in message
                assert "傘の準備" in message
    
    def test_get_summary_fallback_message_sunny(self, mock_config, weather_context):
        """晴天時の要約フォールバックメッセージテスト"""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                service = AIMessageService(mock_config)
                
                message = service._get_summary_fallback_message(weather_context)
                
                assert "☀️" in message
                assert "良いお天気" in message
    
    def test_is_available_with_api_key(self, mock_config):
        """APIキーありでの利用可能性チェック"""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel') as mock_model_class:
                mock_model = MagicMock()
                mock_model_class.return_value = mock_model
                
                service = AIMessageService(mock_config)
                
                assert service.is_available() is True
    
    def test_is_available_without_api_key(self, mock_config_no_key):
        """APIキーなしでの利用可能性チェック"""
        service = AIMessageService(mock_config_no_key)
        
        assert service.is_available() is False
    
    def test_is_available_circuit_breaker_open(self, mock_config):
        """サーキットブレーカー開放時の利用可能性チェック"""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                service = AIMessageService(mock_config)
                
                # サーキットブレーカーを開く
                service._consecutive_errors = 5
                service._last_error_time = time.time()
                
                assert service.is_available() is False
    
    @pytest.mark.asyncio
    async def test_health_check_available(self, mock_config, weather_context):
        """利用可能時のヘルスチェック"""
        mock_response = MagicMock()
        mock_response.text = "テストメッセージ"
        
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel', return_value=mock_model):
                service = AIMessageService(mock_config)
                
                with patch.object(service, 'generate_positive_message', return_value="テストメッセージ"):
                    health = await service.health_check()
                    
                    assert health["status"] == "available"
                    assert health["test_message_length"] == 7
                    assert "response_time_seconds" in health
                    assert health["fallback_available"] is True
    
    @pytest.mark.asyncio
    async def test_health_check_unavailable(self, mock_config_no_key):
        """利用不可時のヘルスチェック"""
        service = AIMessageService(mock_config_no_key)
        
        health = await service.health_check()
        
        assert health["status"] == "unavailable"
        assert "Gemini APIが設定されていません" in health["message"]
        assert health["fallback_available"] is True
    
    @pytest.mark.asyncio
    async def test_health_check_timeout(self, mock_config):
        """タイムアウト時のヘルスチェック"""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                service = AIMessageService(mock_config)
                
                with patch.object(service, 'generate_positive_message', side_effect=asyncio.TimeoutError()):
                    health = await service.health_check()
                    
                    assert health["status"] == "timeout"
                    assert "タイムアウト" in health["message"]
    
    @pytest.mark.asyncio
    async def test_health_check_error(self, mock_config):
        """エラー時のヘルスチェック"""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                service = AIMessageService(mock_config)
                
                with patch.object(service, 'generate_positive_message', side_effect=Exception("Test error")):
                    health = await service.health_check()
                    
                    assert health["status"] == "error"
                    assert "Test error" in health["message"]
    
    def test_get_service_stats(self, mock_config):
        """サービス統計情報取得のテスト"""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                service = AIMessageService(mock_config)
                
                # いくつかのリクエスト時刻を追加
                current_time = time.time()
                service._request_times = [current_time - 30, current_time - 10]
                service._last_request_time = current_time
                
                stats = service.get_service_stats()
                
                assert stats["is_available"] is True
                assert stats["consecutive_errors"] == 0
                assert stats["circuit_breaker_active"] is False
                assert stats["requests_in_last_minute"] == 2
                assert stats["rate_limit_remaining"] == service.MAX_REQUESTS_PER_MINUTE - 2
                assert stats["last_request_time"] == current_time


if __name__ == "__main__":
    pytest.main([__file__])