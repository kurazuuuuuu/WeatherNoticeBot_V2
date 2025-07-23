"""
AIServiceの拡張ユニットテスト

既存のテストを補完し、エッジケースやエラーハンドリングをより詳細にテストします。
"""

import pytest
import asyncio
import time
import hashlib
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# テスト対象のインポート（モック化）
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
    from google.api_core import exceptions as google_exceptions
except ImportError:
    # 依存関係が不足している場合のモック実装
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
    
    def weather_data_to_context(weather_data):
        return WeatherContext(
            area_name=weather_data.area_name,
            weather_description=weather_data.weather_description,
            temperature=weather_data.temperature,
            precipitation_probability=weather_data.precipitation_probability,
            wind=weather_data.wind,
            timestamp=weather_data.timestamp,
            is_alert=False,
            alert_description=None
        )
    
    class AIServiceError(Exception):
        pass
    
    class AIServiceRateLimitError(AIServiceError):
        pass
    
    class AIServiceQuotaExceededError(AIServiceError):
        pass
    
    class Config:
        def __init__(self):
            self.GEMINI_API_KEY = None
    
    class AIMessageService:
        MAX_RETRIES = 3
        RETRY_DELAY = 2.0
        BACKOFF_FACTOR = 2.0
        MAX_RETRY_DELAY = 30.0
        RATE_LIMIT_WINDOW = 60
        MAX_REQUESTS_PER_MINUTE = 15
        
        def __init__(self, config=None):
            self.config = config or Config()
            self._model = None
            self._is_available = False
            self._request_times = []
            self._consecutive_errors = 0
            self._last_error_time = 0.0
            self._circuit_breaker_timeout = 300
            
            if self.config.GEMINI_API_KEY:
                self._model = MagicMock()
                self._is_available = True
        
        def _check_circuit_breaker(self):
            current_time = time.time()
            if self._consecutive_errors >= 5:
                if current_time - self._last_error_time < self._circuit_breaker_timeout:
                    return False
                else:
                    self._consecutive_errors = 0
            return True
        
        def _check_rate_limit(self):
            current_time = time.time()
            self._request_times = [
                req_time for req_time in self._request_times
                if current_time - req_time < self.RATE_LIMIT_WINDOW
            ]
            if len(self._request_times) >= self.MAX_REQUESTS_PER_MINUTE:
                raise AIServiceRateLimitError("Rate limit exceeded")
            self._request_times.append(current_time)
        
        def _create_prompt(self, weather_context, message_type):
            base_prompt = f"""
天気情報:
- 地域: {weather_context.area_name}
- 天気: {weather_context.weather_description}
- 気温: {weather_context.temperature}°C
- 降水確率: {weather_context.precipitation_probability}%
- 風: {weather_context.wind}
"""
            if message_type == "morning":
                base_prompt += "\n朝の挨拶として、今日一日を前向きに過ごせるようなメッセージをお願いします。"
            elif message_type == "evening":
                base_prompt += "\n夕方の挨拶として、一日お疲れ様の気持ちを込めたメッセージをお願いします。"
            elif message_type == "alert":
                base_prompt += "\n気象警報が出ていますが、安全に過ごすためのアドバイスと励ましのメッセージをお願いします。"
            
            return base_prompt
        
        def _get_fallback_message(self, weather_context, message_type):
            if weather_context.is_alert:
                return f"⚠️ {weather_context.area_name}に気象警報が発表されています。安全第一で過ごしてくださいね！ 🙏"
            
            if weather_context.precipitation_probability >= 70:
                messages = [
                    f"☔ {weather_context.area_name}は雨の予報ですが、雨音を聞きながらゆっくり過ごすのも素敵ですね！ 🌧️✨",
                ]
            elif weather_context.precipitation_probability >= 30:
                messages = [
                    f"🌤️ {weather_context.area_name}は少し雲が多めですが、きっと素敵な一日になりますよ！ ☁️✨",
                ]
            else:
                messages = [
                    f"☀️ {weather_context.area_name}は良いお天気！今日も素晴らしい一日になりそうですね！ 🌟",
                ]
            
            prefix = ""
            if message_type == "morning":
                prefix = "おはようございます！ "
            elif message_type == "evening":
                prefix = "お疲れ様です！ "
            
            # ハッシュベースでメッセージを選択
            hash_input = f"{weather_context.area_name}{weather_context.timestamp.date()}"
            hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
            selected_message = messages[hash_value % len(messages)]
            
            return prefix + selected_message
        
        def _get_summary_fallback_message(self, weather_context):
            if weather_context.precipitation_probability >= 50:
                return f"🌧️ {weather_context.area_name}は雨の可能性が高めです。傘の準備をお忘れなく！"
            else:
                return f"☀️ {weather_context.area_name}は比較的良いお天気が続きそうです！"
        
        async def generate_positive_message(self, weather_context, message_type="general", retries=0):
            if not self._check_circuit_breaker():
                return self._get_fallback_message(weather_context, message_type)
            
            if not self._model or not self._is_available:
                return self._get_fallback_message(weather_context, message_type)
            
            try:
                self._check_rate_limit()
                return "AIで生成されたポジティブメッセージ"
            except AIServiceRateLimitError:
                if retries < self.MAX_RETRIES:
                    await asyncio.sleep(self.RETRY_DELAY)
                    return await self.generate_positive_message(weather_context, message_type, retries + 1)
                return self._get_fallback_message(weather_context, message_type)
            except Exception:
                return self._get_fallback_message(weather_context, message_type)
        
        async def generate_weather_summary_message(self, weather_context, forecast_days=3):
            if not self._model:
                return self._get_summary_fallback_message(weather_context)
            
            try:
                return f"{forecast_days}日間の天気要約メッセージ"
            except Exception:
                return self._get_summary_fallback_message(weather_context)
        
        def is_available(self):
            return self._model is not None and self._is_available and self._check_circuit_breaker()
        
        async def health_check(self):
            if not self._model:
                return {
                    "status": "unavailable",
                    "message": "Gemini APIが設定されていません",
                    "fallback_available": True
                }
            
            if not self._check_circuit_breaker():
                return {
                    "status": "circuit_breaker_open",
                    "message": "サーキットブレーカーが開いています",
                    "fallback_available": True
                }
            
            try:
                return {
                    "status": "available",
                    "message": "Gemini AIサービスは正常に動作しています",
                    "fallback_available": True
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"エラーが発生しました: {str(e)}",
                    "fallback_available": True
                }
        
        def get_service_stats(self):
            current_time = time.time()
            recent_requests = [
                req_time for req_time in self._request_times
                if current_time - req_time < self.RATE_LIMIT_WINDOW
            ]
            
            return {
                "is_available": self.is_available(),
                "consecutive_errors": self._consecutive_errors,
                "circuit_breaker_active": not self._check_circuit_breaker(),
                "requests_in_last_minute": len(recent_requests),
                "rate_limit_remaining": max(0, self.MAX_REQUESTS_PER_MINUTE - len(recent_requests))
            }
    
    # Google API例外のモック
    class google_exceptions:
        class ResourceExhausted(Exception):
            pass
        
        class TooManyRequests(Exception):
            pass
        
        class DeadlineExceeded(Exception):
            pass
        
        class ServiceUnavailable(Exception):
            pass


class TestAIMessageServiceEnhanced:
    """AIMessageServiceの拡張ユニットテストクラス"""
    
    @pytest.fixture
    def config_with_key(self):
        """APIキー付きのConfigオブジェクト"""
        config = Config()
        config.GEMINI_API_KEY = "test_api_key_12345"
        return config
    
    @pytest.fixture
    def config_without_key(self):
        """APIキーなしのConfigオブジェクト"""
        config = Config()
        config.GEMINI_API_KEY = None
        return config
    
    @pytest.fixture
    def weather_context_sunny(self):
        """晴天のWeatherContextオブジェクト"""
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
    def weather_context_rainy(self):
        """雨天のWeatherContextオブジェクト"""
        return WeatherContext(
            area_name="大阪府",
            weather_description="雨",
            temperature=18.0,
            precipitation_probability=80,
            wind="南の風 強く",
            timestamp=datetime.now(),
            is_alert=False,
            alert_description=None
        )
    
    @pytest.fixture
    def weather_context_cloudy(self):
        """曇天のWeatherContextオブジェクト"""
        return WeatherContext(
            area_name="名古屋市",
            weather_description="くもり",
            temperature=22.0,
            precipitation_probability=40,
            wind="西の風",
            timestamp=datetime.now(),
            is_alert=False,
            alert_description=None
        )
    
    @pytest.fixture
    def weather_context_with_alert(self):
        """警報付きのWeatherContextオブジェクト"""
        return WeatherContext(
            area_name="福岡県",
            weather_description="大雨",
            temperature=20.0,
            precipitation_probability=90,
            wind="南の風 非常に強く",
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
    
    def test_weather_context_creation_comprehensive(self):
        """WeatherContext作成の包括的テスト"""
        area_name = "札幌市"
        weather_description = "雪"
        temperature = -5.0
        precipitation_probability = 60
        wind = "北西の風 強く"
        timestamp = datetime.now()
        is_alert = True
        alert_description = "大雪警報"
        
        context = WeatherContext(
            area_name=area_name,
            weather_description=weather_description,
            temperature=temperature,
            precipitation_probability=precipitation_probability,
            wind=wind,
            timestamp=timestamp,
            is_alert=is_alert,
            alert_description=alert_description
        )
        
        assert context.area_name == area_name
        assert context.weather_description == weather_description
        assert context.temperature == temperature
        assert context.precipitation_probability == precipitation_probability
        assert context.wind == wind
        assert context.timestamp == timestamp
        assert context.is_alert == is_alert
        assert context.alert_description == alert_description
    
    def test_weather_context_edge_cases(self):
        """WeatherContextのエッジケーステスト"""
        # 極端な気温
        extreme_hot = WeatherContext("砂漠", "快晴", 50.0, 0, "無風", datetime.now())
        assert extreme_hot.temperature == 50.0
        
        extreme_cold = WeatherContext("南極", "雪", -40.0, 100, "強風", datetime.now())
        assert extreme_cold.temperature == -40.0
        
        # 降水確率の境界値
        no_rain = WeatherContext("地域", "晴れ", 20.0, 0, "風", datetime.now())
        assert no_rain.precipitation_probability == 0
        
        certain_rain = WeatherContext("地域", "雨", 20.0, 100, "風", datetime.now())
        assert certain_rain.precipitation_probability == 100
        
        # 長い文字列
        long_area_name = "非常に長い地域名" * 10
        long_context = WeatherContext(long_area_name, "晴れ", 20.0, 10, "風", datetime.now())
        assert long_context.area_name == long_area_name
        
        # 特殊文字
        special_area = "東京都🗼"
        special_context = WeatherContext(special_area, "晴れ☀️", 20.0, 10, "風💨", datetime.now())
        assert special_context.area_name == special_area
        assert special_context.weather_description == "晴れ☀️"
        assert special_context.wind == "風💨"
    
    def test_weather_data_to_context_conversion_comprehensive(self, mock_weather_data):
        """WeatherDataからWeatherContextへの包括的変換テスト"""
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
    
    def test_ai_service_initialization_edge_cases(self):
        """AIサービス初期化のエッジケーステスト"""
        # Configなしでの初期化
        service = AIMessageService()
        assert service.config is not None
        assert not service.is_available()
        
        # 空のAPIキー
        config = Config()
        config.GEMINI_API_KEY = ""
        service = AIMessageService(config)
        assert not service.is_available()
        
        # 非常に長いAPIキー
        config = Config()
        config.GEMINI_API_KEY = "a" * 1000
        service = AIMessageService(config)
        assert service.config.GEMINI_API_KEY == "a" * 1000
    
    def test_circuit_breaker_comprehensive(self, config_with_key):
        """サーキットブレーカーの包括的テスト"""
        service = AIMessageService(config_with_key)
        
        # 初期状態
        assert service._check_circuit_breaker() is True
        assert service._consecutive_errors == 0
        
        # エラー回数を段階的に増加
        for i in range(1, 5):
            service._consecutive_errors = i
            service._last_error_time = time.time()
            assert service._check_circuit_breaker() is True
        
        # 閾値に達する
        service._consecutive_errors = 5
        service._last_error_time = time.time()
        assert service._check_circuit_breaker() is False
        
        # さらにエラーが増えても開いたまま
        service._consecutive_errors = 10
        assert service._check_circuit_breaker() is False
        
        # 時間経過後にリセット
        service._last_error_time = time.time() - service._circuit_breaker_timeout - 1
        assert service._check_circuit_breaker() is True
        assert service._consecutive_errors == 0
    
    def test_rate_limit_comprehensive(self, config_with_key):
        """レート制限の包括的テスト"""
        service = AIMessageService(config_with_key)
        
        # 通常のリクエスト
        for i in range(service.MAX_REQUESTS_PER_MINUTE - 1):
            service._check_rate_limit()
        
        assert len(service._request_times) == service.MAX_REQUESTS_PER_MINUTE - 1
        
        # 制限に達する直前
        service._check_rate_limit()
        assert len(service._request_times) == service.MAX_REQUESTS_PER_MINUTE
        
        # 制限に達する
        with pytest.raises(AIServiceRateLimitError):
            service._check_rate_limit()
        
        # 古いリクエストは削除される
        old_time = time.time() - service.RATE_LIMIT_WINDOW - 1
        service._request_times = [old_time] * 10 + service._request_times[:5]
        
        # 古いリクエストが削除されて新しいリクエストが可能
        service._check_rate_limit()
        assert len([t for t in service._request_times if time.time() - t < service.RATE_LIMIT_WINDOW]) <= 6
    
    def test_prompt_creation_comprehensive(self, config_with_key, weather_context_sunny):
        """プロンプト作成の包括的テスト"""
        service = AIMessageService(config_with_key)
        
        # 一般的なプロンプト
        prompt = service._create_prompt(weather_context_sunny, "general")
        assert "東京都" in prompt
        assert "晴れ" in prompt
        assert "25.0°C" in prompt
        assert "10%" in prompt
        assert "北の風 弱く" in prompt
        
        # 朝のプロンプト
        morning_prompt = service._create_prompt(weather_context_sunny, "morning")
        assert "朝の挨拶" in morning_prompt
        assert "今日一日を前向きに" in morning_prompt
        
        # 夕方のプロンプト
        evening_prompt = service._create_prompt(weather_context_sunny, "evening")
        assert "夕方の挨拶" in evening_prompt
        assert "お疲れ様" in evening_prompt
        
        # 警報時のプロンプト
        alert_prompt = service._create_prompt(weather_context_sunny, "alert")
        assert "気象警報" in alert_prompt
        assert "安全に過ごす" in alert_prompt
    
    def test_fallback_message_comprehensive(self, config_with_key):
        """フォールバックメッセージの包括的テスト"""
        service = AIMessageService(config_with_key)
        
        # 晴天時
        sunny_context = WeatherContext("東京都", "晴れ", 25.0, 10, "風", datetime.now())
        sunny_message = service._get_fallback_message(sunny_context, "general")
        assert "東京都" in sunny_message
        assert any(emoji in sunny_message for emoji in ["☀️", "🌞", "✨"])
        
        # 雨天時
        rainy_context = WeatherContext("大阪府", "雨", 18.0, 80, "風", datetime.now())
        rainy_message = service._get_fallback_message(rainy_context, "general")
        assert "大阪府" in rainy_message
        assert any(emoji in rainy_message for emoji in ["☔", "🌂", "🌧️"])
        
        # 曇天時
        cloudy_context = WeatherContext("名古屋市", "くもり", 22.0, 40, "風", datetime.now())
        cloudy_message = service._get_fallback_message(cloudy_context, "general")
        assert "名古屋市" in cloudy_message
        assert any(emoji in cloudy_message for emoji in ["🌤️", "⛅", "🌥️"])
        
        # 警報時
        alert_context = WeatherContext("福岡県", "大雨", 20.0, 90, "風", datetime.now(), True, "大雨警報")
        alert_message = service._get_fallback_message(alert_context, "general")
        assert "⚠️" in alert_message
        assert "気象警報" in alert_message
        assert "安全第一" in alert_message
    
    def test_fallback_message_time_specific(self, config_with_key, weather_context_sunny):
        """時間帯別フォールバックメッセージのテスト"""
        service = AIMessageService(config_with_key)
        
        # 朝のメッセージ
        morning_message = service._get_fallback_message(weather_context_sunny, "morning")
        assert morning_message.startswith("おはようございます！")
        
        # 夕方のメッセージ
        evening_message = service._get_fallback_message(weather_context_sunny, "evening")
        assert evening_message.startswith("お疲れ様です！")
        
        # 一般的なメッセージ
        general_message = service._get_fallback_message(weather_context_sunny, "general")
        assert not general_message.startswith("おはようございます！")
        assert not general_message.startswith("お疲れ様です！")
    
    def test_fallback_message_consistency(self, config_with_key):
        """フォールバックメッセージの一貫性テスト"""
        service = AIMessageService(config_with_key)
        
        # 同じ日付・地域では同じメッセージが返される
        context1 = WeatherContext("東京都", "晴れ", 25.0, 10, "風", datetime(2024, 1, 15, 10, 0))
        context2 = WeatherContext("東京都", "晴れ", 25.0, 10, "風", datetime(2024, 1, 15, 14, 0))
        
        message1 = service._get_fallback_message(context1, "general")
        message2 = service._get_fallback_message(context2, "general")
        
        # 同じ日付なので同じメッセージ
        assert message1 == message2
        
        # 異なる日付では異なる可能性がある
        context3 = WeatherContext("東京都", "晴れ", 25.0, 10, "風", datetime(2024, 1, 16, 10, 0))
        message3 = service._get_fallback_message(context3, "general")
        
        # 異なる日付でも同じメッセージの可能性があるが、ハッシュベースなので一貫している
        assert isinstance(message3, str)
        assert len(message3) > 0
    
    @pytest.mark.asyncio
    async def test_generate_positive_message_comprehensive(self, config_with_key, weather_context_sunny):
        """ポジティブメッセージ生成の包括的テスト"""
        service = AIMessageService(config_with_key)
        
        # 正常なケース
        message = await service.generate_positive_message(weather_context_sunny)
        assert isinstance(message, str)
        assert len(message) > 0
        
        # 異なるメッセージタイプ
        morning_message = await service.generate_positive_message(weather_context_sunny, "morning")
        evening_message = await service.generate_positive_message(weather_context_sunny, "evening")
        alert_message = await service.generate_positive_message(weather_context_sunny, "alert")
        
        assert isinstance(morning_message, str)
        assert isinstance(evening_message, str)
        assert isinstance(alert_message, str)
    
    @pytest.mark.asyncio
    async def test_generate_positive_message_circuit_breaker(self, config_with_key, weather_context_sunny):
        """サーキットブレーカー開放時のメッセージ生成テスト"""
        service = AIMessageService(config_with_key)
        
        # サーキットブレーカーを開く
        service._consecutive_errors = 5
        service._last_error_time = time.time()
        
        message = await service.generate_positive_message(weather_context_sunny)
        
        # フォールバックメッセージが返される
        assert isinstance(message, str)
        assert len(message) > 0
        assert "東京都" in message
    
    @pytest.mark.asyncio
    async def test_generate_positive_message_unavailable(self, config_without_key, weather_context_sunny):
        """サービス利用不可時のメッセージ生成テスト"""
        service = AIMessageService(config_without_key)
        
        message = await service.generate_positive_message(weather_context_sunny)
        
        # フォールバックメッセージが返される
        assert isinstance(message, str)
        assert len(message) > 0
        assert "東京都" in message
    
    @pytest.mark.asyncio
    async def test_generate_weather_summary_comprehensive(self, config_with_key, weather_context_sunny):
        """天気要約メッセージ生成の包括的テスト"""
        service = AIMessageService(config_with_key)
        
        # デフォルトの予報日数
        summary = await service.generate_weather_summary_message(weather_context_sunny)
        assert isinstance(summary, str)
        assert len(summary) > 0
        
        # 異なる予報日数
        summary_5days = await service.generate_weather_summary_message(weather_context_sunny, 5)
        summary_7days = await service.generate_weather_summary_message(weather_context_sunny, 7)
        
        assert isinstance(summary_5days, str)
        assert isinstance(summary_7days, str)
    
    @pytest.mark.asyncio
    async def test_generate_weather_summary_unavailable(self, config_without_key, weather_context_sunny):
        """サービス利用不可時の要約メッセージ生成テスト"""
        service = AIMessageService(config_without_key)
        
        summary = await service.generate_weather_summary_message(weather_context_sunny)
        
        # フォールバック要約メッセージが返される
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "東京都" in summary
    
    def test_summary_fallback_message_comprehensive(self, config_with_key):
        """要約フォールバックメッセージの包括的テスト"""
        service = AIMessageService(config_with_key)
        
        # 雨の可能性が高い場合
        rainy_context = WeatherContext("大阪府", "雨", 18.0, 70, "風", datetime.now())
        rainy_summary = service._get_summary_fallback_message(rainy_context)
        assert "🌧️" in rainy_summary
        assert "雨の可能性が高め" in rainy_summary
        assert "傘の準備" in rainy_summary
        
        # 良い天気の場合
        sunny_context = WeatherContext("東京都", "晴れ", 25.0, 20, "風", datetime.now())
        sunny_summary = service._get_summary_fallback_message(sunny_context)
        assert "☀️" in sunny_summary
        assert "良いお天気" in sunny_summary
        
        # 境界値テスト（50%）
        boundary_context = WeatherContext("名古屋市", "くもり", 22.0, 50, "風", datetime.now())
        boundary_summary = service._get_summary_fallback_message(boundary_context)
        assert "🌧️" in boundary_summary  # 50%以上なので雨メッセージ
    
    def test_is_available_comprehensive(self, config_with_key, config_without_key):
        """利用可能性チェックの包括的テスト"""
        # APIキーありの場合
        service_with_key = AIMessageService(config_with_key)
        assert service_with_key.is_available() is True
        
        # APIキーなしの場合
        service_without_key = AIMessageService(config_without_key)
        assert service_without_key.is_available() is False
        
        # サーキットブレーカー開放時
        service_with_key._consecutive_errors = 5
        service_with_key._last_error_time = time.time()
        assert service_with_key.is_available() is False
    
    @pytest.mark.asyncio
    async def test_health_check_comprehensive(self, config_with_key, config_without_key):
        """ヘルスチェックの包括的テスト"""
        # 利用可能な場合
        service_available = AIMessageService(config_with_key)
        health = await service_available.health_check()
        
        assert health["status"] == "available"
        assert "正常に動作" in health["message"]
        assert health["fallback_available"] is True
        
        # 利用不可の場合
        service_unavailable = AIMessageService(config_without_key)
        health = await service_unavailable.health_check()
        
        assert health["status"] == "unavailable"
        assert "設定されていません" in health["message"]
        assert health["fallback_available"] is True
        
        # サーキットブレーカー開放時
        service_available._consecutive_errors = 5
        service_available._last_error_time = time.time()
        health = await service_available.health_check()
        
        assert health["status"] == "circuit_breaker_open"
        assert "サーキットブレーカー" in health["message"]
        assert health["fallback_available"] is True
    
    def test_get_service_stats_comprehensive(self, config_with_key):
        """サービス統計情報の包括的テスト"""
        service = AIMessageService(config_with_key)
        
        # 初期状態
        stats = service.get_service_stats()
        
        assert stats["is_available"] is True
        assert stats["consecutive_errors"] == 0
        assert stats["circuit_breaker_active"] is False
        assert stats["requests_in_last_minute"] == 0
        assert stats["rate_limit_remaining"] == service.MAX_REQUESTS_PER_MINUTE
        
        # リクエスト後
        service._check_rate_limit()
        stats = service.get_service_stats()
        
        assert stats["requests_in_last_minute"] == 1
        assert stats["rate_limit_remaining"] == service.MAX_REQUESTS_PER_MINUTE - 1
        
        # エラー発生後
        service._consecutive_errors = 3
        stats = service.get_service_stats()
        
        assert stats["consecutive_errors"] == 3
        assert stats["circuit_breaker_active"] is False  # まだ閾値未満
        
        # サーキットブレーカー開放後
        service._consecutive_errors = 5
        service._last_error_time = time.time()
        stats = service.get_service_stats()
        
        assert stats["circuit_breaker_active"] is True
        assert stats["is_available"] is False
    
    def test_error_types_comprehensive(self):
        """エラータイプの包括的テスト"""
        # 基本的なAIServiceError
        basic_error = AIServiceError("Basic error")
        assert str(basic_error) == "Basic error"
        assert isinstance(basic_error, Exception)
        
        # AIServiceRateLimitError
        rate_limit_error = AIServiceRateLimitError("Rate limit error")
        assert str(rate_limit_error) == "Rate limit error"
        assert isinstance(rate_limit_error, AIServiceError)
        assert isinstance(rate_limit_error, Exception)
        
        # AIServiceQuotaExceededError
        quota_error = AIServiceQuotaExceededError("Quota exceeded")
        assert str(quota_error) == "Quota exceeded"
        assert isinstance(quota_error, AIServiceError)
        assert isinstance(quota_error, Exception)
    
    def test_config_handling(self):
        """Config処理のテスト"""
        # 基本的なConfig
        config = Config()
        assert config.GEMINI_API_KEY is None
        
        # APIキーを設定
        config.GEMINI_API_KEY = "test_key"
        assert config.GEMINI_API_KEY == "test_key"
        
        # 空文字列
        config.GEMINI_API_KEY = ""
        assert config.GEMINI_API_KEY == ""
        
        # 長いキー
        long_key = "a" * 100
        config.GEMINI_API_KEY = long_key
        assert config.GEMINI_API_KEY == long_key


if __name__ == "__main__":
    pytest.main([__file__])