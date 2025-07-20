#!/usr/bin/env python3
"""
WeatherServiceの天気情報取得機能をテストします
"""

import asyncio
import sys
import os
from datetime import datetime

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.weather_service import WeatherService


async def test_weather_functions():
    """天気情報取得機能をテスト"""
    print("=== WeatherService 天気情報取得機能テスト ===\n")
    
    async with WeatherService() as weather_service:
        try:
            # テスト用の地域コード（東京都）
            test_area_code = "130000"
            
            # 1. 現在の天気情報取得テスト
            print("1. 現在の天気情報取得テスト")
            current_weather = await weather_service.get_current_weather(test_area_code)
            if current_weather:
                print(f"地域: {current_weather.area_name} ({current_weather.area_code})")
                print(f"天気: {current_weather.weather_description}")
                print(f"天気コード: {current_weather.weather_code}")
                print(f"風: {current_weather.wind}")
                print(f"波: {current_weather.wave}")
                print(f"気温: {current_weather.temperature}°C" if current_weather.temperature else "気温: データなし")
                print(f"降水確率: {current_weather.precipitation_probability}%")
                print(f"発表時刻: {current_weather.publish_time}")
                print(f"取得時刻: {current_weather.timestamp}")
            else:
                print("現在の天気情報を取得できませんでした")
            print()
            
            # 2. 天気予報取得テスト
            print("2. 天気予報取得テスト（5日間）")
            forecasts = await weather_service.get_forecast(test_area_code, 5)
            if forecasts:
                for i, forecast in enumerate(forecasts):
                    print(f"  {i+1}日目 ({forecast.date}):")
                    print(f"    天気: {forecast.weather_description}")
                    print(f"    最高気温: {forecast.temp_max}°C" if forecast.temp_max else "    最高気温: データなし")
                    print(f"    最低気温: {forecast.temp_min}°C" if forecast.temp_min else "    最低気温: データなし")
                    print(f"    降水確率: {forecast.precipitation_probability}%")
                    print(f"    信頼度: {forecast.reliability}")
            else:
                print("天気予報を取得できませんでした")
            print()
            
            # 3. 気象警報・注意報取得テスト
            print("3. 気象警報・注意報取得テスト")
            alerts = await weather_service.get_weather_alerts(test_area_code)
            if alerts:
                print(f"警報・注意報: {len(alerts)}件")
                for i, alert in enumerate(alerts):
                    print(f"  {i+1}. {alert.title}")
                    print(f"     内容: {alert.description}")
                    print(f"     重要度: {alert.severity}")
                    print(f"     発表時刻: {alert.issued_at}")
            else:
                print("現在、警報・注意報は発表されていません")
            print()
            
            # 4. 無効な地域コードでのテスト
            print("4. 無効な地域コードでのテスト")
            try:
                invalid_weather = await weather_service.get_current_weather("999999")
                print("無効な地域コードでも結果が返されました（予期しない動作）")
            except Exception as e:
                print(f"期待通りエラーが発生しました: {e}")
            
        except Exception as e:
            print(f"エラーが発生しました: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_weather_functions())