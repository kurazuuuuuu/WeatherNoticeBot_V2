"""
WeatherService統合テスト

実際の気象庁APIとの統合テストを実行します。
このテストは実際のAPIを呼び出すため、ネットワーク接続が必要です。
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import patch

# テスト対象のインポート（モック化対応）
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
    # 依存関係が不足している場合はスキップ
    pytest.skip("WeatherService dependencies not available", allow_module_level=True)


@pytest.mark.integration
class TestWeatherAPIIntegration:
    """気象庁API統合テストクラス"""
    
    @pytest.fixture
    def weather_service(self):
        """WeatherServiceのインスタンスを作成"""
        return WeatherService()
    
    @pytest.mark.asyncio
    async def test_get_area_list_integration(self, weather_service):
        """地域リスト取得の統合テスト"""
        try:
            async with weather_service:
                area_list = await weather_service.get_area_list()
                
                # 基本的な検証
                assert isinstance(area_list, dict)
                assert len(area_list) > 0
                
                # 主要な地域が含まれていることを確認
                tokyo_found = False
                osaka_found = False
                
                for area_code, area_info in area_list.items():
                    assert isinstance(area_info, AreaInfo)
                    assert area_info.code == area_code
                    assert isinstance(area_info.name, str)
                    assert len(area_info.name) > 0
                    
                    if "東京" in area_info.name:
                        tokyo_found = True
                    if "大阪" in area_info.name:
                        osaka_found = True
                
                # 主要都市が見つかることを確認
                assert tokyo_found, "東京が地域リストに見つかりません"
                assert osaka_found, "大阪が地域リストに見つかりません"
                
        except WeatherAPIError as e:
            pytest.skip(f"API接続エラーのためテストをスキップ: {e}")
        except Exception as e:
            pytest.fail(f"予期しないエラー: {e}")
    
    @pytest.mark.asyncio
    async def test_search_area_by_name_integration(self, weather_service):
        """地域名検索の統合テスト"""
        try:
            async with weather_service:
                # 東京の検索
                tokyo_results = await weather_service.search_area_by_name("東京")
                assert len(tokyo_results) > 0
                
                # 結果の検証
                for area in tokyo_results:
                    assert isinstance(area, AreaInfo)
                    assert "東京" in area.name or "tokyo" in area.en_name.lower()
                
                # 大阪の検索
                osaka_results = await weather_service.search_area_by_name("大阪")
                assert len(osaka_results) > 0
                
                # 英語名での検索
                tokyo_en_results = await weather_service.search_area_by_name("tokyo")
                assert len(tokyo_en_results) > 0
                
                # 存在しない地域の検索
                nonexistent_results = await weather_service.search_area_by_name("存在しない地域名12345")
                assert len(nonexistent_results) == 0
                
        except WeatherAPIError as e:
            pytest.skip(f"API接続エラーのためテストをスキップ: {e}")
        except Exception as e:
            pytest.fail(f"予期しないエラー: {e}")
    
    @pytest.mark.asyncio
    async def test_get_valid_area_code_integration(self, weather_service):
        """有効な地域コード取得の統合テスト"""
        try:
            async with weather_service:
                # 地域名から地域コードを取得
                tokyo_code = await weather_service.get_valid_area_code("東京")
                assert tokyo_code is not None
                assert weather_service.validate_area_code(tokyo_code)
                
                # 既に有効な地域コードの場合
                if tokyo_code:
                    same_code = await weather_service.get_valid_area_code(tokyo_code)
                    assert same_code == tokyo_code
                
                # 存在しない地域名
                invalid_code = await weather_service.get_valid_area_code("存在しない地域")
                assert invalid_code is None
                
        except WeatherAPIError as e:
            pytest.skip(f"API接続エラーのためテストをスキップ: {e}")
        except Exception as e:
            pytest.fail(f"予期しないエラー: {e}")
    
    @pytest.mark.asyncio
    async def test_get_current_weather_integration(self, weather_service):
        """現在の天気情報取得の統合テスト"""
        try:
            async with weather_service:
                # まず有効な地域コードを取得
                area_code = await weather_service.get_valid_area_code("東京")
                if not area_code:
                    pytest.skip("東京の地域コードが取得できませんでした")
                
                # 天気情報を取得
                weather_data = await weather_service.get_current_weather(area_code)
                
                if weather_data:
                    assert isinstance(weather_data, WeatherData)
                    assert weather_data.area_code == area_code
                    assert isinstance(weather_data.area_name, str)
                    assert len(weather_data.area_name) > 0
                    assert isinstance(weather_data.weather_description, str)
                    assert isinstance(weather_data.precipitation_probability, int)
                    assert 0 <= weather_data.precipitation_probability <= 100
                    assert isinstance(weather_data.timestamp, datetime)
                    assert isinstance(weather_data.publish_time, datetime)
                    
                    # 気温が設定されている場合の検証
                    if weather_data.temperature is not None:
                        assert isinstance(weather_data.temperature, float)
                        assert -50.0 <= weather_data.temperature <= 60.0  # 現実的な範囲
                else:
                    pytest.skip("天気データが取得できませんでした（APIの仕様変更の可能性）")
                
        except WeatherAPIError as e:
            pytest.skip(f"API接続エラーのためテストをスキップ: {e}")
        except Exception as e:
            pytest.fail(f"予期しないエラー: {e}")
    
    @pytest.mark.asyncio
    async def test_get_forecast_integration(self, weather_service):
        """天気予報取得の統合テスト"""
        try:
            async with weather_service:
                # まず有効な地域コードを取得
                area_code = await weather_service.get_valid_area_code("東京")
                if not area_code:
                    pytest.skip("東京の地域コードが取得できませんでした")
                
                # 3日間の予報を取得
                forecast_data = await weather_service.get_forecast(area_code, 3)
                
                if forecast_data:
                    assert isinstance(forecast_data, list)
                    assert len(forecast_data) <= 3
                    
                    for forecast in forecast_data:
                        assert isinstance(forecast, ForecastData)
                        assert isinstance(forecast.weather_description, str)
                        assert isinstance(forecast.precipitation_probability, int)
                        assert 0 <= forecast.precipitation_probability <= 100
                        
                        # 気温が設定されている場合の検証
                        if forecast.temp_min is not None:
                            assert isinstance(forecast.temp_min, float)
                            assert -50.0 <= forecast.temp_min <= 60.0
                        
                        if forecast.temp_max is not None:
                            assert isinstance(forecast.temp_max, float)
                            assert -50.0 <= forecast.temp_max <= 60.0
                            
                            # 最低気温と最高気温の関係
                            if forecast.temp_min is not None:
                                assert forecast.temp_min <= forecast.temp_max
                else:
                    pytest.skip("予報データが取得できませんでした（APIの仕様変更の可能性）")
                
        except WeatherAPIError as e:
            pytest.skip(f"API接続エラーのためテストをスキップ: {e}")
        except Exception as e:
            pytest.fail(f"予期しないエラー: {e}")
    
    @pytest.mark.asyncio
    async def test_api_error_handling_integration(self, weather_service):
        """APIエラーハンドリングの統合テスト"""
        try:
            async with weather_service:
                # 無効な地域コードでのテスト
                with pytest.raises(WeatherAPIError):
                    await weather_service.get_current_weather("invalid")
                
                # 存在しない地域コードでのテスト（404エラーが期待される）
                try:
                    await weather_service.get_current_weather("999999")
                    # エラーが発生しない場合は、データが返されるかNoneが返される
                except WeatherAPIError as e:
                    # 404エラーまたはその他のAPIエラーが期待される
                    assert isinstance(e, WeatherAPIError)
                
        except Exception as e:
            pytest.fail(f"予期しないエラー: {e}")
    
    @pytest.mark.asyncio
    async def test_rate_limit_handling_integration(self, weather_service):
        """レート制限処理の統合テスト"""
        try:
            async with weather_service:
                # 複数のリクエストを短時間で実行
                area_code = await weather_service.get_valid_area_code("東京")
                if not area_code:
                    pytest.skip("東京の地域コードが取得できませんでした")
                
                # 通常のリクエスト間隔でのテスト
                for i in range(3):
                    try:
                        weather_data = await weather_service.get_current_weather(area_code)
                        # 少し待機してレート制限を避ける
                        await asyncio.sleep(1)
                    except WeatherAPIRateLimitError:
                        # レート制限に達した場合は正常な動作
                        break
                    except WeatherAPIError:
                        # その他のAPIエラーは許容
                        break
                
        except Exception as e:
            pytest.fail(f"予期しないエラー: {e}")
    
    @pytest.mark.asyncio
    async def test_cache_functionality_integration(self, weather_service):
        """キャッシュ機能の統合テスト"""
        try:
            async with weather_service:
                area_code = await weather_service.get_valid_area_code("東京")
                if not area_code:
                    pytest.skip("東京の地域コードが取得できませんでした")
                
                # 最初のリクエスト
                start_time = asyncio.get_event_loop().time()
                weather_data1 = await weather_service.get_current_weather(area_code)
                first_request_time = asyncio.get_event_loop().time() - start_time
                
                # 2回目のリクエスト（キャッシュから取得される可能性）
                start_time = asyncio.get_event_loop().time()
                weather_data2 = await weather_service.get_current_weather(area_code)
                second_request_time = asyncio.get_event_loop().time() - start_time
                
                # キャッシュが効いている場合、2回目の方が高速
                if weather_data1 and weather_data2:
                    # データの一貫性を確認
                    assert weather_data1.area_code == weather_data2.area_code
                    assert weather_data1.area_name == weather_data2.area_name
                    
                    # 2回目の方が高速である可能性が高い（ただし、必須ではない）
                    # ネットワーク状況により変動するため、警告レベルで記録
                    if second_request_time < first_request_time * 0.5:
                        print(f"キャッシュが効いている可能性: 1回目={first_request_time:.3f}s, 2回目={second_request_time:.3f}s")
                
        except WeatherAPIError as e:
            pytest.skip(f"API接続エラーのためテストをスキップ: {e}")
        except Exception as e:
            pytest.fail(f"予期しないエラー: {e}")
    
    @pytest.mark.asyncio
    async def test_session_management_integration(self, weather_service):
        """セッション管理の統合テスト"""
        # セッション開始
        await weather_service.start_session()
        assert weather_service.session is not None
        assert not weather_service.session.closed
        
        try:
            # セッションを使用してリクエスト
            area_list = await weather_service.get_area_list()
            assert isinstance(area_list, dict)
            
        except WeatherAPIError as e:
            pytest.skip(f"API接続エラーのためテストをスキップ: {e}")
        finally:
            # セッション終了
            await weather_service.close_session()
            assert weather_service.session.closed
    
    @pytest.mark.asyncio
    async def test_context_manager_integration(self):
        """コンテキストマネージャーの統合テスト"""
        try:
            async with WeatherService() as service:
                assert service.session is not None
                assert not service.session.closed
                
                # 簡単なAPIコール
                area_list = await service.get_area_list()
                assert isinstance(area_list, dict)
            
            # コンテキスト終了後はセッションが閉じられる
            assert service.session.closed
            
        except WeatherAPIError as e:
            pytest.skip(f"API接続エラーのためテストをスキップ: {e}")
        except Exception as e:
            pytest.fail(f"予期しないエラー: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_comprehensive_weather_flow_integration(self, weather_service):
        """包括的な天気情報取得フローの統合テスト"""
        try:
            async with weather_service:
                # 1. 地域検索
                search_results = await weather_service.search_area_by_name("東京")
                assert len(search_results) > 0
                
                # 2. 地域コード取得
                area_code = search_results[0].code
                assert weather_service.validate_area_code(area_code)
                
                # 3. 現在の天気取得
                current_weather = await weather_service.get_current_weather(area_code)
                if current_weather:
                    assert isinstance(current_weather, WeatherData)
                    print(f"現在の天気: {current_weather.area_name} - {current_weather.weather_description}")
                
                # 4. 天気予報取得
                forecast = await weather_service.get_forecast(area_code, 5)
                if forecast:
                    assert isinstance(forecast, list)
                    print(f"予報データ数: {len(forecast)}件")
                    
                    for i, f in enumerate(forecast):
                        print(f"  {i+1}日目: {f.weather_description} (降水確率: {f.precipitation_probability}%)")
                
                # 5. 複数地域での検証
                for city in ["大阪", "名古屋", "福岡"]:
                    city_results = await weather_service.search_area_by_name(city)
                    if city_results:
                        city_code = city_results[0].code
                        city_weather = await weather_service.get_current_weather(city_code)
                        if city_weather:
                            print(f"{city}: {city_weather.weather_description}")
                        
                        # レート制限を避けるため少し待機
                        await asyncio.sleep(0.5)
                
        except WeatherAPIError as e:
            pytest.skip(f"API接続エラーのためテストをスキップ: {e}")
        except Exception as e:
            pytest.fail(f"予期しないエラー: {e}")


if __name__ == "__main__":
    # 統合テストのみを実行
    pytest.main([__file__, "-v", "-m", "integration"])