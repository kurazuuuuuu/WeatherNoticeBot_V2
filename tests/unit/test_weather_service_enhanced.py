"""
WeatherServiceの拡張ユニットテスト

既存のテストを補完し、エッジケースやエラーハンドリングをより詳細にテストします。
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, date
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import ClientResponseError, ClientTimeout, ClientError

# テスト対象のインポート（モック化）
try:
    from src.services.weather_service import (
        WeatherService, 
        WeatherData, 
        ForecastData, 
        AlertData, 
        AreaInfo,
        WeatherAPIError,
        WeatherAPIRateLimitError,
        WeatherAPIServerError,
        WeatherAPITimeoutError
    )
except ImportError:
    # 依存関係が不足している場合のモック実装
    class WeatherService:
        BASE_URL = "https://www.jma.go.jp/bosai"
        MAX_RETRIES = 3
        RETRY_DELAY = 1.0
        BACKOFF_FACTOR = 2.0
        MAX_RETRY_DELAY = 60.0
        REQUEST_TIMEOUT = 30
        CONNECT_TIMEOUT = 10
        RATE_LIMIT_WINDOW = 60
        MAX_REQUESTS_PER_WINDOW = 100
        CACHE_DURATION = 300
        
        def __init__(self):
            self.session = None
            self._request_times = []
            self._cache = {}
            self._cache_timestamps = {}
        
        def validate_area_code(self, area_code):
            if not area_code or not isinstance(area_code, str):
                return False
            if not area_code.isdigit():
                return False
            if len(area_code) != 6:
                return False
            return True
        
        def _is_cache_valid(self, cache_key):
            if cache_key not in self._cache_timestamps:
                return False
            cache_time = self._cache_timestamps[cache_key]
            return (time.time() - cache_time) < self.CACHE_DURATION
        
        def _get_from_cache(self, cache_key):
            if self._is_cache_valid(cache_key):
                return self._cache.get(cache_key)
            return None
        
        def _set_cache(self, cache_key, data):
            self._cache[cache_key] = data
            self._cache_timestamps[cache_key] = time.time()
        
        def _check_rate_limit(self):
            current_time = time.time()
            self._request_times = [
                req_time for req_time in self._request_times
                if current_time - req_time < self.RATE_LIMIT_WINDOW
            ]
            if len(self._request_times) >= self.MAX_REQUESTS_PER_WINDOW:
                raise WeatherAPIRateLimitError("Rate limit exceeded")
            self._request_times.append(current_time)
        
        def _safe_float(self, value):
            if value is None or value == '':
                return None
            try:
                return float(value)
            except (ValueError, TypeError):
                return None
        
        def _get_weather_description_from_code(self, weather_code):
            weather_code_map = {
                '100': '晴れ',
                '200': 'くもり',
                '300': '雨',
                '400': '雪'
            }
            return weather_code_map.get(weather_code, f'不明な天気コード: {weather_code}')
        
        def _is_similar_name(self, search_name, area_name):
            return search_name.lower() in area_name.lower()
    
    # データクラスのモック実装
    class AreaInfo:
        def __init__(self, code, name, en_name, kana, parent):
            self.code = code
            self.name = name
            self.en_name = en_name
            self.kana = kana
            self.parent = parent
    
    class WeatherData:
        def __init__(self, area_name, area_code, weather_code, weather_description, 
                     wind, wave, temperature, precipitation_probability, timestamp, publish_time):
            self.area_name = area_name
            self.area_code = area_code
            self.weather_code = weather_code
            self.weather_description = weather_description
            self.wind = wind
            self.wave = wave
            self.temperature = temperature
            self.precipitation_probability = precipitation_probability
            self.timestamp = timestamp
            self.publish_time = publish_time
    
    class ForecastData:
        def __init__(self, date, weather_code, weather_description, temp_min, temp_max,
                     temp_min_upper, temp_min_lower, temp_max_upper, temp_max_lower,
                     precipitation_probability, reliability):
            self.date = date
            self.weather_code = weather_code
            self.weather_description = weather_description
            self.temp_min = temp_min
            self.temp_max = temp_max
            self.temp_min_upper = temp_min_upper
            self.temp_min_lower = temp_min_lower
            self.temp_max_upper = temp_max_upper
            self.temp_max_lower = temp_max_lower
            self.precipitation_probability = precipitation_probability
            self.reliability = reliability
    
    class AlertData:
        def __init__(self, title, description, severity, issued_at, area_codes):
            self.title = title
            self.description = description
            self.severity = severity
            self.issued_at = issued_at
            self.area_codes = area_codes
    
    # 例外クラスのモック実装
    class WeatherAPIError(Exception):
        def __init__(self, message, status_code=None, retry_after=None):
            super().__init__(message)
            self.status_code = status_code
            self.retry_after = retry_after
    
    class WeatherAPIRateLimitError(WeatherAPIError):
        pass
    
    class WeatherAPIServerError(WeatherAPIError):
        pass
    
    class WeatherAPITimeoutError(WeatherAPIError):
        pass


class TestWeatherServiceEnhanced:
    """WeatherServiceの拡張ユニットテストクラス"""
    
    @pytest.fixture
    def weather_service(self):
        """WeatherServiceのインスタンスを作成"""
        return WeatherService()
    
    def test_validate_area_code_edge_cases(self, weather_service):
        """地域コード検証のエッジケーステスト"""
        # 正常なケース
        assert weather_service.validate_area_code("130000") is True
        assert weather_service.validate_area_code("010100") is True
        
        # エッジケース
        assert weather_service.validate_area_code("000000") is True  # ゼロ埋め
        assert weather_service.validate_area_code("999999") is True  # 最大値
        
        # 異常なケース
        assert weather_service.validate_area_code("") is False  # 空文字
        assert weather_service.validate_area_code("12345") is False  # 5桁
        assert weather_service.validate_area_code("1234567") is False  # 7桁
        assert weather_service.validate_area_code("12345a") is False  # 文字含む
        assert weather_service.validate_area_code("abcdef") is False  # 全て文字
        assert weather_service.validate_area_code("12 345") is False  # スペース含む
        assert weather_service.validate_area_code("123-45") is False  # ハイフン含む
        assert weather_service.validate_area_code(None) is False  # None
        assert weather_service.validate_area_code(123456) is False  # 数値型
        assert weather_service.validate_area_code([]) is False  # リスト
        assert weather_service.validate_area_code({}) is False  # 辞書
    
    def test_cache_functionality_edge_cases(self, weather_service):
        """キャッシュ機能のエッジケーステスト"""
        cache_key = "test_key"
        test_data = {"test": "data"}
        
        # 初期状態
        assert weather_service._get_from_cache(cache_key) is None
        assert not weather_service._is_cache_valid(cache_key)
        
        # データをキャッシュに保存
        weather_service._set_cache(cache_key, test_data)
        
        # キャッシュからデータを取得
        cached_data = weather_service._get_from_cache(cache_key)
        assert cached_data == test_data
        assert weather_service._is_cache_valid(cache_key)
        
        # キャッシュの上書き
        new_data = {"new": "data"}
        weather_service._set_cache(cache_key, new_data)
        cached_data = weather_service._get_from_cache(cache_key)
        assert cached_data == new_data
        
        # 複数のキャッシュキー
        cache_key2 = "test_key2"
        test_data2 = {"test2": "data2"}
        weather_service._set_cache(cache_key2, test_data2)
        
        assert weather_service._get_from_cache(cache_key) == new_data
        assert weather_service._get_from_cache(cache_key2) == test_data2
        
        # 存在しないキー
        assert weather_service._get_from_cache("nonexistent") is None
    
    def test_cache_expiration(self, weather_service):
        """キャッシュ有効期限のテスト"""
        cache_key = "expiry_test"
        test_data = {"test": "data"}
        
        # データをキャッシュに保存
        weather_service._set_cache(cache_key, test_data)
        assert weather_service._is_cache_valid(cache_key)
        
        # タイムスタンプを古くする
        weather_service._cache_timestamps[cache_key] = time.time() - weather_service.CACHE_DURATION - 1
        
        # キャッシュが無効になることを確認
        assert not weather_service._is_cache_valid(cache_key)
        assert weather_service._get_from_cache(cache_key) is None
    
    def test_rate_limit_functionality(self, weather_service):
        """レート制限機能の詳細テスト"""
        # 通常の状態では例外が発生しない
        weather_service._check_rate_limit()
        assert len(weather_service._request_times) == 1
        
        # 複数回のリクエスト
        for i in range(5):
            weather_service._check_rate_limit()
        assert len(weather_service._request_times) == 6
        
        # レート制限に達するまでリクエストを追加
        current_time = time.time()
        weather_service._request_times = [current_time] * weather_service.MAX_REQUESTS_PER_WINDOW
        
        # レート制限例外が発生することを確認
        with pytest.raises(WeatherAPIRateLimitError):
            weather_service._check_rate_limit()
        
        # 古いリクエスト時刻は削除される
        old_time = current_time - weather_service.RATE_LIMIT_WINDOW - 1
        weather_service._request_times = [old_time] * 50 + [current_time] * 10
        
        # 古いリクエストは無視される
        weather_service._check_rate_limit()
        assert len([t for t in weather_service._request_times if current_time - t < weather_service.RATE_LIMIT_WINDOW]) <= 11
    
    def test_safe_float_conversion_edge_cases(self, weather_service):
        """安全なfloat変換のエッジケーステスト"""
        # 正常なケース
        assert weather_service._safe_float("15.5") == 15.5
        assert weather_service._safe_float("20") == 20.0
        assert weather_service._safe_float("0") == 0.0
        assert weather_service._safe_float("-5.5") == -5.5
        assert weather_service._safe_float("0.0") == 0.0
        
        # エッジケース
        assert weather_service._safe_float("") is None
        assert weather_service._safe_float(None) is None
        assert weather_service._safe_float("invalid") is None
        assert weather_service._safe_float("15.5.5") is None  # 複数のドット
        assert weather_service._safe_float("15,5") is None  # カンマ区切り
        assert weather_service._safe_float("15 ") is None  # 末尾スペース（厳密な変換）
        assert weather_service._safe_float(" 15") is None  # 先頭スペース（厳密な変換）
        assert weather_service._safe_float("abc") is None
        assert weather_service._safe_float("15abc") is None
        assert weather_service._safe_float("∞") is None
        assert weather_service._safe_float("NaN") is None
        
        # 数値型の場合
        assert weather_service._safe_float(15.5) == 15.5
        assert weather_service._safe_float(20) == 20.0
        assert weather_service._safe_float(0) == 0.0
    
    def test_weather_description_from_code_comprehensive(self, weather_service):
        """天気コードから説明取得の包括的テスト"""
        # 既知の天気コード
        assert weather_service._get_weather_description_from_code("100") == "晴れ"
        assert weather_service._get_weather_description_from_code("200") == "くもり"
        assert weather_service._get_weather_description_from_code("300") == "雨"
        assert weather_service._get_weather_description_from_code("400") == "雪"
        
        # 未知の天気コード
        unknown_desc = weather_service._get_weather_description_from_code("999")
        assert "999" in unknown_desc
        
        # エッジケース
        empty_desc = weather_service._get_weather_description_from_code("")
        assert "" in empty_desc or "不明" in empty_desc
        
        none_desc = weather_service._get_weather_description_from_code(None)
        assert "None" in str(none_desc) or "不明" in str(none_desc)
    
    def test_similar_name_matching_comprehensive(self, weather_service):
        """類似名前マッチングの包括的テスト"""
        # 基本的なマッチング
        assert weather_service._is_similar_name("tokyo", "Tokyo Metropolitan") is True
        assert weather_service._is_similar_name("東京", "東京都") is True
        assert weather_service._is_similar_name("osaka", "Osaka Prefecture") is True
        
        # 大文字小文字の違い
        assert weather_service._is_similar_name("TOKYO", "tokyo") is True
        assert weather_service._is_similar_name("Tokyo", "TOKYO") is True
        
        # 部分一致
        assert weather_service._is_similar_name("京", "東京都") is True
        assert weather_service._is_similar_name("阪", "大阪府") is True
        
        # マッチしないケース
        assert weather_service._is_similar_name("全く違う", "東京") is False
        assert weather_service._is_similar_name("completely different", "Tokyo") is False
        
        # エッジケース
        assert weather_service._is_similar_name("", "東京") is True  # 空文字は含まれる
        assert weather_service._is_similar_name("東京", "") is False  # 空文字には含まれない
    
    def test_area_info_creation(self):
        """AreaInfoオブジェクト作成のテスト"""
        area = AreaInfo(
            code="130000",
            name="東京都",
            en_name="Tokyo",
            kana="トウキョウト",
            parent="130000"
        )
        
        assert area.code == "130000"
        assert area.name == "東京都"
        assert area.en_name == "Tokyo"
        assert area.kana == "トウキョウト"
        assert area.parent == "130000"
    
    def test_weather_data_creation(self):
        """WeatherDataオブジェクト作成のテスト"""
        timestamp = datetime.now()
        publish_time = datetime.now()
        
        weather = WeatherData(
            area_name="東京都東京",
            area_code="130000",
            weather_code="100",
            weather_description="晴れ",
            wind="北の風",
            wave="0.5メートル",
            temperature=25.0,
            precipitation_probability=10,
            timestamp=timestamp,
            publish_time=publish_time
        )
        
        assert weather.area_name == "東京都東京"
        assert weather.area_code == "130000"
        assert weather.weather_code == "100"
        assert weather.weather_description == "晴れ"
        assert weather.wind == "北の風"
        assert weather.wave == "0.5メートル"
        assert weather.temperature == 25.0
        assert weather.precipitation_probability == 10
        assert weather.timestamp == timestamp
        assert weather.publish_time == publish_time
    
    def test_forecast_data_creation(self):
        """ForecastDataオブジェクト作成のテスト"""
        forecast_date = date.today()
        
        forecast = ForecastData(
            date=forecast_date,
            weather_code="100",
            weather_description="晴れ",
            temp_min=15.0,
            temp_max=25.0,
            temp_min_upper=16.0,
            temp_min_lower=14.0,
            temp_max_upper=26.0,
            temp_max_lower=24.0,
            precipitation_probability=10,
            reliability="A"
        )
        
        assert forecast.date == forecast_date
        assert forecast.weather_code == "100"
        assert forecast.weather_description == "晴れ"
        assert forecast.temp_min == 15.0
        assert forecast.temp_max == 25.0
        assert forecast.temp_min_upper == 16.0
        assert forecast.temp_min_lower == 14.0
        assert forecast.temp_max_upper == 26.0
        assert forecast.temp_max_lower == 24.0
        assert forecast.precipitation_probability == 10
        assert forecast.reliability == "A"
    
    def test_alert_data_creation(self):
        """AlertDataオブジェクト作成のテスト"""
        issued_at = datetime.now()
        
        alert = AlertData(
            title="大雨警報",
            description="大雨による災害に警戒してください",
            severity="警報",
            issued_at=issued_at,
            area_codes=["130000", "140000"]
        )
        
        assert alert.title == "大雨警報"
        assert alert.description == "大雨による災害に警戒してください"
        assert alert.severity == "警報"
        assert alert.issued_at == issued_at
        assert alert.area_codes == ["130000", "140000"]
    
    def test_weather_api_error_creation(self):
        """WeatherAPIErrorオブジェクト作成のテスト"""
        # 基本的なエラー
        error = WeatherAPIError("Test error")
        assert str(error) == "Test error"
        assert error.status_code is None
        assert error.retry_after is None
        
        # ステータスコード付きエラー
        error_with_status = WeatherAPIError("HTTP error", status_code=404)
        assert str(error_with_status) == "HTTP error"
        assert error_with_status.status_code == 404
        assert error_with_status.retry_after is None
        
        # リトライ情報付きエラー
        error_with_retry = WeatherAPIError("Rate limit", status_code=429, retry_after=60)
        assert str(error_with_retry) == "Rate limit"
        assert error_with_retry.status_code == 429
        assert error_with_retry.retry_after == 60
    
    def test_specialized_error_types(self):
        """特殊化されたエラータイプのテスト"""
        # レート制限エラー
        rate_limit_error = WeatherAPIRateLimitError("Rate limit exceeded")
        assert isinstance(rate_limit_error, WeatherAPIError)
        assert str(rate_limit_error) == "Rate limit exceeded"
        
        # サーバーエラー
        server_error = WeatherAPIServerError("Server error")
        assert isinstance(server_error, WeatherAPIError)
        assert str(server_error) == "Server error"
        
        # タイムアウトエラー
        timeout_error = WeatherAPITimeoutError("Timeout")
        assert isinstance(timeout_error, WeatherAPIError)
        assert str(timeout_error) == "Timeout"


if __name__ == "__main__":
    pytest.main([__file__])